import sys

sys.stdout.reconfigure(line_buffering=True)
import glob
import os
import site

# Ensure CuPy can find PyTorch's cusolver in spawned workers
site_packages = site.getsitepackages()
if site_packages:
    nvidia_libs = glob.glob(os.path.join(site_packages[0], "nvidia", "*", "lib"))
    if nvidia_libs:
        os.environ["LD_LIBRARY_PATH"] = (
            ":".join(nvidia_libs) + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        )

import json
import math
import time
from dataclasses import asdict, dataclass, field

import kimimaro
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from tap import Tap

original_skeletonize = kimimaro.skeletonize


def patched_skeletonize(*args, **kwargs):
    kwargs["parallel"] = 1
    return original_skeletonize(*args, **kwargs)


kimimaro.skeletonize = patched_skeletonize

try:
    import wandb

    original_wandb_log = wandb.log  # type: ignore[attr-defined]

    def safe_wandb_log(*args, **kwargs):
        if wandb.run is not None:  # type: ignore[attr-defined]
            return original_wandb_log(*args, **kwargs)

    wandb.log = safe_wandb_log  # type: ignore[attr-defined]
except ImportError:
    pass

from torch.amp import GradScaler, autocast
from torch.utils.data import DataLoader

from scripts import wandb_tracking
from scripts.betti_loss_module import BettiLoss
from scripts.cldice_loss import SoftClDiceLoss
from scroll_augmentations import apply_scroll_specific_3d_augmentations


# AuxiliaryConfig was previously imported from scripts/auxiliary_manager.py.
# That module held an AuxiliaryManager class which was removed when the broken
# aux-loss path was deleted (commit fa22130). The dataclass is kept inline here
# (with its legacy fields) so existing serialized configs in best_model.pt and
# recent_configs.json continue to deserialize. task_types/weights are now
# unused but harmless.
@dataclass
class AuxiliaryConfig:
    enabled: bool = False
    task_types: list = field(
        default_factory=lambda: ["surface_normals", "structure_tensor"]
    )
    weights: dict = field(
        default_factory=lambda: {"surface_normals": 0.05, "structure_tensor": 0.05}
    )


try:
    sys.path.append(os.path.join(os.path.dirname(__file__), "villa/vesuvius/src"))
    from vesuvius.models.build.primus_wrapper import PrimusEncoder
except ImportError:
    PrimusEncoder = None


@dataclass
class ExperimentConfig:
    # Data
    uri: str = None  # Deprecated, use uris instead
    uris: list = None  # List of URIs to pool for training
    val_uri: str = "local_data/PHercParis2Fr143/surface_volume.zarr"
    cache_dir: str = None  # If None, caches are stored next to volume_uri
    use_ridges: bool = False  # 3D Ridge/Frangi feature channel
    use_lasagna: bool = False  # Priority J: Dynamically apply local surface flattening
    ridge_sigma: float = 2.0  # Ridge filter parameter

    # Training Loop
    batch_size: int = 8
    patch_size: int = 64
    num_layers: int = 24
    lr: float = 1e-3
    weight_decay: float = 0.01
    time_budget: int = 3600
    pinned: bool = False  # If True, autoresearch loop should not evolve this config

    # Loss Weights
    loss_ink_bce: float = 0.4
    loss_ink_dice: float = 0.4
    loss_fiber_bce: float = 0.2
    loss_st: float = 0.1
    label_smoothing: float = 0.0  # Standard for GP winner is 0.25
    use_confidence_weight: bool = False
    checkpoint_out: str | None = None
    eval_every_steps: int = 0
    eval_sample_patches: int = 250
    disable_augmentation: bool = False
    # Default 2026-05-19: switched from "albumentations" to "batchgeneratorsv2" —
    # villa's full augmentation pipeline (Rot90, BlankRectangle, GaussianBlur,
    # GaussianNoise, Sharpening, Contrast, Brightness, etc.). The bandit can
    # still sample "albumentations" via the features tweak axis if it
    # performs better.
    aug_mode: str = "batchgeneratorsv2"

    # Domain Randomization (Sprint 006)
    aug_flip_p: float = 0.5
    aug_brightness_p: float = 0.75
    aug_affine_p: float = 0.75
    aug_coarse_dropout_p: float = 0.5
    aug_elastic_p: float = 0.0
    aug_grid_p: float = 0.0
    aug_rotate_limit: int = 180
    aug_scale_limit: float = 0.15
    aug_scroll_decohesion_p: float = 0.0
    aug_scroll_warping_p: float = 0.0
    aug_scroll_squeeze_p: float = 0.0
    aug_scroll_z_dropout_p: float = 0.0
    aug_scroll_intensity_drift_p: float = 0.0

    # New Villa Augmentations
    aug_scroll_sheet_compression_p: float = 0.0
    aug_scroll_thick_slice_p: float = 0.0
    aug_scroll_rician_noise_p: float = 0.0
    aug_scroll_blank_rectangles_p: float = 0.0

    use_betti_loss: bool = False
    betti_loss_weight: float = 0.1
    use_cldice: bool = False
    cldice_weight: float = 0.1
    cldice_iters: int = 10
    use_wandb: bool = False
    auxiliary_config: AuxiliaryConfig = field(default_factory=AuxiliaryConfig)
    # Target for the auxiliary fiber head. "sobel_z" (default, current
    # behavior): train.py computes Sobel-Z of CT inline on GPU. "frangi":
    # the dataloader computes Frangi vesselness per patch (~86ms CPU,
    # parallelized by num_workers) and passes a z-collapsed [1, 1, H, W]
    # target. The bandit can A/B test these two via the preproc tweak axis.
    target_fiber_source: str = "sobel_z"
    target_fiber_sigma: float = 2.0
    # When True, GenericMultiTaskWrapper (used by resenc_unet) replaces its
    # dummy fiber/qc/st heads with real Conv3d/Linear heads operating on
    # cat(input, backbone_output). Gradients from loss_fiber/loss_qc/loss_st
    # then flow back through the backbone — genuine multi-task supervision.
    # Default off for backward-compat: turning it on changes state_dict
    # shape (3 new submodules) so best_model.pt loads with skipped tensors
    # for the heads, which get randomly initialized.
    multi_task_heads: bool = False

    # Model Architecture
    architecture: str = "gated_unet"
    base_feat: int = 64
    num_blocks: int = 16
    num_heads: int = 8
    dropout: float = 0.0
    pseudo_label_dir: str | None = None
    foundation_model_path: str = (
        None  # Path to pretrained foundation model (e.g. LeJEPA)
    )

    # Prize promotion gates. These keep best_model.pt aligned with villa review
    # signals instead of promoting on Dice alone.
    enforce_prize_gates: bool = True
    min_prize_centerline_dice: float = 0.01
    # skel_dist is reported but NOT gated: it is a symmetric-KL divergence of skeleton
    # branch-LENGTH histograms (villa's 3D fiber/surface track), blind to spatial location
    # and recall and hypersensitive to fragmentation, so it is uncorrelated with
    # ink-detection quality. See FINDINGS.md "Phase 4b" and scripts/probe_skel_dist_validity.py.
    max_prize_skel_dist: float = float("inf")
    max_prize_cc_diff: float = 64.0
    min_prize_topology_samples: int = 1

    # UAMT Semi-Supervised Learning
    use_uamt: bool = False
    ema_decay: float = 0.99
    consistency_weight: float = 0.1
    unlabeled_uris: list = field(
        default_factory=lambda: [
            "local_data/PHercParis2Fr143/surface_volume.zarr",
            "local_data/PHercParis2Fr47/surface_volume.zarr",
        ]
    )

    def __post_init__(self):
        if self.uris is None:
            if self.uri is not None:
                self.uris = [self.uri]
            else:
                self.uris = ["local_data/PHercParis2Fr47/surface_volume.zarr"]
        # Data-leakage guard: filter val_uri out of unlabeled_uris. UA-MT
        # consistency loss on val patches is a contract violation — the
        # model gets to optimize predictions on val distribution before
        # val_bpb is measured. The default unlabeled_uris in this dataclass
        # historically included val_uri (`PHercParis2Fr143/surface_volume.zarr`),
        # which would leak whenever the bandit sampled use_uamt=True. This
        # check silently filters the overlap and prints a one-line notice;
        # it does not modify the on-disk config. See audit notes 2026-05-17.
        if self.val_uri and self.unlabeled_uris:
            cleaned = [u for u in self.unlabeled_uris if u != self.val_uri]
            if len(cleaned) != len(self.unlabeled_uris):
                print(
                    f"Warning: filtering val_uri ({self.val_uri!r}) out of "
                    f"unlabeled_uris to prevent UA-MT data leakage. "
                    f"Was {self.unlabeled_uris}; now {cleaned}.",
                    flush=True,
                )
                self.unlabeled_uris = cleaned

    def save(self, path):
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def load(cls, path):
        with open(path) as f:
            data = json.load(f)

        # Manually deserialize nested dataclasses
        if "auxiliary_config" in data and isinstance(data["auxiliary_config"], dict):
            data["auxiliary_config"] = AuxiliaryConfig(**data["auxiliary_config"])

        return cls(**data)


sys.path.append(os.path.abspath("villa/segmentation/evaluation"))
try:
    from metrics.dice import compute as compute_official_dice
except ImportError:
    # Fallback if module is missing during test environments.
    def compute_official_dice(label, prediction, threshold=0.5):
        prediction_bin = (prediction >= threshold).float()
        intersection = torch.sum(label.float() * prediction_bin)
        return (
            (2.0 * intersection)
            / (torch.sum(label.float()) + torch.sum(prediction_bin) + 1e-12)
        ).item()


SKELETON_DISTANCE_AVAILABLE = True
SKELETON_DISTANCE_IMPORT_ERROR = None
try:
    from metrics.skeleton_distance_length import compute as compute_skeleton_dist
except ImportError as exc:
    SKELETON_DISTANCE_AVAILABLE = False
    SKELETON_DISTANCE_IMPORT_ERROR = str(exc)

    def compute_skeleton_dist(label, prediction, **kwargs):
        return float("nan")


try:
    from metrics.centerline_dice import compute as compute_centerline_dice
except ImportError:

    def compute_centerline_dice(label, prediction, **kwargs):
        return {"centerline_dice": 0.0}


try:
    from metrics.mean_ap import compute as compute_mean_ap
except ImportError:

    def compute_mean_ap(gt_bin, pred, **kwargs):
        return {"mAP": 0.0}


try:
    from metrics.connected_components import compute as compute_cc_official

    def compute_cc_diff(gt_bin: np.ndarray, pred_bin: np.ndarray) -> int:
        # Villa metric expects [H, W, D] or [N, H, W, D]
        # Our internal validation loop sends squeezed 3D or (1, H, W)
        try:
            res = compute_cc_official(gt_bin, pred_bin, num_classes=2, ignore_index=0)
            return int(res.get("connected_components_difference_total", 0))
        except Exception:
            return 0
except ImportError:
    try:
        from scipy.ndimage import label as _scipy_cc_label

        def compute_cc_diff(gt_bin: np.ndarray, pred_bin: np.ndarray) -> int:
            _, n_gt = _scipy_cc_label(gt_bin)
            _, n_pred = _scipy_cc_label(pred_bin)
            return abs(int(n_pred) - int(n_gt))
    except ImportError:

        def compute_cc_diff(gt_bin: np.ndarray, pred_bin: np.ndarray) -> int:
            return 0


