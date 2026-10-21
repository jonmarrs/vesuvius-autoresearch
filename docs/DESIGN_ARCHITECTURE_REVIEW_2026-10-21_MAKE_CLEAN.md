# Design and architecture review — `make clean` and the run log, the bench's cube list, the tests outside the suite

Date: 2026-10-21. Baseline: `47b7b9ba` (main after #165).
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- the operator tooling that few reviews have read: the `Makefile`, the `Dockerfile`, the committed experiment
  configs;
- `src/vesuvius_autoresearch/fibers/bench_cli.py` and `skeleton_io.py`, which the reproduction chains for findings 80
  and 83 run;
- the 197 test files outside the standard suite, run on main.

Main has not moved since #165, and no owner PR is open.

## What changed

- **`make clean` deleted `run.log`.**
  - Its help called the files it removes transient stdout logs. `run.log` is the cycles' training output: the loop
    appends each cycle's output to it, and renames it to `run.log.old` past 10 MB.
  - It is git-ignored (`*.log`), so the loop's machine holds the only copy.
  - `scripts/epoch_boundary_overhead.py` and `scripts/cycle_length_gain.py` read each cycle's step count from it, as
    the cycle-length and epoch-boundary reports record (`"run_log": ["run.log.old", "run.log"]`). Those counts cannot
    be rebuilt once it is gone.
  - Run during a cycle, it also unlinks the file the run is writing. The loop's crash handling then finds no
    `run.log`, so it records the crash without its last line and cannot tell an out-of-memory crash.
  - **Change:** `make clean` no longer names `run.log`, and its help says it keeps it. A comment above the target
    gives the reason.
  - The files it still removes are stdout logs of launchers that no longer exist (`shift_stdout_*.log`,
    `dayshift_stdout.log`, `nightshift_stdout.log`) and two files under `/tmp`. No script in the repository writes
    any of them.
- **`bench_cli`'s cube list called itself every published cube.**
  - `CUBES`' comment said every published number draws from its eleven cubes, and `floors --all-cubes`' help said it
    runs every published cube.
  - Since 0.6.0 ScrollGT also publishes ten held-out cubes: eight on Scroll 3 and two on Scroll 5 (finding 83).
    `repro/fibers/run_heldout_chain.sh` traces them from their own data directory.
  - The comment, the help and `_floors_all_cubes`' docstring now say the list is the in-sample eleven. What
    `--all-cubes` runs is unchanged.
- **`LONGEST_RUN_SECONDS`' comment** called it the longest a supervised run may last. It is the longest a loop
  cycle's run may last. An ablation cell can last longer, since its timeout is its `--budget` plus 240 s, and an
  orphaned one older than the limit is stopped all the same. The comment now says so; the value is unchanged
  (the 2026-10-21 night-budget review leaves it to the owner).
- **Test** (`tests/test_loop_lifecycle.py`, in the standard suite): `make clean`'s recipe removes none of `run.log`,
  `run.log.old`, `autoresearch.out`, `watchdog.log` or the sprint logs, by name, by glob, or inside a directory.
  - It fails with the old recipe.
  - It also fails when any of these is added to the recipe: `*.log`, `run.log`, `./run.log`, `run.log*`,
    `sprint_logs/*`, `autoresearch.out`.

## Verified, no change needed

- **The tests outside the standard suite**, on main: 1526 passed and 76 skipped. The 16 failures and 21 errors are
  the ones the 2026-10-20 generated-runners review found, all environmental:
  - 19 errors: the spiral probes cannot find villa's spiral modules;
  - 2 errors and 5 failures: `s3fs` is not installed;
  - 5 failures: `local_data/` is absent;
  - 2 failures each: the villa launchers, and the submodule preflight;
  - 1 failure each: the doc-reference audit, and `correlate_geometry_ink`, which needs the owner's `spiral_out/`.

  The 85 more passes are tests added since. The doc-reference audit still flags only villa's paths and a checkpoint
  under the ignored `models/`, so no merge since has added a stale reference.
- **The committed experiment configs** (`experiments/*/cfg_*.json`) and `test_config.json` load with
  `ExperimentConfig.load`. `from_json` refuses an unknown key, so none carries a field the config has since lost.
- **`skeleton_io.parse_nml` on a real NML.** Villa's `fibers_s5_06500z_02000y_04000x_500_v03.nml`, read in place,
  has 456 fibers. All 20,572 of its node tags and 20,116 edge tags are parsed, and its coordinates are integers.
- **`bench_cli`**:
  - `score` leaves its input checks to `score_tracing`, which refuses non-integer, negative or empty labels;
  - the fiber-probability cache is used only when its record names the same image, model, patch and device, and its
    hash matches the file. Otherwise it is recomputed;
  - the trace defaults are finding 80's published ones, which both chains run with only `--detect-block` added for
    512³ cubes.
- **The `Dockerfile`'s header** says what the image holds and what it does not run, and that it was never built to
  completion. Nothing it copies has moved.

## Observations for the owner (not changed)

- **`parse_nml` drops a node tag its pattern does not match, without saying so.** That would be one with
  non-integer coordinates, or attributes in another order. Any edge to it is dropped too, so the fiber's length
  falls.
  - The NML here parses completely. ScrollGT's published rows rest on its own parse of the 21 cubes, which are not
    in this container.
  - A check that every `<node` tag in a fiber was matched would make such a file fail rather than score short.
    Whether to add it is the owner's call, since it could stop a chain on a file that scores today.

## Verification

- `pytest` on `test_loop_lifecycle`, `test_shift_budgets`, `test_fiber_workflow_contracts` and
  `test_fiber_diagnostic_contracts`: 169 passed.
- Ruff, ruff format and mypy are clean on the changed files.
- The standard suite, the smoke test and the independent review are recorded below once run.
