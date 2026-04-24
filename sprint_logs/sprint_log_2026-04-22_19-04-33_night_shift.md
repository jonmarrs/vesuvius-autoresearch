# Night Shift Sprint - 2026-04-22
- **Start Time**: 19:04:33
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: dropout_0.1 (REVERTED)
- **Timestamp**: 19:20:07
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 1.0, loss: 0.5779939323039586, params: 1.842707M, vram: 18104.80517578125MB, speed: 3.2713867352742043Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: num_layers_16 (CRASHED (OOM))
- **Timestamp**: 19:20:20
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 3: patch_size_96 (CRASHED (OOM))
- **Timestamp**: 19:20:36
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 96, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 4: patch_size_64 (CRASHED (OOM))
- **Timestamp**: 19:20:50
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 5: batch_size_8 (CRASHED (OOM))
- **Timestamp**: 19:21:04
- **Config**: cache_dir: None, use_ridges: False, batch_size: 8, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 6: patch_size_96 (CRASHED (OOM))
- **Timestamp**: 19:21:24
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 7: weight_decay_0.1 (CRASHED (OOM))
- **Timestamp**: 19:21:37
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.1, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 8: num_heads_12 (CRASHED (OOM))
- **Timestamp**: 19:21:50
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 9: lr_0.0005 (CRASHED (OOM))
- **Timestamp**: 19:22:04
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0005, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 10: lr_1e-05 (CRASHED (OOM))
- **Timestamp**: 19:22:19
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 11: weight_decay_0.1 (CRASHED (OOM))
- **Timestamp**: 19:22:38
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 12: base_feat_128 (CRASHED (OOM))
- **Timestamp**: 19:22:51
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 128, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 13: dropout_0.0 (CRASHED (OOM))
- **Timestamp**: 19:23:03
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 14: num_blocks_12 (CRASHED (OOM))
- **Timestamp**: 19:23:15
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 15: num_layers_16 (CRASHED (OOM))
- **Timestamp**: 19:23:27
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 16: num_layers_32 (CRASHED (OOM))
- **Timestamp**: 19:23:45
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 17: batch_size_24 (CRASHED (OOM))
- **Timestamp**: 19:23:59
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 18: batch_size_24 (CRASHED (OOM))
- **Timestamp**: 19:24:11
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 19: lr_0.0001 (CRASHED (OOM))
- **Timestamp**: 19:24:24
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 20: batch_size_24 (CRASHED (OOM))
- **Timestamp**: 19:24:37
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 21: weight_decay_0.001 (CRASHED (OOM))
- **Timestamp**: 19:24:55
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 22: weight_decay_0.0 (CRASHED (OOM))
- **Timestamp**: 19:25:10
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

