# Day Shift Sprint - 2026-05-21
- **Start Time**: 10:06:37
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: lr_5e-05 (REVERTED)
- **Timestamp**: 10:23:50
- **Config**: uris: ['local_data/PHercParis2Fr47/surface_volume.zarr'], cache_dir: None, use_ridges: True, use_lasagna: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 5e-05, weight_decay: 0.01, time_budget: 900, pinned: False, loss_ink_bce: 0.6, loss_ink_dice: 0.2, loss_fiber_bce: 0.3, loss_st: 0.1, label_smoothing: 0.0, aug_mode: batchgeneratorsv2, aug_flip_p: 0.5, aug_brightness_p: 0.75, aug_affine_p: 0.75, aug_coarse_dropout_p: 0.5, aug_elastic_p: 0.0, aug_grid_p: 0.0, aug_rotate_limit: 180, aug_scale_limit: 0.15, aug_scroll_decohesion_p: 0.0, aug_scroll_warping_p: 0.0, aug_scroll_squeeze_p: 0.0, aug_scroll_z_dropout_p: 0.0, aug_scroll_intensity_drift_p: 0.0, use_betti_loss: False, betti_loss_weight: 0.1, auxiliary_config: {'enabled': False, 'task_types': ['surface_normals', 'structure_tensor'], 'weights': {'surface_normals': 0.05, 'structure_tensor': 0.05}}, target_fiber_source: sobel_z, target_fiber_sigma: 2.0, multi_task_heads: False, architecture: resenc_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0, pseudo_label_dir: local_data/pseudo_labels, foundation_model_path: None, enforce_prize_gates: False, min_prize_centerline_dice: 0.01, max_prize_skel_dist: 2.0, max_prize_cc_diff: 64.0, min_prize_topology_samples: 1, use_uamt: False, ema_decay: 0.99, consistency_weight: 0.1, unlabeled_uris: ['local_data/PHercParis2Fr47/surface_volume.zarr']
- **Stats**: val_bpb: 0.4206039099395275, loss: 0.6448967477402769, params: 10.222914M, vram: 10918.21728515625MB, speed: 0.7610032214714171Mvps
- **Result**: No improvement detected. Config reverted.

