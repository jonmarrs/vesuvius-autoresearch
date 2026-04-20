# Day Shift Sprint - 2026-04-20
- **Start Time**: 12:53:23
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: weight_decay_0.0 (REVERTED)
- **Timestamp**: 13:09:07
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.0, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2862460985779762, loss: 0.5940816000889048, params: 1.415443M, vram: 9219.251953125MB, speed: 4.572684500778839Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: num_layers_32 (CRASHED)
- **Timestamp**: 13:09:22
- **Config**: cache_dir: None, batch_size: 16, patch_size: 64, num_layers: 32, lr: 0.001, weight_decay: 0.01, time_budget: 900, loss_ink_bce: 0.4, loss_ink_dice: 0.4, loss_fiber_bce: 0.2, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: Training crashed (Unknown error). Family weight preserved/incremented to retry other values.