try:
    from metrics.critical_components import compute as compute_crit_official

    def compute_crit_comps(gt_bin: np.ndarray, pred_bin: np.ndarray) -> int:
        try:
            # Note: villa.critical_components expects (H, W, D) or similar.
            # We assume classes=[1] for ink.
            res = compute_crit_official(gt_bin, pred_bin)
            return int(res.get("critical_components_total", 0))
        except Exception:
            return 0
except ImportError:

    def compute_crit_comps(gt_bin: np.ndarray, pred_bin: np.ndarray) -> int:
        return 0


def load_shape_compatible_state(module, state_dict, label):
    current_state = module.state_dict()
    compatible = {}
    skipped_shape = 0
    skipped_missing = 0

    for key, value in state_dict.items():
        if key not in current_state:
            skipped_missing += 1
            continue
        if not hasattr(value, "shape") or current_state[key].shape != value.shape:
            skipped_shape += 1
            continue
        compatible[key] = value

    if compatible:
        result = module.load_state_dict(compatible, strict=False)
        print(
            f"  Loaded {len(compatible)}/{len(state_dict)} compatible tensors from {label} "
            f"(skipped missing={skipped_missing}, shape={skipped_shape})."
        )
        if result.missing_keys:
            print(
                f"  Remaining missing keys after partial load: {len(result.missing_keys)}"
            )
    else:
        print(
            f"  Skipped {label}: no shape-compatible tensors "
            f"(missing={skipped_missing}, shape={skipped_shape})."
        )


def extract_checkpoint_state(checkpoint):
    if not isinstance(checkpoint, dict):
        return checkpoint
    for key in ("model", "model_state_dict", "state_dict"):
        state_dict = checkpoint.get(key)
        if isinstance(state_dict, dict):
            return state_dict
    return checkpoint


# Run-to-run val_bpb noise on the fixed Fr143 validation set is ~2e-4 (observed
# band 0.262564..0.262738 across 2026-06-09/10 cycles), while genuine regressions
# show up at >1e-2 (e.g. 0.2746). 5e-3 separates the two by an order of
# magnitude each way. centerline_dice gains below 1e-3 are treated as noise.
BPB_NOISE_TOLERANCE = 5e-3
TOPO_MIN_GAIN = 1e-3


def is_model_improvement(
    val_bpb: float,
    avg_centerline_dice: float,
    best_val_bpb: float,
    best_centerline_dice: float,
) -> bool:
    """
    Prize-aligned model selection: topology first, val_bpb as a guard rail.

    val_bpb is a weak discriminator of segmentation quality (a fresh 1.9M model
    and the 36.6M production model score ~identical val_bpb despite a 10x
    centerline_dice difference), and the prize gates are topological
    (skel_dist, centerline_dice). Under the previous bpb-first rule, a cycle
    with +58% centerline_dice was rejected because its val_bpb was 8e-6 worse
    than the stored best — i.e. selection on metric noise.

    A candidate improves on the best model iff either:
    - topo gain: centerline_dice up by > TOPO_MIN_GAIN and val_bpb not worse
      than the noise tolerance, or
    - bpb gain: val_bpb strictly lower and centerline_dice not down by more
      than TOPO_MIN_GAIN (replaces the older 0.5x collapse guard, which still
      allowed noise-level bpb differences to swap in topologically worse models).
    """
    if np.isnan(val_bpb):
        return False
    topo_improved = (
        avg_centerline_dice > best_centerline_dice + TOPO_MIN_GAIN
        and val_bpb <= best_val_bpb + BPB_NOISE_TOLERANCE
    )
    bpb_improved = (
        val_bpb < best_val_bpb
        and avg_centerline_dice >= best_centerline_dice - TOPO_MIN_GAIN
    )
    return topo_improved or bpb_improved


# The Dice-optimal binarization threshold is not the topology-optimal one. On
# the production resenc_unet, forcing the Dice threshold (~0.05, blobby
# over-prediction) onto the topology metrics reported skel_dist ~21 /
# centerline_dice ~0.10, while a higher threshold reports skel_dist ~12 /
# centerline_dice ~0.25 on the same predictions. A real prize submission is free
# to pick its own binarization threshold, so the topology gates are evaluated at
# the threshold that maximizes centerline_dice, reported alongside the
# Dice-based val_bpb. Candidates stay in the low range because this model's
# probability mass collapses above ~0.25.
TOPOLOGY_THRESHOLD_CANDIDATES = (0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50)


def select_topology_threshold(
    prob_list,
    target_list,
    candidates=TOPOLOGY_THRESHOLD_CANDIDATES,
    subset_step: int = 10,
    fallback: float = 0.5,
):
    """Pick the binarization threshold that maximizes mean centerline_dice over a
    subset of validation patches. Returns (threshold, mean_centerline_dice).

    Evaluated on every `subset_step`-th patch to match (and bound) the cost of
    the per-patch topology metrics. Falls back to `fallback` if no candidate
    produces a finite centerline_dice (e.g. all-empty predictions).
    """
    best_thr = fallback
    best_cd = -1.0
    for thr in candidates:
        cds = []
        for i in range(0, len(prob_list), subset_step):
            tgt = target_list[i]
            prob = prob_list[i]
            gt3 = np.squeeze((tgt > 0.5).numpy().astype(bool))
            pred3 = np.squeeze((prob > thr).numpy().astype(bool))
            if gt3.ndim == 2:
                gt3 = gt3[np.newaxis, ...]
            if pred3.ndim == 2:
                pred3 = pred3[np.newaxis, ...]
            try:
                cd = compute_centerline_dice(gt3, pred3, tolerance_radius=3.0).get(
                    "centerline_dice", 0.0
                )
                if not np.isnan(cd):
                    cds.append(cd)
            except Exception:
                pass
        mean_cd = float(np.mean(cds)) if cds else -1.0
        if mean_cd > best_cd:
            best_cd, best_thr = mean_cd, thr
    return best_thr, (best_cd if best_cd >= 0.0 else 0.0)


def evaluate_prize_gates(
    config: ExperimentConfig,
    val_bpb: float,
    avg_skel_dist: float,
    avg_centerline_dice: float,
    avg_cc_diff: float,
    num_skel_samples: int,
    num_centerline_samples: int,
    num_cc_samples: int,
) -> dict[str, bool | float | list[str]]:
    window_mm = config.patch_size * 8.0 / 1000.0
    window_ok = config.patch_size <= 64 or window_mm <= 0.5 + 1e-9
    failures = []

    if not window_ok:
        failures.append(
            f"ML window {config.patch_size}px/{window_mm:.3f}mm exceeds official prize guidance"
        )
    if not np.isfinite(val_bpb):
        failures.append("val_bpb is not finite")
    # avg_skel_dist is reported but not gated (see field comment / FINDINGS.md Phase 4b)
    if not np.isfinite(avg_centerline_dice):
        failures.append("avg_centerline_dice is not finite")
    if not np.isfinite(avg_cc_diff):
        failures.append("avg_cc_diff is not finite")

    min_samples = int(getattr(config, "min_prize_topology_samples", 1))
    if num_centerline_samples < min_samples:
        failures.append(
            f"only {num_centerline_samples} centerline-dice samples; expected >= {min_samples}"
        )
    if num_cc_samples < min_samples:
        failures.append(
            f"only {num_cc_samples} connected-component samples; expected >= {min_samples}"
        )

    min_centerline = float(getattr(config, "min_prize_centerline_dice", 0.0))
    max_cc = float(getattr(config, "max_prize_cc_diff", float("inf")))
    if np.isfinite(avg_centerline_dice) and avg_centerline_dice < min_centerline:
        failures.append(
            f"avg_centerline_dice {avg_centerline_dice:.6f} below gate {min_centerline:.6f}"
        )
    if np.isfinite(avg_cc_diff) and avg_cc_diff > max_cc:
        failures.append(f"avg_cc_diff {avg_cc_diff:.3f} above gate {max_cc:.3f}")

    villa_metrics_ok = not failures
    return {
        "window_ok": bool(window_ok),
        "window_mm": float(window_mm),
        "villa_metrics_ok": bool(villa_metrics_ok),
        "submittable": bool(window_ok and villa_metrics_ok),
        "failures": failures,
    }


# Add villa to path for ridge detection and structure tensors
VILLA_SRC = os.path.abspath("villa/vesuvius/src")
VILLA_INK_SRC = os.path.abspath("villa/ink-detection")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)
if VILLA_INK_SRC not in sys.path:
    sys.path.append(VILLA_INK_SRC)

try:
    from vesuvius.image_proc.geometry.structure_tensor import StructureTensorComputer
except ImportError:
    StructureTensorComputer = None
try:
    from models.i3dallnl import InceptionI3d
    from models.resnetall import generate_model as generate_resnet3d
except ImportError:
    generate_resnet3d = None
    InceptionI3d = None

try:
    from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet
    from dynamic_network_architectures.building_blocks.helper import (
        convert_dim_to_conv_op,
        get_matching_instancenorm,
    )
except ImportError:
    ResidualEncoderUNet = None

from vesuvius_autoresearch.core.model_wrappers import GenericMultiTaskWrapper

try:
    from vesuvius.models.augmentation.pipelines.training_transforms import (
        create_training_transforms,
    )
except ImportError:
    create_training_transforms = None

_villa_aug_cache = {}
_bg2_aug_cache = {}

# Villa Albumentations recipe (Grand Prize team, tuned for Scroll 2 noise profile).
# See villa/ink-detection/train_timesformer_og.py.
try:
    import albumentations as A

    _HAS_ALBUMENTATIONS = True
except ImportError:
    _HAS_ALBUMENTATIONS = False

_villa_aug_cache = {}


def _get_villa_aug(size: int, config: ExperimentConfig):
    if not _HAS_ALBUMENTATIONS:
        return None

    cache_key = (
        size,
        config.aug_flip_p,
        config.aug_brightness_p,
        config.aug_affine_p,
        config.aug_coarse_dropout_p,
        config.aug_elastic_p,
        config.aug_grid_p,
        config.aug_rotate_limit,
        config.aug_scale_limit,
    )

    if cache_key in _villa_aug_cache:
        return _villa_aug_cache[cache_key]

    transforms = []

    if config.aug_flip_p > 0:
        transforms.extend(
            [A.HorizontalFlip(p=config.aug_flip_p), A.VerticalFlip(p=config.aug_flip_p)]
        )

    if config.aug_brightness_p > 0:
        transforms.append(A.RandomBrightnessContrast(p=config.aug_brightness_p))

    if config.aug_affine_p > 0:
        transforms.append(
            A.Affine(
                rotate=(-config.aug_rotate_limit, config.aug_rotate_limit),
                scale=(1.0 - config.aug_scale_limit, 1.0 + config.aug_scale_limit),
                translate_percent=(-0.15, 0.15),
                mode=0,
                p=config.aug_affine_p,
            )
        )

    transforms.append(
        A.OneOf(
            [
                A.GaussNoise(var_limit=(0.01, 0.03)),
                A.GaussianBlur(),
                A.MotionBlur(),
            ],
            p=0.4,
        )
    )

    if config.aug_coarse_dropout_p > 0:
        transforms.append(
            A.CoarseDropout(
                min_holes=1,
                max_holes=2,
                min_height=0.1,
                max_height=0.2,
                min_width=0.1,
                max_width=0.2,
                fill_value=0,
                mask_fill_value=0,
                p=config.aug_coarse_dropout_p,
            )
        )

    if getattr(config, "aug_elastic_p", 0.0) > 0:
        transforms.append(
            A.ElasticTransform(
                alpha=1, sigma=50, alpha_affine=50, p=config.aug_elastic_p
            )
        )

    if getattr(config, "aug_grid_p", 0.0) > 0:
        transforms.append(
            A.GridDistortion(num_steps=5, distort_limit=0.3, p=config.aug_grid_p)
        )

    pipeline = A.Compose(transforms, additional_targets={"fiber": "mask"})
    _villa_aug_cache[cache_key] = pipeline
    return pipeline


