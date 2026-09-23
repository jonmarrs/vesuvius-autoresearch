# No free offset lever: every displaced copy of the fitted surface scores lower

**2026-09-23.** The result of `docs/preregistration/2026-09-22_ink_maximum_offset.md` (rule amended
before any arm was built), decided by `scripts/analyse_ink_maximum_offset.py`. Data:
`reports/ink_maximum_offset.json`. Seven radial offsets of ONE flattened surface
(`radial_work_rad0`'s `w120–w129_flat`), all written by one tool and rendered with the flatten
reused. Every build was verified (same valid points and axis; `z.tif` byte-identical to the 0 vx
surface), every reuse guard passed, and all seven share one tree and one render image.

## The result

| offset (vx) | −4 | −2 | **0** | +1 | +2 | +3 | +4 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `total_fg_pixels` | 1,363,076 | 1,547,917 | **1,698,914** | 1,650,750 | 1,661,419 | 1,642,112 | 1,622,775 |
| vs 0 vx | −19.77% | −8.89% | — | −2.83% | −2.21% | −3.34% | −4.48% |

**Verdict: NO FREE LEVER.** No displaced offset beats the fitted surface. The best, +2 vx, is
−2.21%, far below the lever threshold. A global radial offset of the flattened surface does not raise
villa's objective at any offset tried, so there is **no objective-gaming route of this kind** to
flag.

* **Prediction 1** (vertex at +1.4 ± 1 vx): the descriptive parabola (R² 0.96) puts its vertex at
  +1.43 vx, "in band". As the amendment recorded before the data, this cannot discriminate: a
  symmetric fit through an asymmetric curve moves its vertex outward whatever the truth. Its **model
  gain is −1.22%**, because the fitted surface is a sharper maximum than a parabola can represent.
* **Prediction 2** (a gain of about 1.4%): **missed**. The best observed arm is −2.21%.

The shape is asymmetric, as the ±4 vx arms had shown: steep inward (−8.9% at −2 vx, −19.8% at −4 vx)
and shallow outward (−2.2% to −4.5% from +1 to +4 vx).

## What the verdict can and cannot carry — a correction to the amendment

The amended rule compares each displaced arm with 0 vx against a margin of 3F, where F = 0.0014% is
the render+score repeat floor on **identical** content. But each displaced arm renders **different**
content. The re-layout work found the scorer re-reads changed content with about ±2.5% noise on a
strip total (`reports/the_flatten_noise_is_local_rescoring.md`, sections 3 and 5). So:

* **"No arm beats 0 vx" is robust.** All six fall below it, by 2.2% to 19.8%.
* **A lever smaller than about 2–3% is not excluded.** Rescoring noise of changed content, not F,
  sets the resolution here.
* **It cannot be told apart whether the fitted surface is a true sharp peak or a favourable draw.**
  The four outward arms sit 2.2–4.5% below it, which is the size of that noise.
* **The amendment overclaimed.** It said: "With the floor at 0.0042% of ink, the only case that
  matters is a peak almost exactly on 0." The floor for this comparison is not 0.0042%. The verdict
  stands; that sentence's resolution does not.

## What it means

* **Displacing the surface costs ink both ways, and the fitted surface is the best of the seven
  positions.** Here the fit lands where the scorer finds the most ink, to within the ~2–3% this sweep
  can resolve.
* **The loop-reachability question is moot for this lever.** The queued flatten-transmission study
  asked whether a mesh offset reaches the flattened surface. With no lever it cannot matter for
  gaming, though its geometry answer stands on its own.
* **Unchanged:** a gain here would have been the metric moving, not more text being readable. No
  legibility endpoint was measured.

## Limits

One surface, one ROI, one point per offset. Prediction 3 (stability across fits) was withheld.
