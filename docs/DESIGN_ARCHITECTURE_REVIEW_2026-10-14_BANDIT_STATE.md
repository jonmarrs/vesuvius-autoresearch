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

- **The family weights are saved after every scored cycle.** Before, only a SUCCESS or a CRASH saved them.
- **Only a scored cycle (SUCCESS or REVERTED) decays them.** The decay used to run before each cycle's
  selection, so a crash, a failed preflight or a stop mid-run also counted. A crash leaves them as they were.
- **The weights are saved before the config files move**, and atomically (a temporary file, then `os.replace`),
  so a stop mid-write leaves the previous file.
- **An unreadable history file is moved aside** (`autoresearch_history.json.unreadable-<time>`) with a warning,
  rather than replaced by the defaults at the end of the first cycle.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **The per-cycle decay was lost on REVERTED cycles.** Each cycle multiplies every active family's weight by 0.95 (floor 1.0), so a family that stops producing promotions loses its dominance: that is the design's stated purpose. The decayed weights were written only on a SUCCESS (with the +1 reward) or a CRASH. REVERTED, the usual outcome, left them in memory. The loop exits at every shift change and the watchdog restarts it, which reloads the file, so a shift without a crash or a promotion put back the weights from before its decay. Whether a family's dominance decayed therefore depended on how often cycles crashed. The committed history has `loss_balance` at 7.83, against 1.0 to 2.1 for every other family, which is about 45% of proposals on the current `resenc_unet` baseline. At 0.95 per active cycle that would take about 40 cycles to reach the floor, if every decay were kept. | `save_history` runs at the end of every cycle. Tests: over three REVERTED cycles from a weight of 2.0, each cycle trains with the previous cycle's decay already on disk, and 2.0 × 0.95³ is saved at the end; a promotion saves 2.0 × 0.95 + 1. The first fails on the old loop. |
| P3 | **A broken environment wore the weights down.** The decay ran before the cycle's selection, so every cycle counted, including crashes and failed preflights, which ran no experiment. Crashes were the outcome that saved, so a run of crashes (a missing volume, a bad driver) brought every active family to the floor and wiped out what the search had learned. | The decay is applied when the cycle is scored: SUCCESS or REVERTED. A crash changes nothing. Test: two crashed cycles leave a weight of 2.0 as it was; it fails on the old loop. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| `save_history` was not atomic, and now runs every cycle; a stop mid-write would leave a truncated file. | Fixed: a temporary file in the same directory, then `os.replace`. |
| A corrupt file was replaced by the defaults at the end of the first cycle, where before it survived until a promotion. | Fixed: it is moved aside with a warning. If it cannot be moved, the warning says so and the loop runs on the defaults. Tested. |
| The decay counted crashes and failed preflights, so a broken environment wore the weights down to the floor, and now every one of those decays would be saved. | Fixed: only scored cycles decay (above). |
| The SUCCESS reward was saved after the config rename, so a failed rename lost it. | Fixed: the weights are saved before the config files move. Tested. |
| The test checked only the end state. | It now checks the file before each cycle trains as well. |
| The temporary-config removal was duplicated across the crash and REVERTED branches. | Merged into one branch. |
| The doc suggested resetting the file without saying to stop the loop first. | Corrected below. |
| The tracked history file is now modified after almost every cycle, so `git checkout -- .` reverts the decay and `git pull` can refuse to merge it. | Recorded below. `recent_configs.json` has been in that state since it was added. |
| The duplicate-avoidance slot is saved when a config is sampled, the decay only when its cycle is scored. | Kept: it predates this PR, and costs only that the stopped config is skipped for the next 20 samples. The decay waits for a score because a stopped cycle taught nothing about its family. |
| Saving the decay shortens how long a reward lasts. | Recorded below. |

## Observations for the owner (not changed)

- **A reward now fades in about 14 scored cycles.** A +1 from the floor (2.0) decays to 1.0 in 14 scored cycles,
  and every active family decays on every scored cycle, not only the one sampled. Before, the decay was lost at
  most restarts, so rewards lasted far longer than the 0.95 rate says. The rate was set for the intended
  behavior; whether 14 cycles (under a day) is the memory the owner wants is a choice about the search.
- **The weights were earned under other promotion rules.** Rewards accrued under protocol v1, the val_bpb
  criterion and noise-level margins still steer selection; `loss_balance`'s 7.83 is the main example. With the
  decay now saved, an unrewarded family falls to the floor within about 40 scored cycles. Resetting the file to
  1.0 everywhere would do it at once: stop the loop first (`stop.sh`), since a running loop rewrites the file
  from memory at the end of its cycle. That is a choice about the search, not a defect.
- **The history file is tracked and now modified between promotions.** The loop commits it with each promotion.
  Between promotions it differs from the committed copy, as `recent_configs.json` always has, so
  `git checkout -- .` or `git stash` on the host reverts the decay, and a `git pull` that changes the file stops
  until it is resolved. Untracking it would keep the weights on the host only.
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
- **The decay's floor** (1.0) keeps every family eligible; a crash neither rewards nor decays.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #62's head, whose tree is `f592a25b`'s.

- Baseline: 42 failed, 2093 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch, after the PR review's fixes: `tests/test_loop_lifecycle.py` and `tests/test_autoresearch_measurement.py`, 61 passed. Full
  validation: pending. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py`:
- the decay is on disk before each REVERTED cycle trains, and at the end (fails on the old loop);
- a promotion saves the decay and the reward;
- a crashed cycle leaves the weights alone (fails on the old loop);
- an unreadable history file is moved aside, not overwritten, and no temporary is left (fails on the old loop).
