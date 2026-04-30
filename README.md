# bountyhunter: Vesuvius Autoresearch

![teaser](progress.png)

*The first autonomous research swarm for the Vesuvius Challenge.*

`bountyhunter` is an experiment in having AI agents perform their own end-to-end computer vision research. It automates the cycle of hypothesis generation, hyperparameter optimization, model training, and performance evaluation to uncover the "Gold Standard" configurations for reading ancient carbonized scrolls.

## 🚀 Key Features

- **Autonomous Research Loop:** Automatically samples from a multidimensional configuration space (architectures, loss functions, augmentations).
- **Grand Prize Architectures:** Native integration of TimeSformer, ResNet3D-101, and Inception-I3D from the 2023 winning solutions.
- **On-the-fly Multi-tasking:** Real-time 3D Structure Tensor and Ridge Map computation for rich structural supervision.
- **Topological Metrics:** Evaluates models using topologically-aware signals like `centerline_dice` and `skeleton_distance_length`.
- **Calibration Baselines:** Periodically re-evaluates against the fixed 2023 Grand Prize recipe to prevent research drift.

## 🛠 Setup

```bash
# 1. Install dependencies (requires uv)
uv sync

# 2. Download a sample dataset (Fragment 1)
uv run download_data.py --fragment 4

# 3. Kick off the research loop
uv run run_autoresearch_loop.py
```

## 📈 Tracking Progress

- **`results.tsv`**: Every successful experiment that beats the current baseline is logged here.
- **`LAB_NOTEBOOK.md`**: High-level strategic record of research milestones and breakthroughs.
- **`sprint_logs/`**: Detailed per-shift execution traces and config samples.

## ✅ Validation

Use the project interpreter for tests; a system `pytest` may not have the GPU/CT
dependencies installed.

```bash
uv run python scripts/run_validation_tests.py
```

For prize-submission mechanics specifically:

```bash
uv run python scripts/build_scroll23_search_queue.py
uv run python scripts/generate_submission_package.py
uv run python scripts/validate_prize_artifact.py --metadata submission_package_dry_run/metadata.json
```

---

## Quick start

**Requirements:** A single NVIDIA GPU (tested on RTX 4090/H100), Python 3.10+, [uv](https://docs.astral.sh/uv/).

```bash
# 1. Install uv project manager (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Download data (~5 min)
uv run download_data.py --fragment 4

# 4. Manually run a single training experiment (~15 min)
uv run train.py
```

If the above commands all work ok, your setup is working and you can go into autonomous research mode.

## Running the agent

Simply spin up your Claude/Codex or whatever you want in this repo (and disable all permissions), then you can prompt something like:

```
Hi have a look at program.md and let's kick off a new experiment!
```

The `program.md` file is essentially a super lightweight "skill".

## Project structure

```
vesuvius_loader.py  — data loading, ridge computation
vesuvius_model.py   — model architectures (GatedUNet, TimeSformer, etc.)
train.py            — main training loop and evaluation
run_autoresearch_loop.py — autonomous experimentation manager
program.md          — agent instructions
pyproject.toml      — dependencies
```

## Design choices

- **Autonomous Tweak Families.** The loop script (`run_autoresearch_loop.py`) intelligently samples from different "families" of tweaks (LR, Architecture, Loss Balance) based on recent success.
- **Fixed Time Budget.** Training runs for a fixed wall-clock budget (default 15 mins for Day Shift, 60 mins for Night Shift). This ensures experiments are comparable and the agent optimizes for the best model *within the available compute*.
- **Multi-task Supervision.** Models are trained not just on ink labels, but also on auxiliary tasks like 3D ridge detection and structure tensor alignment to improve generalization.

## License

MIT
