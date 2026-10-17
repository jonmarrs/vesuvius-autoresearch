# Design and architecture review — the detector reproduce's fragment conversion

Date: 2026-10-17. Baseline: `6d7acd52` (main after #108), merged with `3b22a7ee` (#106). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the first step of `python -m vesuvius_autoresearch.detector.cli reproduce` (`REPRODUCE.md` §5).
`cli._reproduce` converts each fragment's uint16 layers in `local_data/` into the 8-bit `layers/` tree the
detector reads, using `repro/gp_winner/convert_fragment.py`. The detector review of 2026-10-04 covered training,
inference and evaluation, not this step.

## What changed

- **A partial conversion was trusted.**
  - `_reproduce` converted a fragment only when `<data_root>/<fragment>/layers` did not exist. `convert_fragment`
    creates that directory before writing any layer, so any interrupted conversion left it in place, and every
    later `reproduce` skipped conversion. It then failed at `read_volume_mask` on the first missing layer
    (`could not read layer`), with nothing saying that the cached conversion was the cause.
  - `cv2.imwrite` wrote each layer under its final name, so an interruption mid-write left a truncated TIFF there.
    `cv2.imread` returns `None` for such a file (checked cut at 0, 30, 60, 95, 99 and 99.9%, and 1, 8 and 64 bytes short),
    so that too ended in `could not read layer`, on every re-run, until the directory was deleted by hand.
  - The new `_is_converted` checks the files `data.read_image_mask` reads, found the way it finds them:
    - each layer in the configured range;
    - the mask;
    - exactly one `*inklabels.*` under any name, so a villa-style `<id>_inklabels.tiff` counts.

    `_ensure_converted` converts any fragment that fails the check.
  - `convert_fragment` writes every file to a hidden `.<name>.part`, flushes it to disk, and renames it. An
    interrupted conversion therefore lacks files rather than holding truncated ones under their final names.
    - The `.part` is hidden so no reader's glob can take it for a finished file. The first version named it
      `<id>_inklabels.png.part`, which the detector's `*inklabels.*` glob matched, so an interrupted label copy
      left "found 2" on every later run.
    - The layer bytes are `cv2.imencode(".tif")`'s, byte-identical to what `cv2.imwrite` wrote. The independent
      review checked this under OpenCV 5.0.0 (this venv) and 4.13.0 (`uv.lock`), at the real Fr47 and Fr143 shapes.
- **The conversion ignored the configured layer range.**
  - `--config` may set `start_idx` and `end_idx` (validated to span `in_chans`), and `read_volume_mask` reads
    exactly that range. `_reproduce` always converted the default 17–42.
  - With `start_idx` 11, the old code therefore failed with `could not read layer: .../layers/11.tif`. A cached
    conversion from another range was reused the same way.
  - The check and the conversion now both use the configured range. `convert_fragment.py`'s own command line gains
    `--z-start` and `--z-end` to match.
- **Smaller.**
  - `_ensure_converted` appends `repro/gp_winner` to `sys.path` once, not on every call.
- **The conversion's tests now run in the standard suite.** `tests/test_convert_fragment.py` was not in
  `scripts/run_validation_tests.py`. It now is, with seven new tests:
  - a conversion missing one layer is redone, and a complete one is not;
  - a configured range of 11–36 is what is converted and read back;
  - an existing 17–42 conversion is redone for 11–36;
  - a conversion missing its mask is redone;
  - a conversion stopped before its fourth rename leaves three layers;
  - an interrupted label copy leaves the fragment readable, with one label;
  - a label named `<id>_inklabels.tiff` counts as converted.
- **`REPRODUCE.md` §5** says to run from the repository root, what the conversion reads, and when it is redone.

## Verified, no change needed

- `convert_layer_u16_to_u8` keeps the high byte (`//256`), and `read_volume_mask` applies the recipe's `clip(0, 200)`
  afterwards, as the module docstring says.
- `read_volume_mask` and `read_image_mask` fail loudly on a missing or unreadable layer, label or mask, and on a
  shape mismatch. None of these failures let the reproduce run on bad input. They left it failing on every re-run.
- `convert_fragment` is called only by `cli._ensure_converted`, its own `main()` and its tests. `train`, `infer`,
  `eval` and `measure` do not convert.
- The reproduce's fragments (train `PHercParis2Fr47`, held out `PHercParis2Fr143`) and its pixel-AUC ≥ 0.70
  assertion are unchanged.

## Observations for the owner (not changed)

- **`data_root` defaults to `villa/ink-detection/train_scrolls`**, inside the villa submodule's working tree. This
  repository's `.gitignore` lists the path, but a superproject's ignore rules do not apply inside a submodule. So
  a conversion writes untracked files into villa's tree, unless villa's own ignore rules cover them; those could not
  be read here. Moving the default outside `villa/` would change where existing conversions are found, so it is the
  owner's call.
- **The source is not checked before conversion starts.** `src_root` is `local_data`, relative to the working
  directory. A missing source layer fails at its own read.
- **A `.part` left by an interrupted run stays until the next conversion of that file overwrites it.** It is hidden
  and no reader opens it.

## Verification

Environment: CPython 3.10 venv (OpenCV 5.0.0), no GPU visible. No scroll data here; the tests build small fragments.

- `tests/test_convert_fragment.py`: 9 passed.
- Mutation check over eight mutations, each run with the bytecode cache cleared. Every one fails at least one test:
  - the `layers/`-exists check: 4 failed;
  - converting the fixed 17–43: 1 failed;
  - checking the fixed 17–43: 1 failed;
  - layers written straight to their final names: 1 failed;
  - the mask not checked: 1 failed;
  - labels copied straight to their final names: 1 failed;
  - a visible `.part` name: 1 failed;
  - the label checked under its converted name only: 1 failed.
- `CUDA_VISIBLE_DEVICES="" pytest tests/test_detector_*.py tests/test_convert_fragment.py`: 211 passed, 1 skipped
  on the first commit.
- Ruff clean on the changed files. The one line `ruff format` would still change is in an existing test.
- An independent review of the first commit found the `.part` name matching the label glob. It also found that the
  label check named a file the reader does not require, and that three behaviours were untested. All are addressed
  above.
- The standard suite: see the PR.
