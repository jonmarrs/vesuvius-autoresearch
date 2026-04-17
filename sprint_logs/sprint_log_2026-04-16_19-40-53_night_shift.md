# Night Shift Sprint - 2026-04-16
- **Start Time**: 19:40:53
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: num_blocks_20 (REVERTED)
- **Timestamp**: 19:56:08
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 20, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9996350985765458, loss: 0.5285441878579088, params: 1.684963M, vram: 9402.80419921875MB, speed: 9.112262652653127Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 20:11:24
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9996623712778091, loss: 0.4649119382069632, params: 1.417955M, vram: 7891.32958984375MB, speed: 10.33029485441186Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: lr_0.0005 (REVERTED)
- **Timestamp**: 20:26:39
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0005, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9996574491262435, loss: 0.5357193214244033, params: 1.417955M, vram: 7892.95458984375MB, speed: 10.09235902693186Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: num_blocks_10 (REVERTED)
- **Timestamp**: 20:41:53
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 10, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9996611052751541, loss: 0.5303556463464363, params: 1.017443M, vram: 5626.18017578125MB, speed: 12.817590700474128Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: batch_size_24 (REVERTED)
- **Timestamp**: 20:57:12
- **Config**: cache_dir: None, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9996193236112595, loss: 0.5295419595206259, params: 1.417955M, vram: 11823.17919921875MB, speed: 10.964021852222551Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: dropout_0.2 (REVERTED)
- **Timestamp**: 21:12:27
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.9996796470880508, loss: 0.5284759625065705, params: 1.417955M, vram: 8807.57958984375MB, speed: 9.436270043521889Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: num_layers_16 (REVERTED)
- **Timestamp**: 21:27:42
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9996028423309327, loss: 0.5291550958948632, params: 1.383139M, vram: 5243.75537109375MB, speed: 8.942995806914123Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: batch_size_8 (REVERTED)
- **Timestamp**: 21:42:55
- **Config**: cache_dir: None, batch_size: 8, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9995458889007568, loss: 0.5228660282109971, params: 1.417955M, vram: 4029.31396484375MB, speed: 7.805587144360708Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: batch_size_24 (REVERTED)
- **Timestamp**: 21:58:14
- **Config**: cache_dir: None, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9996618241071701, loss: 0.5349726135587256, params: 1.417955M, vram: 11823.17919921875MB, speed: 10.964458236259778Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 22:13:32
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9996628093719483, loss: 0.5280013860893, params: 1.417955M, vram: 7891.32958984375MB, speed: 9.399248849393478Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 22:28:50
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.46935795562889515, params: 1.417955M, vram: 7891.32958984375MB, speed: 7.149388952574314Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: lr_0.0005 (REVERTED)
- **Timestamp**: 22:44:08
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0005, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.596390212205999, params: 1.417955M, vram: 7891.615234375MB, speed: 5.870118925882447Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 22:59:29
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.654130102530955, params: 1.417955M, vram: 7891.365234375MB, speed: 9.461741238962954Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 23:14:45
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5981730210594745, params: 1.417955M, vram: 7892.990234375MB, speed: 9.761667494488554Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 23:30:06
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5939727588536058, params: 1.417955M, vram: 7891.365234375MB, speed: 9.49693197122853Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: batch_size_24 (REVERTED)
- **Timestamp**: 23:45:27
- **Config**: cache_dir: None, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.28540835201740267, loss: 0.6016393719686928, params: 1.417955M, vram: 11823.21484375MB, speed: 10.560765184471869Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 17: batch_size_8 (REVERTED)
- **Timestamp**: 00:00:42
- **Config**: cache_dir: None, batch_size: 8, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.28124133944511415, loss: 0.5935597093672156, params: 1.417955M, vram: 4029.349609375MB, speed: 6.87133874409142Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 00:15:58
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.6, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.7947335191866575, params: 1.417955M, vram: 7891.615234375MB, speed: 9.57915634216052Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 19: base_feat_32 (REVERTED)
- **Timestamp**: 00:31:17
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 32, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5961808740549017, params: 0.385587M, vram: 6351.51025390625MB, speed: 11.119948717236932Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: num_layers_24 (REVERTED)
- **Timestamp**: 00:46:33
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5970053885960948, params: 1.417955M, vram: 7892.615234375MB, speed: 9.695532891677358Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 21: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 01:01:49
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5996178232943278, params: 1.417955M, vram: 7892.615234375MB, speed: 8.990489687730962Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 22: dropout_0.1 (REVERTED)
- **Timestamp**: 01:17:06
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.6035552673242678, params: 1.417955M, vram: 8807.615234375MB, speed: 8.904623446461011Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 23: dropout_0.1 (REVERTED)
- **Timestamp**: 01:32:25
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5960686204424159, params: 1.417955M, vram: 8802.615234375MB, speed: 8.472344147031103Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 24: lr_0.0001 (REVERTED)
- **Timestamp**: 01:47:41
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.6004283583804942, params: 1.417955M, vram: 7891.365234375MB, speed: 9.66040272266419Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 25: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 02:02:57
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5950994261565695, params: 1.417955M, vram: 7892.615234375MB, speed: 9.29805889282497Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 26: patch_size_96 (REVERTED)
- **Timestamp**: 02:03:09
- **Config**: cache_dir: None, batch_size: 16, patch_size: 96, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Config reverted.

