"""Configuration for the productionized TimeSformer ink detector.

Defaults are the proven Grand-Prize recipe values (held-out pixel-AUC 0.711 on
PHercParis2Fr47 -> Fr143). Depth (in_chans) is the through-surface signal axis and is
not subject to the lateral prize window; only the lateral patch `size` is constrained.
"""

import math
from dataclasses import dataclass, field


@dataclass
class DetectorConfig:
    # model / window
    in_chans: int = 26
    size: int = 64
    start_idx: int = 17
    end_idx: int = 43  # exclusive -> 26 slices
    # tiling
    tile_size: int = 256
    stride: int = 32
    # optimization
    train_batch_size: int = 32
    epochs: int = 12
    lr: float = 3e-5
    # These defaults describe the executed reference recipe, rather than the
    # unused constants inherited from its original configuration class.
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    warmup_factor: float = 1.0
    min_lr: float = 1e-6
    seed: int = 0
    num_workers: int = 8
    # loss
    dice_w: float = 0.5
    bce_w: float = 0.5
    bce_smooth: float = 0.25
    # data / io
    data_root: str = "villa/ink-detection/train_scrolls"
    train_fragment_ids: list[str] = field(default_factory=lambda: ["PHercParis2Fr47"])
    valid_fragment_id: str = "PHercParis2Fr143"
    model_dir: str = "models/detector"
    reports_dir: str = "reports/detector"
    use_tta: bool = False
    # prize window
    max_lateral_px: int = 64
    um_per_px: float = 8.0
    # architecture selection (Sub-project B)
    architecture: str = "timesformer"  # "timesformer" | "resenc"
    resenc_n_stages: int = 5
    resenc_base_feat: int = 32

    def validate(self) -> None:
        """Check shape/tiling contracts before reading data or building a model."""
        for name in (
            "in_chans",
            "size",
            "tile_size",
            "stride",
            "train_batch_size",
            "epochs",
            "resenc_n_stages",
            "resenc_base_feat",
            "end_idx",
        ):
            self._integer(name, minimum=1)
        for name in ("start_idx", "num_workers", "seed"):
            self._integer(name, minimum=0)
        for name in ("lr", "max_grad_norm"):
            self._finite_number(name, positive=True)
        for name in ("weight_decay", "min_lr", "dice_w", "bce_w", "bce_smooth"):
            self._finite_number(name)
        self._finite_number("warmup_factor", positive=True)
        if self.warmup_factor < 1:
            raise ValueError("warmup_factor must be >= 1")
        if self.min_lr > self.lr * self.warmup_factor:
            raise ValueError("min_lr must not exceed the warmed-up learning rate")
        if self.bce_smooth > 1:
            raise ValueError("bce_smooth must be between 0 and 1")
        if self.dice_w + self.bce_w <= 0:
            raise ValueError("at least one loss weight must be positive")
        if not isinstance(self.use_tta, bool):
            raise ValueError("use_tta must be a boolean")
        if not isinstance(self.architecture, str) or self.architecture not in {
            "timesformer",
            "resenc",
        }:
            raise ValueError(f"unknown architecture: {self.architecture!r}")
        if (
            not isinstance(self.train_fragment_ids, list)
            or not self.train_fragment_ids
            or any(
                not isinstance(fid, str) or not fid for fid in self.train_fragment_ids
            )
        ):
            raise ValueError(
                "train_fragment_ids must be a nonempty list of fragment names"
            )
        if not isinstance(self.valid_fragment_id, str) or not self.valid_fragment_id:
            raise ValueError("valid_fragment_id must be a nonempty fragment name")
        if self.start_idx < 0 or self.end_idx - self.start_idx != self.in_chans:
            raise ValueError(
                "end_idx - start_idx must equal in_chans, with start_idx >= 0"
            )
        if self.tile_size % self.size:
            raise ValueError("tile_size must be a multiple of size")
        if self.stride > self.size:
            raise ValueError("stride must be <= size to avoid gaps in inference")
        if self.architecture == "timesformer" and self.size % 16:
            raise ValueError("TimeSformer size must be a multiple of 16")
        if self.architecture == "resenc":
            if (
                self.resenc_n_stages < 2
                or self.resenc_n_stages > self.size.bit_length()
            ):
                raise ValueError("resenc_n_stages is incompatible with size")
            divisor = 2 ** (self.resenc_n_stages - 1)
            if self.size % divisor or self.size // divisor < 2:
                raise ValueError(
                    "resenc size must be divisible by its downsampling factor and retain at least 2 pixels"
                )
        self.validate_window()

    def validate_window(self) -> None:
        self._integer("size", minimum=1)
        self._integer("max_lateral_px", minimum=1)
        self._finite_number("um_per_px", positive=True)
        # The lateral limit is the pixel count (<= 64px @ 8um); its physical width
        # (0.512mm) is derived from max_lateral_px rather than a separate rounded bound.
        max_mm = self.max_lateral_px * self.um_per_px / 1000.0
        mm = self.size * self.um_per_px / 1000.0
        if self.size > self.max_lateral_px or mm > max_mm + 1e-9:
            raise ValueError(
                f"lateral window {self.size}px/{mm:.3f}mm exceeds prize guidance "
                f"(<= {self.max_lateral_px}px / {max_mm:.3f}mm)"
            )

    def _integer(self, name: str, minimum: int) -> None:
        value = getattr(self, name)
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            requirement = (
                "a positive integer" if minimum == 1 else "a nonnegative integer"
            )
            raise ValueError(f"{name} must be {requirement}")

    def _finite_number(self, name: str, positive: bool = False) -> None:
        value = getattr(self, name)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
            or (positive and value == 0)
        ):
            requirement = "positive" if positive else "nonnegative"
            raise ValueError(f"{name} must be a finite {requirement} number")

    @property
    def full_res(self) -> bool:
        """Per-pixel models (resenc) keep full-resolution labels; the TimeSformer uses 4x4."""
        return self.architecture != "timesformer"
