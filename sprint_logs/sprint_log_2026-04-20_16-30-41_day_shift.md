# Day Shift Sprint - 2026-04-20
- **Start Time**: 16:30:41
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: dropout_0.0 (REVERTED)
- **Timestamp**: 16:45:58
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5936786060299646, params: 1.842707M, vram: 18102.93017578125MB, speed: 5.0046962625513745Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 17:01:15
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.6543753948417793, params: 1.842707M, vram: 18102.93017578125MB, speed: 5.341939213305867Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 17:16:30
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.6, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.7931623105219414, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.397676198376382Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: loss_ink_bce_0.4 (REVERTED)
- **Timestamp**: 17:31:47
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5953325323926651, params: 1.842707M, vram: 18103.80517578125MB, speed: 5.070503695523181Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: weight_decay_0.0 (REVERTED)
- **Timestamp**: 17:47:05
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.0, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5939643174778737, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.901640778275022Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: lr_0.0005 (REVERTED)
- **Timestamp**: 18:02:25
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0005, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5948750930765597, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.344658705236254Mvps
- **Result**: No improvement detected. Config reverted.

