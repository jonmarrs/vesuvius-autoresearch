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

