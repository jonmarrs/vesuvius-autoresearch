# Design and architecture review — the villa component coverage report

Date: 2026-10-17. Baseline: `f7fed791` (main after #111), merged with `f85e0f7d` (#109). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/build_villa_component_coverage.py`, which maps official villa components to local hooks and writes
`reports/villa_component_coverage.{json,md}`. It runs as a step of the post-sprint handoff
(`scripts/run_post_sprint_villa_handoff.py`), one of the loop's entry points. No earlier review changed the script:
they ran its tests, and the 2026-10-11 review (`61981146`) added a caveat to the committed report by hand.
The search started from top-level code no review had mentioned: `v3_training/`, the two `generate_*.py` scripts,
`submission_package_dry_run/` and `notebooks/`. This script was the one of them still on a live path.

## What changed

- **Six local hooks pointed at paths that had moved.**
  - Refactors in May and June 2026 moved them, each as a pure rename:
    - `test_import.py` to `tests/` (`9f853d64`, 2026-05-12);
    - `vesuvius_loader.py` to `src/vesuvius_autoresearch/core/` (`c26a921e`, 2026-06-02);
    - `train.py` to `scripts/training/` and `predict.py` to `scripts/inference/` (`4d9388e1`, 2026-06-02);
    - `scripts/generate_fiber_labels.py` to `scripts/labeling/` (`ed0714a7`, 2026-06-02).

    `check_loader.py` went to `scripts/` (`d3454e9e`, 2026-05-12), then to `scripts/archive/` (`bde5a5d5`).
  - The list still named the old paths. So every regeneration reported `vesuvius` and `segmentation` as `partial`,
    `foundation` as `unwired`, and their hooks as missing.
  - The committed report carried a hand-written "historical snapshot" caveat for this. The renderer did not write
    that caveat, so the handoff's next regeneration would have overwritten it.
  - The moved hooks now name their current paths. The archived `check_loader.py` is dropped: nothing references it.
- **Official paths are read from the pin, and the checkout is reported beside them.**
  - `_path_exists("villa/...")` tested the working tree, so a sparse villa checkout (as here) reported
    `ink-detection` and `volume-cartographer` as missing although the pin has both.
  - The pin is the commit this repository's HEAD records for `villa` (`git ls-tree HEAD villa`), not villa's own
    HEAD. So a villa checked out at another commit, as while reviewing a pin bump, does not change the answer.
  - Each path is looked up in that commit's tree with `git rev-parse --verify -q <pin>:<path>`. (`cat-file -e`
    would fetch a file's blob in villa's `blob:none` partial clone, and fail offline.)
  - Whether each path is also in the working tree is recorded (`official_checked_out`, `deprecated_checked_out`)
    and rendered as "(not checked out)". The working tree is what a local tool reads: the handoff's next step,
    `build_volume_cartographer_readiness.py`, reports Volume Cartographer `blocked` on this checkout ("Official
    component present: `False`") while this report has it `covered`. The mark says why. The summary counts the
    components with such a path.
  - **When the pin's tree cannot be read, the working tree answers, and the report says so.** The report's `source`
    and its rendered caveat name the reason. The cases are:
    - villa is not a git checkout;
    - git is not installed;
    - `villa/.git` does not open villa's own repository: an empty directory (from which git reads the enclosing
      repository), a broken gitfile, or git's refusal of a repository with another owner;
    - this repository's HEAD records no pin;
    - the pin is not in villa's object store.

    The first version read any git failure as "component absent", so a broken gitfile reported every component
    missing.
  - Git runs without the locator variables a hook exports (`GIT_DIR`, `GIT_INDEX_FILE`, ...), as
    `scripts/audit_doc_references.py` does. With `GIT_DIR` set, every call would read the superproject instead.
  - The report records the commit it read (`villa_commit`), or none.
- **Components villa moved to `deprecated/` are reported as such.**
  - At the pin, `crackle-viewer` and `thaumato-anakalyptor` live under `villa/deprecated/`. Even a full checkout
    reported them as `missing_official_component`.
  - A new status, `deprecated_upstream`, is counted in the summary.
  - The deprecated path is named whenever the pin has it, in a new "Villa path" column. So `ink-detection`, which
    is in both places, shows `villa/deprecated/ink-detection` too: its "prize use" recipes are there.
  - The Thaumato row's next action now says what the old caveat said: the legacy solver sweep is retired here
    (`docs/SHEET_GRAPH_DIAGNOSTICS.md`).
