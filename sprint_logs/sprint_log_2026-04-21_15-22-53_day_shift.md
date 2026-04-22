# Day Shift Sprint - 2026-04-21
- **Start Time**: 15:22:53
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 15:38:10
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.6, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.7801719405610595, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.9578628351281386Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 15:53:29
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.2, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.38161056691067385, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.2924038486895215Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: base_feat_128 (CRASHED (OOM))
- **Timestamp**: 15:53:41
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 128, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 4: patch_size_96 (REVERTED)
- **Timestamp**: 16:09:15
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 96, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5781158841814859, params: 1.842707M, vram: 22233.7958984375MB, speed: 5.230105965478314Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: weight_decay_0.1 (REVERTED)
- **Timestamp**: 16:24:39
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.1, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5740262862351816, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.1921560471820585Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: num_heads_12 (REVERTED)
- **Timestamp**: 16:40:11
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5820519362672589, params: 1.842707M, vram: 18103.43017578125MB, speed: 3.0071107747417867Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: base_feat_32 (REVERTED)
- **Timestamp**: 16:55:28
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 32, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5801846258750496, params: 0.836811M, vram: 14789.73193359375MB, speed: 4.113531801840837Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 17:10:46
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5800437242101524, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.384328637037773Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: lr_0.0005 (REVERTED)
- **Timestamp**: 17:26:05
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0005, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5803068307624075, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.364023905229393Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 17:41:28
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5789657830325581, params: 1.842707M, vram: 18103.80517578125MB, speed: 3.2404515098121967Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: dropout_0.1 (REVERTED)
- **Timestamp**: 17:57:05
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 1.0, loss: 0.5788099548862591, params: 1.842707M, vram: 18104.80517578125MB, speed: 3.5012331434453885Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: lr_5e-05 (REVERTED)
- **Timestamp**: 18:12:25
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5802311458397357, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.9188079446224724Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 18:27:45
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.576484065008851, params: 1.842707M, vram: 18104.80517578125MB, speed: 3.8499924428088983Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: num_blocks_12 (REVERTED)
- **Timestamp**: 18:43:03
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5790784213275042, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.287807103464233Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: patch_size_96 (REVERTED)
- **Timestamp**: 18:58:21
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5790492182085071, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.378151577696551Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 19:13:43
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.578698621965994, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.267780213052463Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 19:13:45
Transitioning to NIGHT SHIFT...
