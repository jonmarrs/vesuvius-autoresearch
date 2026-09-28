# Pre-registration: does inkdelta reproduce every registered replicated interval?

**Written 2026-09-27, before inkdelta was run on any of these arms.** Runner:
`scripts/validate_inkdelta_intervals.py`, committed with this file. Tool: `projects/inkdelta` 0.2.0
(commit b12cc3f in that repository).

## The question

The first validation (`reports/inkdelta_validation.md`) reproduced one registered interval, finding 62,
exactly. One case cannot show that run discovery and the stdlib t quantile hold across the corpus. This
second validation checks every other registered study that reported a Welch interval on
`total_fg_pixels`. That covers both tiers, 3-vs-3 and 3-vs-6 designs, and Welch df from 2.35 to 8.89.

Every expected value below is copied from the registered artifact named, not from running the tool.

## Cases

Direction in all cases: A is the registered analysis's baseline, and rel = (mean B − mean A) / mean A.
That matches `scripts/analyse_gap_ink_arm.py::welch`. Every arm is read from `spiral_out/outer_<tag>`.

| # | study (source) | A | B | required verdict | rel / lo / hi (4 d.p.) | df (2 d.p.) |
|---|---|---|---|---|---|---|
| 1 | gap-expander (`reports/gap_fix_costs_ink_established.md`) | baseline01, seed02..06 | gap133, gap133s2..s6 | **RESOLVED (-)** | −0.1035 / −0.1568 / −0.0503 | 8.89 |
| 2 | patch bootstrap (`reports/patch_bootstrap_verdict.json`) | rand090s1..3 | boot090s1..3 | **NOT RESOLVED** | −0.0083 / −0.1835 / +0.1669 | 3.11 |
| 3 | STRIPMATCH (`reports/stripmatch_verdict.json`) | boot090s1..3 | strip090s1..3 | **NOT RESOLVED** | −0.0380 / −0.2073 / +0.1314 | 3.56 |
| 4 | same-winding, pinned (`reports/samewinding_verdict.json`) | baseline01, seed02..06 | nosame_s1..3 | **NOT RESOLVED** | −0.0174 / −0.1027 / +0.0679 | 4.41 |
| 5 | same-winding, current (`reports/samewinding_current_verdict.json`) | curbase_s1..3 | nosamecur_s1..3 | **NOT RESOLVED** | +0.0028 / −0.0256 / +0.0313 | 4.00 |
| 6 | anchor ablation (`reports/anchor_ablation_verdict.json`) | curbase_s1..3 | anchor10cov_pilot, anchor10cov_s2, anchor10cov_s3 | **NOT RESOLVED** | −0.0086 / −0.1021 / +0.0850 | 2.35 |

Both sides of every case are declared the same build (`edge`). Every render was made with the
published image, and a mismatch is not what is being tested here.

## Stated before running

* **A trap in the data.** `gap133` and `gap133s2` each also have a scored `seedarm_` directory:
  a different, smaller region (249,913 vs 1,591,857). The runner names `outer_` explicitly. A
  checker fed a glob would pick up the wrong run silently. This is the ambiguity
  `scripts/run_patch_bootstrap_verdict.py` already refuses.
* **Logs.** A run's log is `<arm>.render.log`, or failing that `<arm>_render.log`. Otherwise it
  warns `LOG_NOT_FOUND`, which is a warning, not a pass. No case may carry a FAIL finding. The corpus
  audit already found none in these arms.
* **Scorer.** Within each case both sides must report the same scorer identity. A scorer conflict
  (INCOMPARABLE) is a validation failure, because every case was scored by one pinned model.
* **Rule.** A case passes only if the verdict matches and rel/lo/hi match to 4 d.p. and df to 2 d.p.
  Any miss fails validation. It is reported and fixed in the tool, never by editing this table.

## Cost

Seconds on CPU.
