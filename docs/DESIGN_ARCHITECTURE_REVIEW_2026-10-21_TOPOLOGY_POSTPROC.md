# Design and architecture review — the topology post-processing diagnosis

Date: 2026-10-21. Baseline: `dd2a3e5f` (main after #172).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/diagnose_topology_postproc.py`, which no review had read and no test covered.
- **What it asks:** whether post-processing alone could bring `best_model.pt`'s skel_dist to the prize gate (≤ 2.0).
- **How:** it thresholds the validation predictions, removes components under a minimum size, and reports villa's
  topology metrics for each combination.
- **History:** it was added on 2026-06-10 (`d38a20e3`), with the change that moved the loop's topology metrics to
  the centerline_dice-optimal threshold. Its sweep was the evidence that post-processing cannot close the gate.

Main has not moved since #172. The owner's open PR #170 changes only the octant-crop files, none of which this round
touches.

## What changed

- **The prediction cache was used whatever it held.**
  - The script cached its predictions in `/tmp/topo_postproc_preds.pt` and read that file back on every later run.
    Nothing tied it to a checkpoint or to validation data.
  - So after a promotion, or a change of validation labels, it reported the previous model's predictions on the
    previous patches, for "best_model.pt".
  - **Change:**
    - The cache holds a key: the checkpoint's sha256, the validation protocol, the validation inputs' fingerprint
      (`validation_inputs_fingerprint`) and whether the warp is used.
    - A cache made under another key, or one that cannot be read, is ignored and replaced, and the script says so.
      `--refresh` ignores it outright.
    - It is written atomically (`save_checkpoint_atomic`). It is written only for a complete sample, and only when
      the dataset's own inputs fingerprint agrees with the key's.
    - A cache that cannot be written is reported, and the run's results are still printed.
  - The checkpoint is read once and that same buffer is hashed and loaded. So a promotion that replaces the file
    mid-run cannot leave one model's predictions under another's hash.
- **The model was built from config.json and loaded partially.**
  - Its architecture and `multi_task_heads` came from the checkpoint. Everything else, such as the patch size,
    depth, width, blocks, heads and ridge channel, came from config.json.
  - The weights went through `load_shape_compatible_state`, the training warm start. It skips any tensor whose shape
    differs and only prints a count.
  - If config.json and the checkpoint disagreed, the model would have been partly untrained, and its metrics would
    have been reported as the model's. Today they agree, so this was latent.
  - **Change:** `load_tool_checkpoint`, which `reevaluate_best_model.py`, `measure_ink_auc.py` and the other auxiliary
    tools use. It reads the checkpoint's own recipe and loads every tensor strictly.
    - Each batch goes through the checkpoint's own input check (`validate_batch`) and `ink_probabilities`.
    - The validation inputs stay config.json's. The checkpoint's recorded `use_lasagna` is applied, as in
      `reevaluate_best_model.py`, with the same `--unwarped`.
- **Its "Baseline (current eval)" was never the loop's measurement.**
  - It drew its own sample: the first ≤ 30 ink-containing batches the dataset yielded, in its order. It scored
    topology at the Dice-optimal threshold.
  - It took skel_dist on every 5th batch, squeezed into one stack of up to 8 patches. Villa skeletonized that stack
    as one 3D volume, not as separate patches, so its skel_dist was a different quantity from the loop's.
  - The commit that added it moved the loop to the centerline_dice-optimal threshold (`select_topology_threshold`).
    The loop also scores the validation protocol's seeded sample, now v3, and takes its per-patch metrics on that
    sample's ink-containing patches.
  - **Change:**
    - The script scores the protocol's sample through `build_validation_dataset` and `collect_validation_predictions`,
      as `reevaluate_best_model.py` does. It does so in fp32, as the loop validates (`train.py`: `amp_enabled =
      False`), and it refuses an incomplete sample.
    - Its baseline row is the loop's measurement: `select_topology_threshold`'s threshold, no post-processing,
      skel_dist and centerline_dice on every 10th patch, and cc_diff on all of them.
    - The independent review checked this row: with the same predictions it is bit-for-bit what
      `reevaluate_best_model.py` computes.
    - The Dice-optimal threshold is swept too.
    - It prints the checkpoint's stored `avg_skel_dist`. It calls the two comparable only when the stored score's
      protocol and inputs fingerprint are this run's, and otherwise says what the stored score was measured on.
- **The metrics could be stand-ins.**
  - `train.py` finds villa relative to the working directory. Without it, `train.py` reports skel_dist and
    centerline_dice as NaN, and cc_diff as scipy's 4-connected count.
  - The script printed nothing about this.
  - **Change:** it refuses to run unless villa's skeleton, centerline and connected-component metrics imported.
- **Measurements that failed were dropped silently.**
  - Each skeleton and centerline computation sat in a bare `except Exception: pass`, and a NaN was left out of the
    mean without a count.
  - **Change:**
    - The metrics are no longer wrapped. A failure now raises, as it does in `reevaluate_best_model.py`.
    - A value that is not finite is still left out, and counted in a new `undef` column. Villa's skel_dist is NaN
      when the ground truth or the prediction has no skeleton branch, as when despeckling empties a prediction.
    - Dice is now taken on the despeckled mask that the other metrics see. It used to be taken on the raw threshold.
    - Villa's skeleton histograms go to their own folder: they are numbered from 1 in each process, and in the
      loop's folder they overwrote its files.
- **Tests** (`tests/test_diagnose_topology_postproc.py`, 11; none before). With the model load, the protocol and the
  metrics stubbed, they check:
  - despeckling;
  - the loop's sampling. Each patch's ink area names it, so the test checks which patches are measured: cc_diff on
    every patch, and the skeleton metrics on patches 0, 10 and 20;
  - that despeckling comes before every metric, and that an undefined value is counted;
  - that villa's metrics are required;
  - the checkpoint's whole recipe and recorded inputs. Every setting differs from config.json's defaults. Also
    `--unwarped`;
  - that the checkpoint's input check refuses a batch of the wrong shape;
  - fp32, and that only ink-containing patches reach the threshold and the metrics;
  - the baseline row, and when the stored score is called comparable;
  - the cache:
    - reused for the same key;
    - recomputed after a new checkpoint, other inputs, another protocol, `--refresh`, the warp, or an unreadable file;
    - never written for an incomplete sample or for inputs that differ from the key's;
    - a write failure does not lose the run;
  - that the bytes hashed are the bytes loaded.

  Against the original script, two fail and the rest cannot set up, since their stubs name functions it lacks. Each
  of these 27 mutants fails them:
  - the recipe or the recorded inputs not applied, or only some of the recipe;
  - the input check skipped;
  - all patches, not the ink-containing ones, given to the metrics or to the threshold;
  - the key without the checkpoint, the inputs, the protocol or the warp, or not checked;
  - every 5th patch, or patches 1, 11 and 21;
  - no despeckling;
  - the baseline at the Dice threshold;
  - AMP on;
  - villa's metrics not required, or the connected-components one not checked;
  - an incomplete sample accepted;
  - NaN averaged in;
  - `--unwarped` or `--refresh` ignored;
  - the stored score always called comparable;
  - the checkpoint loaded by path;
  - a write failure raised;
  - the dataset's fingerprint unchecked;
  - the loop's histogram folder.

## Verified, no change needed

- **`load_tool_checkpoint` loads this container's `best_model.pt` strictly.**
  - It is resenc_unet, 10,227,482 parameters, patch 64, 16 layers, with the ridge channel and multi-task heads.
  - config.json's recipe agrees with the checkpoint's.
  - Its stored scores are protocol `seeded-sample-400-v3+z1-27`, val_f1 0.266 and avg_skel_dist 31.3.
- **Villa's metrics on an emptied prediction:** skel_dist is NaN, centerline_dice 0, and cc_diff counts the
  ground-truth components. None of them raises, so a sweep that despeckles hard completes.
- **Importing `scripts.reevaluate_best_model`**, for `RECORDED_INPUT_SETTINGS`, has no side effects: no lock, signal
  handler or file. Four other scripts already import the constant from there.

## Observations for the owner (not changed)

- **`reevaluate_best_model.py` re-scores the incumbent with AMP on a GPU; the loop scores candidates in fp32.**
  - It passes `amp_enabled=device.type == "cuda"`, and has autocast on CUDA since before 2026-10-12. `train.py`'s
    validation runs with `amp_enabled = False`, set "for NaN debugging" on 2026-06-01.
  - So `--update-stored` on a GPU stores an incumbent val_f1 measured at another precision from the candidates it is
    compared with.
  - Passing `amp_enabled=False` there would make the two alike. This round leaves the choice to the owner, since it
    changes the stored score that promotions use.
- **Despeckling and cc_diff count components differently.**
  - `despeckle` uses scipy's default 4-connectivity. Villa's cc_diff counts 26-connected components, which is
    8-connected within a patch.
  - So a 1-pixel diagonal stroke is many components to the despeckle and one to cc_diff. A minimum size of 16 or 64
    erases it, which biases the sweep against post-processing on thin strokes.
  - `ndimage.label(mask, structure=np.ones((3, 3)))` would match cc_diff. That is a choice of method, so it is the
    owner's.
- **The sweep's grid is the June one:** thresholds 0.5 and 0.65 beside the two optimal ones, and minimum sizes 1, 16
  and 64.
- **The result was not re-measured here.** This container has `best_model.pt` but no validation data. Re-running it
  scores the current model on the v3 sample at the loop's threshold, per patch. Its numbers are therefore not
  comparable with June's.
- **The cache key does not cover code changes** to the loader or preprocessing. `--refresh` scores afresh after one.
- **The checkpoint-to-config assembly is repeated:** the settings, then the recorded inputs, then `--unwarped`. It
  now appears in `reevaluate_best_model.py`, this script and several probes. A helper in `checkpoint_tools` would
  give them one copy.
- **The new test is not in the standard suite.** The script is not one of the loop's entry points, so
  `test_validation_suite_covers_the_loop` does not require it. It runs under `pytest tests/`.

## Verification

- `pytest tests/test_diagnose_topology_postproc.py`: 11 passed.
- `scripts/diagnose_topology_postproc.py --help` runs.
- Ruff 0.9.10, ruff format and mypy are clean on the changed files.
- **The standard suite** on the first commit (`41af7360`) ran as on main: 2701 passed, with the same 42 failures and
  2 errors, all environmental. The smoke test gave 9 of 11 passed and 2 skipped, as on main.
- **Independent review** of the first commit found nothing blocking.
  - It confirmed:
    - the baseline row equals `reevaluate_best_model.py`'s numbers bit for bit, on 60 synthetic patches with villa's
      real metrics;
    - the stub signatures match the real functions;
    - the cache loads with `weights_only=True`;
    - the checkpoint facts;
    - `d38a20e3`'s content.
  - Its should-fix findings:
    - the stored score compared without its protocol or inputs;
    - AMP on a GPU, unlike the loop, and the cache key without it;
    - the checkpoint hashed and loaded separately;
    - villa's stand-in metrics accepted silently;
    - eight surviving mutants;
    - despeckling's connectivity, which is the observation above.
  - Its nits:
    - code changes not in the key;
    - a failed cache write losing the run;
    - the fingerprint not checked against the dataset's;
    - the histogram folder;
    - the import's side effects;
    - this document's claims about the original tests, the NaN cases, `multi_task_heads`, "since 2026-06-10" and June's
      per-batch skel_dist.

  All are addressed above, as changes or observations.
