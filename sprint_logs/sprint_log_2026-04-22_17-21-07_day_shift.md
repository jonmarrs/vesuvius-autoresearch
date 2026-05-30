# Day Shift Sprint - 2026-04-22
- **Start Time**: 17:21:07
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 17:36:32
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5788314374377228, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.29268444945087Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 17:51:49
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.6, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.7768497519735533, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.375562516524595Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: num_layers_32 (CRASHED)
- **Timestamp**: 17:51:58
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 32, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 4: dropout_0.0 (REVERTED)
- **Timestamp**: 18:07:16
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 1.0, loss: 0.5816532066638951, params: 1.842707M, vram: 16329.18017578125MB, speed: 4.666476004751102Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 18:22:33
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.2, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.37663617566699914, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.288919129321886Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: num_blocks_16 (REVERTED)
- **Timestamp**: 18:37:53
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.579765333186761, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.264821792467616Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 18:53:10
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.2, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5777197662320189, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.365735211568856Mvps
- **Result**: No improvement detected. Config reverted.
