# Design and architecture review — the 0.01 F1 tolerance (#106)

Date: 2026-10-17. Baseline: `cd85607c` (main after #110). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the owner's #106 (`5ea97819`, merged as `3b22a7ee`), which lowered `train.F1_NOISE_TOLERANCE` from 0.03 to
0.01 for protocol v3. It also touched:
- the comment that derives the tolerance;
- the tests that read it;
- the v3 noise probe report;
- the scripts and tests that quote the old value;
- `README.md`, `docs/RESUME_AFTER_RESTART.md` and `scripts/run_validation_tests.py`.

The threshold is the owner's decision. This review checks what the change says about itself, and what it does to the
loop.

## What changed

- **What the false-promotion rates assume is now stated.**
  - `train.py` says that at 0.01 "a no-change cycle promotes ~0.2% of the time at sigma = 0.0025, 5% at 0.0043 and
    ~23% at the CI's top". Those are P(N(0, 2σ²) > 0.01). They model the candidate and the incumbent as two
    independent training draws with a common mean, as the July derivation did.
  - Against the stored score as a fixed number (it re-scores to within 2e-6), the same premise gives 0.003%, 1%
    and 14%.
  - Either way the rates are for a cycle that gains nothing, and a loop cycle does gain:
    - it warm-starts from `best_model.pt`;
    - the probe's identical-config cycles gained 0.012 to 0.018 on the incumbent;
    - so did 8 of the 10 loop candidates in finding 88's part D (below).
  - The comment in `train.py` and the comment on `test_false_promotion_at_the_v3_sigma_is_under_one_percent` now say
    this. They also say that every figure is for the 900 s day budget.
- **Text beside #106's edits now names the rule it used.**
  - The report's "None would be promoted … 0.03, so above 0.2793" was the rule when the probe ran. Under 0.01, all
    four would be promoted.
  - `RESUME_AFTER_RESTART.md`'s "None of the 10 would be promoted" was at 0.03. At 0.01, 8 of the 10 would be.
  - `loop_candidate_spread.py`'s docstring gave 0.03 as the loop's tolerance in the present tense.
  - Each now carries a dated note.
- **The test that pins the report to the old rule says so.** It is renamed
  `..._none_clears_the_probe_time_bar`, and its module docstring no longer claims to quote `train.py`'s rule.
- **The v3 incumbent's committed source is named.** `V3_INCUMBENT = 0.249348` was commented as `best_model.pt`'s
  stored score, but the tracked file holds its v2 score. `reports/loop_candidate_spread.json` records the v3 value
  (0.2493499), and the comment now points there.
- **Smaller.**
  - The July "HONEST IMPLICATION" paragraph is marked as v1.
  - A comment that `ruff format` had left after a parenthesised expression is moved above it.

## Verified, no change needed

- **The arithmetic.**
  - P(N(0, 2σ²) > 0.01) is 0.23% at σ = 0.0025, 5.0% at 0.0043 and 22.6% at 0.0094.
  - The σ interval is 0.0014–0.0094, and the July formula gives 0.0059 on it.
  - 0.249348 + 0.01 = 0.2593 is the new bar, and all four trials (0.2615–0.2669) clear it, AP lift above 1.02.
- **The tests.**
  - `test_noise_probe_v3_report.py` pins the report's numbers to the tolerance at the time and records the decision
    separately.
  - It passes on its own: pyproject's `pythonpath` includes `scripts/training`.
- **Live code and docs.** No live code hardcodes the tolerance; the tests that need it import it. The README, and
  `REPRODUCE.md` and `METHOD.md` since #110, give 0.01. Dated reports and plans keep the value they were written
  under.

## Observations for the owner (not changed)

- **Under 0.01 most loop cycles promote, and keep their tweak.**
  - On a promotion, `run_autoresearch_loop.py`:
    - keeps the cycle's `config.json` change;
    - adds one to its family's success count;
    - commits `best_model.pt`, which every later cycle warm-starts from.
  - The candidate is compared with the stored score, which the loop never re-scores.
  - **Finding 88's part D** measured this on real tweaks (`reports/loop_candidate_spread.json`). Ten ordinary loop
    candidates from 2026-10-13, each with its own tweak and all warm-started from the tracked incumbent, were scored
    on all 400 patches (v3):
    - they beat the incumbent by +0.0034 to +0.0224, mean +0.0134;
    - 8 of the 10 clear 0.01, every one with AP lift ≥ 1.15;
    - the two that do not are the two `lr` 1e-4 cycles.
  - Those candidates predate #74, #75 and #79, so the gain is not the merged recipe or per-run crops.
  - Their own records point elsewhere:
    - every candidate's best threshold is 0.10, against the incumbent's 0.05 (the grid's floor, calling 96% of pixels
      ink);
    - every candidate's config adds `depth_band` [1, 27], which the incumbent's lacks.

    One cycle of training on the current setup appears to move the v2-era incumbent off its near-all-ink operating
    point. If so, the first promotion absorbs that gain, and after it the cycle effect should shrink.
  - Until then, a tweak promotes unless it costs more than the cycle's gain minus 0.01. With the probe's mean gain
    of 0.015 and σ = 0.0025, a tweak costing up to about 0.005 promotes more often than not.
  - **Ways to tell.** Either is a design change for the owner:
    - compare each candidate with an identical-config control cycle run from the same incumbent;
    - or watch whether the margin of the promotion after the first one falls to the noise.
- **Night cycles are unmeasured.** Both noise probes, and finding 88's candidates, ran 900 s cycles. Night cycles run
  3600 s (`run_autoresearch_loop.py`), where both σ and the cycle's gain may differ. The 0.01 applies to both.
- **The tracked `best_model.pt` is still scored under protocol v2.**
  - It holds val_f1 0.7273 under `seeded-sample-400-v2+z1-27` (from `a37b05c4`), while the loop now requires
    `seeded-sample-400-v3+z1-27`.
  - A fresh clone's loop fails closed: `check_incumbent` raises, the loop prints `Not starting: …` with the re-score
    command, and it checks again before each later cycle.
  - The owner's re-scored file (the probe's input hash differs from the tracked file's) was not committed. The
    README asks for it to be ("commit it, as `a37b05c4` did"). It could not be re-scored here: there is no data.
- **Two claims could not be checked here.**
  - The comment's "none of the 34 loop cycles scored under v3 (10-16/17) promoted, though each beat the incumbent by
    0.011-0.022" rests on sprint logs that are not committed.
  - The σ interval rests on n = 4, as the comment says.

## Verification

Environment: CPython 3.10 venv, no GPU visible. No scroll data here.

- **Tests:** `tests/test_f1_improvement_criterion.py`, `tests/test_noise_probe_v3_report.py`,
  `tests/test_loop_v2_constant_control_report.py` and `tests/test_detector_on_loop_sample_report.py` gave 117 passed,
  1 skipped.
- **The rates, recomputed with `math.erfc`:**
  - 2σ² model: 0.0023, 0.0500, 0.2260;
  - σ² model: 0.00003, 0.0100, 0.1437.
- **Part D's margins, from `reports/loop_candidate_spread.json`:** n = 10, min 0.0034, max 0.0224, mean 0.0134;
  8 clear 0.01.
- **`torch.load("best_model.pt")`:** `val_protocol` `seeded-sample-400-v2+z1-27`, `val_f1` 0.7273.
- **Lint:** Ruff clean on the changed files. The `.py` changes are comments, a docstring and one test's name.
- **Independent review:** a review of the first commit found that it stated the rates' premise wrongly, that it
  missed part D and the night shift, and several smaller points. All are addressed above.
- **The standard suite:** see the PR.
