# At villa's metric settings, the source build's band agrees better with villa's labels than the published image's, and a wider band better still

> **Correction (2026-10-04, `reports/supervised_reanalysis.md`):** computed on the whole surface; villa's labels exist only inside its supervision mask. On the supervised region the finding **survives, smaller**: 1.0 beats 0.5 in 8 of 8 (median **−5.3%**, not −8.3%), and 2.0 beats 1.0 in 8 of 8 (**+8.2%**, not +10.3%).

**2026-10-04.** Result of `docs/preregistration/2026-10-04_install_route_band_vs_labels.md` (committed
`bf66d56a` before any arm rendered). Run end to end with inkagree 0.2.2 (`4add4cd`), pinned in its own
environment. Per-segment results: `reports/route_study/`.

## The question

Finding 66: villa's published sampler image (built 2026-05-13) and any post-#1146 source build differ only
in slice step. On the same surface that moves villa's ink count by +5.0% to +9.2%. At group 1 the
published image's default sampling equals a post-#1146 build at `--slice-step 0.5` (finding 66's verified
equivalence). **Which route's sampling agrees better with villa's ink labels**, at the metric's own render
settings?

## Method (as registered)

The 8 PHercParis4 segments with villa labels on the 2.4 µm frame. inkagree's `metric` preset (villa's
spiral-metric settings: group 1, scale 0.25, 5 slices; label level 3) on `vc-render:sampler-f637f3b35`,
slice step 0.5 / **1.0** / 2.0, max over slices (the raw rendered 3D-ink prediction). Each step compared
with 1.0, inkagree defaults, `inkagree summarize --k 6`.

## Result

All 8 segments were compared in both comparisons.

| B (slice step) | verdict, k = 6 | resolved | median ΔAP | ΔAP relative to AP(1.0) | ΔAUC |
|---|---|---|---:|---|---|
| **0.5** (= the published image's sampling) | **1.0 agrees better** | 8 of 8 | −0.0063 | −6.8% … −11.0% (median −8.3%) | −0.019 … −0.033, all 8 |
| **2.0** (wider) | **2.0 agrees better** | 8 of 8 | +0.0084 | +9.4% … +16.4% (median +10.3%) | +0.028 … +0.047, all 8 |

## Predictions, as registered

1. **"0.5 vs 1.0: no consistent difference": FAILED.** 1.0 is better in 8 of 8.
2. **"2.0 vs 1.0: no consistent difference": FAILED.** 2.0 is better in 8 of 8.

## What it means

* **For finding 66 and the install route:** at the metric's settings, the post-#1146 source build's
  thicker band agrees **better** with villa's labels than the published image's: about +8% AP, every
  segment. The published image's +5–9% lower ink count therefore goes with **less** faithful renders.
  The stale published image under-samples the band for this setting.
* **For villa's metric:** agreement rises monotonically from 0.5 through 1.0 to 2.0 on every segment.
  A wider band than the metric's default agrees better (+10% AP at step 2.0), and the optimum lies beyond
  what was tested. This measures the raw render only. Finding 72 found villa's 2D scorer leaves label
  agreement unchanged, and how the scorer's count would respond to a wider band is not measured here.
* **Beside finding 74:** at the tutorial's level (16 slices at group 2), the optimum was at step 0.5, and
  wider bands agreed less. Here (5 slices at group 1) the bands are narrower to begin with, and widening
  helps. Both fit one picture, an optimum band thickness the metric's default falls short of. Mapping the
  two settings onto one physical band width is a hypothesis, not tested here.

## Limits

* Labels are partly pseudo-labels. Unlike finding 74 there is no obvious home advantage for the
  reference arm, since the wider arm wins.
* One scroll, one 3D ink model; the segments share both. Raw renders, not villa's scored count.
* The published-image arm is a post-#1146 build at step 0.5, equivalent by finding 66's verified rule,
  not the published binary itself.
