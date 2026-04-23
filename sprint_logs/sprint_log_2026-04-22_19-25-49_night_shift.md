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

## Cycle 15: batch_size_8 (REVERTED)
- **Timestamp**: 22:59:54
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5788788667683724, params: 1.842707M, vram: 18104.43017578125MB, speed: 4.3394302788491546Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: num_blocks_20 (REVERTED)
- **Timestamp**: 23:15:19
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 20, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5757617405387812, params: 2.109715M, vram: 21580.01806640625MB, speed: 3.6477407840385796Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 17: num_blocks_20 (REVERTED)
- **Timestamp**: 23:30:39
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5801903027716065, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.384467053069956Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 23:46:01
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.57450507096119, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.684246931274498Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 19: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 00:01:31
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5781959857261264, params: 1.842707M, vram: 18104.80517578125MB, speed: 2.0424315811953275Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: batch_size_24 (REVERTED)
- **Timestamp**: 00:17:02
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5759999168950329, params: 1.842707M, vram: 18104.43017578125MB, speed: 2.72452861303552Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 21: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 00:32:35
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5759959477136797, params: 1.842707M, vram: 18104.43017578125MB, speed: 2.7857133479833944Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 22: batch_size_24 (REVERTED)
- **Timestamp**: 00:48:02
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5755309997954204, params: 1.842707M, vram: 18102.43017578125MB, speed: 2.8239938199021246Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 23: batch_size_16 (REVERTED)
- **Timestamp**: 01:03:31
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5780104623075448, params: 1.842707M, vram: 18103.43017578125MB, speed: 2.7228488434265614Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 24: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 01:18:58
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5795254908904213, params: 1.842707M, vram: 18102.43017578125MB, speed: 2.8262983133320105Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 25: num_heads_8 (REVERTED)
- **Timestamp**: 01:34:25
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5775354633276778, params: 1.842707M, vram: 18104.80517578125MB, speed: 2.647975939707421Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 26: weight_decay_0.0 (REVERTED)
- **Timestamp**: 01:49:59
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5791364120532829, params: 1.842707M, vram: 18103.43017578125MB, speed: 2.932847228238318Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 27: num_layers_16 (REVERTED)
- **Timestamp**: 02:05:20
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.575907032924197, params: 1.842707M, vram: 18104.80517578125MB, speed: 3.9655212713104326Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 28: batch_size_16 (REVERTED)
- **Timestamp**: 02:20:36
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5787540561807082, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.452486865302571Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 29: num_heads_12 (REVERTED)
- **Timestamp**: 02:35:51
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5806111881461334, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.403045156644915Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 30: batch_size_24 (REVERTED)
- **Timestamp**: 02:51:07
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5764667209241767, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.449154062652195Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 31: use_ridges_False (REVERTED)
- **Timestamp**: 03:06:27
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.578367719559601, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.40281945509078Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 32: lr_0.001 (REVERTED)
- **Timestamp**: 03:21:43
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5811811889526156, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.445247852385699Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 33: loss_ink_bce_0.4 (REVERTED)
- **Timestamp**: 03:36:59
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5779675357270062, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.39910188324937Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 34: num_blocks_10 (REVERTED)
- **Timestamp**: 03:52:15
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5756097209461962, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.45752295035073Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 35: num_heads_12 (REVERTED)
- **Timestamp**: 04:07:31
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.578565485528909, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.399008257532574Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 36: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 04:22:50
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5769107893208993, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.45891072756676Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 37: base_feat_32 (REVERTED)
- **Timestamp**: 04:38:06
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5792651672872632, params: 1.842707M, vram: 18104.43017578125MB, speed: 4.396064433514089Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 38: batch_size_24 (REVERTED)
- **Timestamp**: 04:53:22
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5760537502679927, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.449595785815572Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 39: num_layers_16 (REVERTED)
- **Timestamp**: 05:08:38
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5773370545052401, params: 1.842707M, vram: 18103.80517578125MB, speed: 4.406432708502504Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 40: num_heads_12 (REVERTED)
- **Timestamp**: 05:23:54
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5790071967594969, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.438448281076389Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 41: use_ridges_False (REVERTED)
- **Timestamp**: 05:39:14
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.577479191168536, params: 1.842707M, vram: 18103.80517578125MB, speed: 4.359108377466095Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 42: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 05:54:30
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5778347318998929, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.428398047625392Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 43: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 06:09:46
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5774580572428115, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.361943030196556Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 44: num_layers_16 (REVERTED)
- **Timestamp**: 06:25:02
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5781380185237437, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.434235301266081Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 45: base_feat_128 (REVERTED)
- **Timestamp**: 06:40:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5798487646307655, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.341997602948943Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 46: num_layers_16 (REVERTED)
- **Timestamp**: 06:55:37
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5782092496022786, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.420157134099174Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 47: batch_size_16 (REVERTED)
- **Timestamp**: 07:10:53
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5783901865762754, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.373986186448442Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 07:10:55
Transitioning to DAY SHIFT...
