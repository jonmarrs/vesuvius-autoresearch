# Progress Prize Submission: Vesuvius-C Python Bindings + Autoresearch Loop (Villa-Metric-Anchored)
**Submission Date:** 2026-06 (target: monthly deadline ≈ 2026-06-30 — verify the current form URL + exact date in `villa/scrollprize.org/docs/34_prizes.md` once the May cycle closes)
**Submission Form:** (TBD — the May form at https://forms.gle/LrpQmSAqdwGpTczLA closes on 2026-05-31; the June form will appear in the prize docs after rollover)
**Target Prize Tier:** Denarius / Sestertius (open to maintainer judgment)
**Submitter:** Jon Marrs &lt;jdmarrs@gmail.com&gt;
**Repository:** https://github.com/jonmarrs/vesuvius-autoresearch
**License:** MIT
**Status:** QUEUED — this is the June filing for two items originally drafted for the April cycle that were never filed through the April form before it closed. Additional June work may be appended here before the cycle deadline.

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

Villa-side integrations the loop relies on directly:

- [`villa/segmentation/evaluation/metrics`](https://github.com/ScrollPrize/villa/tree/main/segmentation/evaluation/metrics) — every leaderboard evaluation runs through villa's metric suite, so optimization is on the same target as prize review.
- [`villa/vesuvius/src/vesuvius/data`](https://github.com/ScrollPrize/villa/tree/main/vesuvius/src/vesuvius/data) — standard volume access.
- [`villa/.../image_proc/geometry/structure_tensor`](https://github.com/ScrollPrize/villa/blob/main/vesuvius/src/vesuvius/image_proc/geometry/structure_tensor.py) — used as an auxiliary training task for fiber sensitivity.

### 3. (Placeholder) Additional June work

To be filled in before the 2026-06 deadline. Candidate items already discussed in the working notes:

- Wiring `prepare_mutex_training.py` against a curated zarr so the mutex-affinity lane (built in May, currently dry-run-only) becomes executable.
- Injecting villa's surface-frame / inplane-direction / distance-transform auxiliary heads into the LeJEPA fine-tune to stack auxiliary supervision on the existing pipeline.
- Following up on PR ScrollPrize/villa#899 with the container-build PR that installs the `vesuvius` package into `optimized_inference`'s requirements so `model_primus.py` becomes runnable end-to-end.
- Any other items shipped during June.

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
| Prior draft | [PROGRESS_PRIZE_SUBMISSION.md](PROGRESS_PRIZE_SUBMISSION.md) (drafted for April 2026 but never filed) |
| Sibling submission | [PROGRESS_PRIZE_SUBMISSION_2026-05.md](PROGRESS_PRIZE_SUBMISSION_2026-05.md) (May filing — villa-baseline launchers + PR ScrollPrize/villa#899) |

## Public release blurb (for socials / forum announcement)

> Two Vesuvius-Challenge infrastructure pieces previously documented but not filed are now queued for the June Progress Prize cycle: a `ctypes` Python wrapper around villa's `vesuvius-c` library (≈31.77M voxels/sec on local storage), and an autonomous architecture-search loop anchored on villa's official metric suite (`centerline_dice`, `skeleton_distance_length`) with the 64×64 ML-window rule enforced. Both live in https://github.com/jonmarrs/vesuvius-autoresearch (public, MIT) alongside the May submission's villa-baseline launcher family.
