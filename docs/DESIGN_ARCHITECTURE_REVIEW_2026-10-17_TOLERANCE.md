# Design and architecture review — the 0.01 F1 tolerance (#106)

Date: 2026-10-17. Baseline: `cd85607c` (main after #110). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the owner's #106 (`5ea97819`, merged as `3b22a7ee`), which lowered `train.F1_NOISE_TOLERANCE` from 0.03 to
0.01 for protocol v3. It also touched the comment that derives the tolerance, the tests that read it, the v3 noise
probe report, and the scripts and tests that quote the old value. The threshold is the owner's decision. This review
checks what the change says about itself, and what it does to the loop.

## What changed

- **"A no-change cycle promotes ~0.2% of the time" needed its premise stated.**
  - The figure is P(N(0, 2σ²) > 0.01) at σ = 0.0025, and the 5% and ~23% beside it follow the same way. That
    describes a cycle whose expected val_f1 equals the incumbent's stored one.
  - The probe's own identical-config cycles are not such cycles. All four started from the incumbent and gained
    0.012 to 0.018 on it, so each would promote under 0.01. #106's
    `test_every_v3_probe_trial_would_be_promoted` asserts exactly that.
  - The comment in `train.py` and the comment on `test_false_promotion_at_the_v3_sigma_is_under_one_percent` now say
    what "no-change" means, and that the identical-config cycles were not that.
- **The July "HONEST IMPLICATION" paragraph** in the same comment is now marked as v1. It spoke of "this wide
  tolerance" when the tolerance was 0.03, and read as current beside 0.01.

## Verified, no change needed

- **The arithmetic.**
  - P(N(0, 2σ²) > 0.01) is 0.23% at σ = 0.0025, 5.0% at 0.0043 and 22.6% at 0.0094, as the comment says.
  - 0.249348 + 0.01 = 0.2593 is the new bar, and all four trials (0.2615–0.2669) clear it, as the report says.
- **The tests.**
  - `test_noise_probe_v3_report.py` now pins the report's "none would be promoted" to the tolerance at the time
    (`TOLERANCE_AT_PROBE = 0.03`), and records the decision in a separate test.
  - It passes on its own (6 passed), so its `import train` does not depend on test order.
  - The scripts and report tests that quote 0.03 now say it was the tolerance when they ran.
- **The live docs** give 0.01: the README, and `REPRODUCE.md` and `METHOD.md` since #110. Dated reports and design
  plans keep the value they were written under.

## Observations for the owner (not changed)

- **A cycle can promote on the cycle alone, and keep its tweak.** On a promotion, `run_autoresearch_loop.py` keeps
  the cycle's `config.json` change and adds one to its family's success count.
  - The probe puts one identical-config 900 s cycle from this incumbent at +0.012 to +0.018. While that holds, the
    next cycles promote whatever they tweak, so long as the tweak costs less than about 0.002 to 0.008. Each such
    promotion is kept, and credited to that family.
  - The report already says the +0.015 "can be a recipe gain or the incumbent's own one-time adaptation to per-run
    crops; this probe cannot separate them". If it is one-time, the first promotion absorbs it and the 0.2% reading
    applies after that. If it recurs, each cycle's tweak is judged against the incumbent plus a cycle's training.
  - Ways to separate the two, each a design change for the owner:
    - score an identical-config control cycle beside each candidate;
    - re-score the incumbent after its own cycle before comparing;
    - or watch whether the second promotion's margin falls to the noise.
- **The tracked `best_model.pt` is still scored under protocol v2** (`seeded-sample-400-v2+z1-27`, val_f1 0.7273,
  from `a37b05c4`). The current protocol is `seeded-sample-400-v3`, and #106's numbers use the v3 re-score, 0.249348.
  - A fresh clone's loop fails closed: it prints `Not starting: …` and asks for a re-score.
  - The owner's re-scored file was not committed. The README asks for it to be ("commit it, as `a37b05c4` did").
  - It could not be re-scored here: there is no data.
- **Two claims could not be checked here.** The comment's "none of the 34 loop cycles scored under v3 (10-16/17)
  promoted, though each beat the incumbent by 0.011-0.022" rests on sprint logs that are not committed. The σ
  interval rests on n = 4, as the comment says.

## Verification

Environment: CPython 3.10 venv, no GPU visible. No scroll data here.

- `pytest tests/test_f1_improvement_criterion.py tests/test_noise_probe_v3_report.py`: 15 passed.
- The false-promotion rates, recomputed with `math.erfc`: 0.0023, 0.0500, 0.2260.
- `torch.load("best_model.pt")`: `val_protocol` `seeded-sample-400-v2+z1-27`, `val_f1` 0.7273.
  `promotion.VALIDATION_PROTOCOL` is `seeded-sample-400-v3`.
- The credit path: `run_autoresearch_loop.py` adds one to `success_counts[family]` on `is_success`, then renames the
  cycle's temporary config onto `config.json`.
- Ruff clean on the changed files. Only comments changed.
- The standard suite: see the PR.
