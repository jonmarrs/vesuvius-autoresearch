# Day Shift Sprint - 2026-04-24
- **Start Time**: 08:38:05
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: num_blocks_12 (REVERTED)
- **Timestamp**: 08:53:20
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 12, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5793319634150034, params: 1.575699M, vram: 14628.71728515625MB, speed: 4.813566739214558Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: lr_1e-05 (REVERTED)
- **Timestamp**: 09:08:37
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5811049318584594, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.400579233415112Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: batch_size_24 (CRASHED (OOM))
- **Timestamp**: 09:08:46
- **Config**: cache_dir: None, use_ridges: False, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 4: num_blocks_20 (REVERTED)
- **Timestamp**: 09:24:02
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 20, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5781780656515799, params: 2.109715M, vram: 21576.01806640625MB, speed: 3.8749234984662495Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: weight_decay_0.001 (REVERTED)
- **Timestamp**: 09:39:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.001, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5791414876930739, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.414224154490879Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: num_blocks_10 (REVERTED)
- **Timestamp**: 09:54:37
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 10, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5794231835489315, params: 1.442195M, vram: 12892.79833984375MB, speed: 5.01142507781895Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: dropout_0.0 (REVERTED)
- **Timestamp**: 10:09:55
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5772046526157212, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.323832009258024Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: lr_5e-05 (REVERTED)
- **Timestamp**: 10:25:14
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 5e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.581837120727981, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.9909421565259726Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: batch_size_16 (REVERTED)
- **Timestamp**: 10:40:32
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5781937706554745, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.220223025989908Mvps
- **Result**: No improvement detected. Config reverted.

