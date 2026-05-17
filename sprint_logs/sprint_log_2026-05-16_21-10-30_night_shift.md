# Night Shift Sprint - 2026-05-16
- **Start Time**: 21:10:30
- **Goal**: Monotonic val_bpb optimization via 60-min cycles (Config-Driven).

## Cycle 1: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 22:12:45
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: False, use_lasagna: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 3600, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.2, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: albumentations, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, aug_scroll_decohesion_p: 0.0, aug_scroll_squeeze_p: 0.0, aug_scroll_z_dropout_p: 0.0, aug_scroll_intensity_drift_p: 0.0, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, architecture: lejepa_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, foundation_model_path: checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth, enforce_prize_gates: True, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1, use_uamt: False, ema_decay: 0.99, consistency_weight: 0.1, unlabeled_uris: ['local_data/PHercParis2Fr143/surface_volume.zarr', 'local_data/PHercParis2Fr47/surface_volume.zarr']
- **Stats**: val_bpb: 0.4145089077949524, loss: 0.6506369120761255, params: 23.905353M, vram: 3062.49609375MB, speed: 4.93999272963053Mvps
- **Result**: No improvement detected. Config reverted.

