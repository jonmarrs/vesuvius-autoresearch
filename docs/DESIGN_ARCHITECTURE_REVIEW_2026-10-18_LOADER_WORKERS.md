# Design and architecture review — persistent loader workers (#113), with #115–#117

Date: 2026-10-18. Baseline: `d9b83efb` (main after #121). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the owner's #113 (`655c8117`, merged as `3b7532ce`), which keeps the training loader's workers across
passes:
- `train.shuffled_loader`;
- `scripts/loader_pass_cost.py`;
- `scripts/epoch_boundary_overhead.py`, with #120's restart correction;
- `reports/loader_epoch_boundary_2026-10-17.md` and its JSON;
- the tests.

Also read for the same class of risk, a change to what training reads or writes: #115 (file modes of atomic
writes), #116 (the unlabeled grid's far edges) and #117 (16-bit labels and masks).

**No defect found; nothing is changed.** This document records what was checked.

## Verified, no change needed

- **The batch order is the in-process loader's, per seed.**
  - The sampler draws each pass's permutation from its own generator (`order`). Each new or reset iterator calls
    `iter(sampler)`, which draws from it once.
  - A new iterator draws its worker base seed from the loader's own generator (`worker_seeds`); a persistent
    iterator's reset draws none. So the two streams no longer interleave, and the reset changes nothing.
  - Checked beyond the test's 2 workers and 3 passes:
    - **3 workers (the loop's count), 5 passes of 37 items at batch 4:** identical to in-process, and all 5 passes
      distinct.
    - **A reset mid-pass** (a new `iter()` after 3 batches): every later pass identical to in-process.
- **What a worker computes does not depend on the worker.**
  - The labeled dataset's crop and depth draws come from `np.random.RandomState(idx + seed)`, per item. A worker
    that lives across passes gives the same patch for an index as a fresh one would.
  - The augmentations that use the global RNG run in the training process.
  - The unlabeled loader runs in-process (`workers=0`), and `persistent_workers` is set only when workers > 0, so
    PyTorch's `ValueError` for 0 workers cannot arise.
- **Worker lifetime is unchanged in effect.**
  - Before, one set of workers lived per pass. The exhausted iterator shut its workers down before the next
    spawned, and the in-flight iterator's workers lived through validation.
  - Now one set lives for the run, and is shut down by the existing `del data_iter, data_loader`.
  - Per-worker memory is bounded by one pass, which already reads the whole catalogue.
  - `_init_worker`'s `os._exit` handler still runs once per worker, and the exit test covers a dropped loader
    holding a persistent iterator.
- **The warning counts.**
  - `share_warning_counts` runs once per worker and sums into the Manager dict for the whole run, as before.
  - Only the per-process print limit now spans the run instead of a pass.
- **No recorded seed is replayed.** Each run draws `sampling_seed` from `os.urandom`, and nothing feeds a stored
  `train_sampling_seed` back into training, so the changed order per seed breaks nothing. No document claims that
  a seed reproduces a run's batches.
- **The report's numbers** were recomputed from the committed JSON with the script's own `fit`:
  - the 72-cycle fit is 84.3 s + 21.29 s per boundary (residual SD 16.5 s);
  - the 75-cycle fit, with the three cycles after a restart, is 86.2 s + 20.97 s (SD 19.7 s);
  - the killed cycle's predictions are 403.7 s and 400.8 s;
  - the boundary table's medians and ranges, the 10,360-step median of the 60-minute batch-4 cycles (n = 9), the
    106 s per 60-minute cycle, and the in-process control's 55 s against 185 s.

  The killed cycle's 28,970 steps at batch 4 cross 15 boundaries.
- **Epoch boundaries counted from steps.**
  - The script takes `steps × batch_size // 7345`, from the last printed step; train.py prints every 10 steps.
  - A pass is ⌈7345 / batch_size⌉ steps, so near a multiple the two counts can differ by one.
  - On every committed row they agree. The closest row, in the in-process control, is 3 steps past a boundary.
- **#115.** `replacement_mode` keeps the replaced file's mode, or gives a new file 0666 less the umask.
  `save_checkpoint_atomic` and the loop's JSON writer apply it to the temporary file before writing.
- **#116.** `_grid_starts` matches inference's flush-edge tiling. A volume smaller than a patch now warns and
  contributes nothing.
- **#117.** `load_unit_image` divides by 255 when the peak is at most 255, and by 65535 above that, and keeps 0/1
  images. It refuses anything still outside [0, 1]. The labeled dataset and the validation dataset both read
  through it.

## Observations for the owner (not changed)

- **The detector's label reader keeps the old rule.** `detector/data.read_image_mask` reads the label with
  `cv2.imread(path, 0)` and divides by 255.
  - OpenCV reduces a 16-bit PNG to 8 bits, so #117's 16-bit case reads correctly there.
  - A 0/1 label would become 1/255, which `_tiles_for_fragment` takes as no ink (`< 0.05`). The loop's loader
    keeps 0/1.
  - The detector reproduce's AUC of 0.709 implies its labels are 0/255. Changing the reader would touch that
    recorded result, so it is left.
- **`scripts/epoch_boundary_overhead.py` hardcodes the catalogue (7,345, Fr47) and infers the budget from the
  sprint log's name.** The report proposes re-running it after a pull to check that the overhead stops rising
  with boundaries. Each run's own "Valid Patches" line would be the safer source if the labeled catalogue changes.
- **The committed `epoch_boundary_overhead_workers.json` is the 72-cycle run.** The script, as corrected in #120,
  now includes the three cycles after a restart. The report says the table uses the 72, and the 75-cycle fit is
  in `epoch_boundary_overhead_restarts.json`.
- **The fix's effect on the loop is predicted, not measured.** No shift since #113 is committed.
- **An unlabeled catalogue that is empty in every volume still stops the run.** `RandomSampler` refuses zero
  items when the loader is built. #116 now warns first. Without unlabeled patches UA-MT has nothing to read, so a
  loud stop is arguably right.

## Verification

Environment: CPython 3.10 venv, CPU only (no GPU visible), no scroll data.

- `pytest tests/test_loader_workers.py`: 14 passed.
- The order check above, with `train.shuffled_loader` against a 37-item index dataset: identical in both cases.
- The fits recomputed with `epoch_boundary_overhead.fit` on the committed rows.
- The boundary formula compared with `(steps + 1) // ⌈7345 / batch_size⌉` on every committed row.
- The standard suite: see the PR.
