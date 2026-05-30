# Night Shift Sprint - 2026-04-15
- **Start Time**: 23:45:51
- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).

## Cycle 1: num_blocks_16 (REVERTED)
- **Timestamp**: 00:01:12
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.3507561988195421, params: 1.412051M, vram: 7894.75732421875MB, speed: 7.225306527760149Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 2: dropout_0.0 (REVERTED)
- **Timestamp**: 00:16:26
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.4601357130081246, params: 1.412051M, vram: 7894.63232421875MB, speed: 9.873940148775969Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 3: dropout_0.2 (REVERTED)
- **Timestamp**: 00:31:41
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.22819541765627468, params: 1.412051M, vram: 8810.25732421875MB, speed: 8.953150224841222Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 4: num_blocks_12 (REVERTED)
- **Timestamp**: 00:46:55
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 12, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.32794942582915676, params: 1.145043M, vram: 6383.65771484375MB, speed: 11.312257778010123Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 5: patch_size_64 (REVERTED)
- **Timestamp**: 01:02:10
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.2199285598244556, params: 1.412051M, vram: 7894.75732421875MB, speed: 9.745577066315002Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 6: num_layers_24 (REVERTED)
- **Timestamp**: 01:17:26
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.4501203647099784, params: 1.412051M, vram: 7894.75732421875MB, speed: 9.86199308692072Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 7: patch_size_96 (REVERTED)
- **Timestamp**: 01:17:34
- **Config**: batch_size: 16, patch_size: 96, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Config reverted.

## Cycle 8: num_blocks_20 (REVERTED)
- **Timestamp**: 01:32:50
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 20, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.3190014486991407, params: 1.679059M, vram: 9405.73193359375MB, speed: 8.642935910767944Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 9: num_heads_12 (REVERTED)
- **Timestamp**: 01:48:06
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.3852252319395657, params: 1.412051M, vram: 7894.75732421875MB, speed: 9.834544539525846Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 10: base_feat_128 (REVERTED)
- **Timestamp**: 02:03:24
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 128, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.4784107624051604, params: 5.399459M, vram: 11019.98974609375MB, speed: 6.228522641606736Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 11: num_blocks_12 (REVERTED)
- **Timestamp**: 02:18:39
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 12, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.2638151251937301, params: 1.145043M, vram: 6383.65771484375MB, speed: 11.253506392534026Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 12: dropout_0.1 (REVERTED)
- **Timestamp**: 02:33:54
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.39978862813516153, params: 1.412051M, vram: 8810.75732421875MB, speed: 8.951772992374362Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 13: dropout_0.1 (REVERTED)
- **Timestamp**: 02:49:10
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.37089802354379864, params: 1.412051M, vram: 8810.25732421875MB, speed: 8.967691644762219Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 14: dropout_0.1 (REVERTED)
- **Timestamp**: 03:04:26
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.3326509971842056, params: 1.412051M, vram: 8812.25732421875MB, speed: 8.934335588630795Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 15: num_blocks_10 (REVERTED)
- **Timestamp**: 03:19:41
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 10, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.43260693699100533, params: 1.011539M, vram: 5627.48291015625MB, speed: 12.15138690709287Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 16: base_feat_128 (REVERTED)
- **Timestamp**: 03:34:59
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 128, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.41611427309047166, params: 5.399459M, vram: 11021.36474609375MB, speed: 6.265802221565653Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 17: dropout_0.2 (REVERTED)
- **Timestamp**: 03:50:13
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.2
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.406003326548533, params: 1.412051M, vram: 8812.25732421875MB, speed: 9.040671332355538Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 18: patch_size_64 (REVERTED)
- **Timestamp**: 04:05:29
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.24531518721998166, params: 1.412051M, vram: 7894.63232421875MB, speed: 9.82124340264475Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 19: dropout_0.0 (REVERTED)
- **Timestamp**: 04:20:44
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.3771890895474258, params: 1.412051M, vram: 7894.75732421875MB, speed: 9.776132166674094Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 20: weight_decay_0.1 (REVERTED)
- **Timestamp**: 04:35:58
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.1, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.22428285415662647, params: 1.412051M, vram: 7894.75732421875MB, speed: 9.89760528995243Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 21: lr_0.001 (REVERTED)
- **Timestamp**: 04:51:13
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.3356825471724058, params: 1.412051M, vram: 7894.75732421875MB, speed: 10.035304623763139Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 22: base_feat_128 (REVERTED)
- **Timestamp**: 05:06:30
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 128, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.6950476471430879, params: 5.399459M, vram: 11019.98974609375MB, speed: 6.328757140098925Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 23: num_heads_12 (REVERTED)
- **Timestamp**: 05:21:44
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 12, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.5304646843841522, params: 1.412051M, vram: 7894.75732421875MB, speed: 10.015356780324199Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 24: num_heads_4 (REVERTED)
- **Timestamp**: 05:36:58
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 4, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.3065348779290492, params: 1.412051M, vram: 5546.75732421875MB, speed: 11.389761612610025Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 25: base_feat_128 (REVERTED)
- **Timestamp**: 05:52:16
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 128, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.228906667272022, params: 5.399459M, vram: 11019.98974609375MB, speed: 6.3338964629727Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 26: dropout_0.1 (REVERTED)
- **Timestamp**: 06:07:30
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.1
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.32278155582349505, params: 1.412051M, vram: 8810.75732421875MB, speed: 9.063901520856515Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 27: base_feat_32 (REVERTED)
- **Timestamp**: 06:22:43
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 32, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.2572848729888882, params: 0.384171M, vram: 6352.337890625MB, speed: 13.059052493335763Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 28: lr_5e-05 (REVERTED)
- **Timestamp**: 06:37:57
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 5e-05, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.9996821594238281, loss: 0.4061575748205797, params: 1.412051M, vram: 7894.75732421875MB, speed: 9.97490877201474Mvps
- **Result**: No improvement detected. Config reverted.

## Cycle 29: num_layers_32 (REVERTED)
- **Timestamp**: 06:38:04
- **Config**: batch_size: 16, patch_size: 64, num_layers: 32, lr: 0.001, weight_decay: 0.01, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: N/A, loss: N/A, params: N/AM, vram: N/AMB, speed: N/AMvps
- **Result**: No improvement detected. Config reverted.

## Cycle 30: weight_decay_0.001 (REVERTED)
- **Timestamp**: 06:53:28
- **Config**: batch_size: 16, patch_size: 64, num_layers: 24, lr: 0.001, weight_decay: 0.001, time_budget: 900, base_feat: 64, num_blocks: 16, num_heads: 8, dropout: 0.0
- **Stats**: val_bpb: 0.2806170701980591, loss: 0.4834808602470121, params: 1.412051M, vram: 7894.63232421875MB, speed: 7.614107535184106Mvps
- **Result**: No improvement detected. Config reverted.
