class ExperimentConfig:
    # Data
    uri: str = None  # Deprecated, use uris instead
    uris: list = None # List of URIs to pool for training
    val_uri: str = 'local_data/PHercParis2Fr143/surface_volume/'
    cache_dir: str = None  # If None, caches are stored next to volume_uri
    use_ridges: bool = False # 3D Ridge/Frangi feature channel
    ridge_sigma: float = 2.0 # Ridge filter parameter

    # Training Loop
    batch_size: int = 16
    patch_size: int = 64
    num_layers: int = 24
    lr: float = 1e-3
    weight_decay: float = 0.01
    time_budget: int = 900
    pinned: bool = False # If True, autoresearch loop should not evolve this config

    # Loss Weights
    loss_ink_bce: float = 0.4
    loss_ink_dice: float = 0.4
    loss_fiber_bce: float = 0.2
    loss_st: float = 0.1
    label_smoothing: float = 0.0 # Standard for GP winner is 0.25
    aug_mode: str = 'albumentations' # 'albumentations' or 'batchgeneratorsv2'

    # Domain Randomization (Sprint 006)
    aug_flip_p: float = 0.5
    aug_brightness_p: float = 0.75
    aug_affine_p: float = 0.75
    aug_coarse_dropout_p: float = 0.5
    aug_elastic_p: float = 0.0
    aug_grid_p: float = 0.0
    aug_rotate_limit: int = 180
    aug_scale_limit: float = 0.15

    # Model Architecture
    architecture: str = "gated_unet"
    base_feat: int = 64
    num_blocks: int = 16
    num_heads: int = 8
    dropout: float = 0.0

    def __post_init__(self):
        if self.uris is None:
            if self.uri is not None:
                self.uris = [self.uri]
            else:
                self.uris = ['local_data/PHercParis2Fr47/surface_volume/']
    def save(self, path):
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def load(cls, path):
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)

