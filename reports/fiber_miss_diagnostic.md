# The fiber mask's failure on two new Scroll-5 cubes is not a frame offset or a threshold: a fifth of their fiber is invisible to it

**2026-10-11.** Result of `docs/preregistration/2026-10-11_s5_heldout_miss_diagnostic.md` (pre-registration `93115122`,
before any shift or threshold outcome was computed). The analysis is `scripts/fiber_miss_diagnostic.py`, unchanged since
that commit. Its output is `reports/fiber_miss_diagnostic.json`, run on all 21 ScrollGT fiber targets after the ten
held-out ones were built.

**Question.** Finding 83: on two Scroll-5 cubes `fiber_hz_vt` never trained on, the reference mask covers 0.64 and 0.53
of the hand-traced fibers, against 0.82–0.91 on the in-sample Scroll-5 256³ cubes. The mask also fires on more of
these cubes than on any in-sample Scroll-5 256³ cube. Is the drop:
* a frame offset between the annotation and the CT;
* a calibration shift a lower threshold recovers;
* or a real miss?

## Verdict: `SOFTER_BUT_NOT_RESCUED`

* **Gates pass on all 21 cubes.**
  * G1: P ≥ 0.5 from the cached probability equals the shipped mask bit for bit.
  * G2: zero-shift coverage and ball-max coverage at 0.5 both reproduce the published connected-components
    coverage to 1e-4.
* **Control passes.** The largest shift gain on an in-sample cube is 0.0102 (`s1_08997_02997_02497`, shift
  (−1, −2, 0)), under the 0.05 flag.
* **P1 (frame offset) was withheld; no flag.** The best rigid shift within ±4 voxels gains 0.0020 and 0.0017 on the two
  new cubes. Every single-axis profile peaks at zero shift or one voxel from it and falls symmetrically, so the skeleton
  and the mask share a frame.
* **P2 HELD: a lower threshold does not rescue them.** At P ≥ 0.1, coverage is 0.764 and 0.689, below the in-sample
  Scroll-5 256³ minimum of 0.8185. At 0.05 it is still 0.804 and 0.748.
* **P3 FAILED: their misses are softer than in sample.** The soft-miss fraction is 0.340 on both, above the in-sample
  Scroll-5 maximum of 0.289. Of the length the mask misses at 0.5, a third has P ≥ 0.1 within 2 voxels.

## Results (tolerance 2.0, scoring version 2)

`C(t)`: coverage at threshold t. `hard miss` = 1 − C(0.05): length with no voxel at P ≥ 0.05 within 2 voxels.
`soft` = (C(0.1) − C(0.5)) / (1 − C(0.5)). `dens ×` = mask density at 0.1 over density at 0.5. `missed median` = the
median ball-max probability over length missed at 0.5.

