# Design and architecture review — the owner's #390, #393, #395 and #399

Date: 2026-11-12. Baseline: `723e0ea` (main after #404).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the hourly firings from 03:12 UTC on 2026-11-10 to 22:12 UTC on 2026-11-12. It was interrupted
several times and is narrower than earlier rounds; the last section says how. The owner merged four PRs on 11-10:
- **#393** (03:42 UTC) is finding 108: suppressing a block's copy of a fiber that a neighbouring block also fitted.
  The decision is `SUPPORTED`.
- **#395** (05:20 UTC) publishes the proofreader's uncertainty masks whole, through `scripts/uncertainty_artifacts.py`.
- **#390** (11:59 UTC) measures the shift between an ink label canvas and its tifxyz grid, and resamples onto the grid.
- **#399** (15:55 UTC) replaces the research strategy.

The owner merged five more PRs while this round was interrupted: #396, #403, #404, #406 and #407. They are in this
branch's base, and their review is left to the next round.

## What changed

### #395: replacing a directory that is not a mask store is refused by name (`scripts/uncertainty_artifacts.py`)

With `overwrite=True`, an existing directory that holds no Zarr store made Zarr raise its own error, "nothing found at
path ''". That message names no path, and it follows the module's advice to "use a new path or overwrite=True". The
error is a ValueError in Zarr 2.18, so callers that catch ValueError already caught it, and the directory was left as
it was. `validate_destination` now reports it as it reports a Zarr group: "existing uncertainty output must be a bare
3D Zarr array", with the path. The new test fails on the merged code.

No registration covers the module. `scripts/active_learning_sampler.py` and `scripts/inference/predict.py` use it.

### #395: four guards no test reached (`tests/test_uncertainty_handoff.py`)

This round made 18 mutants of the module. #395's tests killed 12. Four new tests (nine cases) kill four of the six
survivors, two close variants and the reverted fix. Each passes on the module and fails with its mutant:
- **Replacement is for a mask store only.** A plain directory, a Zarr group and a two-dimensional array are each
  refused under `overwrite=True` and left as they were.
- **The voxel limit admits a mask of exactly that size** and refuses one voxel more.
- **The voxel limit must be a positive integer.** 0, −1, True, 4.0, "4" and None are refused before anything is
  written.
- **A masked array is refused.**

The other two survivors are not worth a test:
- writing all-zero chunks stores the same mask in more files;
- without the "://" test, the scheme pattern on the next line still refuses a path that starts with a scheme.

### #393: finding 108's guards tested without the owner's files (`tests/test_afv_generator_cross_block_duplicates.py`)

#393's own test of the catalogue gate needs the owner's villa clone, so it skips elsewhere. On this machine the two
test modules gave 20 passed and 1 skipped. Ten new test functions (26 cases) replace zarr, ScrollGT, villa and the
generator with stand-ins, so they run anywhere:
- **The decision rule at its bars and in the table's order** (nine cases).
  - P2 is the median, not the mean.
  - P3 fails at 1.07 times the trim's merges.
  - P4 fails at 0.72 times the trim's share and holds at exactly 0.7.
  - An ERLpen that did not move is not "higher".
  - A P1 or P3 miss outranks a P2 or P4 miss, and a failed gate outranks both.
- **One cube's failed gate means no verdict.**
- **The verdict step writes the record once, with the zone.** A second run refuses and leaves the record as it was.
- **Both arms run by default.** The launcher passes no `--variants`, and a run of one arm writes no result.
- **The catalogue gate on a stand-in villa.** It accepts the patch against the named revision, not the clone's
  HEAD. It names a change outside the function, a changed function body, a missing or doubled call, and villa's
  comment left as it was.
- **The run on a 16³ stand-in cube.** Both arms are trimmed with the cube as the read box. Only `trim+dup` uses
  the patched catalogue, and the module's own catalogue is put back afterwards.
- **Each of the cube's five gate checks and the zone's four is recorded** with the result.

Two sets of mutants were run against these tests:
- **A helper's 25 mutants of the script.** In its run, #393's tests killed 2. I reran all 25 against the new tests,
  and all 25 fail.
- **My own 17 mutants of the decision rule and the catalogue gate.** #393's tests kill 11 here and the new tests
  kill 16. The last one changes P2 from "at least 0.03" to "above 0.03". No tested input lands on exactly 0.03.

## Verified, no change needed

- **Finding 108's decision recomputes.** `verdict(record["cubes"])` equals the stored verdict. Every margin is
  clear of its bar:
  - P1: ERLpen at tolerance 4 up on 8 of 8, against at least 6;
  - P2: median gain 0.0571 (0.0251 to 0.1016), against at least 0.03;
  - P3: merges 384, against a limit of 405.3 (1.05 times 386);
  - P4: median duplicated share 0.0319, against a limit of 0.0728 (0.7 times 0.104).
- **Every figure quoted from it recomputes from the records.** This covers the report, the villa draft, the prize
  draft and the strategy:
  - the gains at both tolerances, the merges and the shares;
  - the zone's rows (share 0.0523 to 0.0172, merges 82 to 80);
  - the one-block ratios: main 0.703 to 0.923, the trim 0.822 to 0.963, both changes 0.905 to 1.026;
  - the patch's 18 added and 2 removed lines in villa's `catalog.py`.
- **The `trim` arm reproduces finding 106.** On all eight cubes its rows equal finding 106's `real/patched` rows,
  which is the gate's fourth check.
- **The order of events.** The registration (241b0c8, 13:56 PST on 11-09) precedes the results (27ac328, 15:48 PST).
  The script and its launcher are unchanged since the registration.
- **#395's refusals, each probed.**
  - A 0/255 mask is stored as float32 0/1, with its count in the attributes.
  - An existing store is refused without `overwrite=True` and replaced with it.
  - Refused: a file or a symlink as the destination; a destination that is a source or lies inside one; NaN, mixed
    1 and 255, complex or list masks; non-finite metadata.
  - An all-zero mask is published with status `EMPTY`.
- **#399's bindings.** The 92 tests in the ten modules bound to `docs/RESEARCH_STRATEGY.md` pass, and its links and
  anchors resolve.
- **#399's prize terms, against villa main of 11-12.** The owner asked for a prize roadmap during this round, so the
  prize page was read again. The strategy's three quotations are still there. So are the First Letters terms:
  \$50,000 a scroll, at most 8 more scrolls, deadline June 25, 2027. The "help wanted" label still has no open issue.
- **#390's two test modules pass**, on `723e0ea` and on this branch. Its code was not reviewed (see the last section).

## Observations for the owner (not changed)

- **#399: the award record supports one of three figures.** The strategy gives July \$0, August \$0 and September
  \$250, and links `docs/PROGRESS_PRIZE_AWARDS.md` for them. That file records only September's award.
- **#399: `docs/research_plan.md` says "Updated November 5"** above a paragraph dated November 10. Its text suggests
  this is deliberate.
- **#399: most of the strategy's claims are external.** They concern Villa issues, the community catalogue and other
  contributors' repositories, and were not checked, apart from the prize terms above.
- **#393: the owner's catalogue-gate test runs only beside the owner's villa clone.** The stand-in test above covers
  the same checks elsewhere.
- **A fresh container cannot run `uv sync --frozen`.** The host that serves the locked `torch==2.9.1+cu128` wheel is
  outside this environment's network allowance. See the last section.

## Verification

- **The touched modules pass.**
  - `test_uncertainty_handoff.py` gives 63 passed, against 54 as merged.
  - Finding 108's two modules give 46 passed and 1 skipped, against 20 passed and 1 skipped as merged.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    three changed Python files.
  - Mypy is clean over the whole repository: 970 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 216 modules give the same 171 failing ids on `723e0ea` and on this branch. This
  environment has no villa checkout (see below).
- **The test modules outside the suite.** The 249 modules give the same 23 failing ids on `723e0ea` and on this
  branch.
- **The doc audit**, run alone, lists the same unresolved references on `723e0ea` and on this branch. It checks
  2,274 path and 859 commit references, against 2,264 and 858 on `723e0ea`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

## A note on this round's work

- **The round was interrupted five times by the usage limit and once by a new container.** Three helper agents
  were started for #390, #393 and #395. Only the #393 helper left usable work: the tests above, which I read in
  full and reran. The rest of the review is mine, and narrower than earlier rounds: a sample of mutants, not a
  sweep.
- **#390 was not reviewed in depth.** #406 and #407 changed the same module, `repro/sota_data/canvas_shift.py`,
  after it. The next round should review the three together, with #396, #403 and #404.
- **The environment was rebuilt on 11-12, so its baselines differ from earlier rounds'.**
  - The locked `torch==2.9.1+cu128` wheel could not be downloaded. Every package was installed at its locked
    version, except that torch 2.9.1 came from PyPI.
  - The villa submodule is not checked out, so tests that read villa fail or skip here. Of five failing suite
    modules sampled, three stop at a file missing under `villa/`; the other two fail on a launcher's exit status,
    which I did not trace. Earlier rounds' lists (70 and 34 ids) came from a machine with villa present and do
    not apply.
  - Each comparison above is between `723e0ea` and this branch in this one environment.
- **The owner asked for a prize roadmap during this round.** It is in this PR as
  `docs/PRIZE_ROADMAP_2026-11-12.md`. It is a proposal and does not replace the strategy.
