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
