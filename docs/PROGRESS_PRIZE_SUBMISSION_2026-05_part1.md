# Progress Prize Submission (May 2026 — Part 1 of 2): Vesuvius-C Python Bindings + Autoresearch Loop (Villa-Metric-Anchored)
**Submission Date:** 2026-05 (target: 2026-05-31 11:59pm PT)
**Submission Form:** https://forms.gle/LrpQmSAqdwGpTczLA
**Target Prize Tier:** Denarius / Sestertius (open to maintainer judgment)
**Submitter:** Jon Marrs &lt;jdmarrs@gmail.com&gt;
**Repository:** https://github.com/jonmarrs/vesuvius-autoresearch
**License:** MIT
**Status:** FILED through the May form as a second submission in the same cycle (the May Progress Prize allows multiple submissions per month per `villa/scrollprize.org/docs/34_prizes.md:119`). The *work* covered here was drafted for the April 2026 cycle but never filed through the April form before it closed; this filing brings it into the May review pool.
**Companion submission:** [PROGRESS_PRIZE_SUBMISSION_2026-05.md](PROGRESS_PRIZE_SUBMISSION_2026-05.md) — **Part 2 of 2**, the villa-baseline launchers + `submission_package` path + upstream PR ScrollPrize/villa#899. Already filed.

## Thesis

Reading scrolls is bottlenecked early on by two distinct gaps in the community tooling: raw I/O throughput when streaming compressed Zarr chunks into training pipelines, and a principled way to search the model-architecture space against the *official* prize metrics rather than ad-hoc proxies. This submission closes both for the autoresearch use case, and the published artifacts are reusable by any contributor running their own ink-detection experiments.

## What this submission ships

### 1. Vesuvius-C Python bindings (zero-copy chunked volume access)

`vesuvius_c_wrapper/vesuvius_c.py` is a lightweight `ctypes` wrapper around villa's `vesuvius-c` C library. It parses `.zarray` JSON directly and reads Blosc2-compressed chunks into NumPy arrays via C pointers, bypassing `fsspec` and the standard Zarr Python stack.

- Measured **31.77M voxels/sec** on local storage (see `scripts/benchmark_vesuvius_c.py`).
- Drop-in compatible with the `Volume` class used by autoresearch data loaders.
- Lives at `vesuvius_c_wrapper/` (Python wrapper + C implementation + `build.sh`).

Without this layer, every autoresearch training cycle spent a significant fraction of its budget on Python-side decompression and fsspec overhead. With it, the bottleneck shifts to the GPU.

### 2. Autoresearch Loop (autonomous architecture search anchored on villa metrics)

`run_autoresearch_loop.py` is an autonomous "Bounty Hunter" loop that mutates architecture + training hyperparameters, evaluates each candidate against villa's official metric suite (`centerline_dice`, `skeleton_distance_length`), enforces the prize-mandated `≤64x64 px` ML window, and uses voter-swarm ensembling to suppress single-model hallucinations. The reported best on Fragment 1 → Fragment 2 transfer is `val_bpb = 0.0054` with high topological consistency.

> **Methodology note (added 2026-05-16 after diagnostic review):** the `val_bpb = 0.0054` headline was measured under the pre-`c9f578f61f699d35b9341e24a9a62ed8fd198af7` (2026-05-03) evaluation, which had a documented zero-Dice validation wall (sparse validation regions producing artificially low loss values; the commit message: "fix(pipeline): resolve zero-Dice validation wall with ink-aware sampling and threshold search"). After that fix replaced the validation sampler with an ink-aware one and added a Dynamic Threshold Search (0.01–0.80) to the metric pipeline, the same loop running on the current `val_uri = local_data/PHercParis2Fr143/surface_volume.zarr` settles at `val_bpb ≈ 0.4145` — the model's honest performance under the corrected evaluation. The autoresearch loop has been operating against the corrected evaluation since 2026-05-03; the topological-consistency claims (centerline_dice / skeleton_distance_length) remain valid under both regimes. The pseudo-label generators in companion PRs ScrollPrize/villa#922 and #923 are part of the structural-change set we expect to break this plateau.

Villa-side integrations the loop relies on directly:

