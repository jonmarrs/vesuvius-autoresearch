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

import atexit
import copy
import functools
import json
import math
import time
from dataclasses import asdict

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
from torch.utils.data import DataLoader, default_collate

from scripts import wandb_tracking
from scripts.betti_loss_module import BettiLoss
from scripts.cldice_loss import SoftClDiceLoss
from scripts.training.config import AuxiliaryConfig, ExperimentConfig
from scripts.training.promotion import (
    RESCORE_COMMAND,
    VALIDATION_LABEL_FILES,
    VALIDATION_PROTOCOL,
    IncumbentUnavailable,
    read_incumbent,
    save_checkpoint_atomic,
    scores_ink_free_patches,
    validation_indices,
    validation_input_paths,
    validation_inputs_fingerprint,
    validation_label_path,
    validation_protocol,
)
from scroll_augmentations import apply_scroll_specific_3d_augmentations

try:
    sys.path.append(os.path.join(os.path.dirname(__file__), "villa/vesuvius/src"))
    from vesuvius.models.build.primus_wrapper import PrimusEncoder
except ImportError:
    PrimusEncoder = None


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
# villa's skeleton metric saves a histogram PNG on every call, to "." unless
# told otherwise; send them to the gitignored outputs/ instead.
SKELETON_HIST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "outputs", "skeleton_hists"
)
try:
    from metrics.skeleton_distance_length import compute as _villa_skeleton_dist

    def compute_skeleton_dist(label, prediction, **kwargs):
        kwargs.setdefault("output_folder", SKELETON_HIST_DIR)
        return _villa_skeleton_dist(label, prediction, **kwargs)

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
        raise RuntimeError("villa mean_ap metric is unavailable")


def _as_hwd(mask: np.ndarray) -> np.ndarray:
    """A 2D (H, W) patch as villa's single-slice (H, W, 1) volume."""
    mask = np.asarray(mask)
    return mask[..., np.newaxis] if mask.ndim == 2 else mask


try:
    from metrics.connected_components import compute as compute_cc_official

    def compute_cc_diff(gt_bin: np.ndarray, pred_bin: np.ndarray) -> int:
        # Villa requires [H, W, D]; a 2D patch is one slice. Passing (H, W)
        # raised, and returning 0 on that error made every patch a perfect
        # match, so the cc_diff gate could never fail. Errors now reach the
        # caller, which counts them (validation_diag["cc_errors"]).
        res = compute_cc_official(
            _as_hwd(gt_bin), _as_hwd(pred_bin), num_classes=2, ignore_index=0
        )
        return int(res["connected_components_difference_total"])
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
        # Same [H, W, D] requirement; villa reports positive and negative
        # counts (there is no "_total" key, so this was 0 even when it ran).
        res = compute_crit_official(_as_hwd(gt_bin), _as_hwd(pred_bin))
        return int(
            res["critical_components_positive"] + res["critical_components_negative"]
        )
except ImportError:

    def compute_crit_comps(gt_bin: np.ndarray, pred_bin: np.ndarray) -> int:
        raise RuntimeError("villa critical_components metric is unavailable")


def load_shape_compatible_state(module, state_dict, label):
    """Load the tensors of state_dict whose names and shapes match module's;
    returns how many loaded."""
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
    return len(compatible)


def foundation_encoder_state(state_dict):
    """A LeJEPA checkpoint's encoder weights, named as PrimusNetwork's
    shared_encoder names them, mapped as villa's TrainFineTuneLEJEPA maps them:
    wrapper prefixes (DDP's "module.", torch.compile's "_orig_mod.") removed,
    "encoder.*" and "shared_encoder.*" taken by their prefix, the rest (the
    projector) left out."""
    encoder = {}
    for key, value in state_dict.items():
        while key.startswith(("module.", "_orig_mod.")):
            key = key.split(".", 1)[1]
        for prefix in ("encoder.", "shared_encoder."):
            if key.startswith(prefix):
                encoder[key[len(prefix) :]] = value
                break
    return encoder


# A LeJEPA encoder must fill nearly all of shared_encoder. A matched one
# misses at most its position embedding (another input shape) and its stem's
# convolutions (other in_channels): 5 of 280 entries. One of another size
# (pretraining defaults to "M"; LeJEPAUNet builds "S") fits only its patch
# embedding: 70 of 280. Counted over state_dict() entries, aliases included
# (patch_embed's convolutions appear twice), as villa saves them.
FOUNDATION_ENCODER_MIN_FRACTION = 0.9


def check_foundation_model_path(config):
    """A file check, run first by train() and the --smoke preflight: a missing
    foundation_model_path fails in seconds, not after the validation catalogue
    and the model are built."""
    path = getattr(config, "foundation_model_path", None)
    if path and not os.path.exists(path):
        raise FileNotFoundError(f"foundation_model_path {path} does not exist")


