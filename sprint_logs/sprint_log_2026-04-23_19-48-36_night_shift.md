# Night Shift Sprint - 2026-04-23
- **Start Time**: 19:48:36
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: base_feat_128 (CRASHED (OOM))
- **Timestamp**: 19:48:48
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 128, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 2: weight_decay_0.1 (REVERTED)
- **Timestamp**: 20:04:05
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.1, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5762535506735841, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.207196830852372Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: patch_size_96 (REVERTED)
- **Timestamp**: 20:19:27
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 96, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5750332581588861, params: 1.842707M, vram: 22233.7958984375MB, speed: 6.3232894463323985Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: num_heads_12 (REVERTED)
- **Timestamp**: 20:34:43
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5779330111323787, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.347732258385168Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: batch_size_8 (REVERTED)
- **Timestamp**: 20:49:57
- **Config**: cache_dir: None, use_ridges: False, batch_size: 8, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.576028765602616, params: 1.842707M, vram: 9105.27490234375MB, speed: 3.6172465503302567Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: dropout_0.2 (REVERTED)
- **Timestamp**: 21:05:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5774828735646148, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.415097842609882Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 21:20:34
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.2, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5779246946842364, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.3608182130080415Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: num_layers_16 (REVERTED)
- **Timestamp**: 21:35:49
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5785913024578387, params: 1.842707M, vram: 12010.93017578125MB, speed: 3.7353474986705617Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: lr_0.0005 (REVERTED)
- **Timestamp**: 21:51:06
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0005, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5738523146146608, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.251143012550747Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: lr_0.0001 (REVERTED)
- **Timestamp**: 22:06:24
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5783488875705602, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.332589584605336Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: patch_size_96 (REVERTED)
- **Timestamp**: 22:21:47
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5766490825572351, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.067951104328479Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 22:37:04
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5810386875852132, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.112543048175079Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: batch_size_8 (REVERTED)
- **Timestamp**: 22:52:21
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5795983346831237, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.142868770768333Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: dropout_0.1 (REVERTED)
- **Timestamp**: 23:07:37
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 1.0, loss: 0.5794111828717167, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.344471266207348Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 23:22:54
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5787695161645283, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.308014297437299Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 23:38:14
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5805636083215011, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.353156982319305Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 17: dropout_0.1 (REVERTED)
- **Timestamp**: 23:53:31
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5803108407944014, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.279693989489692Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 00:08:47
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5792348204391929, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.361904332191008Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 19: base_feat_64 (REVERTED)
- **Timestamp**: 00:24:03
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5775835173622025, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.317881565383789Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: base_feat_64 (REVERTED)
- **Timestamp**: 00:39:19
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5786104664802129, params: 1.842707M, vram: 18103.80517578125MB, speed: 4.395935659443834Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 21: num_blocks_20 (REVERTED)
- **Timestamp**: 00:54:39
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5791230198663397, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.355800113081179Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 22: num_heads_4 (REVERTED)
- **Timestamp**: 01:09:55
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5785231933502881, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.4047785036311Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 23: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 01:25:11
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5725942828433108, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.3461111389010005Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 24: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 01:40:27
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5811935336259662, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.396665524753612Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 25: dropout_0.1 (REVERTED)
- **Timestamp**: 01:55:43
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5769351209244311, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.312905506413003Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 26: dropout_0.2 (REVERTED)
- **Timestamp**: 02:11:04
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5777654284821303, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.378831827772733Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 27: num_layers_16 (REVERTED)
- **Timestamp**: 02:26:20
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5786059880706627, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.370865739203705Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 28: dropout_0.0 (REVERTED)
- **Timestamp**: 02:41:36
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5758461555672248, params: 1.842707M, vram: 18107.43017578125MB, speed: 4.387667481056493Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 29: num_heads_4 (REVERTED)
- **Timestamp**: 02:56:53
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5801551211060503, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.351988319799205Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 30: patch_size_96 (REVERTED)
- **Timestamp**: 03:12:09
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5779659723896675, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.373030940815649Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 31: dropout_0.0 (REVERTED)
- **Timestamp**: 03:27:29
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5814663227828504, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.37887988359542Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 32: base_feat_128 (REVERTED)
- **Timestamp**: 03:42:46
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5772817658740181, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.377605138919298Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 33: patch_size_96 (REVERTED)
- **Timestamp**: 03:58:02
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5774846195812876, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.359449873247017Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 34: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 04:13:19
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5741546415966982, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.381520554627527Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 35: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 04:28:35
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5782488262827119, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.373385219576686Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 36: patch_size_64 (REVERTED)
- **Timestamp**: 04:43:55
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.577185212972822, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.364235743683961Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 37: base_feat_128 (REVERTED)
- **Timestamp**: 04:59:11
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5763891912568316, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.338543766434018Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 38: num_heads_4 (REVERTED)
- **Timestamp**: 05:14:27
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5793899538645695, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.38375600583123Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 39: num_blocks_16 (REVERTED)
- **Timestamp**: 05:29:43
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5812350899165711, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.3912766001341Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 40: base_feat_32 (REVERTED)
- **Timestamp**: 05:45:00
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5787107572862188, params: 1.842707M, vram: 18102.93017578125MB, speed: 4.370515592455314Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 41: num_blocks_8 (REVERTED)
- **Timestamp**: 06:00:20
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5772740675444199, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.381014604716696Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 42: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 06:15:36
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5756291320398147, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.3676507900082155Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 43: batch_size_24 (REVERTED)
- **Timestamp**: 06:30:53
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5762358107164007, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.399010825057068Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 44: num_layers_32 (REVERTED)
- **Timestamp**: 06:46:09
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.577727414130466, params: 1.842707M, vram: 18103.43017578125MB, speed: 4.360373621390421Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 45: use_ridges_False (REVERTED)
- **Timestamp**: 07:01:26
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.57851516719729, params: 1.842707M, vram: 18104.80517578125MB, speed: 4.272020896399305Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 07:01:32
Transitioning to DAY SHIFT...
