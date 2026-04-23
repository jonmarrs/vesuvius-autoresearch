# Night Shift Sprint - 2026-04-22
- **Start Time**: 19:25:49
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: num_blocks_8 (REVERTED)
- **Timestamp**: 19:41:06
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 8, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5771329878288534, params: 1.308691M, vram: 11156.25439453125MB, speed: 5.639220504372008Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: lr_5e-05 (REVERTED)
- **Timestamp**: 19:56:22
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 5e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5811013227822924, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.377364313401793Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: patch_size_64 (REVERTED)
- **Timestamp**: 20:11:38
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5757161820292239, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.365001870788533Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: weight_decay_0.001 (REVERTED)
- **Timestamp**: 20:26:55
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.001, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5774880519414394, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.378814152439814Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 20:42:12
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5764696398889275, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.328889756888606Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: base_feat_32 (REVERTED)
- **Timestamp**: 20:57:31
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 32, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5808028419925597, params: 0.836811M, vram: 14789.73193359375MB, speed: 5.17521562166885Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: lr_1e-05 (REVERTED)
- **Timestamp**: 21:12:47
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5806538869571406, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.377979955539491Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: base_feat_64 (REVERTED)
- **Timestamp**: 21:28:04
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5772510486443403, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.377495006771141Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: loss_ink_bce_0.4 (REVERTED)
- **Timestamp**: 21:43:20
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5767177950727203, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.371078225633592Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: num_blocks_10 (REVERTED)
- **Timestamp**: 21:58:36
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 10, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5792416470928745, params: 1.442195M, vram: 12892.79833984375MB, speed: 5.407737441484625Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: lr_0.001 (REVERTED)
- **Timestamp**: 22:13:56
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5774329781985417, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.3974248919132926Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: weight_decay_0.0 (REVERTED)
- **Timestamp**: 22:29:12
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.0, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5799537799594188, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.380854315784277Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: batch_size_24 (CRASHED (OOM))
- **Timestamp**: 22:29:22
- **Config**: cache_dir: None, use_ridges: False, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 14: num_blocks_12 (REVERTED)
- **Timestamp**: 22:44:38
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 12, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5771825636580703, params: 1.575699M, vram: 14630.84228515625MB, speed: 5.037966506182123Mvps
- **Result**: No improvement detected. Config reverted.

