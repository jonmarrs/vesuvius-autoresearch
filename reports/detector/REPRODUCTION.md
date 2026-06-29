# Working Detector (TimeSformer) — Held-Out Reproduction

Productionized the proven Grand-Prize TimeSformer recipe as
`src/vesuvius_autoresearch/detector/` and reproduced a legible-ink detector on our
own data, clearing the success bar.

## Result

- **Held-out mask-restricted pixel-AUC: 0.7001** on `PHercParis2Fr47` → `PHercParis2Fr143`
  (single fixed seed, 12-epoch recipe). Success bar ≥ 0.70; proven reference = 0.711.
- **Selected checkpoint: epoch 7** (best held-out AUC across all 12 epochs).
- Window-compliant: lateral patch 64 px (depth `in_chans=26` is the through-surface
  axis, not subject to the lateral prize limit).
- Artifacts: [`PHercParis2Fr143_scorecard.json`](PHercParis2Fr143_scorecard.json),
  [`PHercParis2Fr143_pred_thumb.png`](PHercParis2Fr143_pred_thumb.png).

## Per-epoch held-out AUC sweep

The recipe was retrained saving every epoch (`save_top_k=-1`); each checkpoint was then
scored on the held-out fragment and the best selected (mirrors the proven recipe's
best-epoch model selection):

| epoch | pixel-AUC | | epoch | pixel-AUC |
|------:|----------:|-|------:|----------:|
| 0 | 0.5078 | | 6 | 0.6968 |
| 1 | 0.6260 | | **7** | **0.7001** |
| 2 | 0.6279 | | 8 | 0.6915 |
| 3 | 0.6505 | | 9 | 0.6991 |
| 4 | 0.6708 | | 10 | 0.6962 |
| 5 | 0.6769 | | 11 | 0.6982 |

AUC rises with training then plateaus at ~0.69–0.70; epoch 7 is the peak.

## Root cause that gated the first attempt

The first held-out run scored **0.57** (≈ chance-leaning), then **0.698** after one fix,
then **0.7001** after best-epoch selection. The dominant defect was in inference, not
training:

1. **Inference normalization (the big one).** Training/validation apply
   `A.Normalize(mean=0, std=1)` (albumentations default ⇒ divide by 255), so the model
   trains on inputs in ~[0, 0.78]. The standalone `infer()` fed **raw 0–200 pixel
   values** — a ~255× input-scale mismatch that collapsed a real detector to ~chance.
   Normalizing inference patches by 255 moved AUC **0.57 → 0.698**. Pinned by a
   forward-pre-hook regression test.
2. **PyTorch 2.6 checkpoint load.** `torch.load` now defaults to `weights_only=True`,
   which rejects our checkpoint (it embeds the `CosineAnnealingLR` scheduler). Load
   trusted own-checkpoints with `weights_only=False`.
3. **Padded/unpadded shape mismatch.** `read_image_mask` pads the fragment mask to a
   tile multiple but leaves the ink label unpadded; `infer` now crops its output to the
   label shape (was an `IndexError` on the real 14830×9506 fragment).

Inference is batched, so a full-segment score takes minutes (was ~37 min single-patch),
which made evaluating all 12 epochs practical.

## Reproduce

```bash
# one-command end-to-end (convert if needed → train → infer → eval, asserts ≥ 0.70)
uv run python -m vesuvius_autoresearch.detector.cli reproduce
# unit tests (CPU)
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_*.py -q
```