## Cycle 27: dropout_0.0 (REVERTED)
- **Timestamp**: 02:18:25
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5923470410991697, params: 1.417955M, vram: 7891.365234375MB, speed: 9.582244331932385Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 28: num_heads_4 (REVERTED)
- **Timestamp**: 02:33:42
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5961213799052978, params: 1.417955M, vram: 5543.615234375MB, speed: 10.701101530237105Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 29: lr_0.001 (REVERTED)
- **Timestamp**: 02:48:58
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.592053212182368, params: 1.417955M, vram: 7891.615234375MB, speed: 9.724061446691785Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 30: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 03:04:15
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.6, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.7965888193625109, params: 1.417955M, vram: 7891.365234375MB, speed: 9.578982157578205Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 31: base_feat_64 (REVERTED)
- **Timestamp**: 03:19:31
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5949148366025828, params: 1.417955M, vram: 7892.615234375MB, speed: 9.745630321880435Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 32: num_blocks_12 (REVERTED)
- **Timestamp**: 03:34:45
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 12, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5942178086332582, params: 1.150947M, vram: 6378.890625MB, speed: 11.168965477937952Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 33: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 03:50:01
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.2, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5968694714394085, params: 1.417955M, vram: 7891.365234375MB, speed: 9.939693107647173Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 34: num_layers_24 (REVERTED)
- **Timestamp**: 04:05:17
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.594501387634922, params: 1.417955M, vram: 7891.365234375MB, speed: 9.675177868397464Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 35: weight_decay_0.01 (REVERTED)
- **Timestamp**: 04:20:34
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.6000052078245722, params: 1.417955M, vram: 7892.615234375MB, speed: 9.973034666399407Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 36: batch_size_24 (REVERTED)
- **Timestamp**: 04:35:52
- **Config**: cache_dir: None, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.28540835201740267, loss: 0.5959001462221598, params: 1.417955M, vram: 11823.21484375MB, speed: 10.45637273753095Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 37: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 04:51:07
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5957626352692205, params: 1.417955M, vram: 7891.365234375MB, speed: 9.886286395142056Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 38: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 05:06:22
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.2, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.3947196545453803, params: 1.417955M, vram: 7891.365234375MB, speed: 9.781074850031334Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 39: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 05:21:37
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5287045747482658, params: 1.417955M, vram: 7892.615234375MB, speed: 9.891738083843597Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 40: num_blocks_16 (REVERTED)
- **Timestamp**: 05:36:52
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5949598378763468, params: 1.417955M, vram: 7891.365234375MB, speed: 9.702217377761112Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 41: num_layers_32 (REVERTED)
- **Timestamp**: 05:37:00
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 32, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Config reverted.

## Cycle 42: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 05:52:15
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.2, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.3934225810208711, params: 1.417955M, vram: 7891.365234375MB, speed: 9.900856233804456Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 43: dropout_0.0 (REVERTED)
- **Timestamp**: 06:07:30
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5979053183045913, params: 1.417955M, vram: 7891.365234375MB, speed: 9.649219555693628Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 44: num_heads_12 (REVERTED)
- **Timestamp**: 06:22:46
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.593675670946723, params: 1.417955M, vram: 7891.365234375MB, speed: 9.931244500367768Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 45: dropout_0.1 (REVERTED)
- **Timestamp**: 06:38:02
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5936281531068917, params: 1.417955M, vram: 8807.615234375MB, speed: 8.887505071768263Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 46: num_blocks_10 (REVERTED)
- **Timestamp**: 06:53:17
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 10, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5934661414451703, params: 1.017443M, vram: 5626.2158203125MB, speed: 12.30945669617133Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 47: dropout_0.0 (REVERTED)
- **Timestamp**: 07:08:32
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170699000359, loss: 0.5951439400255534, params: 1.417955M, vram: 7892.615234375MB, speed: 9.759173548694562Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 07:08:34