- **The caveat is rendered.** The report now says it checks paths only, that a present hook is not shown to run,
  and that nothing in it is scientific validation. It also says where official paths were read from. So
  regeneration keeps the caveat.
- **The committed report is regenerated** from the pin: 6 `covered`, 2 `deprecated_upstream`.
  - The committed version was a hand-annotated snapshot reading 4 `covered`, 3 `partial`, 1 `unwired`.
  - The old tool, run at this pin, gives 1 `covered`, 2 `partial`, 1 `unwired` and 4 missing on this sparse
    checkout. On a full checkout it would give 2, 3, 1 and 2.
  - Four of its components have a villa path not checked out here. That describes this checkout; the owner's
    next handoff run regenerates it.
- **Tests,** in a scratch superproject that pins a scratch villa, with git's locator variables and global config
  removed:
  - official paths read from the pin's tree, not the checkout, and marked not checked out;
  - the pin is the superproject's gitlink, not villa's HEAD;
  - a hook-style `GIT_DIR` does not redirect the lookup;
  - an unreadable pin (a broken gitfile, an empty `villa/.git`, no git) falls back to the working tree and says so;
  - a deprecated copy is named beside a current component;
  - the rendered caveat and the deprecated status;
  - every listed hook exists in this repository, so a move cannot go stale silently again.

## Verified, no change needed

- `test_post_sprint_villa_handoff.py`, which drives the handoff's command list, passes unchanged.
- The `required_hooks` logic (`blocked_missing_required_hook`) is unchanged and still tested.

## Observations for the owner (not changed)

- **`covered` means the paths exist, nothing more.**
  - `ink-detection` is `covered` because `villa/ink-detection/` exists at the pin, but it holds only
    `optimized_inference/`. The Grand Prize recipes its "prize use" names are under `deprecated/ink-detection/`.
  - `vesuvius` counts `v3_training/trainer.py`, which nothing has run or imported since June.
  - `segmentation` counts `tests/test_import.py`, which has no test function. It prints "Dice imported" without
    importing it, and tries one metric import whose failure it prints and skips.
  - `ink-detection` counts `scripts/training/train.py`, whose ties to it are a `sys.path` entry and a comment
    citing `train_timesformer_og.py`, a file the pin has only under `deprecated/ink-detection/`. The detector
    (`src/vesuvius_autoresearch/detector/`, the TimeSformer recipe port) is arguably the closer hook.

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

- **Tests:** `pytest tests/test_villa_component_coverage.py tests/test_post_sprint_villa_handoff.py`: 17 passed.
- **Mutation check** over the full tracked tree, with the bytecode cache cleared. Each mutation fails at least one
  test:
  - on the first commit: the old hook paths, working-tree presence, no deprecated status, no rendered caveat;
  - on the second:
    - git run with the hook's locator variables;
    - villa's HEAD read instead of the gitlink;
    - a git failure read as absent;
    - a crash when git is missing;
    - the deprecated copy named only for an absent component;
    - no "not checked out" mark;
    - the pin's commit not rendered;
    - one caveat for both sources.
- **Regeneration:** `scripts/build_villa_component_coverage.py`, run here, gives 6 covered and 2 deprecated
  upstream, with `villa_commit` `ccb431818…`. The independent review reproduced the first commit's report byte for
  byte from the pin's objects with no villa working tree.
- **Lint:** Ruff clean.
- **The doc-reference audit.** The report now cites six villa paths. `test_audit_doc_references.py`'s
  `test_live_documents_stay_clean` checks paths against the working tree, so on this sparse checkout it lists all
  six as stale. It already failed here on main, for 14 other paths, and it is not in the standard suite. The pin has
  all six (`git ls-tree ccb431818`), so a full checkout passes them.
- **Independent review** of the first commit. It found:
  - the hook moves credited to one commit;
  - any git failure read as "absent";
  - git calls open to a hook's `GIT_DIR`, and a test that could commit into an enclosing repository;
  - "pinned" claimed for villa's HEAD;
  - the disagreement with the readiness report;
  - `cat-file -e` in a partial clone;
  - several smaller points.

  All are addressed above.
- **The standard suite:** see the PR.
