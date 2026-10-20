# Design and architecture review — generated runners in git, and the tests outside the suite

Date: 2026-10-20. Baseline: `d1ed1f2f` (main after #154).
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- the modules on the loop's path that no review had covered:
  - `scripts/launch_proofreader.py`, which the loop names at the end of every night shift;
  - `fibers/skeleton_io.py`, `detector/model_resenc.py` and `core/villa_inference.py`;
  - the topology losses `train.py` can switch on;
  - predict.py's active-learning export, which the loop's benchmark runs every 5 cycles;
  - the ensemble predictor;
- the README's and `docs/program.md`'s account of the loop;
- the 192 test files outside the standard suite, run on main.

The owner's open #153 (finding 93) is not touched.

## What changed

- **Two generated runners were tracked in git, stale.**
  - `launch_gp_winner.py` and `launch_finetune_lejepa.py` write a runner script on every run, with this machine's
    paths, to `scripts/_gp_winner_runner.py` and `scripts/_finetune_lejepa_runner.py`. Both are ignored.
  - The June reorg (`a0a1b10b`) committed one copy of each under `scripts/training/`. Each is the launcher's
    output on the owner's machine, identical after formatting, with its villa path in it.
  - Nothing runs these copies: the launchers, and the markers in `reports/`, name the copies in `scripts/`. Each
    copy's docstring names the launcher's path before the reorg.
  - **Change:** both copies are removed. The docstring each launcher writes into its runner now names the
    launcher's own path, `scripts/training/…`.
- **`proofreader_config.json` is untracked and ignored.**
  - `launch_proofreader.py` writes it into the working directory on every launch, with the volume and prediction
    paths it is given. It runs only beside `villa/`, so that is the repository root.
  - Three May commits had swept a copy in (`dd742032`, `714624ef`, `2d7cf5fe`): a config for
    `predictions/pred_10_1000_1000_64x64_ink.zarr`. Nothing reads it; the launcher only writes it. So every launch
    showed the file as modified.
  - It is removed from the index, and ignored. A checkout that pulls this loses its copy, which the next launch
    writes again.
  - The first commit of this PR only added the ignore line, which leaves a tracked file tracked. The independent
    review caught it.
- **Tests** (`tests/test_villa_baselines_launchers.py`). They need no villa checkout.
  - For each launcher: the runner it writes names the launcher's path, no file of that name is tracked anywhere,
    and where the launcher writes it is ignored.
  - The same for `proofreader_config.json`.
  - Each of these is caught:
    - the old docstring;
    - a tracked copy restored, at its old place or nested deeper;
    - the config tracked again;
    - an ignore line removed.

    A test file whose name merely ends in `_gp_winner_runner.py` is not caught.
  - They skip without git, or in a checkout that is not this repository's own. An unpacked copy inside another
    repository would otherwise be checked against that one.
  - The file's other launcher tests need villa or a LeJEPA checkpoint, which this container lacks.

## Verified, no change needed

- **The tests outside the standard suite**, on main, in this container's baseline checkout: 1441 passed and 76
  skipped. All 16 failures and 21 errors are environmental:
  - 19 errors: the spiral probes cannot find villa's spiral modules;
  - 2 errors and 5 failures: `s3fs` is not installed;
  - 5 failures: `local_data/` is absent;
  - 2 failures: the villa launchers;
  - 2 failures: the submodule preflight, which wants villa's gitlink;
  - 1 failure: the doc-reference audit, which flags villa paths and a checkpoint under the ignored `models/`;
  - 1 failure: `correlate_geometry_ink`, which needs the owner's `spiral_out/`.

  The skips are each gated on missing data, checkouts, git, or a GPU. The counts depend on the checkout. In the
  independent review's worktree, whose `villa/` is empty, 19 tests failed. The extra 3 also want villa, among them
  two more launcher tests. The 21 errors were the same.
- **The proofreader command the loop prints** names
  `reports/pred_<z>_1000_1000_64x64_ink.zarr`.
  - predict.py's width and height default to the checkpoint's patch size (64).
  - It writes beside `--output_img`, which the loop sets in `reports/`.
- **`skeleton_io`**:
  - its node pattern takes WebKnossos's attribute order;
  - an edge to a missing node is dropped with the edge;
  - the cube origin is parsed in one place, z-y-x as the file name gives it.
- **`model_resenc`** wraps the installed ResidualEncoderUNet in 2-D, with depth as channels.
- **`cldice_loss`** follows Shit et al.'s reference: soft erosion as the minimum of two 1-D pools, then dilation,
  and the skeleton's iterated update. It takes clDice per sample and averages over the batch, where the reference
  sums over the batch first. `BettiLoss` is retired and raises. Production has both off.
- **The uncertainty export** normalises binary entropy by its maximum, ln 2.
- **The ensemble predictor.** Each CT-only member of a mixed-depth ensemble sees the window it would see alone at the
  same `--z`, as predict.py defines `--z`. Ridge members must share their depth.
- **The README** (15- and 60-minute budgets; decay of ×0.95, floor 1, +1 per promotion) and **`docs/program.md`**
  (`config.json` with `enforce_prize_gates` off; the AP-lift gate at > 1.02) agree with the code.

## Observations for the owner (not changed)

- **`core/villa_inference.VillaTTAWrapper` is used by nothing**; prediction mirrors in-plane in `core/inference.py`.
  Used as it stands, it would fail or mislead:
  - with `is_multi_task=True`, its default concat unpacks the model's output into three heads. A plain call to the
    production wrapper returns the 2-D ink map alone, so the unpacking runs along the batch. It raises unless the
    batch is 3, and at 3 it would take three samples for three heads;
  - whether villa's TTA un-flips a 2-D output correctly for a 5-D input cannot be checked without villa.
- **The uncertainty export's threshold**, 0.2 of the maximum entropy, marks every pixel with a probability between
  0.031 and 0.969. So on most tiles it is close to the whole tile.

## Verification

- `pytest tests/test_villa_baselines_launchers.py -k "generated_runner or proofreader"`: 3 passed. Each mutant
  above makes its case fail.
- Ruff, ruff format and mypy are clean on the changed files, the test included.
- The standard suite does not import the launchers or their test, and imports no deleted file. Nothing in the
  repository refers to the deleted paths. On the first commit (`d1ed33f5`) it ran as on main: 2672 passed, with the
  same 42 failures and 2 errors, all environmental. The smoke test gave 9 of 11 passed and 2 skipped.
- **Independent review** of the first commit. Its blocking finding was the tracked `proofreader_config.json`
  (above). It confirmed:
  - the deleted runners are referenced nowhere, and regenerate byte-identical after formatting;
  - the test passes with an empty `villa/`, from a worktree, and skips without git.

  Its should-fix findings:
  - the `VillaTTAWrapper` note;
  - the tallies' dependence on the checkout.

  Its nits:
  - the pathspec, which also matched a test file of that name;
  - the ignore comment;
  - the skip's breadth;
  - clDice's reduction.

  All are addressed above.
