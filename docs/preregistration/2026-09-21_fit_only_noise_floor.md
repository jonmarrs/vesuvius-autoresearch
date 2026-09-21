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

## Prediction 2 sharpened, before `detfit_s6` scored

`s6`'s deterministic trim grid differs from its stock grid (`9146x453` → `9147x449`), so by the
grid heuristic a few-percent shift is expected. But `s6`'s stock score leads the next-highest
(`s4`, 3,019,583) by **14%**, and a few-percent flatten shift cannot close a 14% gap. So the two
readings separate cleanly:

* **fit outlier** → `s6` stays top by a wide margin, shifted a few percent either way;
* **flatten draw** → `s6` regresses toward ~3.0M and loses the top spot.

There is no ambiguous middle. Prediction 2 stands as registered: fit outlier.

## What the result cannot do, computed before it arrives

The obvious over-reading — "a tighter floor reopens the nulls" — does not survive arithmetic. At 3v3
the design MDE for each registered band, against the effect each null study *observed*:

| study | observed | CV<0.030 → MDE 5.7% | 0.030–0.055 → 9.6% | >0.055 → 14.9% |
|---|---:|---|---|---|
| patch bootstrap | 0.83% | null | null | null |
| stripmatch | 3.08% | null | null | null |
| same-winding (pinned) | 1.74% | null | null | null |
| same-winding (current) | 0.28% | null | null | null |
| anchor ablation | 5.49% | null (just) | null | null |

**No published null becomes decisive in any band.** The largest observed null effect, the anchor
ablation's 5.49%, falls short of even the most favourable MDE; the other four sit an order of
magnitude below any achievable floor. So this study's result bears on **how many seeds future
studies need**, not on whether any past null was secretly a finding. Recorded now so the number is
not over-read when it lands.

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

**Resolved 2026-09-21 15:11, when `detfit_s5` scored: −0.97%. MET — by 0.03 points.** The bound
was 1%; the result cleared it by three hundredths. That margin is not evidence of anything; a
different draw could have put it on the other side. What the two arms do support is the qualitative
reading: `s4`'s grid changed (`9147x463 → 9157x461`) and it shifted +4.80%; `s5`'s grid coincided
and it shifted −0.97%. The trim grid is a usable signature of whether the flatten landed near its
previous surface — a heuristic with one confirmation, not a law.