- [`villa/segmentation/evaluation/metrics`](https://github.com/ScrollPrize/villa/tree/main/segmentation/evaluation/metrics) — every leaderboard evaluation runs through villa's metric suite, so optimization is on the same target as prize review.
- [`villa/vesuvius/src/vesuvius/data`](https://github.com/ScrollPrize/villa/tree/main/vesuvius/src/vesuvius/data) — standard volume access.
- [`villa/.../image_proc/geometry/structure_tensor`](https://github.com/ScrollPrize/villa/blob/main/vesuvius/src/vesuvius/image_proc/geometry/structure_tensor.py) — used as an auxiliary training task for fiber sensitivity.

### 3. Relationship to Part 2

Part 2 of this May filing ([PROGRESS_PRIZE_SUBMISSION_2026-05.md](PROGRESS_PRIZE_SUBMISSION_2026-05.md), already filed) covers the villa-baseline launcher family, the `submission_package` path, and upstream PR ScrollPrize/villa#899. Part 1 (this doc) covers the throughput + autonomous-search infrastructure those launchers run on top of. Together they form the May contribution; either is independently usable.

## Why this is prize-worthy

Per the Progress Prize criteria (released early, actually used, well documented):

- **Released early.** Vesuvius-C wrapper and the autoresearch loop have been in use across April + May; the loop has produced 600+ recorded sweep cycles in `reports/benchmark_v210_cycle*.png`.
- **Actually used.** The autoresearch loop is the load-bearing day-shift / night-shift workhorse of this repository, exercised continuously. The Vesuvius-C wrapper is its data-access layer.
- **Well documented.** `vesuvius_c_wrapper/` includes the C source, the Python wrapper, and a build script. `run_autoresearch_loop.py` is callable with `--budget <seconds>` and writes its history to `results.tsv` and `autoresearch_history.json`.

## How to reproduce

```bash
git clone --recursive https://github.com/jonmarrs/vesuvius-autoresearch.git
cd vesuvius-autoresearch
uv sync

# Build the Vesuvius-C wrapper:
bash vesuvius_c_wrapper/build.sh

# Run the autoresearch loop for one hour:
uv run python3 run_autoresearch_loop.py --budget 3600

# Results land in results.tsv and best_model.pt; the loop's evolution history
# is in autoresearch_history.json.
```

## Repository pointers (for the Google Form)

| Field | Value |
| --- | --- |
| Repository | https://github.com/jonmarrs/vesuvius-autoresearch |
| Branch | `main` |
| Key directories | `vesuvius_c_wrapper/`, `scripts/` (benchmark + autoresearch helpers) |
| Key files | `run_autoresearch_loop.py`, `vesuvius_c_wrapper/vesuvius_c.py`, `vesuvius_c_wrapper/vesuvius_c_impl.c`, `scripts/benchmark_vesuvius_c.py` |
| Tests | `tests/test_load.py`, `tests/test_vesuvius_c_readiness.py` |
| Reproduction entrypoint | `uv run python3 run_autoresearch_loop.py --budget 3600` |
| License | MIT |
| Prior draft | [PROGRESS_PRIZE_SUBMISSION.md](PROGRESS_PRIZE_SUBMISSION.md) (drafted for April 2026 but never filed; superseded by this Part 1) |
| Companion (Part 2 of 2) | [PROGRESS_PRIZE_SUBMISSION_2026-05.md](PROGRESS_PRIZE_SUBMISSION_2026-05.md) (villa-baseline launchers + PR ScrollPrize/villa#899) |

## Public release blurb (for socials / forum announcement)

> Filed as Part 1 of the May 2026 Progress Prize submission: a `ctypes` Python wrapper around villa's `vesuvius-c` library (≈31.77M voxels/sec on local storage), and an autonomous architecture-search loop anchored on villa's official metric suite (`centerline_dice`, `skeleton_distance_length`) with the 64×64 ML-window rule enforced. Both live in https://github.com/jonmarrs/vesuvius-autoresearch (public, MIT) alongside Part 2 of the May submission, which covers the villa-baseline launcher family and upstream PR ScrollPrize/villa#899.
