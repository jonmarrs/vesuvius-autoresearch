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