# Import our breakthrough components
import sys

print(f"DEBUG: Executing train.py from: {__file__}")
sys.stdout.flush()

import vesuvius_model
from vesuvius_autoresearch.core.vesuvius_loader import (
    VesuviusLabeledDataset,
    VesuviusS3Dataset,
)

print(f"DEBUG: Importing vesuvius_model from: {vesuvius_model.__file__}")
sys.stdout.flush()
from vesuvius_model import InkDetectorOptimized, VesuviusConfig, VesuviusTimeSformer


def mixup_data(x, y, z, alpha=0.2):
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1
    batch_size = x.size()[0]
    index = torch.randperm(batch_size).to(x.device)
    mixed_x = lam * x + (1 - lam) * x[index, :]
    mixed_y = lam * y + (1 - lam) * y[index, :]
    mixed_z = lam * z + (1 - lam) * z[index, :]
    return mixed_x, mixed_y, mixed_z, lam


def cutmix_data(x, y, z, alpha=1.0):
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1
    batch_size = x.size()[0]
    index = torch.randperm(batch_size).to(x.device)

    W, H = x.size(-1), x.size(-2)
    cut_rat = np.sqrt(1.0 - lam)
    cut_w, cut_h = int(W * cut_rat), int(H * cut_rat)
    cx, cy = np.random.randint(W), np.random.randint(H)

    bbx1 = np.clip(cx - cut_w // 2, 0, W)
    bby1 = np.clip(cy - cut_h // 2, 0, H)
    bbx2 = np.clip(cx + cut_w // 2, 0, W)
    bby2 = np.clip(cy + cut_h // 2, 0, H)

    x[..., bby1:bby2, bbx1:bbx2] = x[index, ..., bby1:bby2, bbx1:bbx2]
    y[..., bby1:bby2, bbx1:bbx2] = y[index, ..., bby1:bby2, bbx1:bbx2]
    z[..., bby1:bby2, bbx1:bbx2] = z[index, ..., bby1:bby2, bbx1:bbx2]

    return x, y, z, lam


def confidence_weight(target):
    """Per-pixel confidence weight for soft pseudo-labels: 1.0 where the label
    is confident (0 or 1), 0.0 in the uncertain band (encoded as 0.5). Recomputed
    from the (possibly augmented) target each step, so it survives mixup/affine
    interpolation, and is a no-op on true binary labels."""
    return (2.0 * (target - 0.5).abs()).clamp(0.0, 1.0)


def periodic_pixel_auc_eval(model, val_dataset, config, device, step, elapsed_s):
    """Gated learning-curve probe: pooled pixel AUC on a FIXED random sample of
    validation patches, plus a step-tagged checkpoint and a CSV row. Wrapped so a
    mid-run eval glitch cannot kill a multi-hour training run. Indices are drawn
    once (seeded) so every call scores the same patches."""
    import csv

    from scripts.pixel_auc import pooled_pixel_auc

    prefix = config.checkpoint_out or "long_model.pt"
    curve_path = f"{prefix}.curve.csv"
    nl = config.num_layers
    try:
        n = min(config.eval_sample_patches, len(val_dataset))
        idxs = np.random.RandomState(12345).permutation(len(val_dataset))[:n]
        model.eval()
        probs, labels = [], []
        with torch.no_grad():
            for i in idxs:
                x_raw, t, _ = val_dataset[int(i)]
                x = x_raw[:, 4 : 4 + nl].unsqueeze(0).to(device)
                out = model(x)
                out = out[0] if isinstance(out, tuple) else out
                probs.append(torch.sigmoid(out).squeeze().float().cpu().numpy().ravel())
                labels.append((t.numpy() > 0.5).astype(int).ravel())
        auc = pooled_pixel_auc(probs, labels)
    except Exception as exc:  # an eval glitch must not kill a 12h run
        print(f"  [curve] eval failed at step {step}: {type(exc).__name__}: {exc}")
        auc = float("nan")
    finally:
        model.train()

    write_header = not os.path.exists(curve_path)
    with open(curve_path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["step", "elapsed_s", "pixel_auc"])
        w.writerow([step, round(elapsed_s, 1), f"{auc:.4f}"])
    try:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "step": step,
                "config": asdict(config),
            },
            f"{prefix}.step{step}.pt",
        )
    except Exception as exc:
        print(f"  [curve] checkpoint save failed at step {step}: {exc}")
    print(f"  [curve] step={step} elapsed={elapsed_s:.0f}s pooled_pixel_auc={auc:.4f}")


def compute_dice_loss(pred_2d, target, smooth=1e-5, weight=None):
    """
    Standard Dice Loss for 2D ink detection. Optional per-pixel `weight`
    down-weights pixels (e.g. uncertain pseudo-label band); weight=None is the
    original unweighted behavior.
    """
    pred_2d = torch.sigmoid(pred_2d)

    if target.dim() == 3:
        target = target.unsqueeze(1)

    if weight is not None:
        if weight.dim() == 3:
            weight = weight.unsqueeze(1)
        pred_2d = pred_2d * weight
        target = target * weight

    intersection = (pred_2d * target).sum(dim=(-2, -1))
    union = pred_2d.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))

    dice = (2.0 * intersection + smooth) / (union + smooth)
    return 1.0 - dice.mean()


def compute_hard_dice(pred_2d, target, smooth=1e-5):
    """
    Hard Dice Score (thresholded at 0.5) for evaluation.
    """
    pred_2d = (torch.sigmoid(pred_2d) > 0.5).float()

    if target.dim() == 3:
        target = target.unsqueeze(1)

    intersection = (pred_2d * target).sum(dim=(-2, -1))
    union = pred_2d.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))

    dice = (2.0 * intersection + smooth) / (union + smooth)
    return dice.mean()


