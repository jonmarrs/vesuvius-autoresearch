# Design and architecture review — the loop's family weights across restarts

Date: 2026-10-14. Baseline: `f592a25b` (main after #62). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how `run_autoresearch_loop.py` chooses each cycle's tweak:
- the family weights (`success_counts`, persisted in `autoresearch_history.json`);
- the per-cycle decay;
- the reward on promotion;
- the duplicate-avoidance list (`recent_configs.json`);
- how all of this survives the watchdog's restarts.

The 2026-10-13 loop-proposals review covered which values are proposed and the VRAM cap; this one covers how
the weights evolve.

## What changed

- **The family weights are saved after every cycle, whatever its outcome.** Before, only a SUCCESS or a CRASH
  saved them.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **The per-cycle decay was lost on REVERTED cycles.** Each cycle multiplies every active family's weight by 0.95 (floor 1.0), so a family that stops producing promotions loses its dominance: that is the design's stated purpose. The decayed weights were written only on a SUCCESS (with the +1 reward) or a CRASH. REVERTED, the usual outcome, left them in memory. The loop exits at every shift change and the watchdog restarts it, which reloads the file, so a shift without a crash or a promotion put back the weights from before its decay. Whether a family's dominance decayed therefore depended on how often cycles crashed. The committed history has `loss_balance` at 7.83, against 1.0 to 2.1 for every other family, which is about 45% of proposals on the current `resenc_unet` baseline. At 0.95 per active cycle that would take about 40 cycles to reach the floor, if every decay were kept. | `save_history` runs once at the end of every cycle. Test: three REVERTED cycles from a weight of 2.0 leave 2.0 × 0.95³ saved; it fails on the old loop. |

## Observations for the owner (not changed)

- **The weights were earned under other promotion rules.** Rewards accrued under protocol v1, the val_bpb
  criterion and noise-level margins still steer selection; `loss_balance`'s 7.83 is the main example. With the
  decay now saved, an unrewarded family falls to the floor within about 40 of its cycles. Resetting the file to 1.0
  everywhere would do it at once. That is a choice about the search, not a defect.
- **`"baseline": 18`** in `autoresearch_history.json` belongs to the every-10th-cycle baseline removed on
  2026-10-12. No template uses the family, so it has no effect.
- **The host's history file** may differ from the committed one; the figures above are from the repository.

## Reviewed and sound

- **`template_weights`** gives each family its weight regardless of how many axes it has (2026-10-13).
- **The +1 reward** is given only for a SUCCESS. A blocked promotion counts as REVERTED and a crash earns nothing.
- **`run_result.json`** is deleted before each cycle, so a cycle cannot read a previous cycle's result.
- **Duplicate avoidance** resamples up to ten times. When all ten tries are duplicates it runs the last sample
  and resets the list rather than running the baseline under the tweak's name. The file keeps the last 20
  configs.
- **Promotion of `config.json`** is a rename of the temporary config, so it is atomic.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #62's head, whose tree is `f592a25b`'s.

- Baseline: 42 failed, 2093 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2094 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as
  the baseline; the extra pass is the new test. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) and mypy on the loop: clean.

New test, `tests/test_autoresearch_measurement.py::test_the_family_weight_decay_is_saved_after_a_reverted_cycle`;
on the old loop it fails.
