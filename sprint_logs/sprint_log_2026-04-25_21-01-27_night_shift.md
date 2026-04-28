# Night Shift Sprint - 2026-04-25
- **Start Time**: 21:01:27
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: architecture_i3d (CRASHED)
- **Timestamp**: 21:01:42
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, architecture: i3d, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

