"""Serializable experiment configuration, independent of training/GPU imports.

train.py re-exports both classes for older callers and checkpoint imports.
"""

import json
from dataclasses import asdict, dataclass, field


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
