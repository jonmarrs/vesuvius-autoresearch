# Design and architecture review — the detector reproduce's fragment conversion

Date: 2026-10-17. Baseline: `6d7acd52` (main after #108). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the first step of `python -m vesuvius_autoresearch.detector.cli reproduce` (`REPRODUCE.md` §5).
`cli._reproduce` converts each fragment's uint16 layers in `local_data/` into the 8-bit `layers/` tree the
detector reads, using `repro/gp_winner/convert_fragment.py`. The detector review of 2026-10-04 covered training,
inference and evaluation, not this step.

## What changed

- **A partial conversion was trusted.**
  - `_reproduce` converted a fragment only when `<data_root>/<fragment>/layers` did not exist. A conversion
    interrupted after its first layer left that directory in place, so every later `reproduce` skipped conversion.
    It then failed at `read_volume_mask` on the first missing layer (`could not read layer`), with nothing saying
    that the cached conversion was the cause.
  - `cv2.imwrite` wrote each layer under its final name, so an interruption mid-write left a truncated TIFF there.
    Here `cv2.imread` returns `None` for a TIFF cut at 30%, 60% or 95%, so that too ended in `could not read
    layer`. Every re-run then failed the same way, until the fragment's directory was deleted by hand.
  - The new `_ensure_converted` checks every file the detector will read for the fragment: each layer in the
    configured range, the ink labels and the mask. It converts again if any is missing.
  - `convert_fragment` now writes every file to a `.part` and renames it, so an interrupted conversion lacks files
    rather than holding truncated ones. The layer bytes are `cv2.imencode(".tif")`'s, byte-identical to what
    `cv2.imwrite` wrote (checked on a 300×257 array).
- **The conversion ignored the configured layer range.**
  - `--config` may set `start_idx` and `end_idx` (validated to span `in_chans`), and `read_volume_mask` reads
    exactly that range. `_reproduce` always converted the default 17–42.
  - With `start_idx` 11, it therefore converted layers the detector does not read, and the detector failed on
    layer 11. A cached conversion from another range was reused the same way.
  - `_ensure_converted` passes the configured range to `convert_fragment`, and checks it.
- **The conversion's tests now run in the standard suite.** `tests/test_convert_fragment.py` was not in
  `scripts/run_validation_tests.py`. It now is, with three new tests:
  - a conversion missing one layer is redone, and a complete one is not;
  - a configured range of 11–36 is what is converted and read back;
  - a conversion stopped before its fourth rename leaves three layers and no labels, and nothing under a final name
    it had not finished.

## Verified, no change needed

- `convert_layer_u16_to_u8` keeps the high byte (`//256`), and `read_volume_mask` applies the recipe's `clip(0, 200)`
  afterwards, as the module docstring says.
- `read_volume_mask` and `read_image_mask` fail loudly on a missing or unreadable layer, label or mask, and on a
  shape mismatch, so none of these left the reproduce running on bad input. They did leave it failing on every re-run.
- The reproduce's fragments (train `PHercParis2Fr47`, held out `PHercParis2Fr143`) and its pixel-AUC ≥ 0.70
  assertion are unchanged.

## Observations for the owner (not changed)

- **`data_root` defaults to `villa/ink-detection/train_scrolls`**, inside the villa submodule's working tree. This
  repository's `.gitignore` covers that path, but a conversion still writes into the submodule's tree. Moving the
  default outside `villa/` would change where existing conversions are found, so it is the owner's call.
- **Converting from `local_data/`** assumes `<fragment>/surface_volume/NN.tif`, `inklabels.png` and `mask.png` there.
  The source is not checked before conversion starts; a missing layer fails at its own read.

## Verification

Environment: CPython 3.10 venv, no GPU visible. No scroll data here; the tests build small fragments.

- `tests/test_convert_fragment.py`: 5 passed.
- Mutation check, each run with the bytecode cache cleared; each mutation fails exactly one test:
  - restoring the `layers/`-exists check: 1 failed;
  - restoring the fixed 17–43 range: 1 failed;
  - writing layers straight to their final names: 1 failed.
- `CUDA_VISIBLE_DEVICES="" pytest tests/test_detector_*.py tests/test_convert_fragment.py`: 211 passed, 1 skipped.
- Ruff clean on the changed files. The one line `ruff format` would still change is in an existing test.
- The standard suite: see the PR.
