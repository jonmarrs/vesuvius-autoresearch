# Design and architecture review — the fiber bench's `trace` command, which no test ran

Date: 2026-10-21. Baseline: `27a5ed8d` (main after #180).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `src/vesuvius_autoresearch/fibers/`, the lines the tests do not run. Over every fiber, trace and tracer test
in `tests/`, the package is at 88%. `cli.py`, at 23%, is run in a subprocess by `tests/test_fibers_cli.py`, which
coverage does not follow, so it is not a gap. The gap is `bench_cli.py`, at 73%. What it misses is:
- **all of `cmd_trace`**, lines 397–513;
- **`cmd_floors` for one cube**, lines 318–345.

`bench_cli trace` is the command behind every published row of our tracer. That covers
`docs/preregistration/2026-10-05_tracer_rescore.md` (`repro/fibers/run_tracer_rescore.sh` runs it on all eleven
cubes), the held-out split, and the instances finding 94 and the octant crops score.

Main has not moved since #180. There are no open pull requests. This round covers the 22:12 UTC firing.

## What changed

- **`cmd_trace` had no test.** Nothing checked any of these:
  - that its defaults are the configuration the 2026-10-05 registration names as the published one;
  - that each flag reaches `TraceParams` or `RelinkParams`;
  - that the JSON's `trace_parameters`, `relink_parameters` and `tracing_recipe` are what ran;
  - that `--detect-block` takes the blocked route;
  - that `--save-instances` writes the labelling that was scored.

  `tests/test_fiber_trace_baseline.py` pins only `TraceParams.tangent_window == 1`, and the CLI's own defaults
  override `TraceParams`' (seed percentile 85 for none, minimum length 15 for 8, claim radius 3.5 for 1.5). The one
  test that called `trace` checks that bad options exit before reading data.
- **Tests** (`tests/test_fiber_workflow_contracts.py`, +7, in the standard suite).
  - **The setup.** They run `bench_cli.main(["trace", …])` on a synthetic 40³ cube with two straight fibers, one
    with a 4-voxel gap that only relinking bridges.
    - Only `_load_cube` and `_fiber_prob` are stubbed.
    - Detection, tracing, relinking and scoring are the real functions, wrapped to record each call's arguments by
      name.
    - The CT handed back is a constant, not the probability, so an orientation read from the CT would show.
    - `_measurement_provenance` reads a manifest and skeleton written to the data directory.
  - **The defaults are the registered configuration.**
    - Tracing: seed percentile 85, continue threshold 0.5, minimum length 15, maximum angle 25, claim radius 3.5,
      tangent window 1, skip steps 0, seed suppression 0.
    - Relinking: gap 10 and angle 30. Tolerance 2.0 and mask threshold 0.5.
    - Each is checked on the objects `trace_fibers` and `relink_fragments` received, and on the record.
  - **Every flag reaches the run and the record.**
    - Each of the eight tracing flags and both relink flags is set off its default, with the tangent limit at the
      relink angle plus 5.
    - The record must equal `asdict` of what ran.
    - Both scores use the given tolerance. The connected-components floor is taken at the given mask threshold.
  - **The recorded recipe is what ran**, whole-volume and blocked:
    - orientation from the fiber probability at σ 2 and 3;
    - the seed response at σ 1 and 2;
    - with `--detect-block 16`, both through the blocked functions at that block size;
    - the seed response normalised to a maximum of 1.
  - **Blocked detection traces the same labelling** and the same rows as the whole-volume path, through the
    command.
  - **The saved labelling is the one scored.** The tracer row equals a fresh score of the saved file.
    - With relinking, the gapped fiber is one instance (two in all).
    - With `--no-relink`, `relink_fragments` is not called, `relink_parameters` is null, and there are three.
  - **`floors` for one cube** exits 2 without `--cube` and writes nothing. With one, it records:
    - the cube;
    - the five canonical rows;
    - the tolerance and mask threshold, in the provenance;
    - a connected-components row equal to a fresh score at both.
- **Mutants.** Each of these makes at least one new test fail. On main, every one passes all 35 fiber, trace, tracer
  and orientation test files (566 passed, 24 skipped). The three in the defaults were run against them; the rest
  change lines no test ran.
  - in the defaults: the seed percentile, the relink gap or the tolerance changed;
  - in the wiring:
    - the claim radius, minimum length or seed suppression not passed to `TraceParams`;
    - the tangent limit not offset by 5;
  - in the recipe:
    - the orientation or blocked seed σ changed, or recorded wrong;
    - orientation read from the CT;
    - `--detect-block` taking the whole-volume route;
    - the seed normalisation dropped;
  - in relinking: relinking regardless of `--no-relink`, or its parameters left out of the record;
  - in scoring:
    - the floor at a fixed 0.5;
    - the tracer scored at the default tolerance;
    - the pre-relink labelling saved, or scored;
  - in `floors`:
    - the `--cube` check dropped;
    - the mask or tolerance fixed;
    - the provenance left out.
- **Coverage.** `bench_cli.py` goes from 73% to 92% over the standard suite's thirteen fiber, trace and orientation
  files. The added tests take about 9 seconds.

## Verified, no change needed

- **The blocked route is exact.** `tests/test_fiber_direction_tiled.py` checks it, and amendment 1 of the
  2026-10-05 registration rests on that.
  - `hessian` scales by σ² but filters only at `gauss_sigma`, so a 16-voxel halo covers the support. The halo
    guard asks for `4·gauss_sigma + 2`, which is 10 at σ 2.
  - The new end-to-end test agrees on its cube.
- **The docs' defaults are the CLI's.** `docs/FIBER_TRACING.md` gives `--tangent-window 1 --max-skip-steps 0
  --seed-nms-radius 0.0` as the default and `--tangent-window 5` as the frozen improvement. The registration's list
  matches the parser.
- **`fibers/cli.py`** is tested by a CPU round trip in a subprocess, and its GPU fallback in process
  (`test_gpu_allocation_failure_is_not_silently_retried_on_cpu`).
- **The rest of the package** is at 89–100% outside `bench_cli.py`, apart from `fibers/cli.py`, which is run as
  above.

## Observations for the owner (not changed)

- **`trace --json-out` records no checksum of the instances it saves.** `score --json-out` records
  `instances_sha256`.
  - `run_tracer_rescore.sh` writes `{cube}_instances.npy` beside `{cube}_trace.json`. Nothing in the record ties
    the two together, beyond rescoring the file and comparing the rows.
  - The analyses rescore the saved instances, so no published figure depends on the JSON's rows.
- **One floor, two names.** `trace` and `score --with-floors` call the connected-components floor
  `floor: connected components`. `floors` and every consumer of the all-cubes report call it
  `floor_connected_components`. Nothing reads the first form.
- **The record lists `seed_threshold` 0.5,** which `trace_fibers` does not use when `seed_percentile` is set, as it
  always is from the CLI.
- **`bench_cli.py`'s remaining untested lines:**
  - `_load_cube`, which needs the TIFFs;
  - `_fiber_prob`'s refusals and its cache rejection;
  - `fetch`'s listing filter and size checks;
  - `score --with-floors`;
  - two of `main`'s range errors.

## Verification

- `pytest tests/test_fiber_workflow_contracts.py`: 83 passed, 7 of them new. The mutants above each fail one, and
  were run on a copy of the tree.
- Ruff 0.9.10 `check` and `format` are clean on the test file, which was formatted before. `bench_cli.py` is
  unchanged.
- VAL146
