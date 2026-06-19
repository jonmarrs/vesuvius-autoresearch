# repro/ink_segformer/config.py
from dataclasses import dataclass


@dataclass
class ReproConfig:
    data_root: str = "local_data/kaggle_ink/train"  # contains 1/ 2/ 3/
    tile: int = 224
    stride: int = 112
    z_start: int = 16  # middle 32 of the 65 depth layers
    z_count: int = 32
    stem_channels: int = 32
    encoder: str = "mit_b3"
    batch_size: int = 8
    lr: float = 1e-4
    weight_decay: float = 1e-4
    epochs: int = 25
    min_papyrus: float = 0.05  # min fraction of papyrus mask in a sampled tile
    seed: int = 7
