# Pre-registration: the fit-only noise floor, with the flatten made deterministic

**Written 2026-09-21, before any arm is launched.**

## The question one pair cannot answer

`reports/the_flatten_is_reproducible_when_asked.md` showed the flatten's 3.04% can be switched off.
The obvious next claim — *"so every 3v3 null tightens from ~12% to ~X%"* — is one I computed and
**declined to make**: it subtracts a flatten σ whose df=1 interval spans [1%, 69%] from the total CV,
and at that interval's ends the residual is anywhere from "unchanged" to "imaginary". The same error
as the withdrawn "59%", in a different costume.

The honest route is to **measure the fit-only CV directly**: take existing fits that differ only by
seed, re-flatten every one deterministically, render, score, and compute the within-group CV. With
the flatten's contribution at exactly zero, what remains is fit RNG plus the ~0.003% scorer.

## Arms

The six `curbase_s4..s9` fits: identical config, seeds 4–9, one villa tree (`be09a8503`), meshes on
disk. **No new fits.** Each is re-flattened under `FLATTEN_DETERMINISTIC=1`, rendered on the pinned
image, and scored — the same pipeline as their stock scores, with one variable changed.

This group is chosen deliberately: its stock CV is **0.0742 (df=5)**, the noisy set that carried
`curbase_s6` at 3.45M against 2.82–3.02M for the others. So the study also answers a second question
for free.

## Predictions, fixed now

1. **Fit-only CV lands in [0.030, 0.055].** The stock total is 0.0742; the flatten pair implied
   σ≈0.027 at its point estimate; quadrature subtraction gives ~0.069, but that point estimate is
   unreliable and I think the s6 outlier inflates the stock figure more than the flatten does.
   Recorded so it can be a miss — I have missed the last three registered magnitudes.
2. **`curbase_s6` remains the top scorer** in the deterministic set. If it was a fit outlier, it
   survives re-flattening; if it was a lucky flatten draw, it regresses toward the pack. I predict
   fit outlier, because its `fg_fraction` was elevated (0.00834 vs ≤0.00738) on a mid-range canvas.
3. **The deterministic scores differ from the stock scores by a mean shift of no particular sign** —
   deterministic mode fixes one reduction order, it does not find a better surface
   (`det_a` sat 7 vx from both stock surfaces).

## Decision rule

| fit-only CV (df=5) | reading |
|---|---|
| **< 0.030** | The flatten was most of the noise. 3v3 fit comparisons become materially cheaper with `FLATTEN_DETERMINISTIC=1`; the MDE falls below ~7%. |
| 0.030–0.055 | Fit RNG is comparable to the flatten. Deterministic mode helps but does not transform the design; report the number and its df=5 interval. |
| **> 0.055** | Fit RNG dominates; the flatten's 3% was never the binding constraint on fit comparisons and `FLATTEN_DETERMINISTIC=1` buys little there. |

**Always report the chi-square interval at df=5.** A CV at df=5 has a 95% interval spanning roughly
a factor of three; the point estimate alone is what this project has been burned by three times.

## What this does not settle

Whether the residual is *fit RNG* or *fit + something else undecomposed*. Six seeds of one config on
one tree gives one number; it does not partition further. And it says nothing about the pinned tier,
whose fits ran on a different tree.

## Cost

Six arms, strictly serial (renders hold ~24 GB): ~11 min flatten + ~2 h render + ~15 min score each,
**~14 h**. No fits, no scoring-model changes, no new data.

## Side-prediction recorded mid-chain, BEFORE detfit_s5 scored

The flatten's trim grid is a cheap signature of which surface it landed on. `detfit_s5`'s
deterministic grid coincides with its stock grid to the pixel (`9108x455` both); `detfit_s4`'s did
not (`9147x463` → `9157x461`) and its ink shifted **+4.80%**.

**Prediction: `detfit_s5`'s ink shift from stock is small — under 1%.** A coinciding trim grid does
not prove a coinciding surface (the grid is a bounding box, not the geometry), but a surface that
differs by 7 vx should rarely produce the identical bounding box. If the shift is instead ~3–5%, the
grid is not the signature I think it is, and that is worth knowing too.
