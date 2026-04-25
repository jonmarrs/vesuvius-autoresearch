# Day Shift Sprint - 2026-04-24
- **Start Time**: 14:09:26
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: num_layers_16 (SUCCESS)
- **Timestamp**: 14:25:00
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.08170187473297119, loss: 0.4201949464488675, params: 1.842809M, vram: 13279.28857421875MB, speed: 1.429098729106567Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 2: lr_0.0005 (REVERTED)
- **Timestamp**: 14:40:32
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.0005, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.0933737564086914, loss: 0.4116377908151143, params: 1.842809M, vram: 13279.28857421875MB, speed: 1.3427559677249692Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: loss_ink_bce_0.2 (SUCCESS)
- **Timestamp**: 14:56:20
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.2, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.06193594217300415, loss: 0.34580393183995545, params: 1.842809M, vram: 13279.28857421875MB, speed: 1.4606673203943876Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 4: loss_st_0.1 (CRASHED)
- **Timestamp**: 15:16:22
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 5: lr_1e-05 (SUCCESS)
- **Timestamp**: 15:36:24
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.013109087944030762, loss: 0.29119905951970915, params: 1.842809M, vram: 3390.24609375MB, speed: 0.34520810582320277Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 6: num_heads_4 (SUCCESS)
- **Timestamp**: 15:51:54
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0003663301467895508, loss: 0.42745302151770825, params: 1.842809M, vram: 2480.24609375MB, speed: 0.8989662598082985Mvps
- **Result**: Improvement detected. Config updated.

## Cycle 7: lr_0.001 (REVERTED)
- **Timestamp**: 16:07:21
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.017008066177368164, loss: 0.674298625196314, params: 1.842809M, vram: 2479.74609375MB, speed: 0.5874795467579431Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: lr_5e-05 (REVERTED)
- **Timestamp**: 16:22:49
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 5e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.038671255111694336, loss: 0.6811260945017198, params: 1.842809M, vram: 2479.74609375MB, speed: 0.5437728671426993Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: loss_ink_dice_0.2 (REVERTED)
- **Timestamp**: 16:38:26
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.2, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.007378280162811279, loss: 0.36269457777407704, params: 1.842809M, vram: 2479.74609375MB, speed: 0.465982387913085Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 16:53:54
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.00923985242843628, loss: 0.46559332710006074, params: 1.842809M, vram: 2479.74609375MB, speed: 0.8024148081210896Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: loss_st_0.0 (REVERTED)
- **Timestamp**: 17:09:18
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.0, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.008866965770721436, loss: 0.37628644513001713, params: 1.842809M, vram: 2479.74609375MB, speed: 1.0649692618221969Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: num_layers_32 (CRASHED)
- **Timestamp**: 17:09:30
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 32, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 13: num_heads_12 (REVERTED)
- **Timestamp**: 17:24:48
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.2
- **Stats**: val_bpb: 0.014489173889160156, loss: 0.43799805801367797, params: 1.842809M, vram: 3390.24609375MB, speed: 1.0653462262213877Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 17:40:19
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.005523502826690674, loss: 0.35290536276775664, params: 1.842809M, vram: 2480.24609375MB, speed: 0.48101713684852615Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 17:56:10
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.004783511161804199, loss: 0.5071970170718665, params: 1.842809M, vram: 2480.24609375MB, speed: 0.32523790959574983Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: loss_st_0.2 (REVERTED)
- **Timestamp**: 18:12:24
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.2, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0009775161743164062, loss: 0.5426516499615155, params: 1.842809M, vram: 2479.74609375MB, speed: 0.2977826320146046Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 17: batch_size_8 (REVERTED)
- **Timestamp**: 18:28:50
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 8, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.009570807814598084, loss: 0.525177862360136, params: 1.842809M, vram: 4915.01025390625MB, speed: 0.5143784078043034Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: use_ridges_True (CRASHED)
- **Timestamp**: 18:29:08
- **Config**: cache_dir: None, use_ridges: True, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 19: num_layers_24 (REVERTED)
- **Timestamp**: 18:44:51
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 24, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.06638896465301514, loss: 0.7135479897653116, params: 1.842809M, vram: 3714.21484375MB, speed: 0.49305257814326564Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 19:00:32
- **Config**: cache_dir: None, use_ridges: False, ridge_sigma: 2.0, batch_size: 4, patch_size: 64, num_layers: 16, lr: 1e-05, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.2, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, loss_st: 0.1, architecture: gated_unet, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 0.0030611157417297363, loss: 0.40690566033579756, params: 1.842809M, vram: 2479.74609375MB, speed: 0.38475743780416066Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 19:00:40
Transitioning to NIGHT SHIFT...
