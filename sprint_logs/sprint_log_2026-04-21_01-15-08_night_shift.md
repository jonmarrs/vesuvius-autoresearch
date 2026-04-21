# Night Shift Sprint - 2026-04-21
- **Start Time**: 01:15:08
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 01:30:26
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.6, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5933009219835361, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.1457494667134585Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 01:45:42
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5926016175119099, params: 1.842707M, vram: 18103.80517578125MB, speed: 5.364549717436863Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 02:00:59
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.3, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.6555354397891635, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.408353546209334Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 02:16:16
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.1, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5325458717661826, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.360571794554972Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: use_ridges_True (CRASHED)
- **Timestamp**: 02:21:13
- **Config**: cache_dir: None, use_ridges: True, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 6: batch_size_24 (REVERTED)
- **Timestamp**: 02:37:07
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5938332183509966, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.314030970071962Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 02:52:24
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5917627926034318, params: 1.842707M, vram: 18103.80517578125MB, speed: 5.357229567025807Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: num_heads_4 (REVERTED)
- **Timestamp**: 03:07:40
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5941928168144123, params: 1.842707M, vram: 12484.3447265625MB, speed: 6.563916460927738Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 03:22:56
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5934113047490404, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.372105015236721Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: lr_0.0001 (REVERTED)
- **Timestamp**: 03:38:13
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.0001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5945593409264354, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.373935325294795Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: num_heads_12 (REVERTED)
- **Timestamp**: 03:53:33
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5963840426642658, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.360397183612467Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: loss_ink_dice_0.4 (REVERTED)
- **Timestamp**: 04:08:50
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5943695139030308, params: 1.842707M, vram: 18102.93017578125MB, speed: 5.416084587019021Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 04:24:07
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5954173771005955, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.343080110688422Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 04:39:24
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5941913076051101, params: 1.842707M, vram: 18102.93017578125MB, speed: 5.36219605728583Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: loss_fiber_bce_0.1 (REVERTED)
- **Timestamp**: 04:54:40
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5930124219474726, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.349266882828459Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 05:10:00
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5912712590666233, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.3980480630182095Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 17: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 05:25:18
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5925543959307916, params: 1.842707M, vram: 18104.43017578125MB, speed: 5.34349403852251Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: num_layers_16 (REVERTED)
- **Timestamp**: 05:40:33
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 16, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5885610481252153, params: 1.842707M, vram: 12010.93017578125MB, speed: 4.837114905094497Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 19: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 05:55:50
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5963873511754206, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.344159797514919Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: num_layers_32 (CRASHED)
- **Timestamp**: 05:56:00
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 32, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

## Cycle 21: loss_ink_bce_0.4 (REVERTED)
- **Timestamp**: 06:11:21
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.593166708630825, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.40124012392234Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 22: weight_decay_0.001 (REVERTED)
- **Timestamp**: 06:26:37
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.594245010481556, params: 1.842707M, vram: 18104.80517578125MB, speed: 5.334994762924931Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 23: loss_ink_bce_0.6 (REVERTED)
- **Timestamp**: 06:41:55
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5922541408227777, params: 1.842707M, vram: 18103.80517578125MB, speed: 5.3975717980421045Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 24: loss_fiber_bce_0.2 (REVERTED)
- **Timestamp**: 06:57:13
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5941542046737219, params: 1.842707M, vram: 18103.80517578125MB, speed: 5.105770106715556Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 25: loss_ink_bce_0.2 (REVERTED)
- **Timestamp**: 07:12:30
- **Config**: cache_dir: None, use_ridges: False, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 1.0, loss: 0.5925914024246947, params: 1.842707M, vram: 18102.43017578125MB, speed: 5.128661944178254Mvps
- **Result**: No improvement detected. Config reverted.


## Sprint Completed at 07:12:36
Transitioning to DAY SHIFT...