def apply_augmentations(x, target_ink, target_fiber, step, max_steps, config=None):
    """Villa Augmentation recipes.

    Supports:
    - 'albumentations': Per-item 2D recipe, synchronized across depth.
    - 'batchgeneratorsv2': Official 3D-native MIC-DKFZ pipeline from villa.

    x: (B, 1, D, H, W); target_ink: (B, 1, H, W); target_fiber: (B, 1, 1, H, W).
    """
    if getattr(config, "disable_augmentation", False):
        # Ablation master switch: return inputs untouched (no rot90/flip/scroll/etc).
        return x, target_ink, target_fiber

    aug_mode = getattr(config, "aug_mode", "albumentations")

    if aug_mode == "batchgeneratorsv2" and create_training_transforms is not None:
        B, C, D, H, W = x.shape
        patch_size_3d = (D, H, W)
        if patch_size_3d not in _bg2_aug_cache:
            base_transform = create_training_transforms(patch_size_3d)

            from vesuvius.models.augmentation.transforms.noise.extranoisetransforms import (
                BlankRectangleTransform,
                RicianNoiseTransform,
            )
            from vesuvius.models.augmentation.transforms.spatial.sheet_compression import (
                SheetCompressionTransform,
            )
            from vesuvius.models.augmentation.transforms.spatial.thick_slice import (
                SimulateThickSliceTransform,
            )
            from vesuvius.models.augmentation.transforms.utils.compose import (
                ComposeTransforms,
            )
            from vesuvius.models.augmentation.transforms.utils.random import (
                RandomTransform,
            )

            extra_transforms = []
            if getattr(config, "aug_scroll_sheet_compression_p", 0.0) > 0:
                extra_transforms.append(
                    RandomTransform(
                        SheetCompressionTransform(),
                        apply_probability=getattr(
                            config, "aug_scroll_sheet_compression_p", 0.0
                        ),
                    )
                )
            if getattr(config, "aug_scroll_thick_slice_p", 0.0) > 0:
                extra_transforms.append(
                    RandomTransform(
                        SimulateThickSliceTransform(),
                        apply_probability=getattr(
                            config, "aug_scroll_thick_slice_p", 0.0
                        ),
                    )
                )
            if getattr(config, "aug_scroll_rician_noise_p", 0.0) > 0:
                extra_transforms.append(
                    RandomTransform(
                        RicianNoiseTransform(),
                        apply_probability=getattr(
                            config, "aug_scroll_rician_noise_p", 0.0
                        ),
                    )
                )
            if getattr(config, "aug_scroll_blank_rectangles_p", 0.0) > 0:
                extra_transforms.append(
                    RandomTransform(
                        BlankRectangleTransform(
                            rectangle_size=tuple(
                                (max(1, s // 6), s // 3) for s in patch_size_3d
                            ),
                            rectangle_value=np.mean,
                            num_rectangles=(1, 5),
                        ),
                        apply_probability=getattr(
                            config, "aug_scroll_blank_rectangles_p", 0.0
                        ),
                    )
                )

            if extra_transforms:
                _bg2_aug_cache[patch_size_3d] = ComposeTransforms(
                    [base_transform] + extra_transforms
                )
            else:
                _bg2_aug_cache[patch_size_3d] = base_transform

        bg_aug = _bg2_aug_cache[patch_size_3d]

        # Batchgenerators expects: (C, Z, H, W) for per-sample call
        # but our wrapper handles (B, C, Z, H, W) if it's the official villa one.
        # Actually, let's process sample by sample to be safe, like Albumentations path.

        out_x, out_ink, out_fiber = [], [], []
        try:
            for b in range(B):
                # Prepare inputs for this sample
                img_3d = x[b]  # [C, D, H, W]

                # Ensure ink is [1, D, H, W]
                ink_samp = target_ink[b]
                if ink_samp.ndim == 2:  # [H, W]
                    ink_3d = ink_samp[None, None].repeat(1, D, 1, 1)
                elif ink_samp.ndim == 3:  # [1, H, W]
                    ink_3d = ink_samp[:, None].repeat(1, D, 1, 1)
                else:
                    ink_3d = ink_samp

                # Ensure fiber is [1, D, H, W]
                f_samp = target_fiber[b]
                if f_samp.ndim == 2:  # [H, W]
                    fiber_3d = f_samp[None, None].repeat(1, D, 1, 1)
                elif f_samp.ndim == 3:  # [1, H, W]
                    fiber_3d = f_samp[:, None].repeat(1, D, 1, 1)
                elif f_samp.ndim == 4 and f_samp.shape[1] == 1:  # [1, 1, H, W]
                    fiber_3d = f_samp.repeat(1, D, 1, 1)
                else:
                    fiber_3d = f_samp

                # Compose the data dict
                data_dict = {
                    "image": img_3d,
                    "ink": ink_3d,
                    "fiber": fiber_3d,
                    "regression_keys": [
                        "ink",
                        "fiber",
                    ],  # Hint for bilinear interpolation
                }

                # Call transform with kwargs
                res = bg_aug(**data_dict)

                out_x.append(res["image"])
                # Extract 2D ink from the center slice of the augmented 3D label
                # res['ink'] is [1, D, H, W]
                out_ink.append(res["ink"][:, D // 2])
                # Fiber is used as a 2D pseudo-label (collapsed mean in loss)
                out_fiber.append(res["fiber"][:, D // 2 : D // 2 + 1])

            x_aug = torch.stack(out_x)
            ink_aug = torch.stack(out_ink)
            fiber_aug = torch.stack(out_fiber)

            return x_aug, ink_aug, fiber_aug
        except Exception as e:
            if step % 100 == 0:
                print(
                    f"Warning: batchgeneratorsv2 failed ({e}). Falling back to Albumentations."
                )
            aug_mode = "albumentations"

    # Fallback/Default: Albumentations
    aug = _get_villa_aug(x.shape[-1], config) if _HAS_ALBUMENTATIONS else None
    if aug is None:
        # Bare-bones fallback so the training loop still runs without albumentations.
        k_rot = np.random.randint(0, 4)
        x_aug = torch.rot90(x, k=k_rot, dims=(-2, -1))
        ink_aug = torch.rot90(target_ink, k=k_rot, dims=(-2, -1)).clamp(0, 1)
        fiber_aug = torch.rot90(target_fiber, k=k_rot, dims=(-2, -1)).clamp(0, 1)
        if np.random.rand() > 0.5:
            x_aug = torch.flip(x_aug, dims=[2])  # Flip across Z
        return x_aug, ink_aug, fiber_aug

    B, C, D, H, W = x.shape
    device = x.device
    x_dtype = x.dtype
    ink_dtype = target_ink.dtype
    fiber_dtype = target_fiber.dtype

    x_np = x.detach().float().cpu().numpy()
    ink_np = target_ink.detach().float().cpu().numpy()
    fiber_np = target_fiber.detach().float().cpu().numpy()

    # Collapse fiber's singleton depth dim if present.
    fiber_has_d = fiber_np.ndim == 5
    if fiber_has_d:
        fiber_np = fiber_np[:, :, 0]  # (B, 1, H, W)

    out_x, out_ink, out_fiber = [], [], []
    for b in range(B):
        # img_hwd shape will be (H, W, D*C) for albumentations to process all channels at once
        # but albumentations works best with (H, W, C). For 3D, we have (D, H, W).
        # We need to process each channel's depth slices.
        # Actually, let's process it as (H, W, D, C) and then flatten last two.

        channels_data = []
        for c in range(C):
            channels_data.append(
                np.transpose(x_np[b, c], (1, 2, 0))
            )  # List of (H, W, D)

        img_hwd_all = np.concatenate(channels_data, axis=-1)  # (H, W, D*C)

        mask_ink = ink_np[b, 0].astype(np.float32, copy=False)
        mask_fiber = fiber_np[b, 0].astype(np.float32, copy=False)

        res = aug(image=img_hwd_all, mask=mask_ink, fiber=mask_fiber)

        # Reshape back to (C, D, H, W)
        aug_img = res["image"]  # (H, W, D*C)
        aug_img = np.transpose(aug_img, (2, 0, 1))  # (D*C, H, W)
        aug_img = aug_img.reshape(C, D, *aug_img.shape[1:])  # (C, D, H, W)

        out_x.append(aug_img)
        out_ink.append(res["mask"])
        out_fiber.append(res["fiber"])

    x_aug = torch.from_numpy(np.ascontiguousarray(np.stack(out_x))).to(
        device=device, dtype=x_dtype
    )
    ink_aug = (
        torch.from_numpy(np.ascontiguousarray(np.stack(out_ink)))
        .unsqueeze(1)
        .to(device=device, dtype=ink_dtype)
        .clamp(0, 1)
    )
    fiber_aug = (
        torch.from_numpy(np.ascontiguousarray(np.stack(out_fiber)))
        .unsqueeze(1)
        .to(device=device, dtype=fiber_dtype)
        .clamp(0, 1)
    )
    if fiber_has_d:
        fiber_aug = fiber_aug.unsqueeze(2)  # restore (B, 1, 1, H, W)

    # Cheap 3D-specific aug the villa 2D recipe can't express: random z-flip.
    if np.random.rand() > 0.5:
        x_aug = torch.flip(x_aug, dims=[2])
        if fiber_has_d:
            fiber_aug = torch.flip(fiber_aug, dims=[2])

    return apply_scroll_specific_3d_augmentations(x_aug, ink_aug, fiber_aug, config)


def build_vconfig(config: ExperimentConfig) -> VesuviusConfig:
    """Build the VesuviusConfig for an ExperimentConfig.

    Shared by train() and the --smoke preflight gate so both derive the
    architecture parameters identically.
    """
    return VesuviusConfig(
        patch_size=config.patch_size,
        num_layers=config.num_layers,
        batch_size=config.batch_size,
        base_feat=config.base_feat,
        num_blocks=config.num_blocks,
        num_heads=config.num_heads,
        dropout=config.dropout,
        in_channels=2 if config.use_ridges else 1,
        architecture=getattr(config, "architecture", "gated_unet"),
    )


def build_model(config: ExperimentConfig, v_config: VesuviusConfig, device):
    """Construct the model for v_config.architecture and move it to device.

    Shared by train() and the --smoke preflight gate so the gate exercises the
    exact same construction path as the real run (no drift between them).
    """
    if hasattr(v_config, "architecture") and v_config.architecture == "timesformer":
        print("Instantiating TimeSformer Architecture...")
        model = VesuviusTimeSformer(v_config).to(device)
    elif (
        hasattr(v_config, "architecture")
        and v_config.architecture == "resnet3d_decoder"
    ):
        print("Instantiating ResNet3D-152 3D-Decoder Architecture...")
        from vesuvius_model import VesuviusResNet3DDecoder

        model = VesuviusResNet3DDecoder(v_config).to(device)
    elif hasattr(v_config, "architecture") and v_config.architecture == "resnet3d":
        print("Instantiating ResNet3D-101 Architecture (Grand Prize Variant)...")
        if generate_resnet3d:
            backbone = generate_resnet3d(
                101,
                n_input_channels=v_config.in_channels,
                n_classes=1,
                forward_features=False,
            )
            model = GenericMultiTaskWrapper(
                backbone,
                multi_task_heads=getattr(config, "multi_task_heads", False),
                input_channels=v_config.in_channels,
            ).to(device)
        else:
            raise ImportError("ResNet3D model not found in villa submodule.")
    elif hasattr(v_config, "architecture") and v_config.architecture == "i3d":
        print("Instantiating Inception-I3D Architecture...")
        if InceptionI3d:
            backbone = InceptionI3d(
                num_classes=1,
                in_channels=v_config.in_channels,
                final_endpoint="Logits",
                forward_features=False,
            )
            model = GenericMultiTaskWrapper(
                backbone,
                multi_task_heads=getattr(config, "multi_task_heads", False),
                input_channels=v_config.in_channels,
            ).to(device)
        else:
            raise ImportError("I3D model not found in villa submodule.")
    elif hasattr(v_config, "architecture") and v_config.architecture == "resenc_unet":
        print(
            f"Instantiating nnUNet-style ResEnc UNet (base_feat={v_config.base_feat})..."
        )
        if ResidualEncoderUNet:
            # Shallow 3-stage configuration to avoid dimension mismatch on small patches
            n_stages = 3
            features_per_stage = [v_config.base_feat * (2**i) for i in range(n_stages)]
            strides = [[1, 1, 1]] + [[2, 2, 2]] * (n_stages - 1)

            backbone = ResidualEncoderUNet(
                input_channels=v_config.in_channels,
                n_stages=n_stages,
                features_per_stage=features_per_stage,
                conv_op=convert_dim_to_conv_op(3),
                kernel_sizes=[[3, 3, 3]] * n_stages,
                strides=strides,
                n_blocks_per_stage=[2] * n_stages,
                num_classes=1,
                n_conv_per_stage_decoder=[2] * (n_stages - 1),
                conv_bias=True,
                norm_op=get_matching_instancenorm(convert_dim_to_conv_op(3)),
                norm_op_kwargs={"eps": 1e-5, "affine": True},
                dropout_op=None,
                nonlin=nn.LeakyReLU,
                nonlin_kwargs={"inplace": True},
                deep_supervision=False,
            )
            model = GenericMultiTaskWrapper(
                backbone,
                multi_task_heads=getattr(config, "multi_task_heads", False),
                input_channels=v_config.in_channels,
            ).to(device)
        else:
            raise ImportError(
                "ResidualEncoderUNet not found. Please install dynamic-network-architectures."
            )
    elif hasattr(v_config, "architecture") and v_config.architecture == "lejepa_unet":
        print("Instantiating LeJEPA Foundation-Backed UNet...")
        from vesuvius_model import LeJEPAUNet

        model = LeJEPAUNet(v_config).to(device)
    elif hasattr(v_config, "architecture") and v_config.architecture == "mednext":
        print("Instantiating MedNeXt Architecture...")
        from vesuvius_model import MedNeXtInkDetector

        model = MedNeXtInkDetector(v_config).to(device)
    elif (
        hasattr(v_config, "architecture")
        and v_config.architecture == "neural_tracing_vit"
    ):
        print("Instantiating Vesuvius Neural Tracing ViT (Youssef MAE)...")
        from vesuvius_model import VesuviusNeuralTracingViT

        model = VesuviusNeuralTracingViT(v_config).to(device)
    else:
        print("Instantiating Gated UNet-Transformer Architecture...")
        model = InkDetectorOptimized(v_config).to(device)
    return model


def preflight_smoke(config: ExperimentConfig) -> None:
    """Build the model and run one forward+backward on a synthetic batch.

    Raises on any failure: construction error, shape/channel mismatch, or
    non-finite output/loss. Runs on CPU so it never contends with a live GPU
    cycle and so shape bugs surface deterministically. This is the gate that
    catches model-level breakage in seconds instead of burning a full cycle.
    """
    device = torch.device("cpu")
    v_config = build_vconfig(config)
    model = build_model(config, v_config, device).train()

    x = torch.randn(
        2,
        v_config.in_channels,
        v_config.num_layers,
        v_config.patch_size,
        v_config.patch_size,
    )
    out = model(x, return_fiber=True, return_qc=True, return_proj=True, return_st=True)
    outs = out if isinstance(out, tuple) else (out,)
    for t in outs:
        if not torch.isfinite(t).all():
            raise ValueError("preflight: non-finite values in model output")
    loss = sum(t.float().mean() for t in outs)
    loss.backward()
    if not torch.isfinite(loss):
        raise ValueError("preflight: non-finite loss")


def train(config: ExperimentConfig):
    print("STARTING TRAINING")
    torch.set_float32_matmul_precision("high")
    device = torch.device("cuda")

    v_config = build_vconfig(config)

    print(f"Initializing LOCAL TRANSFORMER Training on {config.uris}...")
    sys.stdout.flush()

    def get_dataloader(uris, seed=None, is_unlabeled=False):
        from torch.utils.data import ConcatDataset

        datasets = []
        for uri in uris:
            if is_unlabeled:
                ds = VesuviusS3Dataset(
                    uri,
                    config.patch_size,
                    config.num_layers + 8,
                    seed=seed,
                    cache_dir=config.cache_dir,
                    use_ridges=config.use_ridges,
                    ridge_sigma=getattr(config, "ridge_sigma", 2.0),
                    use_lasagna=config.use_lasagna,
                    is_unlabeled=True,
                )
                datasets.append(ds)
                continue

            parent_dir = os.path.dirname(uri.rstrip("/"))

            # Check for pseudo-labels first if directory is provided
            labels_path = None
            if config.pseudo_label_dir:
                # Expecting pseudo-labels to be named after the segment directory
                segment_name = os.path.basename(parent_dir)
                pseudo_path = os.path.join(
                    config.pseudo_label_dir, f"{segment_name}_pseudo.png"
                )
                if os.path.exists(pseudo_path):
                    labels_path = pseudo_path

            if labels_path is None:
                labels_path = os.path.join(parent_dir, "inklabels_refined.png")
                if not os.path.exists(labels_path):
                    labels_path = os.path.join(parent_dir, "inklabels_filled.png")
                    if not os.path.exists(labels_path):
                        labels_path = os.path.join(parent_dir, "inklabels.png")

            if os.path.exists(labels_path):
                mask_path = os.path.join(parent_dir, "mask.png")
                patches_json_path = os.path.join(parent_dir, "patches.json")
                ds = VesuviusLabeledDataset(
                    uri,
                    labels_path,
                    mask_path if os.path.exists(mask_path) else None,
                    config.patch_size,
                    config.num_layers + 8,
                    seed=seed,
                    cache_dir=config.cache_dir,
                    use_ridges=config.use_ridges,
                    ridge_sigma=getattr(config, "ridge_sigma", 2.0),
                    use_lasagna=getattr(config, "use_lasagna", False),
                    target_fiber_source=getattr(
                        config, "target_fiber_source", "sobel_z"
                    ),
                    target_fiber_sigma=getattr(config, "target_fiber_sigma", 2.0),
                    patches_json=patches_json_path
                    if os.path.exists(patches_json_path)
                    else None,
                )
            else:
                ds = VesuviusS3Dataset(
                    uri,
                    config.patch_size,
                    config.num_layers + 8,
                    seed=seed,
                    cache_dir=config.cache_dir,
                    use_ridges=config.use_ridges,
                    ridge_sigma=getattr(config, "ridge_sigma", 2.0),
                    use_lasagna=getattr(config, "use_lasagna", False),
                )
            datasets.append(ds)

        combined_ds = ConcatDataset(datasets) if len(datasets) > 1 else datasets[0]
        # Set num_workers to 0 to prevent semaphore leaks (resource_tracker warnings)
        num_workers = 0
        return DataLoader(
            combined_ds,
            batch_size=config.batch_size,
            num_workers=num_workers,
            pin_memory=True,
            multiprocessing_context="spawn" if num_workers > 0 else None,
        )

    data_loader = get_dataloader(config.uris)
    data_iter = iter(data_loader)

    unlabeled_data_iter = None
    if config.use_uamt and config.unlabeled_uris:
        unlabeled_data_loader = get_dataloader(config.unlabeled_uris, is_unlabeled=True)
        unlabeled_data_iter = iter(unlabeled_data_loader)

    # Use fixed seed and num_workers=0 for validation to ensure absolute determinism
    def get_val_dataloader(uri):
        parent_dir = os.path.dirname(uri.rstrip("/"))
        labels_path = os.path.join(parent_dir, "inklabels_refined.png")
        if not os.path.exists(labels_path):
            labels_path = os.path.join(parent_dir, "inklabels_filled.png")
            if not os.path.exists(labels_path):
                labels_path = os.path.join(parent_dir, "inklabels.png")

        mask_path = os.path.join(parent_dir, "mask.png")
        patches_json_path = os.path.join(parent_dir, "patches.json")
        # Use require_ink=True for validation to ensure meaningful Dice scores
        # Validation uses target_fiber_source="sobel_z" regardless of training
        # config — val doesn't use target_fiber (only ink) and we want to avoid
        # paying Frangi cost on every val patch.
        ds = VesuviusLabeledDataset(
            uri,
            labels_path,
            mask_path if os.path.exists(mask_path) else None,
            config.patch_size,
            config.num_layers + 8,
            seed=42,
            cache_dir=config.cache_dir,
            use_ridges=config.use_ridges,
            ridge_sigma=getattr(config, "ridge_sigma", 2.0),
            use_lasagna=getattr(config, "use_lasagna", False),
            require_ink=True,
            target_fiber_source="sobel_z",
            patches_json=patches_json_path
            if os.path.exists(patches_json_path)
            else None,
        )
        return DataLoader(
            ds, batch_size=config.batch_size, num_workers=0, pin_memory=True
        )

    val_data_loader = get_val_dataloader(config.val_uri)
    val_data_iter = iter(val_data_loader)

    model = build_model(config, v_config, device)

    # Opt-in wandb experiment tracking (default off; online to match villa).
    # watch_model logs parameter + gradient histograms over training.
    wandb_run = wandb_tracking.init_run(config)
    wandb_tracking.watch_model(wandb_run, model)

    betti_loss = (
        BettiLoss(weight=config.betti_loss_weight) if config.use_betti_loss else None
    )
    cldice_loss = (
        SoftClDiceLoss(iters=config.cldice_iters) if config.use_cldice else None
    )

    # Load from foundation model if provided
    if config.foundation_model_path and os.path.exists(config.foundation_model_path):
        try:
            print(f"Loading pretrained backbone from {config.foundation_model_path}...")
            checkpoint = torch.load(
                config.foundation_model_path, map_location=device, weights_only=False
            )
            state_dict = extract_checkpoint_state(checkpoint)

            # Map weights to backbone if possible. This is highly architecture dependent.
            # For PrimusNetwork (LeJEPA), the encoder weights start with 'encoder.'
            if hasattr(model, "backbone") and hasattr(model.backbone, "shared_encoder"):
                # Extract encoder weights and strip 'encoder.' prefix
                encoder_state = {
                    k.replace("encoder.", ""): v
                    for k, v in state_dict.items()
                    if k.startswith("encoder.")
                }
                load_shape_compatible_state(
                    model.backbone.shared_encoder, encoder_state, "LeJEPA encoder"
                )
            else:
                load_shape_compatible_state(
                    model, state_dict, "generic pretrained checkpoint"
                )
        except Exception as e:
            print(f"Warning: Could not load foundation model: {e}")

    # Load best model if architecture matches
    best_model_path = "best_model.pt"
    if os.path.exists(best_model_path):
        try:
            checkpoint = torch.load(
                best_model_path, map_location=device, weights_only=False
            )
            best_config = checkpoint.get("config", {})

            # Check compatibility (architecture-defining attributes).
            # NOTE: do NOT include `in_channels` here — it is not a field of
            # ExperimentConfig (it is derived at model build time as
            # `2 if use_ridges else 1`). Listing it caused getattr to raise
            # AttributeError, which the outer except swallowed as
            # "Could not load best model" — silently training every cycle
            # from random init since 2026-05-06 (commit d3da171).
            arch_match = True
            mismatch_attr = None
            for attr in [
                "architecture",
                "use_ridges",
                "num_layers",
                "num_blocks",
                "num_heads",
                "base_feat",
                "patch_size",
            ]:
                if best_config.get(attr) != getattr(config, attr):
                    arch_match = False
                    mismatch_attr = attr
                    break

            if arch_match:
                print(
                    f"Loading weights from {best_model_path} (Incremental Progress)..."
                )
                load_shape_compatible_state(
                    model, checkpoint["model_state_dict"], best_model_path
                )
            else:
                print(
                    "New architecture detected "
                    f"({mismatch_attr}: {best_config.get(mismatch_attr)}->{getattr(config, mismatch_attr)}). "
                    "Starting fresh."
                )
        except Exception as e:
            print(f"Warning: Could not load best model: {e}")

    # UAMT: Initialize EMA Teacher Model
    ema_model = None
    if config.use_uamt:
        import copy

        ema_model = copy.deepcopy(model)
        for param in ema_model.parameters():
            param.detach_()
        ema_model.eval()

    # 1. Linear Scaling Rule for LR
    config.lr = config.lr * (config.batch_size / 16.0)

    # 2. Budget-Aware Scheduling
    # Estimate throughput: ~0.2s per step (conservative estimate for base_feat=64)
    estimated_step_time = 0.2
    max_steps = max(1000, int(config.time_budget / estimated_step_time))
    warmup_steps = int(max_steps * 0.125)  # 12.5% warmup

    print(
        f"Budget-Aware Scheduling: max_steps={max_steps}, warmup_steps={warmup_steps}, scaled_lr={config.lr:.2e}"
    )

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.lr, weight_decay=config.weight_decay
    )

    def lr_lambda(current_step: int):
        if current_step < warmup_steps:
            return float(current_step) / float(max(1, warmup_steps))
        clamped_step = min(current_step, max_steps)
        return 0.5 * (
            1.0
            + math.cos(
                math.pi
                * (clamped_step - warmup_steps)
                / float(max(1, max_steps - warmup_steps))
            )
        )

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    amp_enabled = False  # Disabled for NaN debugging
    scaler = GradScaler(device=device.type, enabled=amp_enabled)

    # Initialize auxiliary task tools
    st_computer = (
        StructureTensorComputer(
            sigma=1.0, component_sigma=1.0, smooth_components=True, device=device
        )
        if StructureTensorComputer
        else None
    )

    print(f"Starting Gated UNet-Transformer Loop (Budget: {config.time_budget}s)...")
    sys.stdout.flush()

    step = 0
    total_training_time = 0
    smooth_loss = 0

    while True:
        t0 = time.time()
        try:
            x_raw, target_ink_raw, target_fiber_from_loader = next(data_iter)
            x_raw = x_raw.to(device)  # [B, 1, Z_buffered, H, W]
            # target_fiber_from_loader: [B, 1, 1, H, W] either zeros (sobel_z
            # source, train.py computes inline below) or real Frangi
            # vesselness (frangi source — see VesuviusLabeledDataset._compute_fiber_target).
            target_fiber_from_loader = target_fiber_from_loader.to(device)

            # Ensure target_ink has 4 dims [B, 1, H, W]
            if target_ink_raw is not None and target_ink_raw.numel() > 0:
                target_ink = target_ink_raw.to(device)
                if target_ink.dim() == 3:
                    target_ink = target_ink.unsqueeze(1)
            else:
                target_ink = torch.zeros(
                    (x_raw.shape[0], 1, x_raw.shape[3], x_raw.shape[4]), device=device
                )

            # UAMT: Fetch Unlabeled Data
            x_unlabeled = None
            if config.use_uamt and unlabeled_data_iter is not None:
                try:
                    x_unlabeled_raw, _ = next(unlabeled_data_iter)
                    x_unlabeled = x_unlabeled_raw.to(device)
                except StopIteration:
                    unlabeled_data_iter = iter(unlabeled_data_loader)
                    x_unlabeled_raw, _ = next(unlabeled_data_iter)
                    x_unlabeled = x_unlabeled_raw.to(device)

            # 2. Z-Compression Augmentation (20% chance): take a thinner Z
            # window (80% of config.num_layers, min 4) and trilinearly resize
            # back to the model's expected depth. Despite the historical
            # "Anisotropic Z-Interpolation" comment, z_len is deterministic
            # at max(4, int(num_layers*0.8)) — not random.
            z_start = np.random.randint(0, 8)
            if (
                not getattr(config, "disable_augmentation", False)
            ) and np.random.rand() > 0.8:
                z_len = max(4, int(config.num_layers * 0.8))
                x_orig = x_raw[:, :, z_start : z_start + z_len]
                if z_len != config.num_layers:
                    x_orig = F.interpolate(
                        x_orig,
                        size=(config.num_layers, config.patch_size, config.patch_size),
                        mode="trilinear",
                        align_corners=False,
                    )

                if x_unlabeled is not None:
                    x_unl_orig = x_unlabeled[:, :, z_start : z_start + z_len]
                    if z_len != config.num_layers:
                        x_unl_orig = F.interpolate(
                            x_unl_orig,
                            size=(
                                config.num_layers,
                                config.patch_size,
                                config.patch_size,
                            ),
                            mode="trilinear",
                            align_corners=False,
                        )
            else:
                x_orig = x_raw[:, :, z_start : z_start + config.num_layers]
                if x_unlabeled is not None:
                    x_unl_orig = x_unlabeled[
                        :, :, z_start : z_start + config.num_layers
                    ]

        except StopIteration:
            data_iter = iter(data_loader)
            continue

        # 3. Per-patch fiber pseudo-label for the fiber head's loss.
        # source="frangi": dataloader already computed Frangi vesselness for
        # this patch and z-collapsed it; we use it as-is and only normalize.
        # source="sobel_z" (default): compute Sobel-Z gradient of CT inline
        # on GPU (cheap, current behavior).
        with torch.no_grad():
            if getattr(config, "target_fiber_source", "sobel_z") == "frangi":
                # target_fiber_from_loader: [B, 1, 1, H, W] z-collapsed already
                target_fiber = target_fiber_from_loader
            else:
                # Sobel-Z pseudo-label (BEFORE mixup to avoid boundary artifacts).
                # Use only the raw CT channel (index 0) for pseudo-labels.
                grad_z = x_orig[:, :1, 1:] - x_orig[:, :1, :-1]
                target_fiber = grad_z.abs().mean(dim=2, keepdim=True)
            # Per-batch min-max normalize so the BCE target sits in [0, 1].
            b_sz = target_fiber.shape[0]
            tf_flat = target_fiber.view(b_sz, -1)
            tf_min = tf_flat.min(dim=1, keepdim=True)[0].view(b_sz, 1, 1, 1, 1)
            tf_max = tf_flat.max(dim=1, keepdim=True)[0].view(b_sz, 1, 1, 1, 1)
            target_fiber = (target_fiber - tf_min) / (tf_max - tf_min + 1e-8)

        if (not getattr(config, "disable_augmentation", False)) and x_orig.size(0) > 1:
            r = np.random.rand()
            if r < 0.2:
                x_orig, target_ink, target_fiber, _ = mixup_data(
                    x_orig, target_ink, target_fiber
                )
            elif r < 0.4:
                x_orig, target_ink, target_fiber, _ = cutmix_data(
                    x_orig, target_ink, target_fiber
                )

        # Generate two augmented views for DINO-Lite Consistency
        x_aug1, target_ink_aug1, target_fiber_aug1 = apply_augmentations(
            x_orig, target_ink, target_fiber, step, max_steps, config=config
        )
        x_aug2, _, _ = apply_augmentations(
            x_orig, target_ink, target_fiber, step, max_steps, config=config
        )

        # UAMT Unlabeled Augmentations
        if config.use_uamt and x_unlabeled is not None:
            dummy_ink = torch.zeros(
                (x_unl_orig.shape[0], 1, x_unl_orig.shape[3], x_unl_orig.shape[4]),
                device=device,
            )
            dummy_fiber = torch.zeros(
                (x_unl_orig.shape[0], 1, 1, x_unl_orig.shape[3], x_unl_orig.shape[4]),
                device=device,
            )
            x_unl_aug_student, _, _ = apply_augmentations(
                x_unl_orig, dummy_ink, dummy_fiber, step, max_steps, config=config
            )
            x_unl_aug_teacher, _, _ = apply_augmentations(
                x_unl_orig, dummy_ink, dummy_fiber, step, max_steps, config=config
            )

        # Compute Structure Tensor targets on the fly for view 1
        with torch.no_grad():
            if st_computer:
                # x_aug1 is [B, 1, D, H, W] or [B, 2, D, H, W]
                # ST computer expects [B, 1, D, H, W]
                st_input = x_aug1[:, :1]
                target_st = st_computer.compute(st_input)  # [B, 6, D, H, W]
            else:
                target_st = None

        # Disable anomaly detection for normal training
        torch.autograd.set_detect_anomaly(False)
        optimizer.zero_grad(set_to_none=True)
        with autocast(device_type=device.type, enabled=amp_enabled):
            # Forward pass for view 1 (full multi-task if supported)
            model_out = model(
                x_aug1,
                return_fiber=True,
                return_qc=True,
                return_proj=True,
                return_st=True,
            )
            if isinstance(model_out, tuple):
                out_ink_2d = model_out[0]
                # Diagnostic check: Isolate if NaN comes from backbone forward pass
                if torch.isnan(out_ink_2d).any():
                    print(
                        f"DEBUG: NaN detected in model backbone output (out_ink_2d) at step {step}"
                    )
                # Map remaining outputs if they exist
                # This is a bit brittle, but works with our current return order
                out_fiber = model_out[1] if len(model_out) > 1 else None
                out_qc = model_out[2] if len(model_out) > 2 else None
                p1 = model_out[3] if len(model_out) > 3 else None
                out_st = model_out[4] if len(model_out) > 4 else None
            else:
                out_ink_2d = model_out
                out_fiber = out_qc = p1 = out_st = None

            # --- START FIX: Prevent NaN/Inf loss from AMP float16 overflow ---
            if out_ink_2d is not None:
                out_ink_2d = torch.nan_to_num(
                    out_ink_2d, nan=0.0, posinf=100.0, neginf=-100.0
                ).clamp(-100.0, 100.0)
            if out_fiber is not None:
                out_fiber = torch.nan_to_num(
                    out_fiber, nan=0.0, posinf=100.0, neginf=-100.0
                ).clamp(-100.0, 100.0)
            if out_qc is not None:
                out_qc = torch.nan_to_num(
                    out_qc, nan=0.0, posinf=100.0, neginf=-100.0
                ).clamp(-100.0, 100.0)
            # out_st (structure-tensor head) and p1 (projection for the consistency
            # loss) were previously left unsanitized, so a non-finite value in either
            # NaN'd the ST / Cons loss terms and skipped the step. Sanitize them too.
            if out_st is not None:
                out_st = torch.nan_to_num(
                    out_st, nan=0.0, posinf=100.0, neginf=-100.0
                ).clamp(-100.0, 100.0)
            if p1 is not None:
                p1 = torch.nan_to_num(p1, nan=0.0, posinf=100.0, neginf=-100.0).clamp(
                    -100.0, 100.0
                )
            # --- END FIX ---

            # Forward pass for view 2 (consistency only)
            if p1 is not None:
                p2_out = model(x_aug2, return_proj=True)
                if isinstance(p2_out, tuple):
                    # InkDetectorOptimized returns [ink, fiber, qc, proj, st]
                    # if only return_proj=True: [ink, proj]
                    p2 = p2_out[1]
                    if p2 is not None:
                        p2 = torch.nan_to_num(
                            p2, nan=0.0, posinf=100.0, neginf=-100.0
                        ).clamp(-100.0, 100.0)
                else:
                    p2 = None  # Should not happen if return_proj=True
            else:
                p2 = None

            # UAMT Forward Passes
            uamt_loss = torch.tensor(0.0, device=device)
            if config.use_uamt and x_unlabeled is not None and ema_model is not None:
                student_out = model(x_unl_aug_student)
                student_ink = (
                    student_out[0] if isinstance(student_out, tuple) else student_out
                )
                # Sanitize the UA-MT student forward the same way the main forward is
                # sanitized (see nan_to_num at the supervised forward): this separate
                # unlabeled forward pass is otherwise unguarded, so a non-finite student
                # prediction here NaNs the consistency MSE and the whole loss.
                student_ink = torch.nan_to_num(student_ink)
                student_prob = torch.sigmoid(student_ink)

                with torch.no_grad():
                    # UAMT: T stochastic forward passes to estimate epistemic uncertainty
                    T = 4
                    ema_model.train()  # Enable dropout for stochastic passes
                    teacher_preds = []
                    for _ in range(T):
                        # Add small gaussian noise to input for extra stochasticity
                        noise = torch.randn_like(x_unl_aug_teacher) * 0.01
                        t_out = ema_model(x_unl_aug_teacher + noise)
                        t_ink = t_out[0] if isinstance(t_out, tuple) else t_out
                        # Belt-and-suspenders: sanitize the teacher output the same way
                        # the student output is sanitized (see nan_to_num above), so a
                        # non-finite teacher prediction can never NaN the consistency loss.
                        t_ink = torch.nan_to_num(t_ink)
                        teacher_preds.append(torch.sigmoid(t_ink))

                    teacher_preds = torch.stack(teacher_preds)  # [T, B, 1, H, W]
                    if torch.isnan(teacher_preds).any():
                        print(f"DEBUG: NaN detected in teacher_preds at step {step}")
                    teacher_prob = torch.mean(teacher_preds, dim=0)  # [B, 1, H, W]
                    teacher_var = torch.var(teacher_preds, dim=0)  # [B, 1, H, W]
                    if torch.isnan(teacher_var).any():
                        print(f"DEBUG: NaN detected in teacher_var at step {step}")
                    ema_model.eval()  # Restore eval mode

                # Uncertainty-Aware Consistency Loss: Weight MSE by exp(-variance)
                uncertainty_weight = torch.exp(-teacher_var)
                if torch.isnan(uncertainty_weight).any():
                    print(f"DEBUG: NaN in uncertainty_weight at step {step}")
                mse_loss = F.mse_loss(student_prob, teacher_prob, reduction="none")
                if torch.isnan(mse_loss).any():
                    print(f"DEBUG: NaN in mse_loss at step {step}")
                uamt_loss = config.consistency_weight * torch.mean(
                    uncertainty_weight * mse_loss
                )

            # Supervised Losses
            if getattr(config, "use_confidence_weight", False):
                # Soft pseudo-labels encode the uncertain band as 0.5; down-weight
                # those pixels to ~0 so they contribute no gradient. No-op on true
                # binary labels (weight == 1 everywhere).
                conf_w = confidence_weight(target_ink_aug1)
                bce_map = F.binary_cross_entropy_with_logits(
                    out_ink_2d, target_ink_aug1.clamp(0, 1), reduction="none"
                )
                loss_ink = (bce_map * conf_w).sum() / conf_w.sum().clamp_min(1.0)
                loss_dice = compute_dice_loss(
                    out_ink_2d, target_ink_aug1.clamp(0, 1), weight=conf_w
                )
            elif config.label_smoothing > 0:
                smoothed_target = (
                    target_ink_aug1 * (1.0 - config.label_smoothing)
                    + 0.5 * config.label_smoothing
                )
                loss_ink = F.binary_cross_entropy_with_logits(
                    out_ink_2d, smoothed_target
                )
                loss_dice = compute_dice_loss(out_ink_2d, target_ink_aug1)
            else:
                loss_ink = F.binary_cross_entropy_with_logits(
                    out_ink_2d, target_ink_aug1, pos_weight=None, reduction="mean"
                )
                loss_dice = compute_dice_loss(out_ink_2d, target_ink_aug1)

            loss_betti = (
                betti_loss(out_ink_2d, target_ink_aug1)
                if betti_loss is not None
                else 0.0
            )

            loss_cldice = (
                cldice_loss(out_ink_2d, target_ink_aug1)
                if cldice_loss is not None
                else torch.tensor(0.0, device=device)
            )

            loss_fiber = torch.tensor(0.0, device=device)
            if out_fiber is not None:
                out_fiber_2d = torch.mean(out_fiber, dim=2, keepdim=True)
                loss_fiber = F.binary_cross_entropy_with_logits(
                    out_fiber_2d, target_fiber_aug1
                )

            loss_qc = torch.tensor(0.0, device=device)
            hallucination_penalty = torch.tensor(0.0, device=device)
            if out_qc is not None:
                target_qc = target_fiber_aug1.mean(dim=(-3, -2, -1)).view(-1)
                loss_qc = F.binary_cross_entropy_with_logits(out_qc.view(-1), target_qc)
                B = out_ink_2d.shape[0]
                hallucination_penalty = (
                    torch.sigmoid(out_ink_2d)
                    * (1.0 - torch.sigmoid(out_qc).view(B, 1, 1, 1))
                ).mean()

            loss_st_val = torch.tensor(0.0, device=device)
            if out_st is not None and target_st is not None:
                loss_st_val = F.mse_loss(out_st, target_st)

            consistency_loss = torch.tensor(0.0, device=device)
            if config.use_uamt and p1 is not None and p2 is not None:
                consistency_loss = (
                    1.0 - F.cosine_similarity(p1, p2, dim=1, eps=1e-6).mean()
                )
            total_loss = (
                config.loss_ink_bce * loss_ink
                + config.loss_ink_dice * loss_dice
                + config.loss_fiber_bce * loss_fiber
                + (config.betti_loss_weight * loss_betti)
                + (config.cldice_weight * loss_cldice)
                + 0.1 * loss_qc
                + 0.02 * hallucination_penalty
                + config.loss_st * loss_st_val
                + (
                    config.consistency_weight * consistency_loss
                    if config.use_uamt
                    else 0.0
                )
                + uamt_loss
            )

        # Pre-backward check
        if not torch.isfinite(total_loss) or total_loss.item() > 1e6:
            print(
                f"\n[WARNING] Numerical Instability at Step {step}: Loss {total_loss.item() if torch.isfinite(total_loss) else 'NaN'}"
            )
            print(
                f"Ink: {loss_ink.item():.2e}, Dice: {loss_dice.item():.2e}, Fiber: {loss_fiber.item():.2e}, QC: {loss_qc.item():.2e}, ST: {loss_st_val.item():.2e}, Halluc: {hallucination_penalty.item():.2e}, UAMT: {uamt_loss.item():.2e}, Cons: {consistency_loss.item():.2e}, Betti: {loss_betti.item() if isinstance(loss_betti, torch.Tensor) else loss_betti:.2e}, clDice: {loss_cldice.item():.2e}"
            )
            # Detailed NaN source diagnostics
            if torch.isnan(out_ink_2d).any():
                print(" -> out_ink_2d has NaN")
            if torch.isnan(target_ink_aug1).any():
                print(" -> target_ink_aug1 has NaN")
            if out_fiber is not None and torch.isnan(out_fiber).any():
                print(" -> out_fiber has NaN")

            optimizer.zero_grad(set_to_none=True)
            # We MUST provide a dummy backward pass with 0 loss to keep GradScaler state valid,
            # otherwise it will either crash (AssertionError) or stall.
            total_loss = torch.tensor(0.0, device=device, requires_grad=True)

        scaler.scale(total_loss).backward()
        scaler.unscale_(optimizer)

        # Diagnostic check for NaNs in gradients or weights
        for name, param in model.named_parameters():
            if param.grad is not None and torch.isnan(param.grad).any():
                print(f"DEBUG: NaN in gradient for {name} at step {step}")
            if torch.isnan(param).any():
                print(f"DEBUG: NaN in weights for {name} at step {step}")

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()

        # Debug: Log current learning rate
        if step % 10 == 0:
            current_lr = scheduler.get_last_lr()[0]

        # UAMT: Update Teacher EMA
        if config.use_uamt and ema_model is not None:
            with torch.no_grad():
                decay = config.ema_decay
                for param_student, param_teacher in zip(
                    model.parameters(), ema_model.parameters(), strict=False
                ):
                    # Never absorb a (transiently) non-finite student weight: a single
                    # NaN/Inf would poison the teacher permanently (NaN * decay == NaN),
                    # which then NaNs the consistency loss for the rest of the cycle.
                    if not torch.isfinite(param_student.data).all():
                        continue
                    param_teacher.data.mul_(decay).add_(
                        param_student.data, alpha=1.0 - decay
                    )

        dt = time.time() - t0
        total_training_time += dt
        loss_val = total_loss.item()
        smooth_loss = 0.9 * smooth_loss + 0.1 * loss_val if step > 0 else loss_val

        if step % 10 == 0:
            remaining = max(0, config.time_budget - total_training_time)
            print(
                f"Step {step:04d} | Loss: {smooth_loss:.6f} | dt: {dt * 1000:.0f}ms | Remaining: {remaining:.0f}s"
            )
            sys.stdout.flush()
            wandb_tracking.log(
                {
                    "train/total_loss": loss_val,
                    "train/smooth_loss": smooth_loss,
                    "train/loss_ink": float(loss_ink.item()),
                    "train/loss_dice": float(loss_dice.item()),
                    "train/loss_fiber": float(loss_fiber.item()),
                    "train/loss_cldice": float(loss_cldice.item()),
                    "train/throughput_ms": dt * 1000,
                },
                step=step,
            )

        step += 1
        if (
            getattr(config, "eval_every_steps", 0)
            and step % config.eval_every_steps == 0
        ):
            periodic_pixel_auc_eval(
                model,
                val_data_loader.dataset,
                config,
                device,
                step,
                total_training_time,
            )
        if total_training_time >= config.time_budget:
            break

    print(
        "Evaluating metrics on 100 ink-containing patches (searching for best threshold)..."
    )
    if not SKELETON_DISTANCE_AVAILABLE:
        print(
            f"  Skeleton-distance metric unavailable: {SKELETON_DISTANCE_IMPORT_ERROR}"
        )
    sys.stdout.flush()
    val_losses = []
    val_skel_dists = []
    val_centerline_dices = []
    val_cc_diffs = []
    val_crit_comps = []
    val_mean_aps = []
    validation_diag = {
        "requested_patches": 100,
        "empty_target_patches": 0,
        "batch_errors": 0,
        "cc_errors": 0,
        "skeleton_errors": 0,
        "centerline_errors": 0,
        "mean_ap_errors": 0,
    }

    all_probs = []
    all_targets = []

    model.eval()
    torch.manual_seed(42)
    with torch.no_grad():
        for val_idx in range(100):
            try:
                val_x_raw, val_target, _val_fiber = next(val_data_iter)
                val_x = val_x_raw[:, :, 4 : 4 + config.num_layers].to(device)
                if val_target is not None and val_target.numel() > 0:
                    val_target = val_target.to(device)
                    if val_target.dim() == 3:
                        val_target = val_target.unsqueeze(1)

                    target_sum = torch.sum(val_target.float())
                    if target_sum < 1.0:
                        validation_diag["empty_target_patches"] += 1
                        continue

                    with autocast(device_type=device.type, enabled=amp_enabled):
                        val_out = model(val_x)
                        if isinstance(val_out, tuple):
                            out_2d = val_out[0]
                        else:
                            out_2d = val_out

                    prob_2d = torch.sigmoid(out_2d)
                    all_probs.append(prob_2d.cpu())
                    all_targets.append(val_target.cpu())

            except StopIteration:
                val_data_iter = iter(val_data_loader)
            except Exception as exc:
                validation_diag["batch_errors"] += 1
                if validation_diag["batch_errors"] <= 3:
                    print(
                        f"  Warning: validation batch {val_idx} failed: {type(exc).__name__}: {exc}"
                    )

    best_dice = 0.0
    best_threshold = 0.5
    if all_probs:
        probs_cat = torch.cat(all_probs)
        targets_cat = torch.cat(all_targets)

        # Search for best threshold to get a real signal of learning
        for t in np.linspace(0.01, 0.8, 40):
            dice = compute_official_dice(targets_cat, probs_cat, threshold=t)
            if dice > best_dice:
                best_dice = dice
                best_threshold = t

        print(
            f"  Best Validation Dice: {best_dice:.6f} at threshold {best_threshold:.3f}"
        )

        # The topology gates (skel_dist, centerline_dice, cc_diff) are evaluated
        # at the threshold that maximizes centerline_dice, not the Dice-optimal
        # one — see select_topology_threshold(). val_bpb stays on the Dice
        # threshold since it is defined as 1 - Dice.
        topo_threshold, topo_cd = select_topology_threshold(all_probs, all_targets)
        print(
            f"  Topology threshold: {topo_threshold:.3f} (centerline_dice {topo_cd:.6f})"
        )

        # Now re-run with best threshold for other metrics
        for i in range(len(all_probs)):
            prob_2d = all_probs[i]
            val_target = all_targets[i]
            val_losses.append(
                1.0
                - compute_official_dice(val_target, prob_2d, threshold=best_threshold)
            )

            try:
                gt_bin_b = (val_target > 0.5).numpy().astype(bool)
                pred_bin_b = (prob_2d > topo_threshold).numpy().astype(bool)
                for b in range(gt_bin_b.shape[0]):
                    val_cc_diffs.append(
                        compute_cc_diff(gt_bin_b[b, 0], pred_bin_b[b, 0])
                    )
                    val_crit_comps.append(
                        compute_crit_comps(gt_bin_b[b, 0], pred_bin_b[b, 0])
                    )

                    try:
                        ap_res = compute_mean_ap(
                            gt_bin_b[b, 0].astype(np.uint8),
                            prob_2d[b, 0].numpy().astype(np.float32),
                            ignore_index=0,
                        )
                        val_mean_aps.append(ap_res.get("mAP", 0.0))
                    except Exception as exc:
                        validation_diag["mean_ap_errors"] += 1
                        if validation_diag["mean_ap_errors"] <= 3:
                            print(
                                f"  Warning: mean_ap metric failed: {type(exc).__name__}: {exc}"
                            )
            except Exception as exc:
                validation_diag["cc_errors"] += 1
                if validation_diag["cc_errors"] <= 3:
                    print(
                        f"  Warning: connected-component metric failed for validation sample {i}: {type(exc).__name__}: {exc}"
                    )

            if i % 10 == 0:
                gt_3d = np.squeeze((val_target > 0.5).numpy().astype(bool))
                pred_3d = np.squeeze((prob_2d > topo_threshold).numpy().astype(bool))
                if gt_3d.ndim == 2:
                    gt_3d = gt_3d[np.newaxis, ...]
                if pred_3d.ndim == 2:
                    pred_3d = pred_3d[np.newaxis, ...]
                try:
                    skel_dist = compute_skeleton_dist(gt_3d, pred_3d)
                    if not np.isnan(skel_dist):
                        val_skel_dists.append(skel_dist)
                except Exception as exc:
                    validation_diag["skeleton_errors"] += 1
                    if validation_diag["skeleton_errors"] <= 3:
                        print(
                            f"  Warning: skeleton-distance metric failed for validation sample {i}: {type(exc).__name__}: {exc}"
                        )
                try:
                    cd = compute_centerline_dice(gt_3d, pred_3d, tolerance_radius=3.0)
                    cd_val = cd.get("centerline_dice", 0.0)
                    if not np.isnan(cd_val):
                        val_centerline_dices.append(cd_val)
                except Exception as exc:
                    validation_diag["centerline_errors"] += 1
                    if validation_diag["centerline_errors"] <= 3:
                        print(
                            f"  Warning: centerline-dice metric failed for validation sample {i}: {type(exc).__name__}: {exc}"
                        )

    validation_diag.update(
        {
            "usable_patches": len(all_probs),
            "skel_samples": len(val_skel_dists),
            "centerline_samples": len(val_centerline_dices),
            "cc_samples": len(val_cc_diffs),
            "crit_samples": len(val_crit_comps),
        }
    )

    val_bpb = np.mean(val_losses) if val_losses else 1.0
    avg_skel_dist = np.mean(val_skel_dists) if val_skel_dists else float("nan")
    avg_centerline_dice = np.mean(val_centerline_dices) if val_centerline_dices else 0.0
    avg_cc_diff = np.mean(val_cc_diffs) if val_cc_diffs else 0.0
    avg_crit_comp = np.mean(val_crit_comps) if val_crit_comps else 0.0
    avg_mean_ap = np.mean(val_mean_aps) if val_mean_aps else 0.0
    prize_gates = evaluate_prize_gates(
        config,
        val_bpb,
        avg_skel_dist,
        avg_centerline_dice,
        avg_cc_diff,
        len(val_skel_dists),
        len(val_centerline_dices),
        len(val_cc_diffs),
    )
    window_mm = prize_gates["window_mm"]
    window_ok = prize_gates["window_ok"]
    villa_metrics_ok = prize_gates["villa_metrics_ok"]
    submittable = prize_gates["submittable"]
    prize_gate_failures = prize_gates["failures"]
    submittable = bool(window_ok and villa_metrics_ok)
    log_file = "results.tsv"
    is_improvement = True
    if np.isnan(val_bpb):
        is_improvement = False
    if getattr(config, "enforce_prize_gates", True) and not submittable:
        is_improvement = False

    best_previous_val_bpb = 1.0
    best_previous_avg_centerline_dice = 0.0
    if os.path.exists("best_model.pt"):
        try:
            chk = torch.load("best_model.pt", map_location="cpu", weights_only=False)
            best_previous_val_bpb = chk.get("val_bpb", 1.0)
            best_previous_avg_centerline_dice = chk.get("avg_centerline_dice", 0.0)
        except Exception as exc:
            print(
                f"Warning: could not load best_model.pt for improvement comparison: {type(exc).__name__}: {exc}"
            )

    if is_improvement:
        is_improvement = is_model_improvement(
            val_bpb,
            avg_centerline_dice,
            best_previous_val_bpb,
            best_previous_avg_centerline_dice,
        )

    peak_vram_mb = torch.cuda.max_memory_allocated() / 1024**2
    num_params_M = sum(p.numel() for p in model.parameters()) / 1e6
    throughput_Mvps = (
        step
        * config.batch_size
        * config.num_layers
        * config.patch_size**2
        / total_training_time
        / 1e6
    )

    print("\n--- Foundation Pretraining Complete ---")
    print(
        f"val_bpb (Official):    {val_bpb:.6f} {'[NEW BEST]' if is_improvement else ''}"
    )
    print(f"avg_skel_dist:         {avg_skel_dist:.6f}")
    print(f"avg_centerline_dice:   {avg_centerline_dice:.6f}")
    print(f"avg_cc_diff:           {avg_cc_diff:.3f}")
    print(f"avg_crit_comp:         {avg_crit_comp:.3f}")
    print(f"avg_mean_ap:           {avg_mean_ap:.4f}")

    wandb_tracking.log(
        {
            "val/val_bpb": val_bpb,
            "val/dice": best_dice,
            "val/skel_dist": avg_skel_dist,
            "val/centerline_dice": avg_centerline_dice,
            "val/cc_diff": avg_cc_diff,
            "val/mean_ap": avg_mean_ap,
            "val/peak_vram_mb": peak_vram_mb,
            "val/throughput_Mvps": throughput_Mvps,
        }
    )
    if wandb_run is not None and all_probs:
        wandb_tracking.log_prediction_image(
            wandb_run,
            all_probs[0][0].numpy(),
            all_targets[0][0].numpy(),
            topo_threshold,
        )
    print(f"submittable:           {submittable} (window={window_mm:.3f}mm)")
    if prize_gate_failures:
        print("prize_gate_failures:   " + " | ".join(prize_gate_failures))
    print(
        "validation_diag:       "
        f"usable={validation_diag['usable_patches']}/{validation_diag['requested_patches']}, "
        f"empty={validation_diag['empty_target_patches']}, "
        f"batch_errors={validation_diag['batch_errors']}, "
        f"cc_errors={validation_diag['cc_errors']}, "
        f"skeleton_errors={validation_diag['skeleton_errors']}, "
        f"centerline_errors={validation_diag['centerline_errors']}, "
        f"mean_ap_errors={validation_diag['mean_ap_errors']}"
    )
    print(f"train_loss:            {smooth_loss:.6f}")
    print(f"throughput_Mvps:       {throughput_Mvps:.2f}")
    sys.stdout.flush()

    # Log EVERY run to history.tsv for auditability — UNLESS this is an isolated
    # experiment run (checkpoint_out set), which must not touch loop state.
    if not getattr(config, "checkpoint_out", None):
        history_file = "history.tsv"
        history_header = "timestamp\tval_bpb\tavg_skel_dist\tavg_centerline_dice\tavg_cc_diff\tavg_crit_comp\tavg_mean_ap\ttrain_loss\tthroughput_Mvps\tnum_params_M\tpeak_vram_mb\tconfig\n"
        if not os.path.exists(history_file):
            with open(history_file, "w") as f:
                f.write(history_header)

        with open(history_file, "a") as f:
            cfg_json = json.dumps(asdict(config))
            f.write(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{val_bpb:.6f}\t{avg_skel_dist:.6f}\t{avg_centerline_dice:.6f}\t{avg_cc_diff:.3f}\t{avg_crit_comp:.3f}\t{avg_mean_ap:.4f}\t{smooth_loss:.6f}\t{throughput_Mvps:.2f}\t{num_params_M:.3f}\t{peak_vram_mb:.1f}\t{cfg_json}\n"
            )
            f.flush()

    ckpt_out = getattr(config, "checkpoint_out", None)
    if ckpt_out:
        ckpt_dir = os.path.dirname(ckpt_out)
        if ckpt_dir:
            os.makedirs(ckpt_dir, exist_ok=True)
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "val_bpb": val_bpb,
                "avg_skel_dist": avg_skel_dist,
                "avg_centerline_dice": avg_centerline_dice,
                "avg_cc_diff": avg_cc_diff,
                "avg_mean_ap": avg_mean_ap,
                "submittable": submittable,
                "window_ok": window_ok,
                "window_mm": window_mm,
                "villa_metrics_ok": villa_metrics_ok,
                "config": asdict(config),
            },
            ckpt_out,
        )
        print(f"Saved experiment checkpoint to {ckpt_out} (loop state untouched)")
    elif is_improvement:
        print(f"Saving new best model with val_bpb: {val_bpb:.6f}")
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "val_bpb": val_bpb,
                "avg_skel_dist": avg_skel_dist,
                "avg_centerline_dice": avg_centerline_dice,
                "avg_cc_diff": avg_cc_diff,
                "avg_mean_ap": avg_mean_ap,
                "submittable": submittable,
                "window_ok": window_ok,
                "window_mm": window_mm,
                "villa_metrics_ok": villa_metrics_ok,
                "prize_gate_failures": prize_gate_failures,
                "validation_diag": validation_diag,
                "config": asdict(config),
            },
            "best_model.pt",
        )

        header = "timestamp\tval_bpb\tavg_skel_dist\tavg_centerline_dice\tavg_cc_diff\tavg_crit_comp\ttrain_loss\tthroughput_Mvps\tnum_params_M\tpeak_vram_mb\tconfig\n"
        if not os.path.exists(log_file):
            with open(log_file, "w") as f:
                f.write(header)
                f.flush()
                os.fsync(f.fileno())

        with open(log_file, "a") as f:
            cfg_json = json.dumps(asdict(config))
            f.write(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{val_bpb:.6f}\t{avg_skel_dist:.6f}\t{avg_centerline_dice:.6f}\t{avg_cc_diff:.3f}\t{avg_crit_comp:.3f}\t{smooth_loss:.6f}\t{throughput_Mvps:.2f}\t{num_params_M:.3f}\t{peak_vram_mb:.1f}\t{cfg_json}\n"
            )
            f.flush()
            os.fsync(f.fileno())

        prize_log_file = "prize_readiness.tsv"
        prize_header = "timestamp\tsubmittable\twindow_ok\twindow_mm\tvilla_metrics_ok\tpatch_size\tval_bpb\tavg_skel_dist\tavg_centerline_dice\tavg_cc_diff\tavg_crit_comp\tconfig\n"
        if not os.path.exists(prize_log_file):
            with open(prize_log_file, "w") as f:
                f.write(prize_header)
                f.flush()
                os.fsync(f.fileno())

        with open(prize_log_file, "a") as f:
            f.write(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{submittable}\t{window_ok}\t{window_mm:.4f}\t{villa_metrics_ok}\t{config.patch_size}\t{val_bpb:.6f}\t{avg_skel_dist:.6f}\t{avg_centerline_dice:.6f}\t{avg_cc_diff:.3f}\t{avg_crit_comp:.3f}\t{cfg_json}\n"
            )
            f.flush()
            os.fsync(f.fileno())

        # Ensure filesystem sync (so best_model.pt / results.tsv / prize_readiness.tsv
        # are durable before the cycle returns).
        if hasattr(os, "sync"):
            os.sync()
    else:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "val_bpb": val_bpb,
                "avg_skel_dist": avg_skel_dist,
                "avg_centerline_dice": avg_centerline_dice,
                "avg_cc_diff": avg_cc_diff,
                "submittable": submittable,
                "window_ok": window_ok,
                "window_mm": window_mm,
                "villa_metrics_ok": villa_metrics_ok,
                "prize_gate_failures": prize_gate_failures,
                "validation_diag": validation_diag,
                "config": asdict(config),
            },
            "last_model.pt",
        )

    if not is_improvement:
        print("\n[RESULT] No improvement detected. Recommended: Revert.")
    else:
        print("\n[RESULT] Improvement detected! Recommended: Keep changes.")

    result_data = {
        "val_bpb": float(val_bpb),
        "avg_skel_dist": float(avg_skel_dist),
        "avg_centerline_dice": float(avg_centerline_dice),
        "avg_cc_diff": float(avg_cc_diff),
        "avg_crit_comp": float(avg_crit_comp),
        "avg_mean_ap": float(avg_mean_ap),
        "train_loss": float(smooth_loss),
        "throughput_Mvps": float(throughput_Mvps),
        "num_params_M": float(num_params_M),
        "peak_vram_mb": float(peak_vram_mb),
        "submittable": bool(submittable),
        "window_ok": bool(window_ok),
        "window_mm": float(window_mm),
        "villa_metrics_ok": bool(villa_metrics_ok),
        "prize_gate_failures": prize_gate_failures,
        "validation_diag": validation_diag,
        "is_success": bool(is_improvement),
    }

    # Cleanup multiprocessing iterators to avoid leaked semaphores
    del data_iter
    del data_loader
    if unlabeled_data_iter is not None:
        del unlabeled_data_iter
        del unlabeled_data_loader
    del val_data_iter
    del val_data_loader

    # Write run_result.json as the VERY LAST step
    with open("run_result.json", "w") as f:
        json.dump(result_data, f, indent=4)
        f.flush()
        os.fsync(f.fileno())

    wandb_tracking.finish_run(wandb_run)


if __name__ == "__main__":
    import torch.multiprocessing as mp

    try:
        mp.set_start_method("spawn")
    except RuntimeError:
        pass

    class TrainArgs(Tap):
        config: str = "config.json"  # Path to configuration JSON
        test: bool = False  # Run a 30s smoke test
        smoke: bool = False  # Preflight: build model + one fwd/bwd, then exit

    args = TrainArgs().parse_args()

    if os.path.exists(args.config):
        config = ExperimentConfig.load(args.config)
    else:
        config = ExperimentConfig()
        config.save(args.config)

    if args.smoke:
        try:
            preflight_smoke(config)
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"PREFLIGHT FAILED: {e}")
            sys.stdout.flush()
            sys.exit(1)
        print("PREFLIGHT OK")
        sys.stdout.flush()
        sys.exit(0)

    if args.test:
        config.time_budget = 30
        train(config)
    else:
        train(config)
