# The tutorial's sampling band (slice step 0.5) agrees best with villa's ink labels; thinner and wider bands agree less

> **Correction (2026-10-04, `reports/supervised_reanalysis.md`):** computed on the whole surface; villa's labels exist only inside its supervision mask. On the supervised region **this finding does not survive as stated.** 0.5 still beats 0.25 (8 of 8, −6.1%) and 2.0 (8 of 8, −20.4%), but **against 1.0 there is no consistent difference** (4 of 8 resolved, median −1.5%, range −4.8% … +1.4%). The best band is around 0.5–1.0.

**2026-10-03.** Result of `docs/preregistration/2026-10-03_sampling_band_vs_labels.md` (committed `da148ac8`
before any arm rendered; procedural amendment `45a830eb` before any comparison). It was run end to end
with **inkagree 0.2.2** (github.com/jonmarrs/inkagree @ `4add4cd`), pinned in its own environment.
Per-segment results: `reports/band_study/` (24 comparisons and 3 summaries, as inkagree wrote them).

## The question

villa's 3D-ink tutorial renders the ink prediction with 16 slices at `--slice-step 0.5`: "a focused band
around the surface without accumulating as much papyrus texture as a wider step". Does that band agree
with villa's ink labels better than a thinner or a wider one?

## Method (as registered)

* The 8 PHercParis4 segments with villa labels on the 2.4 µm frame.
* Arms: inkagree's `tutorial` preset (group 2, scale 1, 16 slices) on `vc-render:sampler-f637f3b35`,
  slice step ∈ {0.25, **0.5**, 1.0, 2.0}, max over slices.
* Each step compared with 0.5 (A = 0.5, B = step), inkagree defaults, aggregated with
  `inkagree summarize --k 6`.

## Result

All 8 segments were compared for every step; none failed the gate.

| B (slice step) | verdict, k = 6 | resolved for 0.5 | median ΔAP | ΔAP relative to AP(0.5) | ΔAUC |
|---|---|---|---:|---|---|
| 0.25 | **0.5 agrees better** | 8 of 8 | −0.0048 | −3.4% … −11.7% (median −4.7%) | negative in 8 of 8 |
| 1.0 | **0.5 agrees better** | 7 of 8 | −0.0091 | −3.1% … −14.4% (median −11.2%) | **positive in 8 of 8** (+0.001 … +0.024) |
| 2.0 | **0.5 agrees better** | 8 of 8 | −0.0358 | −32.9% … −47.1% (median −37.8%) | negative in 7 of 8 |

## Predictions, as registered

1. **"Step 2.0 agrees worse than 0.5": HELD**, 8 of 8 resolved, about −38% of AP.
2. **"Step 0.25 vs 0.5: no consistent difference": FAILED.** 0.5 is better in 8 of 8, about −5% of AP.
3. **"Step 1.0 vs 0.5: no consistent difference": FAILED.** 0.5 is better in 7 of 8, about −11% of AP.

## What it means

* **The tutorial's step is the best of the four here.** Agreement with the labels peaks at 0.5, drops a
  little on the thin side (0.25), more on the wide side (1.0), and sharply at 2.0. That supports the
  tutorial's rationale, as an interior optimum rather than "thinner is better".
* **A wider band trades precision for reach.** At 1.0, AP falls in 7 of 8 segments while AUC rises in
  all 8. The wider band reaches labelled ink the focused band misses, at low scores, but also brings in
  bright non-ink that costs precision at the top of the ranking.
* **For finding 66 (indirect).** The post-#1146 sampler doubled the slice step and raised villa's ink
  count by 5–9%. At this level, doubling the step (0.5 → 1.0) lowers AP by about 11% while raising AUC.
  A doubled band is not more faithful by AP: it finds more, less precisely. Finding 66 was at the spiral
  metric's settings (group 1, 5 slices) with villa's 2D scorer, so this is suggestive, not a direct test.

## Limits, and the confound that matters most here

* **Home advantage for 0.5.** As registered: villa's labels are partly pseudo-labels refined on default
  renders. If those used this tutorial band, the reference arm is favoured by construction. That could
  account for the small gaps at 0.25 (−5%) and 1.0 (−11%). It is hard to stretch to the −38% at 2.0.
* One scroll and one 3D ink model; the segments share both. Group 2 / 16 slices only.
* This measures agreement with labels, not legibility.
