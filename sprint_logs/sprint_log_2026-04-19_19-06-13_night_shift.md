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

