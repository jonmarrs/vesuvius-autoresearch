# Design and architecture review — the topology post-processing diagnosis

Date: 2026-10-21. Baseline: `dd2a3e5f` (main after #172).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/diagnose_topology_postproc.py`, which no review had read and no test covered. It asks whether
post-processing alone could bring `best_model.pt`'s skel_dist to the prize gate (≤ 2.0). It thresholds the
validation predictions, removes components under a minimum size, and reports villa's topology metrics for each
combination. On 2026-06-10 its sweep established that post-processing cannot close the gate (`d38a20e3`).

Main has not moved since #172. The owner's open PR #170 changes only the octant-crop files, none of which this round
touches.

## What changed

- **The prediction cache was used whatever it held.**
  - The script cached its predictions in `/tmp/topo_postproc_preds.pt` and read that file back on every later run.
    Nothing tied it to a checkpoint or to validation data.
  - So after a promotion, or a change of validation labels, it reported the previous model's predictions on the
    previous patches, for "best_model.pt".
  - **Change:** the cache holds a key: the checkpoint's sha256, the validation protocol, the validation inputs'
    fingerprint (`validation_inputs_fingerprint`) and whether the warp is used. A cache made under another key, or
    one that cannot be read, is ignored and replaced, and the script says so.
  - The cache is written atomically (`save_checkpoint_atomic`), and only for a complete sample. `--cache` names it.
- **The model was built from config.json and loaded partially.**
  - The architecture came from the checkpoint. Everything else, such as the patch size, depth, width, blocks, heads
    and ridge channel, came from config.json.
  - The weights went through `load_shape_compatible_state`, the training warm start, which skips any tensor whose
    shape differs and only prints a count.
  - If config.json and the checkpoint disagreed, the model would have been partly untrained, and its metrics would
    have been reported as the model's. Today they agree, so this was latent.
  - **Change:** `load_tool_checkpoint`, as `reevaluate_best_model.py`, `measure_ink_auc.py` and the other auxiliary
    tools use. It reads the checkpoint's own recipe and loads every tensor strictly.
  - Each batch goes through the checkpoint's own input check (`validate_batch`) and `ink_probabilities`. The
    validation inputs stay config.json's, and the checkpoint's recorded `use_lasagna` is applied, as in
    `reevaluate_best_model.py`, with the same `--unwarped`.
- **Its "Baseline (current eval)" had not been the current evaluation since 2026-06-10.**
  - It drew its own sample: the first ≤ 30 ink-containing batches the dataset yielded, in its order.
  - It scored topology at the Dice-optimal threshold.
  - The commit that added the script moved the loop's topology metrics to the centerline_dice-optimal threshold
    (`select_topology_threshold`). The loop also scores the validation protocol's seeded sample, now v3, of which the
    per-patch metrics use the ink-containing patches.
  - **Change:**
    - the script scores the protocol's sample through `build_validation_dataset` and `collect_validation_predictions`,
      as `reevaluate_best_model.py` does, and refuses an incomplete sample;
    - its baseline row is the loop's measurement: `select_topology_threshold`'s threshold, no post-processing,
      skel_dist and centerline_dice on every 10th patch, and cc_diff on all of them;
    - the Dice-optimal threshold is swept too, as one of the thresholds;
    - it prints the checkpoint's stored `avg_skel_dist` beside the baseline, so the two can be compared on the
      same inputs.
- **Measurements that failed were dropped silently.** Each skeleton and centerline computation sat in a bare
  `except Exception: pass`, and a NaN was left out of the mean without a count.
  - **Change:** the metrics are no longer wrapped. A failure now raises, as it does in `reevaluate_best_model.py`.
  - A value that is not finite is still left out, and counted in a new `undef` column. This happens when despeckling
    empties a prediction: villa's skel_dist is then NaN.
  - Dice is now taken on the despeckled mask that the other metrics see. It used to be taken on the raw threshold.
- **Tests** (`tests/test_diagnose_topology_postproc.py`, 6; none before). With the model load, the protocol and the
  metrics stubbed, they check:
  - despeckling;
  - the loop's sampling: cc_diff on every patch, the skeleton metrics on every 10th;
  - that despeckling comes before every metric, and that an undefined value is counted;
  - that the checkpoint's recipe and recorded inputs, not config.json's, build the dataset, and `--unwarped`;
  - that each prediction goes through the checkpoint's input check;
  - the baseline row;
  - that the cache is reused for the same key, and recomputed after a new checkpoint, other inputs or an unreadable
    file;
  - that an incomplete sample is neither measured nor cached.

  The original script fails 5 of the 6. Each of these 11 mutants fails them:
  - the recipe or the recorded inputs not applied;
  - the key without the checkpoint or the inputs, or not checked;
  - every 5th patch;
  - no despeckling;
  - the baseline at the Dice threshold;
  - an incomplete sample accepted;
  - NaN averaged in;
  - `--unwarped` ignored.

## Verified, no change needed

- **`load_tool_checkpoint` loads this container's `best_model.pt` strictly:** resenc_unet, 10.2 M parameters, patch
  64, 16 layers, ridge channel and multi-task heads.
  - config.json's recipe agrees with the checkpoint's.
  - Its stored scores are protocol `seeded-sample-400-v3+z1-27`, val_f1 0.266 and avg_skel_dist 31.3.
- **Villa's metrics on an emptied prediction:** skel_dist is NaN, centerline_dice 0, and cc_diff counts the
  ground-truth components. None of them raises, so a sweep that despeckles hard completes.
- **`despeckle`** keeps components of at least `min_size` pixels, with scipy's default 4-connectivity.

## Observations for the owner (not changed)

- **The sweep's grid is the June one:** thresholds 0.5 and 0.65 beside the two optimal ones, and minimum sizes 1, 16
  and 64. Whether to widen it is a research choice.
- **The result was not re-measured here.** This container has `best_model.pt` but no validation data. Re-running it
  scores the current model on the v3 sample at the loop's threshold, so its numbers are not comparable with June's.
- **The new test is not in the standard suite.** The script is not one of the loop's entry points, so
  `test_validation_suite_covers_the_loop` does not require it. It runs under `pytest tests/`.

## Verification

- `pytest tests/test_diagnose_topology_postproc.py`: 6 passed.
- `scripts/diagnose_topology_postproc.py --help` runs.
- Ruff 0.9.10, ruff format and mypy are clean on the changed files.
- PLACEHOLDER: standard suite and smoke.
- PLACEHOLDER: independent review.