| cube | split | C(0.5) | best shift C | best shift | C(0.1) | C(0.05) | hard miss | soft | dens × | missed median |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| s1_00497_01497_03997 | primary | 0.9177 | 0.9194 | (0, -1, -1) | 0.9421 | 0.9477 | 0.052 | 0.296 | 1.39 | 0.015 |
| s1_00497_02497_02997 | primary | 0.8197 | 0.8197 | (0, 0, 0) | 0.8652 | 0.8778 | 0.122 | 0.253 | 1.34 | 0.008 |
| s1_00997_02497_02997 | primary | 0.8225 | 0.8225 | (0, 0, 0) | 0.8563 | 0.8667 | 0.133 | 0.190 | 1.34 | 0.004 |
| s1_08997_02997_02497 | primary | 0.7617 | 0.7719 | (-1, -2, 0) | 0.8143 | 0.8314 | 0.169 | 0.221 | 1.35 | 0.008 |
| s1_10997_02997_02997 | primary | 0.8553 | 0.8653 | (1, 0, -2) | 0.8844 | 0.8930 | 0.107 | 0.201 | 1.31 | 0.004 |
| s5_03997_01497_03997 | cross_scroll | 0.8666 | 0.8666 | (0, 0, 0) | 0.8926 | 0.9034 | 0.097 | 0.195 | 1.36 | 0.007 |
| s5_06494_01994_03994 | cross_scroll | 0.8882 | 0.8929 | (0, 0, -1) | 0.9182 | 0.9278 | 0.072 | 0.268 | 1.32 | 0.015 |
| s5_06994_00994_04994 | cross_scroll | 0.8130 | 0.8181 | (-1, -1, -1) | 0.8671 | 0.8850 | 0.115 | 0.289 | 1.42 | 0.021 |
| s5_07994_01994_05494 | cross_scroll | 0.8223 | 0.8223 | (0, 0, 0) | 0.8589 | 0.8703 | 0.130 | 0.206 | 1.33 | 0.005 |
| s5_07997_02997_05497 | cross_scroll | 0.9119 | 0.9124 | (-1, 1, 0) | 0.9368 | 0.9431 | 0.057 | 0.283 | 1.32 | 0.014 |
| s5_14997_01497_01497 | cross_scroll | 0.8185 | 0.8239 | (0, 0, -1) | 0.8635 | 0.8793 | 0.121 | 0.248 | 1.38 | 0.012 |
| s3_00994_00494_01994 | held_out | 0.8096 | 0.8096 | (0, 0, 0) | 0.8905 | 0.9146 | 0.085 | 0.425 | 1.80 | 0.067 |
| s3_00994_01994_00494 | held_out | 0.8097 | 0.8109 | (0, 0, -1) | 0.8813 | 0.9019 | 0.098 | 0.376 | 1.56 | 0.045 |
| s3_00994_02494_01494 | held_out | 0.7938 | 0.7938 | (0, 0, 0) | 0.8835 | 0.9113 | 0.089 | 0.435 | 1.73 | 0.072 |
| s3_01994_01494_00994 | held_out | 0.8424 | 0.8430 | (0, -1, 0) | 0.9144 | 0.9334 | 0.067 | 0.457 | 1.83 | 0.079 |
| s3_01994_01994_01494 | held_out | 0.8626 | 0.8626 | (0, 0, 0) | 0.9263 | 0.9429 | 0.057 | 0.464 | 1.75 | 0.082 |
| s3_02994_02494_01994 | held_out | 0.8677 | 0.8677 | (0, 0, 0) | 0.9159 | 0.9294 | 0.071 | 0.364 | 1.45 | 0.040 |
| s3_03494_01494_00494 | held_out | 0.7694 | 0.7698 | (0, -1, 0) | 0.8656 | 0.8928 | 0.107 | 0.417 | 1.69 | 0.062 |
| s3_04494_00994_01494 | held_out | 0.8573 | 0.8573 | (0, 0, 0) | 0.9173 | 0.9322 | 0.068 | 0.420 | 1.53 | 0.060 |
| s5_13497_01497_02497 | held_out | 0.6427 | 0.6446 | (0, -1, 0) | 0.7643 | 0.8040 | 0.196 | 0.340 | 1.82 | 0.035 |
| s5_16997_03997_04497 | held_out | 0.5291 | 0.5308 | (0, -1, 0) | 0.6893 | 0.7480 | 0.252 | 0.340 | 1.96 | 0.041 |

## Descriptive, not registered

* **Softness is a held-out signature, not this failure's.** Scroll 3, where the mask's coverage holds, is softer still:
  * soft-miss fraction 0.364–0.464, against 0.340 on the new Scroll-5 cubes and 0.190–0.296 in sample;
  * missed-length median probability 0.040–0.082, against 0.035–0.041 and 0.004–0.021;
  * density at 0.1 is 1.45–1.83× density at 0.5, against 1.82–1.96× and 1.31–1.42×.

  On unseen data the model is less confident everywhere, and that alone did not cost it coverage on Scroll 3. So P3's
  failure does not explain the Scroll-5 drop.
* **What sets the two Scroll-5 cubes apart is length the model does not see at all.** With no voxel at P ≥ 0.05 within
  2 voxels:
  * 19.6% and 25.2% of their annotated fiber;
  * 5.7–10.7% on Scroll 3;
  * 5.2–16.9% in sample. The top of that range is `s1_08997_02997_02497`, a cube villa's revision added 37% of its
    length to (finding 82).

## What it means

ScrollGT 0.6.0's two Scroll-5 targets are built correctly: the skeleton and the CT share a frame, as the mask sees it.
Their low coverage is not a threshold artifact either. Lowering the threshold to 0.1 recovers a third of the missed
length, at nearly double the mask's volume, and still leaves both cubes below every in-sample Scroll-5 cube. About a
fifth to a quarter of their fiber produces essentially no response from `fiber_hz_vt`. That is a real miss, and finding
83's three candidates remain: the region of the scroll, the content of the cubes, and the annotators. One more
observation fits the annotator reading without testing it. The only in-sample cube whose hard-miss share approaches
theirs is the one villa's revision extended most. Revisions add fiber the mask was not trained to see.

## Limits

* Two failing cubes. The comparison is descriptive beyond the registered P2/P3.
* Rigid integer shifts only. A rotation, a scale error or a sub-voxel offset would not show as a peak. The symmetric
  single-axis profiles make a large one unlikely.
* "The mask sees a common frame" is not a CT check. A misregistration the mask shares with the skeleton would be
  invisible here, but no mechanism for one is known.
* One model, one tolerance, and cutoffs (0.1, 0.05) fixed before the run. The full sweep is in the JSON.
