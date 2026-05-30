# Day Shift Sprint - 2026-04-20
- **Start Time**: 14:05:33
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: num_heads_8 (REVERTED)
- **Timestamp**: 14:20:53
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.27499203085899354, loss: 0.5969049110335518, params: 1.842707M, vram: 18102.43017578125MB, speed: 3.5098689394237517Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: base_feat_32 (REVERTED)
- **Timestamp**: 14:36:12
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 32, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2837449786067009, loss: 0.5942072875989711, params: 0.836811M, vram: 14789.73193359375MB, speed: 5.7755992038896835Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: base_feat_128 (CRASHED (OOM))
- **Timestamp**: 14:36:21
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 128, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (OOM). Family weight preserved/incremented to retry other values.

## Cycle 4: weight_decay_0.1 (REVERTED)
- **Timestamp**: 14:51:36
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.1, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.29249282568693163, loss: 0.5932375581769068, params: 1.842707M, vram: 18102.43017578125MB, speed: 4.700137621242369Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: dropout_0.1 (REVERTED)
- **Timestamp**: 15:06:52
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.28811306625604627, loss: 0.5970942801813311, params: 1.842707M, vram: 18103.80517578125MB, speed: 4.747224647426208Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: num_blocks_20 (REVERTED)
- **Timestamp**: 15:22:10
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 20, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.29499061226844786, loss: 0.5969911892080809, params: 2.109715M, vram: 21578.64306640625MB, speed: 4.669453162455171Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: loss_fiber_bce_0.3 (REVERTED)
- **Timestamp**: 15:37:28
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.29249554365873337, loss: 0.3406059316458799, params: 1.842707M, vram: 18104.43017578125MB, speed: 4.701558824921725Mvps
- **Result**: No improvement detected. Config reverted.
