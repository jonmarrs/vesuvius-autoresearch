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
  - `scripts/epoch_boundary_overhead.py` and `scripts/cycle_length_gain.py` read each cycle's step count from it. All
    six of their committed reports name it among their sources (`run_log`).
  - What it holds since the last rotation exists nowhere else. The loop itself deletes the previous `run.log.old` at
    each rotation; `run.log.old` is tracked, so only the rotations someone committed survive.
  - Run during a cycle, it also unlinks the file the run is writing, so that cycle's whole output is lost, a
    successful run's step count included. If the run then crashes, the loop finds no `run.log`: it records the crash
    without its last line and cannot tell an out-of-memory crash.
  - **Change:** `make clean` no longer names `run.log`, and its help says it keeps it. A comment above the target
    gives the reason.
  - The files it still removes (`shift_stdout_*.log`, `dayshift_stdout.log`, `nightshift_stdout.log`,
    `/tmp/reeval.log`, `/tmp/fiber_gen.log`) appear only in the Makefile, now and in the repository's history
    (`git log -S`). Nothing here writes them. The two under `/tmp` are shared by every checkout on the machine.
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
  (the 2026-10-21 night-budget review leaves it to the owner). `unsupervised_runs_reason`'s docstring said it stops
  "a loop's own run"; it now names the ablation's too.
- **Test** (`tests/test_loop_lifecycle.py`, in the standard suite). It reads the commands `make -n` would run for
  `clean` and `clean-cache`, so continuation lines, comments, variables and prefixes are as make reads them.
  - Any command but `rm -f` or `find .` fails it.
  - So does a path or `find -name` pattern that would remove the loop's runtime state (the file's
    `LOOP_RUNTIME_STATE`), `run.log.old`, `results.tsv` or the sprint logs. That covers a name, a glob, or anything
    under a directory.
  - It skips where `make` is not installed.
  - It fails with the old recipe. All 22 of the independent review's harmful mutants fail it, among them:
    - a continuation line indented with spaces;
    - a comment or blank line before `rm -f run.log`;
    - `sprint_logs/*.md`, or `rm -rf sprint_logs/`;
    - `"run.log"`, `$(CURDIR)/run.log`, or `$(LOGS)` with `LOGS = run.log`;
    - `find . -name "*.log" -delete`, and `git clean -fX`;
    - `*.tsv`, `*.lo?`, `*.log`, `run.log*`.
  - Two of its mutants still remove only the old launchers' logs, and pass: `$(RM)`, and a `-` prefix.

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

- **`parse_nml` reads the NML with regular expressions, and several malformed files parse without an error.** The
  independent review reproduced each of these on small files:
  - a node with non-integer coordinates, single-quoted attributes, or `id` not first is dropped, with its edges;
  - an edge with another attribute, another attribute order or `></edge>` is dropped;
  - an unclosed `<thing>` takes in the next fiber, a merge that is not in the annotation;
  - a self-closing `<thing id="9"/>` takes the next fiber's body under its own id;
  - a commented-out node is read as a node.

  The NML here parses completely, and ScrollGT's published rows rest on its own parse of the 21 cubes, which are not
  in this container. Two fixes are possible:
  - compare the raw counts of `<node`, `<edge`, `<thing` and `</thing>` with what was parsed;
  - parse with `xml.etree`, which handles quoting, attribute order and comments, and raises on an unclosed tag.

  Either would make such a file fail rather than score wrong. Whether to add one is the owner's call, since it could
  stop a chain on a file that scores today.
- **`scripts/dev_worktree.sh remove`** runs `git worktree remove`, which also deletes that worktree's ignored files.
  A loop run in a development worktree would leave its `run.log`, `results.tsv` and `autoresearch.out` there. The
  data links are unlinked first, so the main checkout's data is safe.

## Verification

- `pytest` on `test_loop_lifecycle`, `test_shift_budgets`, `test_fiber_workflow_contracts` and
  `test_fiber_diagnostic_contracts`: 169 passed.
- Ruff, ruff format and mypy are clean on the changed files.
- **The standard suite** on the first commit (`48e11bcd`) ran as on main: 2690 passed, with the same 42 failures and
  2 errors, all environmental. The 7 passes more than the last review's run are its 6 doc tests, added after that run,
  and this review's test. The smoke test gave 9 of 11 passed and 2 skipped, as on main.
- **Independent review** of the first commit found nothing blocking. It confirmed:
  - each statement about `run.log` against the loop's code, and that no script deletes a loop record but the
    loop's own rotation;
  - the cube counts against the held-out registration and both chains;
  - `LONGEST_RUN_SECONDS`' comment;
  - the configs, the NML parse and the doc-reference audit.

  It reran the tests outside the suite in its own worktree, whose `villa/` is empty: the same 1618 tests, with 3 more
  failures, each for want of villa.

  Its should-fix findings:
  - the test missed realistic regressions;
  - the `parse_nml` observation named only one of its silent failures;
  - this section's placeholder.

  Its nits:
  - the old logs' history;
  - which reports name `run.log`;
  - the loop's own rotation;
  - the test's placement;
  - `unsupervised_runs_reason`'s docstring;
  - `dev_worktree.sh remove`.

  All are addressed above.
