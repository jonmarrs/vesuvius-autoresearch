# Design and architecture review — what the augmentation ablation records

Date: 2026-10-19. Baseline: `450c103f` (main after #139).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/ablate_scroll_augmentations.py`, the harness that trains one short cell per (scroll augmentation,
seed) from the incumbent. Its isolation from the loop was reviewed on 2026-10-15 (operator scripts) and since. This
review is of what each cell's row records.

The round also read `scripts/build_villa_review_manifest.py`, one of the handoff's least-reviewed steps. It needs
no change (below).

## What changed

- **A cell's row did not carry what the loop selects on.**
  - Each cell's row, and the CSV, held `val_bpb`, the train loss, the three topology metrics and `is_success`. The
    summary ranks conditions by mean `val_bpb`.
  - The harness was written before 2026-07-11. Since then the loop selects on val_f1 gated by AP lift, and
    `val_bpb` and the topology metrics are reported only (`train.promotion_decision`). So an ablation run today could
    not be read on the loop's metric at all.
  - Its last runs (`reports/ablation_2026-05-20…` and `…2026-06-05…`) predate the switch.
  - Each row now also records:
    - `val_f1` and `val_f1_threshold`;
    - `ap_prevalence_lift` and `roc_auc`;

    all under `run_result.json`'s names. The per-cell line prints val_f1 beside val_bpb.
- **Nor whether the cell started from the incumbent.**
  - The docstring says every cell "warm-starts from the current best_model.pt", and the comparison across conditions
    rests on it. Since #134, `run_result.json` records how many of the model's tensors came from `best_model.pt`
    (`warm_start`).
  - Each row now carries `warm_start_loaded` and `warm_start_tensors`, empty for a result without the record.
- **The docstring** says what the CSV holds, and that the summary is of `val_bpb`.
- **Tests** (`tests/test_ablation_harness_isolation.py`, in the standard suite, 2 new, 3 cases):
  - a cell's result read into its row, and the row into the CSV, with each new field;
  - a result without the warm-start record, or with a malformed one, still read.

  All fail with main's script.

## Verified, no change needed

- **`build_villa_review_manifest.py`** names each candidate's expected prediction from the GPU queue's
  `artifact_stem`. The evidence chain names it from the ranked table's. The two agree, because the queue copies
  the ranked row's stem (`summarize_villa_evidence_preflight.py`), and the ranker fills it for every row: 110 of 110
  ranked, 12 of 12 queued. The manifest's own fallback, `candidate_NNN`, differs from the chain's
  (`pred_<z>_<y>_<x>_<w>x<h>`). It is reached only by a row with no stem, which neither table has.
- **The ablation's isolation is unchanged:**
  - each cell is an experiment run (`checkpoint_out`);
  - the lock is held throughout, and orphaned runs are refused;
  - `run_result.json` is cleared before each cell.

## Observations for the owner (not changed)

- **The summary still ranks conditions by `val_bpb`** ("lower = better"). Which metric an augmentation ablation
  should be judged on, val_f1 as the loop is, or val_bpb as it was designed, is the owner's call. The rows now carry
  both.
- **`is_success`** in a row is `promotion_decision`'s verdict against the incumbent with the prize gates off
  (`enforce_prize_gates: false`). As a `checkpoint_out` run it promotes nothing.

## Verification

- `pytest tests/test_ablation_harness_isolation.py`: 10 passed. With main's script, the 3 new cases fail.
- Ruff and mypy clean on the changed files.
- The standard suite: see the PR.
