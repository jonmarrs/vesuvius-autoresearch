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

Main has not moved since #180. There are no open pull requests. This round covers the 22:12 to 01:13 UTC firings.

## What changed

- **`cmd_trace` had no test.** Nothing checked any of these:
  - that its defaults are the configuration the 2026-10-05 registration names as the published one;
  - that each flag reaches `TraceParams` or `RelinkParams`;
  - that the JSON's `trace_parameters`, `relink_parameters` and `tracing_recipe` are what ran;
  - that `--detect-block` takes the blocked route;
  - that `--save-instances` writes the labelling that was scored.

  - `tests/test_fiber_trace_baseline.py` pins only the three improvement settings `TraceParams` defaults to
    (tangent window 1, skip steps 0, seed suppression 0).
  - The CLI's own defaults override most of `TraceParams`' and `RelinkParams`':
    - tracing: seed percentile 85 for none, continue threshold 0.5 for 0.25, maximum angle 25 for 30, minimum length
      15 for 8, claim radius 3.5 for 1.5;
    - relinking: gap 10 for 6, link angle 30 for 20, tangent angle 35 for 25.
  - The one test that called `trace` checks that bad options exit before reading data.
- **Tests** (`tests/test_fiber_workflow_contracts.py`, in the standard suite): seven cases in six new functions, and
  one more case for the existing bad-options test.
  - **The setup.** They run `bench_cli.main(["trace", …])` on a synthetic 40³ cube with two straight fibers, one
    with a 4-voxel gap that only relinking bridges.
    - Only `_load_cube` and `_fiber_prob` are stubbed.
    - Detection, tracing, relinking and scoring are the real functions, wrapped to record each call's arguments by
      name. Tracing and relinking also keep what they returned.
    - The CT handed back is a constant, not the probability, so an orientation read from the CT would show.
    - `_measurement_provenance` reads a manifest and skeleton written to the data directory.
  - **The defaults are the published configuration.**
    - The registration names seed percentile 85, continue threshold 0.5, minimum length 15, maximum angle 25, claim
      radius 3.5, tangent window 1, skip steps 0, seed suppression 0, relink gap 10 and angle 30, and tolerance 2.0.
    - The rest of the configuration is pinned too, at the values the published rows ran with:
      - every other field of `TraceParams` (step 0.7, at most 4000 steps, seed stride 2, and the unused seed
        threshold 0.5);
      - every other field of `RelinkParams` (tangent angle 35, endpoint window 4, gap-fill step 0.7, and the two
        cost weights);
      - the recipe (σ 2 and 3 for orientation, vesselness at σ 1 and 2 normalised to a maximum of 1, and
        rasterization radius 1.0).

      None of them has changed in `trace.py` or `bench_cli.py` since before the 2026-10-05 run. A deliberate change
      to any of them now has to update the test.
    - The mask threshold, 0.5, is the parser's default; the registration does not name one.
    - Each is checked on the objects `trace_fibers` and `relink_fragments` received, and on the record.
  - **Every flag reaches the run and the record.**
    - Each of the eight tracing flags and both relink flags is set off its default, with the tangent limit at the
      relink angle plus 5. The continue and mask thresholds differ, 0.45 and 0.4, so neither can stand in for the
      other.
    - What ran must equal the published configuration with those changes, and the record must equal what ran.
    - Both scores use the given tolerance. The connected-components floor is taken at the given mask threshold.
  - **The recorded recipe is what ran**, whole-volume and blocked. The values the tracer received are checked
    against the recipe computed afresh on the probability, not only the calls' arguments:
    - its directions and valid mask equal `fiber_direction` of the σ 2 and 3 Hessian;
    - its seed response equals vesselness at σ 1 and 2, divided by its maximum;
    - its response is the probability;
    - with `--detect-block 16`, both filters go through the blocked functions at that block size;
    - the saved labelling is the relinked result rasterized at the recorded radius.
  - **Blocked detection traces the same labelling** and the same rows as the whole-volume path, through the
    command.
  - **The saved labelling is the one scored.** The tracer row equals a fresh score of the saved file.
    - The record names the cube, and its stop counts are the tracer's.
    - With relinking, the gapped fiber is one instance (two in all).
    - With `--no-relink`, `relink_fragments` is not called, `relink_parameters` is null, and there are three. The
      saved labelling is then the tracer's own result, rasterized.
  - **`floors` for one cube** exits 2 without `--cube` and writes nothing. With one, it records:
    - the cube;
    - the five canonical rows;
    - the tolerance and mask threshold, in the provenance;
    - a connected-components row equal to a fresh score at both.
  - **A negative `--detect-block`** exits 2 before reading data, with the other bad options.
