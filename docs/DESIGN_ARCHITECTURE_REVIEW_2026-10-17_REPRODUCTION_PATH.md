# Design and architecture review — the reproduction path

Date: 2026-10-17. Baseline: `ead6176a` (main after #105). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the documents and files a newcomer reproduces from, which no earlier review covered: `REPRODUCE.md`, the
`Dockerfile`, `METHOD.md` and `SUBMISSION.md`. Each command they give was run here where it can run without data
or a GPU, and checked against the code otherwise. `CONTRIBUTING.md` and the README's Quick start were checked for
consistency with them: the README's is current, and `CONTRIBUTING.md` lacked only the submodule step.

## What changed

- **`REPRODUCE.md` §2: the preflight needs the training volumes' label files.**
  - It said `train.py --smoke` needs "no data download". Since 2026-10-14 the preflight first resolves each
    configured training volume's label file, so it fails fast when one is missing.
  - Run here without data: `PREFLIGHT FAILED: no label file for training volume
    local_data/PHercParis2Fr47/surface_volume.zarr ...`, exit 1.
  - The section now says it needs those label files, not the volumes. With only an `inklabels.png` beside a
    volume that does not exist, it passes. (A pseudo-label does not substitute under `config.json`: with
    `use_confidence_weight` off it is refused.) The README's Quick start already ran it "with the data in place".
- **`REPRODUCE.md` §7–§8: the loop's tracked log is `history.tsv`.**
  - §7 told the reader to inspect `results.tsv`, "retained for provenance". That file is gitignored and local, with
    one row per promotion. The tracked log is `history.tsv`: one row per `train.py` run that finished validation,
    except experiment runs with `checkpoint_out` (the noise probe's and the ablation's).
  - Neither file has val_f1, the metric that decides promotion. §7 now points to `sprint_logs/`, the latest
    `run_result.json` and the README's "Tracking progress", which already said so.
  - §8 said every cycle appends to `results.tsv`, and ran the loop bare. It now scores the incumbent first and starts
    the loop with `./start.sh`, and names the README's prerequisites: the loop starts only on an incumbent scored
    under the current protocol, and exits at the end of its shift.
- **`REPRODUCE.md`, smaller.**
  - It gave Python "3.10/3.11"; `pyproject.toml` requires `>=3.10,<3.11`.
  - §1 now checks out the villa submodule, as the README's Quick start does.
  - §4's test counts (30 and 60 passed, 2026-09-06) are re-run: 206 passed and 1 skipped, and 106 passed.
  - §3's smoke result, from 2026-06-04, depends on the environment, and a note now says how. The two dataloader
    tests skip without data, and `augmentations_bg2`, listed as skipped, passes with villa checked out. Re-run here
    (villa at the pin, no data) it is also 9 passed and 2 skipped, but with the dataloader tests as the skips.
- **`METHOD.md`'s search loop described an older loop.**
  - Step 1 listed four architectures as sampled. The loop's architecture arm has been pinned to `resenc_unet`
    since 2026-06-09, before the file was last edited, and so are the other fields a warm start must match.
  - `build_model` still dispatches all four, but two cannot build at the villa pin. `resnet3d` (ResNet3D-101) and
    `i3d` (Inception-I3D) import `models.resnetall` and `models.i3dallnl` with `villa/ink-detection` on the path.
    At the pin that directory holds only `optimized_inference/`; villa moved its `models/` to
    `deprecated/ink-detection/`. So both raise `ImportError ... not found in villa submodule`.
  - `resnet3d_decoder` imports from `ink-detection/optimized_inference/`, which the pin has. Step 1 now names the
    two exceptions.
  - Steps 4–5 and the `val_bpb` bullet had promotion on `val_bpb` and topology. Since 2026-07-11 it is `val_f1`
    beating the incumbent by more than 0.03 with an AP-prevalence lift above 1.02, on the same validation protocol
    and inputs, and `val_bpb` decides nothing.
  - Step 3 gave "≈60 minutes": that is the night shift. The day shift's cycles are 15 minutes.
  - Step 5 said every cycle is appended to `results.tsv`.
  - All are corrected, with a dated note.
- **The Docker build context, and what the image holds.**
  - There was no `.dockerignore`, so `docker build .` sent the whole working tree as its context. On this checkout
    that is 9.1 GB besides `.git` (3.3 GB), almost all of it `.venv`. The image copies only the top-level `*.py`
    files, `pyproject.toml`, `uv.lock`, `README.md` and `SUBMISSION.md`.
  - A new allowlist `.dockerignore` excludes everything else.
  - The `Dockerfile`'s header now says what the image holds: none of `src/`, `scripts/`, `repro/` or `tests/`, so
    no step of `REPRODUCE.md` runs in it.
  - Its CMD, `vesuvius_model.py`'s self-check, scores a small gated UNet-transformer with unseeded random weights,
    on synthetic tensors, on the CPU. In six runs here, two of its four checks printed `[FAIL]` each time, and it
    exited 0. The header's "NVIDIA GPU at run time" carries a note that nothing in the image uses one.
  - The header also notes that the "~60 GB to build" was measured before the `.dockerignore` existed, and has not
    been re-measured.
- **`CONTRIBUTING.md` and `SUBMISSION.md`.**
  - `CONTRIBUTING.md`'s setup gains the submodule step.
  - `SUBMISSION.md`, the July filing's summary, gains a dated note. Its Quick start predates the submodule step and
    the incumbent re-score. Its architectures have been selectable by config, not per cycle, since 2026-06-09.

## Verified, no change needed

- Every path `REPRODUCE.md` names exists, and every subcommand it runs is defined:
  - `detector.cli reproduce` and `measure`;
  - `repro.sota_data.distill_run prep`, `baseline`, `train` and `measure`;
  - `smoke_test.py --list-only`;
  - `repro/spiral_render/preflight.sh`.
- §5's fragments and assertion match `DetectorConfig` (train `PHercParis2Fr47`, held out `PHercParis2Fr143`) and
  `cli._reproduce` (pixel-AUC ≥ 0.70), and `reports/detector/REPRODUCTION.md` records 0.7090.
- The smoke test's eleven names match the listed passes and skips.
- `.dockerignore`, through Docker's own matcher (moby/patternmatcher v0.6.0) over every tracked path plus `.venv/`,
  `.git/` and `local_data/` entries, keeps exactly the ten files the `Dockerfile` copies. `!*.py` re-includes
  top-level files only.
- `uv lock --check --offline` passes, with 248 packages resolved.
- **The image's `uv sync`.** The project package is built as an editable install without `src/`. setuptools
  84 builds that editable wheel, empty, while a regular wheel build stops on "'src' does not exist". So
  `uv sync`, which installs editable, is not broken by the missing directory.
- `CONTRIBUTING.md` states the F1 and AP-lift promotion and the 15/60-minute shifts correctly.

## Observations for the owner (not changed)

- **The image reproduces nothing in `REPRODUCE.md`.** Copying `src/`, `scripts/`, `repro/` and `tests/` and making
  the smoke test the CMD would change what the image is for, and it could not be built here (no Docker daemon). The
  same goes for the CMD itself, whose PASS/FAIL lines describe an untrained model.
- **ResNet3D-101 and Inception-I3D cannot be built at the villa pin.** `train.py` looks for them in
  `villa/ink-detection/models/`, which villa moved to `deprecated/ink-detection/`. A repair has to handle the
  shadowing `vesuvius_model.py` describes for the ResNet3D decoder: a local, gitignored `models/` data directory at
  the repository root takes the package name. Whether to repair the import or drop the two from `build_model` is
  the owner's call; neither is sampled.
- **`train.is_model_improvement`**, the `val_bpb`/topology promotion rule, has had no caller since 2026-07-11.
  Only `tests/test_improvement_criterion.py` still exercises it.
- **`history.tsv` and `results.tsv` have no val_f1 column**: they record runs, not the decision. The README says
  so; the frozen `results.tsv` schema is there for `scripts/experiment_report_data.py`.

## Verification

Environment: CPython 3.10 venv (no GPU visible), pytest, uv 0.11.32. No scroll data here. Villa is at the pin
in a sparse checkout without `ink-detection/`, so its tree at the pin was read with `git ls-tree`.

- `PYTHONPATH=src:. train.py --config config.json --smoke` without data: `PREFLIGHT FAILED: no label file ...`,
  exit 1.
- `scripts/smoke_test.py`: 9 passed, 2 skipped (`dataloader_3tuple_sobel` and `dataloader_frangi_target`, no
  data; `augmentations_bg2` passes). `--list-only` gives the eleven names.
- `CUDA_VISIBLE_DEVICES="" pytest tests/test_detector_*.py`: 206 passed, 1 skipped in 168.93 s.
  `tests/test_sota_*.py`, with an empty stand-in for `s3fs`, which is not installed here: 106 passed in 11.33 s.
- `vesuvius_model.py` (the image's CMD) on the CPU: `[FAIL]` on the SNR and layer-isolation checks, exit 0.
- The setuptools editable and regular wheel builds of the project, from only the files the image copies.
- `uv lock --check --offline`: resolved 248 packages.
- No image was built (no Docker daemon). The `.dockerignore` was checked with Docker's pattern matcher, as above.
- An independent review of the first commit found two errors in it, both corrected above: the architecture sentence
  (`build_model` does dispatch Inception-I3D), and the smoke result called "unchanged". It also reported the
  ResNet3D decoder as unbuildable at the pin; that was the sparse checkout here, not the pin.
- The standard suite: see the PR.
