# Vesuvius Autoresearch: Progress Prize Submission

**Submission Tier:** Denarius ($10k) / Gold Aureus ($20k)
**Deadline:** April 30, 2026

> **Status note (added 2026-05-15):** This file is the original April 2026
> framing and was never filed through the April Google Form before it closed.
> The contributions below (Vesuvius-C bindings + autoresearch loop) were filed
> as **Part 1 of 2** of the May 2026 Progress Prize cycle; the villa-baseline
> launchers + `submission_package` path + upstream PR ScrollPrize/villa#899
> were filed as **Part 2 of 2**. Canonical current filings:
> - [`docs/PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md`](docs/PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md) — Part 1 (Vesuvius-C + autoresearch loop), queued for May filing.
> - [`docs/PROGRESS_PRIZE_SUBMISSION_2026-05.md`](docs/PROGRESS_PRIZE_SUBMISSION_2026-05.md) — Part 2 (villa launchers + PR #899), filed 2026-05-15.
>
> This file is kept for historical record only. The May submission deadline is
> 2026-05-31 11:59pm PT and the form is https://forms.gle/LrpQmSAqdwGpTczLA .

## Overview

`bountyhunter` is an autonomous research loop designed to continuously optimize 3D ink detection models for the Vesuvius Challenge. It uses a fully automated pipeline to randomly sample configurations, evaluate them against a fixed baseline on cross-fragment validation, and retain successful architectures.

This submission packages our framework as a tool for the community. It includes integrated architectural baselines, metric suites, and an automated execution loop.

## Video Walkthrough

[Link to Walkthrough Video] (Placeholder: video demonstrating setup, a single 15-minute training cycle, and the automatic logging of results)

## Quick Start

The framework is designed for a single NVIDIA GPU (e.g., RTX 4090 or H100) and uses `uv` for fast dependency management.

```bash
# 1. Install dependencies
uv sync

# 2. Download sample dataset (PHerc. Paris 2 Fr 47)
uv run download_data.py --fragment 4

# 3. Kick off the autonomous research loop
uv run run_autoresearch_loop.py
```

## Results & Baselines

Our `results.tsv` (included in this repository) and `best_model.pt` (available on [HuggingFace](https://huggingface.co/jonmarrs/vesuvius-autoresearch/blob/main/best_model.pt)) demonstrate that the autonomous loop consistently discovers models that beat our initial fixed baseline. 

*   **Baseline val_bpb:** ~0.274
*   **Evolved val_bpb:** ~0.087

## Integrations with Villa Components

This project builds heavily upon the excellent foundation provided by the official Vesuvius Challenge `villa` repository. Explicitly, we have integrated:

*   **[Villa Metrics Suite](https://github.com/ScrollPrize/villa/tree/main/segmentation/evaluation/metrics):** We use `centerline_dice` and `skeleton_distance_length` to rigorously evaluate our models on topological correctness.
*   **[Villa Volume API](https://github.com/ScrollPrize/villa/tree/main/vesuvius/src/vesuvius/data):** We load OME-Zarr formats directly utilizing the official `Volume` class.
*   **[Villa Albumentations Recipe](https://github.com/ScrollPrize/villa/blob/main/ink-detection/train_timesformer_og.py):** Our augmentation pipeline evolves from the official recipe tuned for Scroll 2 noise profiles.
*   **[Villa 3D Structure Tensors](https://github.com/ScrollPrize/villa/blob/main/vesuvius/src/vesuvius/image_proc/geometry/structure_tensor.py):** We use the structure tensor computation to supervise our auxiliary tasks.

## Prize Readiness Tooling

See [`VILLA_PRIZE_READINESS.md`](./VILLA_PRIZE_READINESS.md) for the current
Scroll 2/3 search and validation workflow. The package includes a deterministic
candidate queue builder, VC3D-compatible prediction metadata export, and a local
validator for scale-bar, provenance, ML-window, and train/predict-overlap checks.

## License

This project is licensed under the MIT License. See `README.md` for full details.
