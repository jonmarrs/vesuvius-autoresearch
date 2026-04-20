# Night Shift Sprint - 2026-04-19
- **Start Time**: 19:06:13
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: batch_size_8 (CRASHED)
- **Timestamp**: 19:13:25
- **Config**: cache_dir: None, batch_size: 8, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 2: batch_size_24 (REVERTED)
- **Timestamp**: 19:28:56
- **Config**: cache_dir: None, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.28415934145450594, loss: 0.6024812467479325, params: 1.416419M, vram: 12003.20849609375MB, speed: 8.815202816164266Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: dropout_0.2 (SUCCESS)
- **Timestamp**: 19:44:16
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.27499299734830857, loss: 0.6023029160001573, params: 1.416419M, vram: 8930.60888671875MB, speed: 8.643085519593676Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 4: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 19:59:31
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.28374526351690293, loss: 0.5318003352215144, params: 1.416419M, vram: 8930.626953125MB, speed: 8.85923484503661Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: batch_size_24 (REVERTED)
- **Timestamp**: 20:14:49
- **Config**: cache_dir: None, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2841568303108215, loss: 0.592948699111767, params: 1.416419M, vram: 13355.8515625MB, speed: 9.20072680412885Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: dropout_0.1 (REVERTED)
- **Timestamp**: 20:30:05
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.2774975249171257, loss: 0.594092836728883, params: 1.416419M, vram: 8929.126953125MB, speed: 8.859697025979052Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: num_heads_12 (REVERTED)
- **Timestamp**: 20:45:21
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.2
- **Stats**: val_bpb: 0.3074946901202202, loss: 0.5939294201779822, params: 1.416419M, vram: 8928.626953125MB, speed: 8.805322421352301Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: batch_size_16 (SUCCESS)
- **Timestamp**: 21:00:39
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2693719446659088, loss: 0.5962404688699517, params: 1.416419M, vram: 8930.626953125MB, speed: 8.845573344482778Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 9: loss_ink_bce_0.4 (REVERTED)
- **Timestamp**: 21:15:54
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.28874216943979264, loss: 0.35332452358279004, params: 1.416419M, vram: 8928.626953125MB, speed: 8.799446312506266Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: lr_1e-05 (REVERTED)
- **Timestamp**: 21:31:10
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.28187080830335615, loss: 0.5974459068478275, params: 1.416419M, vram: 8930.626953125MB, speed: 8.847064126670043Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: batch_size_16 (REVERTED)
- **Timestamp**: 21:46:26
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.30061611443758013, loss: 0.33227961866256533, params: 1.416419M, vram: 8930.626953125MB, speed: 8.78226560769616Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: num_blocks_20 (REVERTED)
- **Timestamp**: 22:02:03
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 20, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.27686442792415616, loss: 0.6002778023160302, params: 1.683427M, vram: 10668.9765625MB, speed: 6.318120475588904Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 22:18:48
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.2, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2824960547685623, loss: 0.32216058449165363, params: 1.416419M, vram: 8928.626953125MB, speed: 4.110106963392578Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: batch_size_8 (REVERTED)
- **Timestamp**: 22:34:13
- **Config**: cache_dir: None, batch_size: 8, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.29749520689249037, loss: 0.29831744979367686, params: 1.416419M, vram: 4526.603515625MB, speed: 4.740433107613721Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: num_layers_24 (SUCCESS)
- **Timestamp**: 22:49:33
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2662423020601273, loss: 0.3327777936679038, params: 1.416419M, vram: 8928.626953125MB, speed: 8.122308676715514Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 16: num_layers_32 (CRASHED)
- **Timestamp**: 22:49:42
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 32, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 17: num_heads_4 (REVERTED)
- **Timestamp**: 23:04:57
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.2862409168481827, loss: 0.5939009335736554, params: 1.416419M, vram: 6174.626953125MB, speed: 9.601199798699996Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: num_heads_12 (REVERTED)
- **Timestamp**: 23:20:13
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.2
- **Stats**: val_bpb: 0.3012449809908867, loss: 0.5920452166803393, params: 1.416419M, vram: 8930.626953125MB, speed: 8.730094125708343Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 19: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 23:35:28
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2956198820471764, loss: 0.35912263582601267, params: 1.416419M, vram: 8928.626953125MB, speed: 8.566826631557959Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: num_blocks_20 (REVERTED)
- **Timestamp**: 23:50:45
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 20, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.28249573916196824, loss: 0.596251565423289, params: 1.683427M, vram: 10664.3515625MB, speed: 7.6325702002456675Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 21: patch_size_64 (REVERTED)
- **Timestamp**: 00:06:03
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.29374654054641725, loss: 0.3464791569411797, params: 1.416419M, vram: 8930.626953125MB, speed: 8.481842724966342Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 22: num_layers_16 (REVERTED)
- **Timestamp**: 00:21:22
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.28562242329120635, loss: 0.5926537600353132, params: 1.416419M, vram: 5926.314453125MB, speed: 5.163966828249913Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 23: batch_size_8 (REVERTED)
- **Timestamp**: 00:36:41
- **Config**: cache_dir: None, batch_size: 8, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.26999631375074384, loss: 0.3624765586792489, params: 1.416419M, vram: 4526.603515625MB, speed: 4.012866616001562Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 24: base_feat_128 (REVERTED)
- **Timestamp**: 00:52:03
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 128, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.3149948963522911, loss: 0.5885469909800627, params: 5.089731M, vram: 12296.373046875MB, speed: 5.615497224767429Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 25: num_layers_32 (CRASHED)
- **Timestamp**: 00:52:11
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 32, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 26: base_feat_64 (REVERTED)
- **Timestamp**: 01:07:28
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.3012415152788162, loss: 0.3286449799134982, params: 1.416419M, vram: 8929.126953125MB, speed: 7.940695327832743Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 27: lr_0.0001 (REVERTED)
- **Timestamp**: 01:22:48
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2812434929609299, loss: 0.3586100901116057, params: 1.416419M, vram: 8930.626953125MB, speed: 8.084439022209756Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 28: num_heads_8 (REVERTED)
- **Timestamp**: 01:38:06
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.30061604619026183, loss: 0.33238217801844316, params: 1.416419M, vram: 8929.126953125MB, speed: 7.8412963079591504Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 29: loss_ink_dice_0.6 (REVERTED)
- **Timestamp**: 01:53:22
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.6, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2799953007698059, loss: 0.40449746473734327, params: 1.416419M, vram: 8930.626953125MB, speed: 7.982524369433988Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 30: dropout_0.1 (REVERTED)
- **Timestamp**: 02:08:38
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.2837449786067009, loss: 0.3482930658643331, params: 1.416419M, vram: 8930.626953125MB, speed: 8.382162005211377Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 31: batch_size_24 (REVERTED)
- **Timestamp**: 02:23:58
- **Config**: cache_dir: None, batch_size: 24, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2895794922113419, loss: 0.3338434279103984, params: 1.416419M, vram: 13356.8515625MB, speed: 9.27153222470945Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 32: weight_decay_0.01 (REVERTED)
- **Timestamp**: 02:39:13
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2799929982423782, loss: 0.37732791417323147, params: 1.416419M, vram: 8930.626953125MB, speed: 8.757351754008512Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 33: patch_size_96 (REVERTED)
- **Timestamp**: 02:54:34
- **Config**: cache_dir: None, batch_size: 16, patch_size: 96, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.34811493039131164, loss: 0.5930625912906303, params: 1.416419M, vram: 10947.173828125MB, speed: 13.683996852964729Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 34: batch_size_16 (REVERTED)
- **Timestamp**: 03:09:49
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2756188917160034, loss: 0.3287867828169779, params: 1.416419M, vram: 8930.626953125MB, speed: 8.747653720924404Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 35: num_layers_16 (REVERTED)
- **Timestamp**: 03:25:03
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.29186755657196045, loss: 0.595910466433372, params: 1.416419M, vram: 5926.314453125MB, speed: 7.741599994005417Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 36: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 03:40:20
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.26999172270298005, loss: 0.31625800783611185, params: 1.416419M, vram: 8930.626953125MB, speed: 8.73210440808125Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 37: base_feat_32 (REVERTED)
- **Timestamp**: 03:55:34
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 32, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2868680822849274, loss: 0.6023567280873877, params: 0.426163M, vram: 7256.291015625MB, speed: 10.994870850294818Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 38: weight_decay_0.01 (REVERTED)
- **Timestamp**: 04:10:48
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.266247478723526, loss: 0.3418497983918084, params: 1.416419M, vram: 8928.626953125MB, speed: 8.717697884215372Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 39: lr_5e-05 (REVERTED)
- **Timestamp**: 04:26:04
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 5e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.31374121487140655, loss: 0.34500680328609296, params: 1.416419M, vram: 8930.626953125MB, speed: 8.811114381964655Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 40: patch_size_64 (REVERTED)
- **Timestamp**: 04:41:19
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2849953407049179, loss: 0.31154077629309823, params: 1.416419M, vram: 8930.626953125MB, speed: 8.732519120307328Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 41: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 04:56:34
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.28999519884586333, loss: 0.341219034302544, params: 1.416419M, vram: 8930.626953125MB, speed: 8.810914490223896Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 42: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 05:11:49
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2893624582886696, loss: 0.3440060001895577, params: 1.416419M, vram: 8930.626953125MB, speed: 8.75468548939275Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 43: lr_0.001 (REVERTED)
- **Timestamp**: 05:27:04
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.3062431126832962, loss: 0.34735832443688924, params: 1.416419M, vram: 8928.626953125MB, speed: 8.82498056095942Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 44: lr_5e-05 (REVERTED)
- **Timestamp**: 05:42:20
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 5e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.3024929666519165, loss: 0.3241641651357008, params: 1.416419M, vram: 8930.626953125MB, speed: 8.702405921052266Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 45: patch_size_64 (REVERTED)
- **Timestamp**: 05:57:35
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.29874257892370226, loss: 0.33023883237896867, params: 1.416419M, vram: 8929.126953125MB, speed: 8.781287586100724Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 46: batch_size_16 (REVERTED)
- **Timestamp**: 06:12:51
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.28499504625797273, loss: 0.30998990606494603, params: 1.416419M, vram: 8930.626953125MB, speed: 8.771207053202376Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 47: dropout_0.0 (REVERTED)
- **Timestamp**: 06:28:07
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.28812006682157515, loss: 0.3463469319662133, params: 1.416419M, vram: 8014.001953125MB, speed: 9.608868153198435Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 48: weight_decay_0.1 (REVERTED)
- **Timestamp**: 06:43:21
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.1, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2881188064813614, loss: 0.3295890309190435, params: 1.416419M, vram: 8930.626953125MB, speed: 8.690658042717043Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 49: lr_1e-05 (REVERTED)
- **Timestamp**: 06:58:37
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.28811881721019744, loss: 0.33361449267103815, params: 1.416419M, vram: 8929.126953125MB, speed: 8.805334094816299Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 50: dropout_0.0 (REVERTED)
- **Timestamp**: 07:13:52
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2868696391582489, loss: 0.3389623472457845, params: 1.416419M, vram: 8011.501953125MB, speed: 9.516181396781713Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 07:13:54
Transitioning to DAY SHIFT...
