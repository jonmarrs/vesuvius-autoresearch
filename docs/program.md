# autoresearch

This is an experiment to have the LLM do its own research.

> **Strategy note (2026-07):** the project's primary thrust is now the
> registered-ground-truth evaluation work (see `FINDINGS.md` and
> `docs/PRIZE_FILING_DRAFT_2026-07.md`), with the autonomous loop as a
> secondary, idle-window activity. Read `FINDINGS.md` before proposing
> experiments — several obvious-looking levers are documented dead ends.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `jul11`).
2. **Read the in-scope files**:
   - `README.md` — repository context.
   - `FINDINGS.md` — what has already been tried and ruled out.
   - `src/vesuvius_autoresearch/core/vesuvius_loader.py` — data loading and preprocessing.
   - `vesuvius_model.py` — the loop's architecture zoo.
   - `scripts/training/train.py` — the loop's training and evaluation script.
   - `src/vesuvius_autoresearch/detector/` — the productionized (separate) TimeSformer detector.
3. **Verify data exists**: Check that `local_data/` contains volumes. If not, ask the human which download script under `scripts/archive/` applies (e.g. `uv run python scripts/archive/download_data.py`).
4. **Confirm and go**: Confirm setup looks good.

## Experimentation

Each experiment runs on a single GPU. The training script runs for a **fixed time budget** (900s for Day Shift, 3600s for Night Shift). Launch:
`PYTHONPATH=. uv run python scripts/training/train.py --config config.json`
(`--test` = 30s smoke; `--smoke` = build + one fwd/bwd preflight).

**What you CAN do:**
- Modify `scripts/training/train.py` or `vesuvius_model.py` — architecture, optimizer, hyperparameters, training loop, batch size, model size, etc. **But first pause the loop if it is running** (`.loop_paused` + kill PIDs; `stop.sh`'s pgrep pattern misses `-u` invocations).

**What you CANNOT do:**
- Install new packages or add dependencies. You can only use what's already in `pyproject.toml`.
- Modify the evaluation harness in `scripts/training/train.py` unless requested — model selection runs on the honest metric contract (threshold-swept `val_f1`, gated by AP-prevalence-lift and the ≤64px prize window; see `docs/superpowers/specs/2026-07-10-loop-honest-metric-selection-design.md`).

**The goal is ink-detection generalization measured honestly.** The selection metric is `val_f1` (with `ap_prevalence_lift > 1` as the real-signal gate); `val_bpb` and topology metrics are reported but do not decide. Known context from `FINDINGS.md`: fresh 64px training sits near chance on this data; the productionized detector and the SOTA-distillation work live outside this loop.

**VRAM** is a soft constraint (24GB card). Some increase is acceptable for meaningful `val_f1` gains, but it should not blow up dramatically.

**Simplicity criterion**: All else being equal, simpler is better.

## Output format

Once the script finishes it prints a summary including:

```
val_bpb (Official):    ...  [reported only]
val_f1:                ...  (thr ...) [NEW BEST if promoted]
ap_prevalence_lift:    ...
roc_auc:               ...  [selection: F1 gated by AP-lift]
```

and writes `run_result.json` (carries `val_f1`, `ap_prevalence_lift`, `roc_auc`,
`is_success`).

## Logging results

Every run appends to `history.tsv`; improving runs append to `results.tsv` and
update `best_model.pt` (which carries the honest metrics). Sprint logs land in
`sprint_logs/`.

## The experiment loop

The experiment is managed by `run_autoresearch_loop.py` (`./start.sh` / `./stop.sh`). It handles iteration and logging automatically.

LOOP FOREVER:

1. Look at the state of research in `results.tsv`, `FINDINGS.md`, and `docs/LAB_NOTEBOOK.md`.
2. Propose a new experiment (architecture change or hyperparameter tweak) that is not already ruled out by `FINDINGS.md`.
3. Update `scripts/training/train.py` or `vesuvius_model.py` (loop paused).
4. Run the loop or a single test.
5. Record findings.

**NEVER STOP**: Once the experiment loop has begun, do NOT pause to ask the human if you should continue. The loop runs until the human interrupts you, period.
