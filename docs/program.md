# autoresearch

This is an experiment to have the LLM do its own research.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `apr30`).
2. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context.
   - `vesuvius_loader.py` — data loading and preprocessing.
   - `vesuvius_model.py` — architecture definitions.
   - `train.py` — the main training script.
3. **Verify data exists**: Check that `local_data/` contains volumes. If not, tell the human to run `uv run download_data.py`.
4. **Confirm and go**: Confirm setup looks good.

## Experimentation

Each experiment runs on a single GPU. The training script runs for a **fixed time budget** (900s for Day Shift, 3600s for Night Shift). You launch it simply as: `uv run train.py`.

**What you CAN do:**
- Modify `train.py` or `vesuvius_model.py` — these are the files you edit. Everything is fair game: model architecture, optimizer, hyperparameters, training loop, batch size, model size, etc.

**What you CANNOT do:**
- Install new packages or add dependencies. You can only use what's already in `pyproject.toml`.
- Modify the evaluation harness in `train.py` unless requested.

**The goal is cross-scroll ink detection generalization.** You must maximize the validation Dice score on PHerc. 0172 (Scroll 5) or similar.

**VRAM** is a soft constraint. Some increase is acceptable for meaningful val_bpb gains, but it should not blow up dramatically.

**Simplicity criterion**: All else being equal, simpler is better.

## Output format

Once the script finishes it prints a summary like this:

```
---
val_bpb:          0.997900
training_seconds: 900.1
peak_vram_mb:     45060.2
num_params_M:     50.3
```

## Logging results

Results are logged to `results.tsv` (tab-separated).

## The experiment loop

The experiment is managed by `run_autoresearch_loop.py`. It handles the iteration and logging automatically.

LOOP FOREVER:

1. Look at the state of research in `results.tsv` and `LAB_NOTEBOOK.md`.
2. Propose a new experiment (architecture change or hyperparameter tweak).
3. Update `train.py` or `vesuvius_model.py`.
4. Run the loop or a single test.
5. Record findings.

**NEVER STOP**: Once the experiment loop has begun, do NOT pause to ask the human if you should continue. The loop runs until the human interrupts you, period.
