# RECORD, POSTED 2026-08-30

Posted as ScrollPrize/villa#1659: https://github.com/ScrollPrize/villa/issues/1659

A record of what was said, not a draft. Corrections go to the thread as a new comment, never as a
silent edit here. No nudges: await a reply.

---

The six released `PHerc.1667-iteration-N` checkpoints document their input convention in three places, the three disagree, and none of them is the one that produces usable output.

### The three documented conventions

**1. `modeling_inkdetection.py` module docstring**

> Input: float32 tensor of shape `(B, 1, D, H, W)` or `(B, D, H, W)`, where D = 62, H = W = 256 (intensity already z-score normalised).

**2. The model card quickstart comment**

> Intensity should already be in roughly [0, 1] (the training pipeline clipped raw uint8 layers to [0, 200] then applied Normalize(mean=0, std=1) which keeps the magnitude small).

`Normalize(mean=0, std=1)` computes `(x - 0) / 1`, so it is the identity. Clipping raw uint8 to [0, 200] and applying it leaves values in [0, 200], not "roughly [0, 1]". The sentence contradicts itself.

**3. The model card's own full-segment inference snippet**, which normalises nothing:

```python
tile = image[y:y+WINDOW, x:x+WINDOW]            # (256,256,62) uint8
t = torch.from_numpy(tile).permute(2, 0, 1)
t = t.unsqueeze(0).unsqueeze(0).float().cuda()  # passed straight to the model
```

### What each one actually does

`iteration-5`, one 2048x2048 window at level 0 on the models' own scroll, PHerc 1667 `w011` (home scroll on purpose, so a bad result cannot be blamed on cross-scroll transfer):

| convention | fires above 0.5 | mean prob |
|---|---:|---:|
| docstring: z-score per tile | 99.11% | 0.7675 |
| card prose: clip to [0, 200], Normalize is identity | 92.13% | 0.9172 |
| card snippet: raw uint8 | 91.43% | 0.9102 |
| `clip(x, 0, 200) / 255`, not documented anywhere | 18.06% | 0.3644 |

The published canon prediction on this segment fires at 2.82%.

All three documented conventions saturate the model. The only one that lands in a usable range is `clip(x, 0, 200) / 255`, which appears in none of the three. It is still about 6x the published rate, and I have two known deviations from the published recipe that would account for some of that (I scored each tile once rather than overlap-averaging at stride 128, and I did not skip windows touching the fragment mask).

One window and one member, so the exact percentages will move. The gap between 91 to 99% and 18% is large enough that the ranking is not in question.

### Also worth a line in the card

These checkpoints are trained at 2.4 um. The segment zarrs are multiscale, and for anything registered at level 2 that level is a natural default to reach for. Feeding level 2 produces the same saturation pathology on the home scroll, which is how I first found this: it looks exactly like a model that does not transfer, rather than like a scale error.
