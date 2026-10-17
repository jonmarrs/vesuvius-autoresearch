# Design and architecture review — the reproduction path

Date: 2026-10-17. Baseline: `ead6176a` (main after #105). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the documents and files a newcomer reproduces from, which no earlier review covered: `REPRODUCE.md`, the
`Dockerfile`, `METHOD.md` and `SUBMISSION.md`. Each command they give was run here where it can run without data
or a GPU, and checked against the code otherwise. `CONTRIBUTING.md` and the README's Quick start were checked for
consistency with them and are current.

## What changed

- **`REPRODUCE.md` §2: the preflight needs the training volumes' label files.**
  - It said `train.py --smoke` needs "no data download". Since 2026-10-14 the preflight first resolves each
    configured training volume's label file, so it fails fast when one is missing.
  - Run here without data: `PREFLIGHT FAILED: no label file for training volume
    local_data/PHercParis2Fr47/surface_volume.zarr ...`, exit 1.
  - The section now says it needs those label files (or a pseudo-label), not the volumes. The README's Quick
    start already ran it "with the data in place".
- **`REPRODUCE.md` §7–§8: the loop's tracked log is `history.tsv`.**
  - §7 told the reader to inspect `results.tsv`, "retained for provenance". That file is gitignored and local, with
    one row per promotion. The tracked log is `history.tsv`, one row per run that finished validation.
  - §8 said every cycle appends to `results.tsv`.
  - Both now say what is where. Neither file has val_f1, the metric that decides promotion, so both point to
    `sprint_logs/`, `run_result.json` and the README's "Tracking progress", which already said so.
- **`REPRODUCE.md`, smaller.**
  - It gave Python "3.10/3.11"; `pyproject.toml` requires `>=3.10,<3.11`.
  - §1 now checks out the villa submodule, as the README's Quick start does.
  - §4's test counts (30 and 60 passed, 2026-09-06) are re-run: 206 passed and 1 skipped, and 106 passed.
  - §3's smoke result is re-run and unchanged.
- **`METHOD.md`'s search loop described an older loop.**
  - Step 1 listed four architectures as sampled. The loop's architecture arm has been pinned to `resenc_unet`
    since 2026-06-09, before the file was last edited. It also named Inception-I3D, which `build_model` does not
    accept; the list is now the architectures it does.
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
    no step of `REPRODUCE.md` runs in it. Its CMD, `vesuvius_model.py`'s self-check, scores one model with random
    initial weights on synthetic tensors on the CPU. Run here, two of its four checks print `[FAIL]` and it exits 0.
  - The header also notes that its "~60 GB to build" was measured without the `.dockerignore`.

## Verified, no change needed

- Every path `REPRODUCE.md` names exists, and every subcommand it runs is defined:
  - `detector.cli reproduce` and `measure`;
  - `repro.sota_data.distill_run prep`, `baseline`, `train` and `measure`;
  - `smoke_test.py --list-only`;
  - `repro/spiral_render/preflight.sh`.
- §5's fragments and assertion match `DetectorConfig` (train `PHercParis2Fr47`, held out `PHercParis2Fr143`) and
  `cli._reproduce` (pixel-AUC ≥ 0.70), and `reports/detector/REPRODUCTION.md` records 0.7090.
- The smoke test's eleven names match the listed passes and skips.
- `uv lock --check --offline` passes, with 248 packages resolved.
- **The image's `uv sync`.** The project package is built as an editable install without `src/`. setuptools
  84 builds that editable wheel, empty, while a regular wheel build stops on "'src' does not exist". So
  `uv sync`, which installs editable, is not broken by the missing directory.
- `CONTRIBUTING.md` states the F1 and AP-lift promotion and the 15/60-minute shifts correctly.

## Observations for the owner (not changed)

- **The image reproduces nothing in `REPRODUCE.md`.** Copying `src/`, `scripts/`, `repro/` and `tests/` and making
  the smoke test the CMD would change what the image is for, and it could not be built here (no Docker daemon). The
  same goes for the CMD itself, whose PASS/FAIL lines describe an untrained model.
- **`SUBMISSION.md`** is the July filing's repository summary. It lists TimeSformer, ResNet3D-101, Inception-I3D
  and the gated UNet-transformer as "selectable per cycle", which the loop's pinned architecture arm has not done
  since 2026-06-09. It was left as filed.
- **`train.is_model_improvement`**, the `val_bpb`/topology promotion rule, has had no caller since 2026-07-11.
  Only `tests/test_improvement_criterion.py` still exercises it.
- **`history.tsv` and `results.tsv` have no val_f1 column**: they record runs, not the decision. The README says
  so; the frozen `results.tsv` schema is there for `scripts/experiment_report_data.py`.

## Verification

Environment: CPython 3.10 venv (no GPU visible), pytest, uv 0.11.32. No scroll data here.

- `PYTHONPATH=src:. train.py --config config.json --smoke` without data: `PREFLIGHT FAILED: no label file ...`,
  exit 1.
- `scripts/smoke_test.py`: 9 passed, 2 skipped. `--list-only` gives the eleven names.
- `CUDA_VISIBLE_DEVICES="" pytest tests/test_detector_*.py`: 206 passed, 1 skipped in 168.93 s.
  `tests/test_sota_*.py`, with an empty stand-in for `s3fs`, which is not installed here: 106 passed in 11.33 s.
- `vesuvius_model.py` (the image's CMD) on the CPU: `[FAIL]` on the SNR and layer-isolation checks, exit 0.
- The setuptools editable and regular wheel builds of the project, from only the files the image copies.
- `uv lock --check --offline`: resolved 248 packages.
- The `.dockerignore` could not be exercised here (no Docker daemon). It follows Docker's documented allowlist
  form: `*`, then a `!` exception per copied file; `*.py` matches top-level files only.
- The standard suite: see the PR.