def load_foundation_model(model, path):
    """Start model from the pretrained checkpoint at path (foundation_model_path):
    a LeJEPA encoder into PrimusNetwork's shared_encoder, else any checkpoint
    by name. Raises if the file is missing or unreadable, if no tensor fits, or
    if a LeJEPA encoder fills under FOUNDATION_ENCODER_MIN_FRACTION of
    shared_encoder: a run asked to start from a pretrained model must not
    train from scratch under its name. That used to be a printed warning, or
    nothing at all for a missing path. The checkpoint is read on the CPU (it
    can hold optimizer state too); load_state_dict copies to the model."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"foundation_model_path {path} does not exist")
    print(f"Loading pretrained backbone from {path}...")
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    state_dict = extract_checkpoint_state(checkpoint)
    if not isinstance(state_dict, dict):
        raise TypeError(f"{path} holds a {type(state_dict).__name__}, not a state dict")
    lejepa = hasattr(model, "backbone") and hasattr(model.backbone, "shared_encoder")
    if lejepa:
        target = model.backbone.shared_encoder
        state, label = foundation_encoder_state(state_dict), "LeJEPA encoder"
    else:
        target, state, label = model, state_dict, "generic pretrained checkpoint"
    total = len(target.state_dict())
    needed = math.ceil(FOUNDATION_ENCODER_MIN_FRACTION * total) if lejepa else 1
    loaded = load_shape_compatible_state(target, state, label)
    if loaded < needed:
        raise ValueError(
            f"only {loaded} of {total} tensors of the model ({label}) load from "
            f"{path}; it needs {needed}"
            + (" (an encoder of another size?)" if lejepa else "")
        )


def extract_checkpoint_state(checkpoint):
    if not isinstance(checkpoint, dict):
        return checkpoint
    for key in ("model", "model_state_dict", "state_dict"):
        state_dict = checkpoint.get(key)
        if isinstance(state_dict, dict):
            return state_dict
    return checkpoint


# These are recorded fields, not reconstructed defaults. In particular,
# in_channels is derived from use_ridges and is not an ExperimentConfig field.
WARM_START_FIELDS = (
    "architecture",
    "use_ridges",
    "num_layers",
    "num_blocks",
    "num_heads",
    "base_feat",
    "patch_size",
)


def warm_start_mismatch(recorded, config):
    return next(
        (
            key
            for key in WARM_START_FIELDS
            if key not in recorded or recorded[key] != getattr(config, key)
        ),
        None,
    )


def load_required_starting_checkpoint(model, config, path="best_model.pt"):
    """Load every starting tensor or fail before the first optimizer step.

    CPU deserialization avoids allocating a second full checkpoint on the GPU.
    This strict path is opt-in for repeatability trials; load failures propagate.
    """
    saved = torch.load(path, map_location="cpu", weights_only=False)
    mismatch = warm_start_mismatch(saved["config"], config)
    if mismatch is not None:
        raise ValueError(f"starting checkpoint must record matching {mismatch}")
    model.load_state_dict(saved["model_state_dict"], strict=True)
    print(f"Loaded complete required starting checkpoint from {path}.")


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


# --- Honest, prize-aligned promotion criterion (2026-07 rewire) --------------
# Selection now runs on the detector's honest metric contract (threshold-swept
# F1, gated by AP-prevalence-lift) instead of val_bpb (weak discriminator) and
# skel_dist (proven location-blind / invalid). val_bpb & topology stay computed
# and reported but no longer decide promotion. See
# docs/superpowers/specs/2026-07-10-loop-honest-metric-selection-design.md
#
# MEASURED 2026-07-12 by the identical-config noise probe (scripts/f1_noise_probe.py,
# 4 runs of the promoted config at the 900s budget, isolated via checkpoint_out):
# TRUE run-to-run sigma = 0.0120 (range 0.026; reports/detector/f1_noise_probe.json).
# A promotion compares two noisy draws (sigma_diff = sqrt(2)*sigma ~= 0.017), so the
# tolerance for a ~5% false-promotion rate is 1.645*0.017 ~= 0.028 -> 3e-2.
# History of this constant: 5e-3 (guess) -> 1e-2 (cross-tweak upper-bound estimate,
# 2026-07-11 — that "upper bound" turned out to UNDERSTATE true noise) -> 3e-2 (measured).
# HONEST IMPLICATION: at the 900s budget no tweak tried so far separates from noise
# (the 2026-07-11 cycle-9 "+0.0137 improvement" was 0.8 sigma_diff = noise). Promotions
# at this budget need either this wide tolerance (rare promotions, honest) or
# multi-seed averaging per cycle (sigma_mean = sigma/sqrt(k)) — a design change.
# LIFT_MARGIN validated 2026-07-11: observed lifts 1.13-1.54; the >1.02 real-signal
# gate binds only on constant-collapse, as intended.
F1_NOISE_TOLERANCE = 3e-2
LIFT_MARGIN = 0.02


def is_f1_improvement(val_f1: float, ap_lift: float, best_val_f1: float) -> bool:
    """Prize-aligned promotion: threshold-swept F1, gated by a real-signal check.

    A candidate improves on the best model iff all hold:
    - val_f1 is finite,
    - ap_lift is finite and > 1 + LIFT_MARGIN (beats the trivial prevalence
      baseline — kills the constant/all-positive prediction artifact that made
      Dice/val_bpb untrustworthy), and
    - val_f1 exceeds the stored best by more than F1_NOISE_TOLERANCE.

    best_val_f1 is -inf on a checkpoint that predates val_f1, so the first
    submittable, lift-positive cycle bootstraps the baseline.
    """
    if not np.isfinite(val_f1):
        return False
    if not (np.isfinite(ap_lift) and ap_lift > 1.0 + LIFT_MARGIN):
        return False
    return val_f1 > best_val_f1 + F1_NOISE_TOLERANCE


def append_tsv_row(path: str, columns, values) -> None:
    """Append one row to a TSV log whose header must be exactly ``columns``.

    Columns used to be added in code without touching an existing file's header,
    so history.tsv and prize_readiness.tsv gained rows with one more field than
    their header and every later column was mislabelled. A file whose header
    differs is now moved aside (``<name>.until-<timestamp>.tsv``) and a new one
    started, so each file stays readable by its own header.
    """
    if len(values) != len(columns):
        raise ValueError(f"{path}: {len(values)} values for {len(columns)} columns")
    header = "\t".join(columns) + "\n"
    if os.path.exists(path):
        with open(path) as f:
            existing = f.readline()
        if existing != header:
            stem, ext = os.path.splitext(path)
            aside = f"{stem}.until-{time.strftime('%Y%m%d-%H%M%S')}{ext}"
            os.replace(path, aside)
            print(f"{path}: header differs from the current columns; moved to {aside}")
    start = not os.path.exists(path)
    with open(path, "a") as f:
        if start:
            f.write(header)
        f.write("\t".join(str(v) for v in values) + "\n")
        f.flush()
        os.fsync(f.fileno())


HISTORY_COLUMNS = (
    "timestamp",
    "val_bpb",
    "avg_skel_dist",
    "avg_centerline_dice",
    "avg_cc_diff",
    "avg_crit_comp",
    "avg_mean_ap",
    "train_loss",
    "throughput_Mvps",
    "num_params_M",
    "peak_vram_mb",
    "config",
)
# results.tsv's schema is frozen for scripts/experiment_report_data.py.
RESULTS_COLUMNS = tuple(c for c in HISTORY_COLUMNS if c != "avg_mean_ap")
PRIZE_READINESS_COLUMNS = (
    "timestamp",
    "submittable",
    "window_ok",
    "window_mm",
    "villa_metrics_ok",
    "patch_size",
    "val_bpb",
    "avg_skel_dist",
    "avg_centerline_dice",
    "avg_cc_diff",
    "avg_crit_comp",
    "config",
)


def promotion_decision(
    val_f1: float,
    ap_lift: float,
    *,
    submittable: bool,
    enforce_prize_gates: bool,
    validation_complete: bool,
    protocol: str,
    incumbent_path: str = "best_model.pt",
    inputs: str | None = None,
):
    """Whether this run replaces the incumbent: (promote, incumbent_val_f1, reason).

    ``reason`` names what blocked the comparison itself (an incomplete validation
    sample, an incumbent that cannot be read or was scored under another
    protocol, or one scored on other validation inputs than ``inputs``, this
    run's validation_diag["inputs_sha256"]); it is None when the candidate was
    simply compared and lost. Every path that cannot compare like with like fails
    closed. An incumbent scored before fingerprints were recorded is compared on
    its protocol alone.
    """
    try:
        incumbent, incumbent_inputs = read_incumbent(incumbent_path, protocol)
    except IncumbentUnavailable as exc:
        return False, float("nan"), str(exc)
    if not validation_complete:
        return False, incumbent, "the validation sample is incomplete (failed reads)"
    if incumbent_inputs is not None and inputs != incumbent_inputs:
        reason = (
            "this run recorded no validation-input fingerprint"
            if inputs is None
            else "the validation inputs (label file, mask or patches.json) differ "
            "from those the incumbent was scored on; re-score it with "
            f"`{RESCORE_COMMAND}`"
        )
        return False, incumbent, reason
    if enforce_prize_gates and not submittable:
        return False, incumbent, None
    return is_f1_improvement(val_f1, ap_lift, incumbent), incumbent, None


def pooled_segmentation_metrics(all_probs, all_targets):
    """Pool per-patch validation predictions/targets and score them with the
    detector's honest metric contract (single source of truth). Every pixel is
    valid here, so the mask is all-True. Returns {} when there are no patches.
    """
    if not all_probs:
        return {}
    # Lazy import: keep module import light and side-effect-free for the loop.
    from vesuvius_autoresearch.detector.metrics import segmentation_metrics

    prob = torch.cat([p.reshape(-1) for p in all_probs]).numpy()
    label = torch.cat([t.reshape(-1) for t in all_targets]).numpy()
    mask = np.ones_like(label, dtype=bool)
    return segmentation_metrics(prob, label, mask)


# Warmup then cosine decay, as fractions of the time budget. The schedule used to
# be in steps, from an assumed 0.2 s/step; production steps take 3-5 s, so a 900 s
# cycle ran ~250 of an estimated 4,500 steps and ended inside the 562-step warmup,
# at ~45% of the intended learning rate and without ever annealing.
WARMUP_FRACTION = 0.125


def budget_lr_factor(progress: float, warmup_fraction: float = WARMUP_FRACTION):
    """Learning-rate multiplier after ``progress`` (0..1) of the time budget."""
    progress = min(max(progress, 0.0), 1.0)
    if progress < warmup_fraction:
        return progress / warmup_fraction
    decay = (progress - warmup_fraction) / (1.0 - warmup_fraction)
    return 0.5 * (1.0 + math.cos(math.pi * decay))


def guarded_update(model, optimizer, scaler, lr, max_norm=1.0, step=None) -> bool:
    """Clip and apply one optimizer step, or skip it when the gradient norm is not finite.

    AMP is off, so GradScaler does not skip non-finite steps itself: a finite loss
    with a NaN or infinite gradient reached AdamW and made every weight and moment
    NaN for the rest of the cycle. The norm is checked before clipping, which
    would otherwise spread a NaN into every gradient, and the offending tensors
    are named only when it fails (one check per step, not two GPU syncs per
    tensor). Returns True when the step was applied.
    """
    named = [(n, p) for n, p in model.named_parameters() if p.grad is not None]
    if not named:
        return False  # nothing to apply; the scaler is left untouched
    scaler.unscale_(optimizer)
    named = [(n, p.grad) for n, p in named]
    norms = torch.stack([torch.linalg.vector_norm(g.detach()) for _, g in named])
    if not torch.isfinite(torch.linalg.vector_norm(norms)):
        bad = [n for (n, g) in named if not torch.isfinite(g).all()]
        where = f" at step {step}" if step is not None else ""
        if bad:
            names = ", ".join(bad[:3]) + (", ..." if len(bad) > 3 else "")
            problem = f"Non-finite gradient{where} in {len(bad)} tensors ({names})"
        else:
            problem = f"Gradient norm{where} overflowed although every tensor is finite"
        print(f"[WARNING] {problem}; skipping this update.")
        optimizer.zero_grad(set_to_none=True)
        scaler.update()
        return False
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)
    for group in optimizer.param_groups:
        group["lr"] = lr
    scaler.step(optimizer)
    scaler.update()
    return True


# Worker processes preparing training batches. With none, every batch was read
# and given its ridge channel and Frangi fiber target in the training process
# while the GPU waited: the Frangi target alone took ~150 ms a patch (CPU, one
# thread), ~0.6 s of a batch of 4, and the GPU was busy ~7% of each ~480 ms
# step (2026-10-14). Each patch is drawn from its index and the run's seed
# (jitter, depth), so workers prepare the same batches in the same order, only
# in parallel.
LOADER_WORKERS_ENV = "AUTORESEARCH_LOADER_WORKERS"


def loader_workers() -> int:
    """Workers for the labeled training loader: one fewer than the CPUs, at most
    three, unless AUTORESEARCH_LOADER_WORKERS sets it (0: read in this process)."""
    value = os.environ.get(LOADER_WORKERS_ENV)
    if value is None:
        return max(0, min(3, (os.cpu_count() or 1) - 1))
    try:
        workers = int(value)
    except ValueError:
        workers = -1
    if workers < 0:
        raise ValueError(f"{LOADER_WORKERS_ENV} must be an integer >= 0, not {value!r}")
    return workers


def _init_worker(init, worker_id):
    """A training-loader worker's start: it will leave without finalizing the
    interpreter, then runs ``init``.

    Training stops mid-pass with batches in flight, and finalization ends a
    worker's queue thread wherever it is. Inside PyTorch's C++ (releasing a
    batch) that ends in std::terminate: "terminate called without an active
    exception", SIGABRT, in 4 of 12 mid-pass stops on Fr47 (2026-10-15). Nothing
    a worker holds at exit is needed: its batches have gone through the queue,
    its warnings to the shared counts. Exit handlers run before finalization
    ends threads, so this one exits first.
    """
    atexit.register(os._exit, 0)
    if init is not None:
        init(worker_id)


def shuffled_loader(
    dataset, batch_size: int, seed: int, workers: int = 0, worker_init_fn=None
) -> DataLoader:
    """Training batches drawn in a seeded random order over the whole catalogue.

    Without a sampler the loader read the catalogue in raster order from index 0,
    and a cycle only reaches ~1,000 patches: every cycle fine-tuned on the same
    strip at the top of the fragment (and UA-MT on the top ~220 px of the
    volume). Each re-iteration after StopIteration draws a fresh permutation.
    The order comes from ``seed`` alone, so ``workers`` changes only where the
    batches are prepared.
    """
    generator = torch.Generator()
    generator.manual_seed(seed)
    options = {}
    if workers > 0:
        options = {
            "num_workers": workers,
            # Spawned, not forked: the ridge channel runs on CuPy, and a forked
            # child of a process that has used CUDA cannot.
            "multiprocessing_context": "spawn",
            # Not persistent: a persistent iterator's reset skips the generator
            # draw a new iterator makes, so the next pass would be another order.
            "worker_init_fn": functools.partial(_init_worker, worker_init_fn),
        }
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
        pin_memory=True,
        **options,
    )


def fiber_source(heads, config) -> str:
    """The fiber head's target: config.target_fiber_source for a model with a
    fiber or QC head, else the cheap Sobel-Z placeholder (no head trains on it)."""
    if heads & {"fiber", "qc"}:
        return getattr(config, "target_fiber_source", "sobel_z")
    return "sobel_z"


def fiber_target(x_raw, x_orig, source: str, sigma: float = 2.0):
    """The fiber head's target before its per-patch min-max: [B, 1, 1, H, W].

    "frangi": Frangi vesselness of the CT channel of the whole read (every
    slice, the margins included), averaged over z, computed on the batch's
    device. The loader computed it per patch with skimage until 2026-10-15,
    ~150 ms a patch on the CPU, two thirds of a training patch's preparation;
    frangi_torch reproduces it (tests/test_frangi_torch.py).
    "sobel_z": the mean absolute z-gradient of the CT channel of the model's
    window.
    """
    if source == "frangi":
        return frangi_vesselness_zcollapsed_torch(x_raw[:, 0], sigma)[:, None, None]
    grad_z = x_orig[:, :1, 1:] - x_orig[:, :1, :-1]
    return grad_z.abs().mean(dim=2, keepdim=True)


def build_validation_dataset(config: ExperimentConfig):
    """The validation catalogue promotion is scored on (see promotion.py).

    Reads are strict: a failed read raises instead of returning an all-zero patch,
    which would silently be scored as an ink-free patch.
    """
    # The same paths the fingerprint hashes (promotion.validation_input_paths),
    # fingerprinted before and after the dataset reads them.
    band = getattr(config, "depth_band", None)
    inputs = validation_inputs_fingerprint(config.val_uri, band)
    paths = validation_input_paths(config.val_uri)
    labels_path, mask_path = paths["labels"], paths["mask"]
    patches_json_path = paths["patches_json"]
    # Validation uses target_fiber_source="sobel_z" regardless of training
    # config — val doesn't use target_fiber (only ink) and we want to avoid
    # paying Frangi cost on every val patch.
    dataset = VesuviusLabeledDataset(
        config.val_uri,
        labels_path,
        mask_path if os.path.exists(mask_path) else None,
        config.patch_size,
        config.num_layers + 2 * DEPTH_MARGIN,
        seed=42,
        cache_dir=config.cache_dir,
        use_ridges=config.use_ridges,
        ridge_sigma=getattr(config, "ridge_sigma", 2.0),
        use_lasagna=getattr(config, "use_lasagna", False),
        require_ink=False,
        target_fiber_source="sobel_z",
        patches_json=patches_json_path if os.path.exists(patches_json_path) else None,
        strict_reads=True,
        depth_band=getattr(config, "depth_band", None),
        depth_margin=DEPTH_MARGIN,
    )
    # Recorded with every score (validation_diag["inputs_sha256"]) and compared
    # with the incumbent's (promotion.py). A file written while the dataset read
    # them could otherwise be recorded without having been read.
    if validation_inputs_fingerprint(config.val_uri, band) != inputs:
        raise RuntimeError(
            f"the validation inputs for {config.val_uri} changed while they were read"
        )
    dataset.validation_inputs = inputs
    return dataset


def training_label_path(uri: str, config: ExperimentConfig) -> str:
    """The label file training reads for a labeled volume.

    A `<segment>_pseudo.png` in pseudo_label_dir takes precedence over the
    volume's own labels (docs/PSEUDO_LABEL_HANDOFF.md). Its uncertain band (PNG
    128) is a target like any other unless use_confidence_weight down-weights it,
    so a pseudo-label from pseudo_label_dir without it is refused rather than
    trained as ink 128/255.
    """
    if config.pseudo_label_dir:
        segment = os.path.basename(os.path.dirname(uri.rstrip("/")))
        pseudo = os.path.join(config.pseudo_label_dir, f"{segment}_pseudo.png")
        if os.path.exists(pseudo):
            if not getattr(config, "use_confidence_weight", False):
                raise ValueError(
                    f"{pseudo} replaces the labels of {uri}, but "
                    "use_confidence_weight is off, so its uncertain band would be "
                    "trained as ink probability 128/255 (docs/PSEUDO_LABEL_HANDOFF.md)"
                )
            return pseudo
    path = validation_label_path(uri)  # the same order as validation
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"no label file for training volume {uri} (looked for "
            f"{', '.join(VALIDATION_LABEL_FILES)} beside it)"
        )
    return path


def resolve_training_labels(config: ExperimentConfig) -> dict[str, str]:
    """Each training volume's label file (training_label_path), printed.

    Only file checks, so train() and the --smoke preflight run it first: a
    missing or refused label file fails in seconds, not after the validation
    catalogue and the model are built.
    """
    labels = {uri: training_label_path(uri, config) for uri in config.uris}
    for uri, path in labels.items():
        print(f"Training labels for {uri}: {path}")
    return labels


def unlabeled_dataset(uri: str, config: ExperimentConfig, seed=None):
    """UA-MT's reader for one unlabeled_uris volume.

    The band names slices of the volumes it was set for, so it applies to an
    unlabeled volume that is also one of them (a training volume, matched by
    path as inference_constants.depth_band_for matches a checkpoint's), whose
    labeled reads use it. Any other unlabeled volume is read over its whole
    depth: it may number its slices differently.
    """
    band = depth_band_for(
        {
            "depth_band": getattr(config, "depth_band", None),
            "uri": config.uri,
            "uris": config.uris,
            "val_uri": config.val_uri,
        },
        uri,
    )
    return VesuviusS3Dataset(
        uri,
        config.patch_size,
        config.num_layers + 2 * DEPTH_MARGIN,
        seed=seed,
        cache_dir=config.cache_dir,
        use_ridges=config.use_ridges,
        ridge_sigma=getattr(config, "ridge_sigma", 2.0),
        use_lasagna=config.use_lasagna,
        is_unlabeled=True,
        depth_band=band,
        depth_margin=DEPTH_MARGIN,
    )


def _sigmoid_ink(model, x):
    out = model(x)
    return torch.sigmoid(out[0] if isinstance(out, tuple) else out)


def probe_validation_read(dataset) -> None:
    """Read the protocol's first validation patch, before any training.

    collect_validation_predictions counts a failed read as a batch error and marks
    the sample incomplete, which blocks promotion. A patch the strict read cannot
    produce (an unavailable lasagna warp, a ridge failure) therefore makes the
    whole cycle unpromotable; reading one patch first fails it before training
    instead of after the training budget.
    """
    index = int(validation_indices(len(dataset))[0])
    try:
        dataset[index]
    except Exception as exc:
        raise RuntimeError(
            f"validation patch {index} cannot be read, so this run could not be "
            f"scored: {type(exc).__name__}: {exc}"
        ) from exc


# UA-MT (Yu et al., 2019) estimates the teacher's uncertainty from stochastic
# passes; the variance comes from dropout-like layers, plus 0.01 input noise.
UAMT_TEACHER_PASSES = 4


def _ink(out):
    return out[0] if isinstance(out, tuple) else out


def teacher_is_stochastic(teacher, x, passes=UAMT_TEACHER_PASSES) -> bool:
    """Whether train-mode passes over the same input differ.

    Asked of the model rather than of its layer types, so dropout, stochastic
    depth (DropPath) and functional dropout all count. Several passes, because a
    per-sample mask can repeat between two (1 in 16 for DropPath at batch 4; 1 in
    4,096 over four passes). Nondeterministic kernels also count, which keeps the
    four passes: the safe side.
    """
    was_training = teacher.training
    teacher.train()
    try:
        with torch.no_grad():
            first = _ink(teacher(x))
            return any(
                not torch.equal(first, _ink(teacher(x))) for _ in range(passes - 1)
            )
    finally:
        teacher.train(was_training)


def uamt_teacher(teacher, x, passes):
    """The teacher's mean ink probability and its variance over ``passes``
    stochastic passes (train mode, 0.01 input noise each).

    Without dropout-like layers the passes differ only by that noise: on the
    production resenc_unet the variance is ~1e-6, so exp(-variance) is 1 to 4
    decimals and three of four passes bought nothing (2026-10-14). One pass then
    gives the same mean and a variance of zero; torch.var of one sample would be
    NaN. The teacher's mode is restored afterwards.
    """
    was_training = teacher.training
    teacher.train()  # dropout, where there is any
    try:
        preds = []
        for _ in range(passes):
            noise = torch.randn_like(x) * 0.01
            # Sanitized like the student output, so a non-finite teacher
            # prediction cannot NaN the consistency loss.
            ink = torch.nan_to_num(_ink(teacher(x + noise)))
            preds.append(torch.sigmoid(ink))
        preds = torch.stack(preds)  # [T, B, 1, H, W]
        prob = preds.mean(dim=0)
        var = preds.var(dim=0) if passes > 1 else torch.zeros_like(prob)
        return prob, var
    finally:
        teacher.train(was_training)


def trained_outputs(model_out, heads):
    """(ink, fiber, qc, proj, st) from a forward with every return_* flag set,
    with the auxiliary outputs the model does not declare as heads set to None.

    A placeholder fiber is the ink logits, so a loss on it trained ink toward the
    fiber target, and the hallucination penalty on a zero QC pushed all ink down
    (model_wrappers.task_heads).
    """
    if not isinstance(model_out, tuple):
        return model_out, None, None, None, None
    padded = list(model_out) + [None] * (5 - len(model_out))
    ink, fiber, qc, proj, st = padded[:5]
    return (
        ink,
        fiber if "fiber" in heads else None,
        qc if "qc" in heads else None,
        proj,
        st if "st" in heads else None,
    )


def check_validation_inputs(dataset, protocol, incumbent_path="best_model.pt"):
    """Fail before training when the validation inputs differ from those the
    incumbent is compared on. The loop checks before each cycle; this covers a
    change since (during the preflight) without spending the training budget."""
    try:
        incumbent_inputs = read_incumbent(incumbent_path, protocol)[1]
    except IncumbentUnavailable:
        return  # promotion_decision reports why after training
    if incumbent_inputs not in (None, getattr(dataset, "validation_inputs", None)):
        raise RuntimeError(
            "the validation inputs differ from those the incumbent is compared on; "
            f"re-score it with `{RESCORE_COMMAND}`"
        )


def collect_validation_predictions(
    model,
    dataset,
    num_layers: int,
    device,
    batch_size: int = 4,
    amp_enabled=False,
    probabilities=_sigmoid_ink,
    protocol=VALIDATION_PROTOCOL,
):
    """Score the protocol's fixed sample of ``dataset``.

    Returns per-patch ink probabilities and targets (each ``[1, 1, H, W]``) and
    diagnostics. The protocol decides which patches count
    (promotion.scores_ink_free_patches): every patch of the draw, or, under v2,
    its ink-containing patches only. ``usable_patches`` counts the ink-containing
    patches and ``empty_target_patches`` the ink-free ones either way;
    ``scored_patches`` counts those returned. ``batch_size`` only groups the
    forward passes: which patches count is decided per patch, so it does not change
    the result. ``complete`` is False when any read or forward pass failed; such a
    sample is not the protocol's sample and cannot support a promotion.
    ``probabilities(model, x)`` maps an input batch to ink probabilities; checkpoint
    tools pass a validating version. ``protocol`` is recorded in the diagnostics
    (validation_protocol(config.depth_band) for the dataset's depth range).
    """
    keep_ink_free = scores_ink_free_patches(protocol)
    indices = validation_indices(len(dataset))
    diag = {
        "protocol": protocol,
        "requested_patches": int(len(indices)),
        "empty_target_patches": 0,
        "batch_errors": 0,
    }
    all_probs, all_targets = [], []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(indices), batch_size):
            chunk = indices[start : start + batch_size]
            try:
                val_x_raw, val_target, _fiber = default_collate(
                    [dataset[int(i)] for i in chunk]
                )
                val_x = val_x_raw[:, :, DEPTH_MARGIN : DEPTH_MARGIN + num_layers].to(
                    device
                )
                if val_target.dim() == 3:
                    val_target = val_target.unsqueeze(1)
                with autocast(device_type=device.type, enabled=amp_enabled):
                    prob_2d = probabilities(model, val_x).float().cpu()
            except Exception as exc:
                diag["batch_errors"] += 1
                if diag["batch_errors"] <= 3:
                    print(
                        f"  Warning: validation patches {chunk.tolist()} failed: "
                        f"{type(exc).__name__}: {exc}"
                    )
                continue
            for j in range(len(chunk)):
                if torch.sum(val_target[j].float()) < 1.0:
                    diag["empty_target_patches"] += 1
                    if not keep_ink_free:
                        continue
                all_probs.append(prob_2d[j : j + 1])
                all_targets.append(val_target[j : j + 1].float().cpu())
    diag["scored_patches"] = len(all_probs)
    diag["usable_patches"] = (
        len(all_probs) - diag["empty_target_patches"]
        if keep_ink_free
        else len(all_probs)
    )
    diag["complete"] = diag["batch_errors"] == 0
    # What the sample was drawn from (build_validation_dataset); None for a
    # dataset built another way.
    diag["inputs_sha256"] = getattr(dataset, "validation_inputs", None)
    return all_probs, all_targets, diag


def ink_containing(probs, targets):
    """The patches whose target holds ink, in order. The per-patch diagnostics
    (Dice, val_bpb, topology, mean AP) are defined on these; val_f1, AP lift and
    AUC pool every patch the protocol scores."""
    kept = [i for i, target in enumerate(targets) if float(target.sum()) >= 1.0]
    return [probs[i] for i in kept], [targets[i] for i in kept]


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
    diag=None,
):
    """Pick the binarization threshold that maximizes mean centerline_dice over a
    subset of validation patches. Returns (threshold, mean_centerline_dice).

    Evaluated on every `subset_step`-th patch to match (and bound) the cost of
    the per-patch topology metrics. Falls back to `fallback` if no candidate
    produces a finite centerline_dice: every evaluation NaN, or every one failed.
    Failed evaluations are printed (the first three) and counted, into
    ``diag["topology_threshold_errors"]`` when a diagnostics dict is given, as
    the validation pass counts its own metrics' failures.
    """
    best_thr = fallback
    best_cd = -1.0
    errors = 0
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
            except Exception as exc:
                errors += 1
                if errors <= 3:
                    print(
                        f"  Warning: centerline-dice failed while choosing the "
                        f"topology threshold (at {thr}): {type(exc).__name__}: {exc}"
                    )
        mean_cd = float(np.mean(cds)) if cds else -1.0
        if mean_cd > best_cd:
            best_cd, best_thr = mean_cd, thr
    if errors:
        print(
            f"  Warning: the topology threshold was chosen without {errors} failed "
            "centerline-dice evaluations"
        )
    if diag is not None:
        diag["topology_threshold_errors"] = errors
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

from vesuvius_autoresearch.core.frangi_torch import frangi_vesselness_zcollapsed_torch
from vesuvius_autoresearch.core.inference import DEPTH_MARGIN
from vesuvius_autoresearch.core.inference_constants import depth_band_for
from vesuvius_autoresearch.core.model_wrappers import (
    GenericMultiTaskWrapper,
    build_resenc_unet,
    task_heads,
)

TRAINING_TRANSFORMS_IMPORT_ERROR = None
try:
    from vesuvius.models.augmentation.pipelines.training_transforms import (
        create_training_transforms,
    )
except ImportError as exc:
    create_training_transforms = None
    TRAINING_TRANSFORMS_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

# Batches that asked for batchgeneratorsv2 but were augmented with the
# Albumentations recipe because the villa pipeline raised; reported per run.
AUGMENTATION_FALLBACKS = {"batchgeneratorsv2": 0}

# The four scroll augmentations villa's pipeline adds itself (see
# apply_augmentations); the other five come from scroll_augmentations in
# either mode.
_VILLA_SCROLL_AUGMENTATIONS = (
    "aug_scroll_sheet_compression_p",
    "aug_scroll_thick_slice_p",
    "aug_scroll_rician_noise_p",
    "aug_scroll_blank_rectangles_p",
)

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
    share_warning_counts,
    warning_counts,
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
                x = x_raw[:, DEPTH_MARGIN : DEPTH_MARGIN + nl].unsqueeze(0).to(device)
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


def uamt_views(x_unlabeled, step, config):
    """Student and teacher inputs for UA-MT's pixel-wise consistency loss.

    Both see one augmented view; the teacher's stochastic passes add their own
    input noise. Two independent apply_augmentations calls gave each network a
    different flip/rotation/affine, so the MSE compared misaligned pixels (the
    same stroke overlapped with IoU 0-0.2) and rewarded predictions that ignore
    the image.
    """
    B, _, _, H, W = x_unlabeled.shape
    dummy_ink = torch.zeros((B, 1, H, W), device=x_unlabeled.device)
    dummy_fiber = torch.zeros((B, 1, 1, H, W), device=x_unlabeled.device)
    view, _, _ = apply_augmentations(
        x_unlabeled, dummy_ink, dummy_fiber, step, None, config=config
    )
    return view, view


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

    if aug_mode == "batchgeneratorsv2" and create_training_transforms is None:
        # This used to fall through to Albumentations without a word, so a cycle
        # recorded as batchgeneratorsv2 trained with the other recipe.
        raise RuntimeError(
            "aug_mode='batchgeneratorsv2' needs villa's training transforms, which "
            f"failed to import ({TRAINING_TRANSFORMS_IMPORT_ERROR})"
        )

    if aug_mode == "batchgeneratorsv2":
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
        except Exception as e:
            AUGMENTATION_FALLBACKS["batchgeneratorsv2"] += 1
            if AUGMENTATION_FALLBACKS["batchgeneratorsv2"] <= 3:
                print(
                    f"Warning: batchgeneratorsv2 failed ({e}). Falling back to "
                    "Albumentations for this batch (count in run_result.json)."
                )
            aug_mode = "albumentations"
        else:
            # The Albumentations path applies the aug_scroll_* settings below;
            # this path returned before them, so switching aug_mode also turned
            # off the scroll augmentations the config enables. Villa's pipeline
            # already covers four of them, so only the other five apply here.
            others = copy.copy(config)
            for name in _VILLA_SCROLL_AUGMENTATIONS:
                setattr(others, name, 0.0)
            return apply_scroll_specific_3d_augmentations(
                x_aug, ink_aug, fiber_aug, others
            )

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
        # The construction inference uses too (model_wrappers.build_resenc_unet).
        try:
            model = build_resenc_unet(
                v_config.in_channels,
                v_config.base_feat,
                getattr(config, "multi_task_heads", False),
            ).to(device)
        except ImportError as exc:
            raise ImportError(
                "ResidualEncoderUNet not found. Please install dynamic-network-architectures."
            ) from exc
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


def save_cycle_checkpoints(checkpoint, checkpoint_out, is_improvement) -> list[str]:
    """Save this cycle's model and return the paths written.

    An experiment run (checkpoint_out) writes only its own file and leaves the
    loop's untouched. A loop cycle writes its candidate to last_model.pt every
    cycle, promoted or not (scripts/snapshot_loop_candidates.sh copies it as
    the cycle's candidate), and to best_model.pt when it is promoted, last: a
    run stopped between the two leaves the incumbent the loop still records.
    """
    if checkpoint_out:
        directory = os.path.dirname(checkpoint_out)
        if directory:
            os.makedirs(directory, exist_ok=True)
        save_checkpoint_atomic(checkpoint, checkpoint_out)
        print(f"Saved experiment checkpoint to {checkpoint_out} (loop state untouched)")
        return [checkpoint_out]
    paths = ["last_model.pt"] + (["best_model.pt"] if is_improvement else [])
    for path in paths:
        save_checkpoint_atomic(checkpoint, path)
    return paths


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
    # A foundation model that does not fit stops the cycle here, in seconds.
    if getattr(config, "foundation_model_path", None):
        load_foundation_model(model, config.foundation_model_path)

    x = torch.randn(
        2,
        v_config.in_channels,
        v_config.num_layers,
        v_config.patch_size,
        v_config.patch_size,
    )
    # The configured augmentation recipe too: an unavailable aug_mode fails here,
    # in seconds, instead of mid-cycle.
    size = v_config.patch_size
    x, _, _ = apply_augmentations(
        x,
        torch.zeros(2, 1, size, size),
        torch.zeros(2, 1, 1, size, size),
        0,
        None,
        config=config,
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


def train(config: ExperimentConfig, *, strict_warm_start=False):
    print("STARTING TRAINING")
    # What this run's score is comparable with; the depth band is part of it.
    protocol = validation_protocol(getattr(config, "depth_band", None))
    torch.set_float32_matmul_precision("high")
    device = torch.device("cuda")

    v_config = build_vconfig(config)

    print(f"Initializing LOCAL TRANSFORMER Training on {config.uris}...")
    # The label file each training volume is read with, recorded with the
    # result: a pseudo-label takes precedence over the volume's own labels.
    training_labels = resolve_training_labels(config)
    check_foundation_model_path(config)
    sys.stdout.flush()

    def get_dataloader(uris, is_unlabeled=False):
        from torch.utils.data import ConcatDataset

        # The run's seed draws each entry's crop (lateral jitter, read depth) as
        # well as the order. Without one, entry i had the same crop in every
        # run: Fr47's 7,345 fixed crops held 74.8% of its labelled ink pixels.
        seed = sampling_seed + (1 if is_unlabeled else 0)
        datasets = []
        for uri in uris:
            if is_unlabeled:
                datasets.append(unlabeled_dataset(uri, config, seed))
                continue

            parent_dir = os.path.dirname(uri.rstrip("/"))
            labels_path = training_labels[uri]
            mask_path = os.path.join(parent_dir, "mask.png")
            patches_json_path = os.path.join(parent_dir, "patches.json")
            ds = VesuviusLabeledDataset(
                uri,
                labels_path,
                mask_path if os.path.exists(mask_path) else None,
                config.patch_size,
                config.num_layers + 2 * DEPTH_MARGIN,
                seed=seed,
                cache_dir=config.cache_dir,
                use_ridges=config.use_ridges,
                ridge_sigma=getattr(config, "ridge_sigma", 2.0),
                use_lasagna=getattr(config, "use_lasagna", False),
                # A zero placeholder: the training step computes the fiber
                # target from the batch (fiber_target).
                target_fiber_source="sobel_z",
                target_fiber_sigma=getattr(config, "target_fiber_sigma", 2.0),
                patches_json=patches_json_path
                if os.path.exists(patches_json_path)
                else None,
                depth_band=getattr(config, "depth_band", None),
                depth_margin=DEPTH_MARGIN,
            )
            datasets.append(ds)

        combined_ds = ConcatDataset(datasets) if len(datasets) > 1 else datasets[0]
        return shuffled_loader(
            combined_ds,
            config.batch_size,
            seed,
            # UA-MT's unlabeled patches need no fiber target: read in-process.
            workers=0 if is_unlabeled else workers,
            worker_init_fn=share_counts,
        )

    # Built and read before anything else, so a missing or empty validation
    # catalogue, or a patch the strict read refuses, fails before the training
    # data is loaded, not after the budget.
    val_dataset = build_validation_dataset(config)
    probe_validation_read(val_dataset)
    check_validation_inputs(val_dataset, protocol)

    # Fresh per run, so successive warm-started cycles see different patches,
    # cropped differently; recorded in run_result.json and the checkpoint.
    sampling_seed = int.from_bytes(os.urandom(4), "little") & 0x7FFFFFFF
    print(f"Training sampling seed: {sampling_seed}")
    # Built before the loaders: which heads it trains decides the fiber target.
    model = build_model(config, v_config, device)
    # Before the loaders and logging start: a checkpoint that does not fit
    # stops the run at once. The warm start below can still overwrite it.
    if config.foundation_model_path:
        load_foundation_model(model, config.foundation_model_path)
    # Only the outputs the model declares as heads are trained
    # (model_wrappers.task_heads); the rest are placeholders.
    heads = task_heads(model)
    print(f"Trained auxiliary heads: {', '.join(sorted(heads)) or 'none'}")
    fiber_target_source = fiber_source(heads, config)
    workers = loader_workers()
    shared_warnings = share_counts = None
    if workers:
        import multiprocessing

        manager = multiprocessing.get_context("spawn").Manager()
        shared_warnings = manager.dict()
        share_counts = functools.partial(
            share_warning_counts, shared_warnings, manager.Lock()
        )
    print(f"Training loader workers: {workers}")
    data_loader = get_dataloader(config.uris)
    data_iter = iter(data_loader)

    unlabeled_data_iter = None
    if config.use_uamt and config.unlabeled_uris:
        unlabeled_data_loader = get_dataloader(config.unlabeled_uris, is_unlabeled=True)
        unlabeled_data_iter = iter(unlabeled_data_loader)

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

    # Load best model if architecture matches
    best_model_path = "best_model.pt"
    if strict_warm_start:
        load_required_starting_checkpoint(model, config, best_model_path)
    elif os.path.exists(best_model_path):
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
            for attr in WARM_START_FIELDS:
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
    # UA-MT teacher passes, decided on the first unlabeled batch.
    teacher_passes = None

    # Linear scaling rule. Kept local: config.lr is the recorded setting, and
    # scaling it in place wrote the scaled value into checkpoints and history.tsv.
    peak_lr = config.lr * (config.batch_size / 16.0)

    # Schedule by elapsed fraction of the time budget (see budget_lr_factor).
    print(
        f"Budget-time schedule: {WARMUP_FRACTION:.1%} warmup then cosine decay over "
        f"{config.time_budget}s, peak_lr={peak_lr:.2e}"
    )

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=0.0, weight_decay=config.weight_decay
    )
    amp_enabled = False  # Disabled for NaN debugging
    scaler = GradScaler(device=device.type, enabled=amp_enabled)

    # Initialize auxiliary task tools (the ST target only for an ST head).
    st_computer = (
        StructureTensorComputer(
            sigma=1.0, component_sigma=1.0, smooth_components=True, device=device
        )
        if StructureTensorComputer and "st" in heads
        else None
    )

    print(f"Starting Gated UNet-Transformer Loop (Budget: {config.time_budget}s)...")
    sys.stdout.flush()

    step = 0
    total_training_time = 0
    smooth_loss = 0
    # Steps not applied: a non-finite or exploding (> 1e6) loss, or a gradient
    # whose norm is not finite.
    skipped_updates = 0
    smoothed = False

    while True:
        t0 = time.time()
        try:
            # The loader's fiber target is a zero placeholder (fiber_target).
            x_raw, target_ink_raw, _ = next(data_iter)
            x_raw = x_raw.to(device)  # [B, C, Z_buffered, H, W]

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
            z_start = np.random.randint(0, 2 * DEPTH_MARGIN)
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

        # 3. Per-patch fiber pseudo-label for the fiber head's loss, on the
        # batch's device, BEFORE mixup to avoid boundary artifacts.
        with torch.no_grad():
            target_fiber = fiber_target(
                x_raw,
                x_orig,
                fiber_target_source,
                getattr(config, "target_fiber_sigma", 2.0),
            )
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

        x_aug1, target_ink_aug1, target_fiber_aug1 = apply_augmentations(
            x_orig, target_ink, target_fiber, step, None, config=config
        )
        # UAMT Unlabeled Augmentations
        if config.use_uamt and x_unlabeled is not None:
            x_unl_aug_student, x_unl_aug_teacher = uamt_views(x_unl_orig, step, config)

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
            out_ink_2d, out_fiber, out_qc, p1, out_st = trained_outputs(
                model_out, heads
            )
            # Diagnostic check: Isolate if NaN comes from backbone forward pass
            if torch.isnan(out_ink_2d).any():
                print(
                    f"DEBUG: NaN detected in model backbone output (out_ink_2d) at step {step}"
                )

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

            # A second view for the DINO-lite projection consistency, which is
            # trained only under UA-MT. Built and forwarded only then: otherwise
            # the view and its pass (~20% of a step) were computed and dropped.
            p2 = None
            if config.use_uamt and p1 is not None:
                x_aug2, _, _ = apply_augmentations(
                    x_orig, target_ink, target_fiber, step, None, config=config
                )
                p2_out = model(x_aug2, return_proj=True)
                if isinstance(p2_out, tuple):
                    # InkDetectorOptimized returns [ink, fiber, qc, proj, st]
                    # if only return_proj=True: [ink, proj]
                    p2 = p2_out[1]
                    if p2 is not None:
                        p2 = torch.nan_to_num(
                            p2, nan=0.0, posinf=100.0, neginf=-100.0
                        ).clamp(-100.0, 100.0)

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
                    if teacher_passes is None:
                        stochastic = teacher_is_stochastic(ema_model, x_unl_aug_teacher)
                        teacher_passes = UAMT_TEACHER_PASSES if stochastic else 1
                        print(
                            f"UA-MT teacher passes: {teacher_passes}"
                            + (
                                ""
                                if stochastic
                                else " (deterministic teacher: uncertainty weights are 1)"
                            )
                        )
                    # Finite by construction: sigmoids of sanitized logits.
                    teacher_prob, teacher_var = uamt_teacher(
                        ema_model, x_unl_aug_teacher, teacher_passes
                    )

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
            skip_step = True
        else:
            skip_step = False

        current_lr = peak_lr * budget_lr_factor(
            total_training_time / config.time_budget if config.time_budget > 0 else 1.0
        )
        if not skip_step:
            scaler.scale(total_loss).backward()
            skip_step = not guarded_update(
                model, optimizer, scaler, current_lr, step=step
            )
        skipped_updates += int(skip_step)

        # UAMT: Update Teacher EMA
        if config.use_uamt and ema_model is not None:
            with torch.no_grad():
                decay = config.ema_decay
                # Student weights stay finite: guarded_update skips any update
                # whose gradient is not (a per-tensor check here cost one GPU
                # sync per tensor per step).
                for param_student, param_teacher in zip(
                    model.parameters(), ema_model.parameters(), strict=False
                ):
                    param_teacher.data.mul_(decay).add_(
                        param_student.data, alpha=1.0 - decay
                    )

        dt = time.time() - t0
        total_training_time += dt
        if skip_step:
            # A skipped step reports no loss and leaves the smoothed loss alone.
            loss_val = float("nan")
        else:
            loss_val = total_loss.item()
            smooth_loss = 0.9 * smooth_loss + 0.1 * loss_val if smoothed else loss_val
            smoothed = True

        if step % 10 == 0:
            remaining = max(0, config.time_budget - total_training_time)
            print(
                f"Step {step:04d} | Loss: {smooth_loss:.6f} | LR: {current_lr:.2e} | dt: {dt * 1000:.0f}ms | Remaining: {remaining:.0f}s"
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
                val_dataset,
                config,
                device,
                step,
                total_training_time,
            )
        if total_training_time >= config.time_budget:
            break

    print(
        f"Evaluating metrics on validation protocol {protocol} "
        "(a fixed sample; searching for best threshold)..."
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

    torch.manual_seed(42)
    all_probs, all_targets, validation_diag = collect_validation_predictions(
        model,
        val_dataset,
        config.num_layers,
        device,
        batch_size=config.batch_size,
        amp_enabled=amp_enabled,
        protocol=protocol,
    )
    validation_diag.update(
        {
            "cc_errors": 0,
            "crit_errors": 0,
            "skeleton_errors": 0,
            "centerline_errors": 0,
            "mean_ap_errors": 0,
            "topology_threshold_errors": 0,
        }
    )

    # Per-patch diagnostics on the ink-containing patches; promotion pools all.
    ink_probs, ink_targets = ink_containing(all_probs, all_targets)
    best_dice = 0.0
    best_threshold = 0.5
    if ink_probs:
        probs_cat = torch.cat(ink_probs)
        targets_cat = torch.cat(ink_targets)

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
        topo_threshold, topo_cd = select_topology_threshold(
            ink_probs, ink_targets, diag=validation_diag
        )
        print(
            f"  Topology threshold: {topo_threshold:.3f} (centerline_dice {topo_cd:.6f})"
        )

        # Now re-run with best threshold for other metrics
        for i in range(len(ink_probs)):
            prob_2d = ink_probs[i]
            val_target = ink_targets[i]
            val_losses.append(
                1.0
                - compute_official_dice(val_target, prob_2d, threshold=best_threshold)
            )

            gt_bin_b = (val_target > 0.5).numpy().astype(bool)
            pred_bin_b = (prob_2d > topo_threshold).numpy().astype(bool)
            for b in range(gt_bin_b.shape[0]):
                # Each metric is counted on its own: a failure is recorded under
                # its own key instead of as a value (or as another metric's error).
                for key, values, measure in (
                    ("cc_errors", val_cc_diffs, compute_cc_diff),
                    ("crit_errors", val_crit_comps, compute_crit_comps),
                ):
                    try:
                        values.append(measure(gt_bin_b[b, 0], pred_bin_b[b, 0]))
                    except Exception as exc:
                        validation_diag[key] += 1
                        if validation_diag[key] <= 3:
                            print(
                                f"  Warning: {key[:-7]} metric failed for validation "
                                f"sample {i}: {type(exc).__name__}: {exc}"
                            )
                try:
                    ap_res = compute_mean_ap(
                        gt_bin_b[b, 0].astype(np.uint8),
                        prob_2d[b, 0].numpy().astype(np.float32),
                        ignore_index=0,
                    )
                    # villa's key is "mean_ap"; reading "mAP" recorded 0.0 for
                    # every run.
                    val_mean_aps.append(float(ap_res["mean_ap"]))
                except Exception as exc:
                    validation_diag["mean_ap_errors"] += 1
                    if validation_diag["mean_ap_errors"] <= 3:
                        print(
                            f"  Warning: mean_ap metric failed: {type(exc).__name__}: {exc}"
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
            "usable_patches": len(ink_probs),
            "skel_samples": len(val_skel_dists),
            "centerline_samples": len(val_centerline_dices),
            "cc_samples": len(val_cc_diffs),
            "crit_samples": len(val_crit_comps),
        }
    )

    val_bpb = np.mean(val_losses) if val_losses else 1.0
    avg_skel_dist = np.mean(val_skel_dists) if val_skel_dists else float("nan")
    avg_centerline_dice = np.mean(val_centerline_dices) if val_centerline_dices else 0.0
    # No samples is "not measured" (NaN), not a perfect 0.
    avg_cc_diff = np.mean(val_cc_diffs) if val_cc_diffs else float("nan")
    avg_crit_comp = np.mean(val_crit_comps) if val_crit_comps else float("nan")
    avg_mean_ap = np.mean(val_mean_aps) if val_mean_aps else float("nan")
    # Honest, prize-aligned selection metrics (single source of truth:
    # detector.metrics). val_bpb / skel_dist / centerline_dice above remain
    # reported but no longer decide promotion.
    _seg = pooled_segmentation_metrics(all_probs, all_targets)
    val_f1 = float(_seg.get("val_f1", float("nan")))
    val_f1_threshold = float(_seg.get("best_threshold", float("nan")))
    ap_prevalence_lift = float(_seg.get("ap_prevalence_lift", float("nan")))
    roc_auc = float(_seg.get("roc_auc", float("nan")))
    val_positive_rate = float(_seg.get("positive_rate", float("nan")))
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
    # Promotion runs on the honest F1 + AP-lift contract; val_bpb / topology are
    # reported but no longer decide.
    is_improvement, best_previous_val_f1, promotion_blocked = promotion_decision(
        val_f1,
        ap_prevalence_lift,
        submittable=submittable,
        enforce_prize_gates=getattr(config, "enforce_prize_gates", True),
        validation_complete=validation_diag["complete"],
        protocol=protocol,
        inputs=validation_diag.get("inputs_sha256"),
    )
    if promotion_blocked:
        print(f"Promotion blocked: {promotion_blocked}")

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
    print(f"val_bpb (Official):    {val_bpb:.6f}  [reported only]")
    print(f"avg_skel_dist:         {avg_skel_dist:.6f}")
    print(f"avg_centerline_dice:   {avg_centerline_dice:.6f}")
    print(f"avg_cc_diff:           {avg_cc_diff:.3f}")
    print(f"avg_crit_comp:         {avg_crit_comp:.3f}")
    print(f"avg_mean_ap:           {avg_mean_ap:.4f}")
    print(
        f"val_f1:                {val_f1:.6f} (thr {val_f1_threshold:.3f}; "
        f"incumbent {best_previous_val_f1:.6f}) {'[NEW BEST]' if is_improvement else ''}"
    )
    print(f"ap_prevalence_lift:    {ap_prevalence_lift:.4f}")
    print(f"roc_auc:               {roc_auc:.4f}  [selection: F1 gated by AP-lift]")

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
    if wandb_run is not None and ink_probs:
        wandb_tracking.log_prediction_image(
            wandb_run,
            ink_probs[0][0].numpy(),
            ink_targets[0][0].numpy(),
            topo_threshold,
        )
    print(f"submittable:           {submittable} (window={window_mm:.3f}mm)")
    if prize_gate_failures:
        print("prize_gate_failures:   " + " | ".join(prize_gate_failures))
    print(
        "validation_diag:       "
        f"scored={validation_diag['scored_patches']}/{validation_diag['requested_patches']}, "
        f"usable={validation_diag['usable_patches']}, "
        f"empty={validation_diag['empty_target_patches']}, "
        f"batch_errors={validation_diag['batch_errors']}, "
        f"cc_errors={validation_diag['cc_errors']}, "
        f"crit_errors={validation_diag['crit_errors']}, "
        f"skeleton_errors={validation_diag['skeleton_errors']}, "
        f"centerline_errors={validation_diag['centerline_errors']}, "
        f"mean_ap_errors={validation_diag['mean_ap_errors']}"
    )
    loader_warnings = warning_counts()
    for key, count in dict(shared_warnings or {}).items():  # the loader workers'
        loader_warnings[key] = loader_warnings.get(key, 0) + count
    if loader_warnings:
        print(f"loader_warnings:       {loader_warnings}")
    if skipped_updates:
        print(f"skipped_updates:       {skipped_updates} of {step} steps")
    print(f"train_loss:            {smooth_loss:.6f}")
    print(f"throughput_Mvps:       {throughput_Mvps:.2f}")
    sys.stdout.flush()

    # Log EVERY run to history.tsv for auditability — UNLESS this is an isolated
    # experiment run (checkpoint_out set), which must not touch loop state.
    if not getattr(config, "checkpoint_out", None):
        append_tsv_row(
            "history.tsv",
            HISTORY_COLUMNS,
            [
                time.strftime("%Y-%m-%d %H:%M:%S"),
                f"{val_bpb:.6f}",
                f"{avg_skel_dist:.6f}",
                f"{avg_centerline_dice:.6f}",
                f"{avg_cc_diff:.3f}",
                f"{avg_crit_comp:.3f}",
                f"{avg_mean_ap:.4f}",
                f"{smooth_loss:.6f}",
                f"{throughput_Mvps:.2f}",
                f"{num_params_M:.3f}",
                f"{peak_vram_mb:.1f}",
                json.dumps(asdict(config)),
            ],
        )

    # One record for every file this cycle's model is saved to (they had drifted
    # apart: last_model.pt lacked avg_mean_ap, checkpoint_out prize_gate_failures).
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "val_bpb": val_bpb,
        "avg_skel_dist": avg_skel_dist,
        "avg_centerline_dice": avg_centerline_dice,
        "avg_cc_diff": avg_cc_diff,
        "avg_mean_ap": avg_mean_ap,
        "val_f1": float(val_f1),
        "val_f1_threshold": float(val_f1_threshold),
        "val_protocol": protocol,
        "train_sampling_seed": sampling_seed,
        "training_labels": training_labels,
        "ap_prevalence_lift": float(ap_prevalence_lift),
        "roc_auc": float(roc_auc),
        "val_positive_rate": float(val_positive_rate),
        "submittable": submittable,
        "window_ok": window_ok,
        "window_mm": window_mm,
        "villa_metrics_ok": villa_metrics_ok,
        "prize_gate_failures": prize_gate_failures,
        "validation_diag": validation_diag,
        "config": asdict(config),
    }
    ckpt_out = getattr(config, "checkpoint_out", None)
    promoted = is_improvement and not ckpt_out
    if promoted:
        print(
            f"Saving new best model — val_f1: {val_f1:.6f} "
            f"(ap_lift {ap_prevalence_lift:.3f}, thr {val_f1_threshold:.3f})"
        )
    save_cycle_checkpoints(checkpoint, ckpt_out, is_improvement)
    if promoted:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cfg_json = json.dumps(asdict(config))
        append_tsv_row(
            log_file,
            RESULTS_COLUMNS,
            [
                stamp,
                f"{val_bpb:.6f}",
                f"{avg_skel_dist:.6f}",
                f"{avg_centerline_dice:.6f}",
                f"{avg_cc_diff:.3f}",
                f"{avg_crit_comp:.3f}",
                f"{smooth_loss:.6f}",
                f"{throughput_Mvps:.2f}",
                f"{num_params_M:.3f}",
                f"{peak_vram_mb:.1f}",
                cfg_json,
            ],
        )
        append_tsv_row(
            "prize_readiness.tsv",
            PRIZE_READINESS_COLUMNS,
            [
                stamp,
                submittable,
                window_ok,
                f"{window_mm:.4f}",
                villa_metrics_ok,
                config.patch_size,
                f"{val_bpb:.6f}",
                f"{avg_skel_dist:.6f}",
                f"{avg_centerline_dice:.6f}",
                f"{avg_cc_diff:.3f}",
                f"{avg_crit_comp:.3f}",
                cfg_json,
            ],
        )

        # Ensure filesystem sync (so best_model.pt / results.tsv / prize_readiness.tsv
        # are durable before the cycle returns).
        if hasattr(os, "sync"):
            os.sync()
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
        "val_f1": float(val_f1),
        "val_f1_threshold": float(val_f1_threshold),
        "val_protocol": protocol,
        "incumbent_val_f1": float(best_previous_val_f1),
        "promotion_blocked": promotion_blocked,
        "train_sampling_seed": sampling_seed,
        "training_labels": training_labels,
        "ap_prevalence_lift": float(ap_prevalence_lift),
        "roc_auc": float(roc_auc),
        "val_positive_rate": float(val_positive_rate),
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
        "augmentation_fallbacks": dict(AUGMENTATION_FALLBACKS),
        # Loader fallbacks this run hit (zero ridges, unwarped lasagna patches,
        # zero patches on read errors), counted past the few messages, the
        # loader workers' included (share_warning_counts).
        "loader_warnings": loader_warnings,
        # Steps not applied: a non-finite or > 1e6 loss, or a non-finite
        # gradient norm (see guarded_update).
        "skipped_updates": skipped_updates,
        # UA-MT teacher passes per step: 4 when its passes are stochastic, 1
        # when not (uncertainty weights 1); None without UA-MT batches.
        "uamt_teacher_passes": teacher_passes,
        "is_success": bool(is_improvement),
    }

    # Cleanup multiprocessing iterators to avoid leaked semaphores
    del data_iter
    del data_loader
    if unlabeled_data_iter is not None:
        del unlabeled_data_iter
        del unlabeled_data_loader

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
            resolve_training_labels(config)
            check_foundation_model_path(config)
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
