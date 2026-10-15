# The loop's model reads ink about as well from shallow windows as from deep ones (finding 90)

**2026-10-14.** A read-only measurement, **pre-registered**: its reading rule was committed (`2c493fed`) before it
ran. CPU, one thread, lowest priority, beside the running loop. Script `scripts/loop_model_depth_offset.py`, run at
`2c493fed`; output `reports/loop_model_depth_offset.json`.

**Question.** Finding 89 found that the TimeSformer detector reads ink mostly from zarr slices 20–26. The loop
reads each patch's 24 slices from a start z0 between 0 and 7 (`depth_band` [1, 27], a 4-slice margin), and its
model sees the middle 16, zarr z0+4 to z0+19. That window holds none of slices 20–26 at z0 = 0 and all seven at
z0 = 7. Finding 89 suggested pinning the band deep (`depth_band` [11, 27], every read at z0 = 7) as a candidate
lever. Does the loop's own model, not the detector, read ink better from deep windows?

**Method.** The loop's 400-patch validation draw of Fr143 (seed 42, each patch moved in the plane as the loop reads
it), every patch kept, as in protocol v3 (PR #66): **400** patches, **97** of them with ink. Each model is scored
with every read forced to start at one z0:

* the incumbent (`best_model.pt`, sha256 `d7da2776…`) at z0 = 0 to 7, and at each patch's own z0, which reproduces
  finding 88 C's incumbent card within 1e-4;
* finding 88 D's 10 loop candidates (cycle snapshots `candidate_20261013-155821` and the 9 after it; names and
  sha256 checked against `reports/loop_candidate_spread.json`) at z0 = 0 and z0 = 7.

The loader draws a patch's plane position before its depth, and draws no depth when the range holds one start, so
every z0 scores the same pixels against the same targets (the script checks this). Each comparison is paired.

The rule: delta = pooled ROC AUC at z0 = 7 minus at z0 = 0, over all 400 patches. delta(incumbent) ≥ +0.02 with
delta > 0 for at least 8 of the 10 candidates would mean deep windows read better; ≤ −0.02 with at least 8 below 0,
that shallow windows do; |delta(incumbent)| < 0.01 with |mean candidate delta| < 0.01, no dependence on the
window's position; anything else, mixed.

## Result

The incumbent at each start, all 400 patches pooled (AUC on the 97 ink-containing patches beside it):

| z0 | zarr slices seen | AUC | AP lift | val_f1 | AUC, ink-containing patches |
|---|---|---:|---:|---:|---:|
| 0 | 4–19 | **0.5856** | 1.1784 | 0.2495 | 0.5861 |
| 1 | 5–20 | 0.5842 | 1.1776 | 0.2496 | 0.5842 |
| 2 | 6–21 | 0.5842 | 1.1842 | 0.2497 | 0.5827 |
| 3 | 7–22 | 0.5875 | 1.2200 | 0.2493 | 0.5802 |
| 4 | 8–23 | 0.5875 | 1.2134 | 0.2493 | 0.5815 |
| 5 | 9–24 | 0.5851 | 1.1783 | 0.2495 | 0.5811 |
| 6 | 10–25 | 0.5808 | 1.1553 | 0.2495 | 0.5747 |
| 7 | 11–26 | **0.5765** | 1.1431 | 0.2495 | 0.5750 |
| each patch's own (0–7) | — | 0.5717 | 1.1437 | 0.2493 | 0.5615 |

The 10 candidates at the shallowest and deepest start:

| candidate | AUC, z0 = 0 | AUC, z0 = 7 | delta |
|---|---:|---:|---:|
| 155821 | 0.5780 | 0.5777 | −0.0002 |
| 161428 | 0.5794 | 0.5725 | −0.0070 |
| 163045 | 0.5950 | 0.5899 | −0.0051 |
| 164705 | 0.5885 | 0.5826 | −0.0058 |
| 170319 | 0.5813 | 0.5744 | −0.0068 |
| 171939 | 0.5781 | 0.5735 | −0.0047 |
| 173544 | 0.5866 | 0.5851 | −0.0015 |
| 175154 | 0.5794 | 0.5701 | −0.0094 |
| 180802 | 0.5902 | 0.5875 | −0.0027 |
| 182407 | 0.5850 | 0.5854 | +0.0003 |

delta(incumbent) = **−0.0091**; the candidates' mean delta is **−0.0043** (SD 0.0032). Both are under 0.01 in size,
so by the pre-registered rule the loop's model shows **no dependence on the window's position.**

## What this means

* **The detector's preference for deep slices does not carry over to the loop's model.** Finding 89's detector,
  kept to 16 slices, lost 0.0756 AUC reading zarr 4–19 (the loop's shallowest window) and 0.0208 reading zarr 11–26
  (its deepest). The loop's incumbent reads 0.5856 from the shallowest window and 0.5765 from the deepest, its
  lowest of the eight starts. Pinning the band deep would read every patch at the incumbent's worst start, so
  finding 89's lever has no support from the models the loop actually has.
* **What the rule does not decide (not pre-registered):** the small differences lean the other way, toward shallow
  windows. 9 of the 10 candidate deltas and the incumbent's are negative, and 8 of 10 on the ink-containing patches
  alone. The size, a mean of −0.0043, is under half the rule's 0.01 and smaller than the spread between candidates
  at one start (SD 0.0058 at z0 = 0, 0.0071 at z0 = 7). The candidates are fine-tunes of the same incumbent, so the
  9 of 10 are not independent evidence.
* **Reading every patch from its own start costs AUC (not pre-registered).** With each patch at its own random
  start, which is how the loop validates, the incumbent's pooled AUC is 0.5717. That is below every fixed start
  (0.5765 to 0.5875), and on the ink-containing patches 0.5615 against 0.5747 to 0.5861. The patches and targets
  are the same; only each patch's start differs. One explanation, untested: the model's output level shifts with
  the window's depth, so pooling patches read at different depths mixes scales. This is a property of the
  measurement, paid by every model the loop scores, not a difference in how well a model reads ink. Whether a
  fixed validation start would change which candidate ranks first was not measured.
* **val_f1 does not move with the window at all.** The incumbent's pooled val_f1 is 0.2493 to 0.2497 at every
  start, 0.004 above the all-ink F1 of 0.2451 on these 400 patches. AUC and AP lift vary with the start; val_f1
  stays at the floor (finding 86, finding 88).

## Caveats

* **This measures the loop's existing models, which were trained on starts drawn from 0–7.** Pinning `depth_band`
  to [11, 27] would change training too, and a model trained only on deep windows might learn the deep slices'
  ink signal that the detector uses. That is not tested here. What is shown is that models already trained on deep
  windows one start in eight, and on part of the deep slices in most other starts, read no better from them.
* One fragment (Fr143), one draw of 400 patches, one incumbent and 10 candidates from one afternoon of cycles.
  Pixels within a patch are not independent; no significance is claimed.
* Scored on the CPU in fp32. The loop validates on the GPU under autocast; the incumbent's own-start card
  reproduces finding 88 C's (also CPU) within 1e-4.
* **Cost to the loop:** the run took 09:36–17:13, about 16 minutes per model pass, longer than the 4–5 hours
  planned. The loop's median throughput over the 28 cycles that overlapped it was 0.24 Mvps, against 0.29 over the
  10 cycles of the previous night, when no side job ran. Other jobs ran beside it at times, so not all of the
  difference is this run's.
