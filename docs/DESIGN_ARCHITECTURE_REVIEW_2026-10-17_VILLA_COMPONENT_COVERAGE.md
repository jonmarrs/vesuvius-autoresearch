# Design and architecture review — the villa component coverage report

Date: 2026-10-17. Baseline: `f7fed791` (main after #111). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/build_villa_component_coverage.py`, which maps official villa components to local hooks and writes
`reports/villa_component_coverage.{json,md}`. It runs as a step of the post-sprint handoff
(`scripts/run_post_sprint_villa_handoff.py`), one of the loop's entry points. Earlier reviews only ran its tests.
The search started from top-level code no review had mentioned: `v3_training/`, the two `generate_*.py` scripts,
`submission_package_dry_run/` and `notebooks/`. This script was the one of them still on a live path.

## What changed

- **Six local hooks pointed at paths that had moved.**
  - The 2026-06-02 refactor (`c26a921e`) moved these hooks:
    - `vesuvius_loader.py` to `src/vesuvius_autoresearch/core/`;
    - `train.py` to `scripts/training/`;
    - `predict.py` to `scripts/inference/`;
    - `test_import.py` to `tests/`;
    - `generate_fiber_labels.py` to `scripts/labeling/`.

    `check_loader.py` went to `scripts/archive/`.
  - The list still named the old paths. So every regeneration reported `vesuvius` and `segmentation` as `partial`,
    `foundation` as `unwired`, and their hooks as missing.
  - The committed report carried a hand-written "historical snapshot" caveat for this. The renderer did not write
    that caveat, so the handoff's next regeneration would have overwritten it.
  - The moved hooks now name their current paths. The archived `check_loader.py` is dropped: nothing references it.
- **Official paths are read from the pin, not the checkout.**
  - `_path_exists("villa/...")` tested the working tree, so a sparse villa checkout (as here) reported
    `ink-detection` and `volume-cartographer` as missing although the pin has both.
  - `_official_present` reads villa's own HEAD tree (`git cat-file -e HEAD:<path>`) when villa is a git checkout,
    and the working tree otherwise.
  - The report records the commit it read (`villa_commit`).
- **Components villa moved to `deprecated/` are reported as such.**
  - At the pin, `crackle-viewer` and `thaumato-anakalyptor` live under `villa/deprecated/`. Even a full checkout
    reported them as `missing_official_component`.
  - A new status, `deprecated_upstream`, names the deprecated path and is counted in the summary.
  - The Thaumato row's next action now says what the old caveat said: the legacy solver sweep is retired here
    (`docs/SHEET_GRAPH_DIAGNOSTICS.md`).
- **The caveat is rendered.** The report now says it checks paths only, that a present hook is not shown to run,
  and that nothing in it is scientific validation. So regeneration keeps the caveat.
- **The committed report is regenerated** from the pin: 6 `covered`, 2 `deprecated_upstream`. Before, it read 4
  `covered`, 3 `partial`, 1 `unwired`.
- **Four tests:**
  - the rendered caveat;
  - the deprecated status;
  - official paths read from the pinned tree, not the checkout (a scratch git repo with a committed directory
    deleted from its working tree);
  - every listed hook exists in this repository, so a move cannot go stale silently again.

## Verified, no change needed

- `test_post_sprint_villa_handoff.py`, which drives the handoff's command list, passes unchanged.
- The `required_hooks` logic (`blocked_missing_required_hook`) is unchanged and still tested.

## Observations for the owner (not changed)

- **`covered` means the paths exist, nothing more.**
  - `ink-detection` is `covered` because `villa/ink-detection/` exists at the pin, but it holds only
    `optimized_inference/`. The Grand Prize recipes its "prize use" names are under `deprecated/ink-detection/`.
  - `vesuvius` counts `v3_training/trainer.py`, which nothing has run or imported since June.

  A coverage report that checked hooks run, rather than exist, is a larger design change.
- **Legacy top-level code with no caller:**
  - `v3_training/` (it imports villa's `multi-task-3d-unet` trainer, present at the pin);
  - `generate_fiber_image.py` and `generate_real_scroll_evidence.py`;
  - `notebooks/`.

  These are unchanged since May or June. Nothing references them outside `scripts/archive/`, except this report's
  `v3_training` hook.
  Whether to archive them is the owner's call.
- **Two components the next actions recommend are deprecated upstream.** `crackle-viewer`'s next action
  recommends human review in it; `thaumato-anakalyptor`'s is now marked retired. Whether to keep using deprecated
  villa tools is the owner's call.

## Verification

Environment: CPython 3.10 venv. Villa is at the pin (`ccb431818`), in a sparse checkout without `ink-detection/`,
`volume-cartographer/` or `deprecated/`.

- **Tests:** `pytest tests/test_villa_component_coverage.py tests/test_post_sprint_villa_handoff.py`: 11 passed.
- **Mutation check** over the full tracked tree, with the bytecode cache cleared. Each mutation fails one test:
  - the old hook paths;
  - working-tree presence;
  - no deprecated status;
  - no rendered caveat.
- **Regeneration:** `scripts/build_villa_component_coverage.py`, run here, gives 6 covered and 2 deprecated
  upstream, with `villa_commit` `ccb431818…`. On a full checkout at the pin it gives the same, since it reads the
  tree.
- **Lint:** Ruff clean.
- **The standard suite:** see the PR.
