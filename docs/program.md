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
   - `src/vesuvius_autoresearch/core/model_wrappers.py` — builds the loop's production `resenc_unet`
     (`build_resenc_unet`, which inference uses too).
   - `vesuvius_model.py` — alternative architectures (GatedUNet, TimeSformer, MedNeXt, ...).
   - `scripts/training/config.py` — the serializable experiment configuration.
   - `scripts/training/train.py` — the loop's training and evaluation script.
   - `src/vesuvius_autoresearch/detector/` — the productionized (separate) TimeSformer detector.
3. **Verify data exists**: Check that `config.json`'s `uris` and `val_uri` exist, each with its ink labels and
   `mask.png` beside it (README, Quick start, "Data"). If not, ask the human: no maintained script builds them,
   and the downloaders under `scripts/archive/` are unmaintained.
4. **Confirm and go**: Confirm setup looks good.

## Experimentation

Each experiment runs on a single GPU. The training script runs for a **fixed time budget** (900s for Day Shift, 3600s for Night Shift). Launch, with the loop paused:
`PYTHONPATH=. uv run python scripts/training/train.py --config config.json`
A direct run takes no lock and writes the loop's state: `history.tsv`, `last_model.pt` and `run_result.json`,
and, if it promotes, `best_model.pt`, `results.tsv` and `prize_readiness.tsv`. `--test` is the same run with
a 30 s budget and the same writes; `--smoke` builds the model and runs one forward/backward on the CPU, and
writes nothing.

**What you CAN do:**
- Modify `scripts/training/train.py`, `src/vesuvius_autoresearch/core/model_wrappers.py` or `vesuvius_model.py` — architecture, optimizer, hyperparameters, training loop, batch size, model size, etc. **But first pause the loop if it is running** (`./stop.sh` stops the registered loop and creates `.loop_paused`; `./start.sh` resumes it).

**What you CANNOT do:**
- Install new packages or add dependencies. You can only use what's already in `pyproject.toml`.
- Modify the evaluation harness in `scripts/training/train.py` unless requested — model selection runs on the honest metric contract (threshold-swept `val_f1`, gated by AP-prevalence-lift and, when `enforce_prize_gates` is on, the ≤64px
  prize window; `config.json` has it off; see `docs/superpowers/specs/2026-07-10-loop-honest-metric-selection-design.md`).

**The goal is ink-detection generalization measured honestly.** The selection metric is `val_f1` (with `ap_prevalence_lift > 1.02` as the real-signal gate); `val_bpb` and topology metrics are reported but do not decide. Known context from `FINDINGS.md`: fresh 64px training sits near chance on this data; the productionized detector and the SOTA-distillation work live outside this loop.

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

Every run that finishes validation appends to `history.tsv` (it has no `val_f1`;
the noise probe's and the ablation's runs write elsewhere); a
promoting run appends to `results.tsv` (local-only) and `prize_readiness.tsv`, and
replaces `best_model.pt` (which carries the honest metrics). Sprint logs, with each
cycle's `val_f1`, land in `sprint_logs/`.

## The experiment loop

The experiment is managed by `run_autoresearch_loop.py` (`./start.sh` / `./stop.sh`). It handles iteration and logging automatically.

LOOP FOREVER:

1. Look at the state of research in `sprint_logs/` (each cycle's `val_f1`), `FINDINGS.md`, and `docs/LAB_NOTEBOOK.md`.
2. Propose a new experiment (architecture change or hyperparameter tweak) that is not already ruled out by `FINDINGS.md`.
3. Update `scripts/training/train.py`, `src/vesuvius_autoresearch/core/model_wrappers.py` or `vesuvius_model.py` (loop paused).
4. Run the loop, or one training run with the loop paused.
5. Record findings.

**NEVER STOP**: Once the experiment loop has begun, do NOT pause to ask the human if you should continue. The loop runs until the human interrupts you, period.