- **Mutants.** Each of these 41 makes at least one new test fail. On main, every one passes all 35 fiber, trace,
  tracer and orientation test files (566 passed, 24 skipped). Those that change lines main runs were run against
  them: the parser's and the two dataclasses' defaults, the two integer flags' types, and the negative-block check.
  The rest change lines no test ran.
  - in the defaults:
    - the seed percentile, the relink gap or the tolerance changed;
    - the seed stride, step or step limit changed;
    - the relink endpoint window or gap-fill step changed;
  - in the wiring:
    - the claim radius, minimum length or seed suppression not passed to `TraceParams`;
    - the continue threshold taken from the mask threshold;
    - the tangent window or skip steps parsed as a float;
    - a negative `--detect-block` accepted;
    - the tangent limit not offset by 5;
  - in the recipe:
    - the orientation or blocked seed σ changed, or recorded wrong;
    - the directions computed at the seed's σ after the right Hessian call;
    - orientation read from the CT;
    - the probability, not the vesselness, used to seed;
    - the valid mask ignored;
    - `--detect-block` taking the whole-volume route;
    - the seed normalisation dropped;
    - the filter recorded as ridges;
    - the rasterization radius changed, or recorded wrong;
  - in relinking: relinking regardless of `--no-relink`, or its parameters left out of the record;
  - in the record: the stop counts left out, or the wrong cube named;
  - in scoring:
    - the floor at a fixed 0.5, or at the continue threshold;
    - the tracer scored at the default tolerance;
    - the pre-relink labelling saved, or scored;
  - in `floors`:
    - the `--cube` check dropped;
    - the mask or tolerance fixed;
    - the provenance left out.
- **Coverage.** `bench_cli.py` goes from 73% to 93% over the standard suite's thirteen fiber, trace and orientation
  files. The added tests take about 6 seconds.

## Verified, no change needed

- **The blocked route is exact.** `tests/test_fiber_direction_tiled.py` checks it, and amendment 1 of the
  2026-10-05 registration rests on that.
  - `hessian` filters only at `gauss_sigma` and scales by σ². Its support is the Gaussian's radius of 8 at σ 2, plus
    2 for the two gradient passes, so a 16-voxel halo covers it. The halo guard asks for `4·gauss_sigma + 2`, which
    is 10 at σ 2.
  - The new end-to-end test agrees on its cube.
- **The docs' defaults are the CLI's.** `docs/FIBER_TRACING.md` gives `--tangent-window 1 --max-skip-steps 0
  --seed-nms-radius 0.0` as the default and `--tangent-window 5` as the frozen improvement. The registration's list
  matches the parser.
- **`fibers/cli.py`** is tested by a CPU round trip in a subprocess, and its GPU fallback in process
  (`test_gpu_allocation_failure_is_not_silently_retried_on_cpu`).
- **The rest of the package** is at 88–100% outside `bench_cli.py`, apart from `fibers/cli.py`, which is run as
  above. The lowest is `field_quality.py`, at 88%.

## Observations for the owner (not changed)

- **`trace --json-out` records no checksum of the instances it saves.** `score --json-out` records
  `instances_sha256`.
  - `run_tracer_rescore.sh` writes `{cube}_instances.npy` beside `{cube}_trace.json`. Nothing in the record ties
    the two together, beyond rescoring the file and comparing the rows.
  - The analyses rescore the saved instances, so no published figure depends on the JSON's rows.
- **One floor, two names.** `trace` and `score --with-floors` call the connected-components floor
  `floor: connected components`. `floors` and every consumer of the all-cubes report call it
  `floor_connected_components`. No script reads the first form. A test asserts it, and the July report
  `reports/fiber_connectivity_eval_s1.json` uses it.
- **The record lists `seed_threshold` 0.5,** which `trace_fibers` does not use when `seed_percentile` is set, as it
  always is from the CLI.
- **`bench_cli.py`'s remaining untested lines:**
  - `_load_cube`, which needs the TIFFs;
  - `_fiber_prob`'s refusals of a bad patch, device or output shape, and its rejection of a corrupt cache;
  - `fetch`'s refusal of a bad stem or a missing cube, its skips, and its empty and short download checks;
  - `score`'s refusal of instances of the wrong shape.

## Verification

- `pytest tests/test_fiber_workflow_contracts.py`: 84 passed, 8 of them new. The mutants above each fail one, and
  were run on a copy of the tree.
- Ruff 0.9.10 `check` and `format` are clean on the test file, which was formatted before. `bench_cli.py` and
  `trace.py` are unchanged.
- **The standard suite** on the first commit (`5c507bf0`), with the locked-package overlay, gave 2765 passed. That
  is main's 2758 plus the seven new cases. The same nine villa-file failures as on main remain (six
  `label_curation`, three `geometry_handoff`). The smoke test gave 9 of 11 passed and 2 skipped, as on main.
- **Independent review** of the first commit, in a worktree without villa or ScrollGT. It found nothing blocking.
  - It confirmed:
    - every listed mutant is killed, and the parser-default ones pass main's 35 files;
    - the counts, coverage figures and halo arithmetic;
    - the registration's constants;
    - the observations.
  - Its should-fix findings:
    - the recipe test checked the filters' arguments, not what the tracer received, so seeding from the
      probability, directions from the wrong Hessian, and a changed or misrecorded rasterization radius or filter
      label passed;
    - the continue and mask thresholds shared a value in both tests;
    - only the ten flagged fields were pinned, so the seed stride, step, step limit, endpoint window and gap-fill
      step could drift;
    - the list of untested lines was wrong;
    - the baseline test's pins were understated.
  - Its nits:
    - the incomplete list of overridden defaults;
    - the mask threshold called registered;
    - 89% for 88%;
    - "nothing reads" the first floor name;
    - the test count;
    - the call-order assumptions;
    - the fixture's name;
    - the argument lists' layout.

  The should-fix findings and the nits are fixed. Every mutant it reported surviving is among the 41 above: the
  twelve behind its should-fix findings, and the six it called minor (the stop counts, the cube, the two integer
  flags, the valid mask, and a negative block size).
