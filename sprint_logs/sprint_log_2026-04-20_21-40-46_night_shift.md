# Night Shift Sprint - 2026-04-20
- **Start Time**: 21:40:46
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 21:56:30
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5992185949200315, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.105379409941785Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: dropout_0.1 (REVERTED)
- **Timestamp**: 22:14:24
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 1.0, loss: 0.5917342031668517, params: 1.842707M, vram: 18102.43017578125MB, speed: 1.669029959373786Mvps
- **Result**: No improvement detected. Config reverted.

