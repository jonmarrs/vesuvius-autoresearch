# Progress Prize Submission: Vesuvius-C Python Bindings & Autoresearch Loop
**Submission Date:** April 30, 2026
**Target Prize:** Progress Prize (Aureus/Denarius/Sestertius)

> **Status note (added 2026-05-15):** This April draft was never filed through the April Google Form before that cycle closed. The two contributions documented below (Vesuvius-C Python bindings + Autoresearch loop) were later filed as **Part 1 of 2** of the May 2026 Progress Prize cycle. See [`PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md`](PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md) for the canonical May filing; the companion Part 2 is [`PROGRESS_PRIZE_SUBMISSION_2026-05.md`](PROGRESS_PRIZE_SUBMISSION_2026-05.md). This file is kept for historical record of the original April framing.

## 1. Vesuvius-C Python Bindings (High-Performance Data Access)
One of the major bottlenecks in the "Master Plan" Stage 2 is **Unwrapping at Scale**. Processing terabytes of OME-Zarr data efficiently is critical.

### The Contribution
We have developed a lightweight, zero-copy `ctypes` wrapper for the official `ScrollPrize/villa/vesuvius-c` library.
- **Efficiency**: Directly parses `.zarray` JSON and reads Blosc2-compressed chunks into NumPy arrays via C pointers, bypassing `fsspec` and standard Zarr overhead.
- **Integration**: Designed to be a drop-in replacement for the `Volume` class in Python-based loaders.
- **Speed**: Measured at **31.77M voxels/sec** on local storage, enabling significantly faster training cycles for deep learning models.

### Location in Repo
- Source: `vesuvius_c_wrapper/vesuvius_c.py`
- Implementation: `vesuvius_c_wrapper/vesuvius_c_impl.c` (Wraps `vesuvius-c.h`)
- Build: `vesuvius_c_wrapper/build.sh`

---

## 2. Vesuvius Autoresearch Loop (Automated Model Discovery)
To solve **Ink Identification** (Stage 2 bottleneck), we need to move beyond fixed architectures that overfit to Fragment 1.

### The Contribution
The `run_autoresearch_loop.py` framework provides an autonomous "Bounty Hunter" loop that:
- **Architecture Search**: Automatically mutates and evaluates UNet/ResEnc architectures (Gated UNet, multi-task heads).
- **Official Metric Integration**: Uses the `villa` metric suite (`centerline_dice`, `skeleton_distance_length`) as the primary optimization target, ensuring models are rewarded for topological continuity, not just pixel accuracy.
- **Hallucination Mitigation**: Enforces the official `< 64x64 px` window size rule and uses "Voter Swarm" ensembles to eliminate artifact-based hallucinations.
- **Result**: Achieved a `val_bpb` of **0.0054** with high topological consistency on the Fragment 1 -> Fragment 2 transfer task. *(Methodology note added 2026-05-16: this number was measured before commit `c9f578f` on 2026-05-03 fixed a zero-Dice validation wall in the evaluation pipeline; under the corrected ink-aware validation, the same loop converges to `val_bpb ≈ 0.4145`. See [PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md](PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md) for the full methodology-shift annotation. Topological-consistency claims are unaffected.)*

### Integration with Villa
We have explicitly integrated and verified the following components from the `villa` repository:
1. **[Villa Metrics Suite](https://github.com/ScrollPrize/villa/tree/main/segmentation/evaluation/metrics)**: Used for all leaderboard evaluations.
2. **[Villa Volume API](https://github.com/ScrollPrize/villa/tree/main/vesuvius/src/vesuvius/data)**: Used for standard data loading.
3. **[Villa 3D Structure Tensors](https://github.com/ScrollPrize/villa/blob/main/vesuvius/src/vesuvius/image_proc/geometry/structure_tensor.py)**: Used as an auxiliary training task to improve fiber sensitivity.

---

## 3. How to Reproduce
Our submission is designed for "One-Command" reproduction:
1. `git clone --recursive ...` (Submodules initialized)
2. `uv run python3 run_autoresearch_loop.py --budget 3600`
3. Results are logged to `results.tsv` and `best_model.pt`.

## 4. Community Value
This package provides a bridge between the high-performance C-based tooling of `vesuvius-c` and the flexible experimentation of Python/PyTorch. By automating the architecture search around official metrics, we lower the barrier for researchers to contribute to the Grand Prize.
