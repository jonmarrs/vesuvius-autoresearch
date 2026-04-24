# Day Shift Sprint - 2026-04-23
- **Start Time**: 07:33:13
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: num_heads_8 (REVERTED)
- **Timestamp**: 07:48:29
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5765027423145617, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.7689157991277145Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: num_layers_32 (CRASHED)
- **Timestamp**: 07:48:38
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 32, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 3: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 08:03:54
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5830792961743254, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.3484154960963854Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: num_heads_4 (REVERTED)
- **Timestamp**: 08:19:09
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.580939730766141, params: 1.842707M, vram: 12484.3447265625MB, speed: 5.312227440015775Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 08:34:26
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5233745999047058, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.40013539529043Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: use_ridges_True (CRASHED)
- **Timestamp**: 08:38:12
- **Config**: cache_dir: None, use_ridges: True, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 7: dropout_0.0 (REVERTED)
- **Timestamp**: 08:53:52
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 1.0, loss: 0.5803866019509267, params: 1.842707M, vram: 16330.18017578125MB, speed: 4.908866305403865Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: dropout_0.0 (REVERTED)
- **Timestamp**: 09:09:07
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5779050928243317, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.461424561264205Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 09:24:23
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.6321889279594897, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.473854813522651Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 09:39:38
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.2, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.3775610528853095, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.47681066166471Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 09:54:58
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.6, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.779710620919817, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.443062300968568Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: num_heads_8 (REVERTED)
- **Timestamp**: 10:10:16
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.578291019894235, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.780857909065842Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: batch_size_16 (REVERTED)
- **Timestamp**: 10:25:35
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5805475660742425, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.260765059196975Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: patch_size_96 (REVERTED)
- **Timestamp**: 10:40:58
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5804219956878504, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.480779394704868Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 10:56:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5779996972869983, params: 1.842707M, vram: 18104.80517578125MB, speed: 3.5453268633151147Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: num_heads_12 (REVERTED)
- **Timestamp**: 11:11:43
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.579073010348146, params: 1.842707M, vram: 18104.80517578125MB, speed: 3.771757904439318Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 17: weight_decay_0.01 (REVERTED)
- **Timestamp**: 11:27:00
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5766006268362054, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.345220573770003Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 11:42:15
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5760110718208937, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.412238458924155Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 19: num_blocks_8 (REVERTED)
- **Timestamp**: 11:57:31
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5789566652552418, params: 1.842707M, vram: 18104.43017578125MB, speed: 4.385838180477015Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 12:12:47
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5768070551930304, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.096035451369136Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 21: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 12:28:09
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5771107279799272, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.22918607006006Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 22: num_blocks_20 (REVERTED)
- **Timestamp**: 12:43:27
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5797446578759109, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.078228392530868Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 23: num_heads_12 (REVERTED)
- **Timestamp**: 12:58:43
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5795291127068554, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.26702816159765Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 24: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 13:14:00
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5761341534622121, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.358378261269341Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 25: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 13:29:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5765678573069981, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.360966655965572Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 26: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 13:44:37
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5777199546081254, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.439637071962159Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 27: base_feat_32 (REVERTED)
- **Timestamp**: 13:59:54
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.57560473433789, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.02269495411914Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 28: patch_size_96 (REVERTED)
- **Timestamp**: 14:15:11
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5772391744674, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.954637454179664Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 29: patch_size_96 (REVERTED)
- **Timestamp**: 14:30:28
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5799819920108167, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.274984990238933Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 30: num_blocks_10 (REVERTED)
- **Timestamp**: 14:45:44
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5778125528677285, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.410298590845383Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 31: num_blocks_20 (REVERTED)
- **Timestamp**: 15:01:06
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5761704621709482, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.28012516243294Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 32: batch_size_16 (REVERTED)
- **Timestamp**: 15:16:23
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5788954182334367, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.409335929777853Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 33: dropout_0.1 (REVERTED)
- **Timestamp**: 15:31:39
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5777019461785641, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.138310701366072Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 34: weight_decay_0.0 (REVERTED)
- **Timestamp**: 15:46:55
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5779341937791989, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.080094135193052Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 35: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 16:02:14
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5826915838073256, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.262669299437563Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 36: num_blocks_16 (REVERTED)
- **Timestamp**: 16:17:35
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5771315700521122, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.021826208704029Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 37: weight_decay_0.0 (REVERTED)
- **Timestamp**: 16:32:52
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5757968175614662, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.102680905818578Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 38: weight_decay_0.0 (REVERTED)
- **Timestamp**: 16:48:11
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5768190070693442, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.186176489727927Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 39: lr_5e-05 (REVERTED)
- **Timestamp**: 17:03:28
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5798143317014738, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.348461715549244Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 40: dropout_0.2 (REVERTED)
- **Timestamp**: 17:18:44
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5795809291247839, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.319886100069549Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 41: use_ridges_True (REVERTED)
- **Timestamp**: 17:34:04
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5786006101574256, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.37053923190692Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 42: num_layers_32 (REVERTED)
- **Timestamp**: 17:49:20
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5782225056686575, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.305222927474394Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 43: use_ridges_False (REVERTED)
- **Timestamp**: 18:04:36
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5760001794307951, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.3661987342048665Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 44: num_heads_8 (REVERTED)
- **Timestamp**: 18:19:53
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5748488830395546, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.332994492536117Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 45: base_feat_64 (REVERTED)
- **Timestamp**: 18:35:09
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5737068736546287, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.366852896681076Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 46: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 18:50:30
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5782453902766662, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.305671168194343Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 47: dropout_0.1 (REVERTED)
- **Timestamp**: 19:05:46
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5765629105735363, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.147929659560951Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 19:05:48
Transitioning to NIGHT SHIFT...
