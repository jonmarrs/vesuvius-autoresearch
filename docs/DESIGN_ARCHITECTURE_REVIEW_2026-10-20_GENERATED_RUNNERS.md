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
- **`proofreader_config.json` is ignored.** `launch_proofreader.py` writes it into the working directory on every
  launch, with the volume and prediction paths given. It was the one generated file there that git did not ignore.
  The loop's promotion commit takes only its own files, so the file was never committed; it showed as untracked.
- **Test** (`tests/test_villa_baselines_launchers.py`): for each launcher, the runner it writes names the launcher's
  path, no copy is tracked, and where the launcher writes it is ignored. It needs no villa checkout.
  - Each of these is caught: the old docstring, a tracked copy restored, and the ignore line removed.
  - The file's other launcher tests need villa or a LeJEPA checkpoint, and fail here as on main.

## Verified, no change needed

- **The tests outside the standard suite**, on main: 1441 passed and 76 skipped. All 16 failures and 21 errors are
  environmental:
  - 19 errors: the spiral probes cannot find villa's spiral modules;
  - 2 errors and 5 failures: `s3fs` is not installed;
  - 5 failures: `local_data/` is absent;
  - 2 failures: the villa launchers;
  - 2 failures: the submodule preflight, which wants villa's gitlink;
  - 1 failure: the doc-reference audit, which flags villa paths and a checkpoint under the ignored `models/`;
  - 1 failure: `correlate_geometry_ink`, which needs the owner's `spiral_out/`.

  The skips are each gated on missing data, checkouts, git, or a GPU.
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
  and the skeleton's iterated update. `BettiLoss` is retired and raises. Production has both off.
- **The uncertainty export** normalises binary entropy by its maximum, ln 2.
- **The ensemble predictor.** Each CT-only member of a mixed-depth ensemble sees the window it would see alone at the
  same `--z`, as predict.py defines `--z`. Ridge members must share their depth.
- **The README** (15- and 60-minute budgets; decay of ×0.95, floor 1, +1 per promotion) and **`docs/program.md`**
  (`config.json` with `enforce_prize_gates` off; the AP-lift gate at > 1.02) agree with the code.

## Observations for the owner (not changed)

- **`core/villa_inference.VillaTTAWrapper` is used by nothing**; prediction mirrors in-plane in `core/inference.py`.
  Used as it stands, it would fail or mislead:
  - a plain call to the production wrapper returns the 2-D ink map alone, so the wrapper's default multi-task
    concat, which unpacks three outputs, would raise;
  - whether villa's TTA un-flips a 2-D output correctly for a 5-D input cannot be checked without villa.
- **The uncertainty export's threshold**, 0.2 of the maximum entropy, marks every pixel with a probability between
  0.031 and 0.969. So on most tiles it is close to the whole tile.

## Verification

- `pytest tests/test_villa_baselines_launchers.py -k generated_runner`: 2 passed. Each mutant above makes its case
  fail.
- Ruff, ruff format and mypy are clean on the changed files, the test included.
- The standard suite does not import the launchers or their test, and imports no deleted file. Nothing in the
  repository refers to the deleted paths.
