# Design and architecture review — the render-equivalence checker

Date: 2026-10-18. Baseline: `6316c9bf` (main after #129). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/check_render_equivalence.py`.
- `check_villa_render_path.py` (#129) asks whether a villa ref moved anything on the render path. This script asks
  the next question: can that change reach a render?
- Its verdicts:
  - INTERCHANGEABLE: identical trees;
  - RENDERS MAY DIFFER: an entry point changed;
  - RENDER-INERT: nothing the entry points import, or the flatten, changed;
  - NEEDS A HUMAN.
- `repro/spiral_render/README.md` §13 prescribes it when villa moves. Two preregistrations and one report cite its
  verdicts.
- Its own tests name the dangerous failure: "a false INTERCHANGEABLE … would let a corpus split silently". A false
  RENDER-INERT is the same failure one step later.

The script had no review. This round also swept the scripts that run git in `villa/` for the hazard #124 and #129
fixed: in an empty directory, an uninitialised submodule, git answers for the repository around it.

## What changed

- **Every git failure read as the permissive verdict.**
  - Its `git()` returned `""` on any failure:
    - a tree lookup that failed matched one that failed at the other ref;
    - a `git show` that failed gave an entry point no imports;
    - a `git diff` that failed gave no changed files.
  - Main's verdict in each case, which the new tests cover:
    - **An empty `villa/`.** Run here on an empty directory inside this checkout, it compared this repository's own
      commits (`89ab4b6ee -> 6316c9bf9`), found none of the three trees at either ref, and printed "INTERCHANGEABLE
      — every extracted path is the same tree object … No render can differ", with exit 0.
    - **An inherited `GIT_DIR`** (a hook's): INTERCHANGEABLE, for a range that changes a module `render_ink.py`
      imports.
    - **A tree at neither ref, or an entry point at neither ref:** RENDER-INERT.
    - **An entry point whose blob cannot be read:** RENDER-INERT, for a change to `tifxyz.py`, which it imports.
      Villa's clone is blob:none, so a blob may not be local: `render_ink.py` at `9afddaf0f` is not, nor
      `get_ink_metrics.py` at `757f70c01`. Offline, that fetch fails.
    - **A ref that does not resolve:** exit 1, as from the other errors.
  - It now uses `check_villa_render_path`'s `git` and `not_own_repository`:
    - a git call that fails exits 2, with git's message;
    - git's locator and pathspec variables are dropped;
    - a directory that is not a repository of its own exits 2.
  - A path at neither ref exits 2; that covers the three extracted trees and the two entry points. `tree()` reads
    each from its parent tree's entry, so it returns None for an absent path rather than an empty string that
    equals another. A path at one ref only still compares as different.
- **A change to a library the flatten imports read RENDER-INERT.** The independent review found it.
  - `lasagna/fit.py` imports `atlas`, whose `vc3d_fiber_format_adapter.py` puts `vesuvius/src` on `sys.path` and
    imports `vc3d_fiber_format`. `repro/spiral_render/run_render.sh` says so too.
  - The flatten is a pipeline stage, so it was never import-traced. `vesuvius/src/vc3d_fiber_format/` was in no
    stage.
  - On real villa ranges that change only its `__init__.py`, `757f70c01..b944a656c` and `59b454a81..41701aa0e`,
    main printed RENDER-INERT.
  - It is now in `STAGE_LIBRARIES`, whose non-test, non-doc changes are suspects like the flatten's. Both ranges
    now read NEEDS A HUMAN.
- **A package's change was never a suspect.** Changed files were matched by stem against the names the entry
  points import, and a package's `__init__.py` has the stem `__init__`. A file now also matches by the name an
  import resolves to: its first component below `spiral-fitting/` or `vesuvius/src/`. So
  `spiral-fitting/tifxyz/__init__.py` is `tifxyz`, and `vesuvius/src/vesuvius/...` would be `vesuvius`. Matching
  on any path component instead named `vesuvius/src/vesuvius/tifxyz/reader.py` for `import tifxyz`, so it was not
  used.
- **A module moved away from its import read RENDER-INERT.** The changed-file listing detected renames.
  - With `spiral-fitting/tifxyz.py` moved to `tifxyz_old.py`, only the new name was listed. Nothing imports it, so
    the verdict was RENDER-INERT while `render_ink.py`'s import of `tifxyz` broke.
  - It now uses `--no-renames`, which lists both sides and reads trees only, and `-z` for names git would quote.
- **Smaller fixes:**
  - **Refs are resolved once, and the SHAs are used throughout.** The README runs it against `origin/main`, which
    the upstream monitor fetches, so a fetch mid-run could move it between calls.
  - **An entry point that is not a regular file exits 2.** A symlink or a submodule entry was compared as the link,
    not what it points to.
  - **The sibling import resolves the script's directory.** `build_stripmatch_dataset.py`'s pattern uses
    `abspath`, which keeps a symlink's directory, so a launch through one under `python -I` did not find
    `check_villa_render_path.py`.
- **Docs.** The docstring says when it exits 2.
- **Tests** (`tests/test_check_render_equivalence.py`, 14 new), against a throwaway villa-shaped repository:
  - an imported module's change still NEEDS A HUMAN;
  - the empty directory, a tree at neither ref, an entry point at neither ref, an unresolvable ref, an inherited
    `GIT_DIR`, and an unreadable entry-point blob;
  - a tree or entry point at one ref only;
  - a module moved away from its import;
  - a package;
  - the flatten's library;
  - a quoted name;
  - a symlinked entry point;
  - a symlinked launch under `-I`.

## Verified, no change needed

- **The verdicts on real ranges are unchanged, except the two corrected above.** Main's script and this one give
  the same verdict and the same suspects, with exit 0, for 12 ranges:
  - the four refs cleared by hand on 2026-09-14 against `be09a8503` (INTERCHANGEABLE);
  - `d9d70bef1`, `1f544fa71` and `0e01fe1c7` against `be09a8503` (NEEDS A HUMAN);
  - `d8c5f488a..be09a8503`, the 09-11 split (NEEDS A HUMAN);
  - `d8c5f488a..d82e13edf`, the report's comparison (NEEDS A HUMAN);
  - `be09a8503..9afddaf0f` (RENDERS MAY DIFFER);
  - `ccb431818..b29f3109` (INTERCHANGEABLE);
  - a ref against itself.

  Only the suspects line's label is reworded, to name the libraries.
- **The entry points' own import trace is complete at the pin.**
  - `render_ink.py` imports `surface_orientation` and `tifxyz`, and `get_ink_metrics.py` imports
    `make_ink_report`. Of those, `tifxyz` imports `surface_orientation`.
  - The independent review traced the flatten's closure at the pin: 44 files, of which one is outside `lasagna/`,
    `vesuvius/src/vc3d_fiber_format/__init__.py`, now covered.
- **The other scripts that run git in villa** fail loudly or check first:
  - `repro/spiral_render/setup_workdir.sh`: in an empty `villa/`, `git archive` names paths this repository lacks,
    and `set -euo pipefail` stops it.
  - `repro/spiral_render/preflight.sh`: its `git rev-parse --git-dir` answers for the enclosing repository there;
    its `cat-file -e "$VILLA_SHA:spiral-fitting"` is what stops it.
  - These fail on a villa object they require, or stop under `set -e`:
    - `run_upstream_fitter_chain.sh`, `run_upstream_render_path_chain.sh` and `recover_arm.sh`;
    - `repro/fibers/setup_neural_tracer_env.sh`;
    - `scripts/check_villa_runner_pr.py`.
  - These check for villa's `.git`, or the repository itself:
    - `watch_villa_upstream.sh`;
    - the audit, the component coverage report and the gate (#114, #124, #129);
    - `dev_worktree.sh`.
  - `scripts/identify_fit_tree_provenance.py`'s docstring records the hazard.

## Observations for the owner (not changed)

- **`scripts/reconstruct_render_provenance.py`** reads `git -C <villa> reflog show origin/main` without checking that
  villa is its own repository. In an empty `villa/` it would read this repository's reflog. It validates itself
  against the arms that logged a `VILLA_SHA`, so the mismatch would show there; it is a tool for arms from before
  2026-09-14.
- **The import trace reads names, not code paths.**
  - It follows the entry points' imports one level, and the flatten's not at all; `STAGE_LIBRARIES` lists what the
    flatten imports from outside `lasagna/`, as read at the pin.
  - A new `sys.path` entry in the flatten, or an entry point importing a module that imports another changed one,
    would need that list or a deeper trace. A real import tracer would be a change to the tool's method.
- **All four verdicts exit 0.** Only errors exit nonzero (now 2). Nothing reads the code; the verdict is in the
  output.

## Verification

Environment: CPython 3.10 venv, git 2.43. Villa at the pin, in a sparse blob:none checkout, with network for its
lazy fetches.

- `pytest tests/test_check_render_equivalence.py`: 29 passed (15 before, 14 new). With main's script, the first
  commit's 5 behavioural tests fail.
- **Main's verdict for each case**, as recorded above, run against main's script.
- **Mutation check.** Each mutation fails its test:
  - no own-repository check;
  - no check for a path at neither ref, a check for the trees only, or one that also refuses a path at one ref;
  - `GIT_DIR` inherited;
  - `imports_of` swallowing a failed `git show`;
  - renames listed;
  - no import-name match;
  - no stage libraries;
  - no regular-file check;
  - the script directory unresolved.
- The real-range comparison above, 14 ranges. Ruff and mypy clean on the changed files.
- **Independent review** of the first commit. It found:
  - the flatten's library (should-fix), with the two real ranges;
  - that plausible wrong implementations passed the tests: a swallowed `git show`, an `or` in the absence check,
    renames listed;
  - the symlinked launch, refs resolved but not used, the sweep's omissions and `preflight.sh`'s check, and a
    symlinked entry point.

  All are addressed above. The import trace's method is left (the observation above).
- The standard suite: see the PR.
