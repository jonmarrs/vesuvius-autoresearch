"""Configuration for the productionized TimeSformer ink detector.

Defaults are the proven Grand-Prize recipe values (held-out pixel-AUC 0.711 on
PHercParis2Fr47 -> Fr143). Depth (in_chans) is the through-surface signal axis and is
not subject to the lateral prize window; only the lateral patch `size` is constrained.
"""
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
    weight_decay: float = 1e-6
    max_grad_norm: int = 100
    warmup_factor: int = 10
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
        for name in ("in_chans", "size", "tile_size", "stride", "train_batch_size"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.architecture not in {"timesformer", "resenc"}:
            raise ValueError(f"unknown architecture: {self.architecture!r}")
        if self.start_idx < 0 or self.end_idx - self.start_idx != self.in_chans:
            raise ValueError("end_idx - start_idx must equal in_chans, with start_idx >= 0")
        if self.tile_size % self.size:
            raise ValueError("tile_size must be a multiple of size")
        if self.stride > self.size:
            raise ValueError("stride must be <= size to avoid gaps in inference")
        if self.architecture == "timesformer" and self.size % 16:
            raise ValueError("TimeSformer size must be a multiple of 16")
        if self.architecture == "resenc":
            if self.resenc_n_stages < 2 or self.resenc_n_stages > self.size.bit_length():
                raise ValueError("resenc_n_stages is incompatible with size")
            divisor = 2 ** (self.resenc_n_stages - 1)
            if self.size % divisor or self.size // divisor < 2:
                raise ValueError("resenc size must be divisible by its downsampling factor and retain at least 2 pixels")
        self.validate_window()

    def validate_window(self) -> None:
        # The lateral limit is the pixel count (<= 64px @ 8um); its physical width
        # (0.512mm) is derived from max_lateral_px rather than a separate rounded bound.
        max_mm = self.max_lateral_px * self.um_per_px / 1000.0
        mm = self.size * self.um_per_px / 1000.0
        if self.size > self.max_lateral_px or mm > max_mm + 1e-9:
            raise ValueError(
                f"lateral window {self.size}px/{mm:.3f}mm exceeds prize guidance "
                f"(<= {self.max_lateral_px}px / {max_mm:.3f}mm)"
            )

    @property
    def full_res(self) -> bool:
        """Per-pixel models (resenc) keep full-resolution labels; the TimeSformer uses 4x4."""
        return self.architecture != "timesformer"
