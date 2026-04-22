# Night Shift Sprint - 2026-04-21
- **Start Time**: 20:28:59
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: lr_5e-05 (REVERTED)
- **Timestamp**: 20:44:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 5e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5791825634997325, params: 1.842707M, vram: 18102.93017578125MB, speed: 3.6173192938000245Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: num_blocks_20 (REVERTED)
- **Timestamp**: 20:59:37
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 20, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5781931745356292, params: 2.109715M, vram: 21576.01806640625MB, speed: 3.4263165122911023Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: lr_1e-05 (REVERTED)
- **Timestamp**: 21:14:57
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5815302943994006, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.036416795330176Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: weight_decay_0.001 (REVERTED)
- **Timestamp**: 21:30:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.001, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5783656092036734, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.4811172875155236Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: num_blocks_12 (REVERTED)
- **Timestamp**: 21:45:40
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 12, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.577989861638996, params: 1.575699M, vram: 14627.84228515625MB, speed: 3.8112147577986115Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: use_ridges_True (REVERTED)
- **Timestamp**: 22:01:09
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5746687261972644, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.1848443266339097Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: num_blocks_10 (REVERTED)
- **Timestamp**: 22:16:30
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 10, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5785961784173028, params: 1.442195M, vram: 12892.79833984375MB, speed: 4.289730859326346Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 22:31:49
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5810679179931034, params: 1.842707M, vram: 18104.43017578125MB, speed: 4.121536979351796Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: num_blocks_8 (REVERTED)
- **Timestamp**: 22:47:06
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 8, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5793821751096806, params: 1.308691M, vram: 11152.75439453125MB, speed: 5.565055386668356Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: num_layers_16 (REVERTED)
- **Timestamp**: 23:02:27
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5788885403586818, params: 1.842707M, vram: 18104.80517578125MB, speed: 3.853133657077637Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: batch_size_24 (CRASHED (OOM))
- **Timestamp**: 23:02:44
- **Config**: cache_dir: None, use_ridges: False, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 12: batch_size_24 (REVERTED)
- **Timestamp**: 23:18:04
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5786696443730367, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.4091993210824905Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: weight_decay_0.001 (REVERTED)
- **Timestamp**: 23:33:23
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5768916775349121, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.225851707218844Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: weight_decay_0.0 (REVERTED)
- **Timestamp**: 23:48:40
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.0, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5775325495422845, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.388470883940601Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: loss_ink_bce_0.4 (REVERTED)
- **Timestamp**: 00:03:57
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.579241069979935, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.372350302742057Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: dropout_0.1 (REVERTED)
- **Timestamp**: 00:19:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5770203324866016, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.389576135458198Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 17: dropout_0.0 (REVERTED)
- **Timestamp**: 00:34:35
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5789722727298743, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.4090990827049135Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: lr_0.0005 (REVERTED)
- **Timestamp**: 00:49:52
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.577252587310171, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.425246359188121Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 19: num_heads_8 (REVERTED)
- **Timestamp**: 01:05:09
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5784548344237224, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.405047677095151Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: num_heads_4 (REVERTED)
- **Timestamp**: 01:20:27
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5800649298529048, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.408549085715285Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 21: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 01:35:47
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5780998597456743, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.41022700010186Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 22: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 01:51:04
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.576759503754451, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.421221725902414Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 23: weight_decay_0.0 (REVERTED)
- **Timestamp**: 02:06:22
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5780238865563454, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.416489709236722Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 24: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 02:21:38
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5753796692952428, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.431110135151273Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 25: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 02:36:55
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5742865352389714, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.397436730881192Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 26: dropout_0.1 (REVERTED)
- **Timestamp**: 02:52:16
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5801273512827132, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.41336915106329Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 27: batch_size_24 (REVERTED)
- **Timestamp**: 03:07:33
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5780178136027505, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.4131743661722656Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 28: loss_ink_bce_0.4 (REVERTED)
- **Timestamp**: 03:22:50
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5768092310460055, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.433890219397744Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 29: patch_size_96 (REVERTED)
- **Timestamp**: 03:38:07
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5770577613505172, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.41289092996759Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 30: weight_decay_0.0 (REVERTED)
- **Timestamp**: 03:53:23
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5760254064335038, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.414286257827086Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 31: patch_size_96 (REVERTED)
- **Timestamp**: 04:08:44
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5762529525133573, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.419312807011737Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 32: num_layers_24 (REVERTED)
- **Timestamp**: 04:24:00
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5770547497976299, params: 1.842707M, vram: 18104.43017578125MB, speed: 4.425859289991656Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 33: use_ridges_False (REVERTED)
- **Timestamp**: 04:39:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5768558520139283, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.40045213004892Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 34: use_ridges_True (REVERTED)
- **Timestamp**: 04:54:35
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5793618234700019, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.424572242252009Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 35: num_layers_16 (REVERTED)
- **Timestamp**: 05:09:52
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5751274620866703, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.232692659296333Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 36: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 05:25:14
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5793709252473105, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.2793419739766945Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 37: lr_0.0001 (REVERTED)
- **Timestamp**: 05:40:32
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5760510214838638, params: 1.842707M, vram: 18104.43017578125MB, speed: 4.236181282165196Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 38: use_ridges_False (REVERTED)
- **Timestamp**: 05:55:50
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.578453341565402, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.301679736510987Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 39: num_blocks_12 (REVERTED)
- **Timestamp**: 06:11:20
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5763223760421782, params: 1.842707M, vram: 18103.80517578125MB, speed: 4.148374319013178Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 40: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 06:26:42
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5784376857825958, params: 1.842707M, vram: 18104.80517578125MB, speed: 3.9236584849912592Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 41: patch_size_96 (REVERTED)
- **Timestamp**: 06:42:03
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5775813446279, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.260291023695443Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 42: num_layers_24 (REVERTED)
- **Timestamp**: 06:57:21
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5775317147477571, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.504812018623146Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 43: use_ridges_False (REVERTED)
- **Timestamp**: 07:12:52
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5779399510279829, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.2331874128445985Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 07:12:54
Transitioning to DAY SHIFT...
