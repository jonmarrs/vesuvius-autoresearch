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
- `repro/spiral_render/README.md` prescribes it before rendering from a new ref. Two preregistrations and one
  report cite its verdicts.
- Its own tests name the dangerous failure: "a false INTERCHANGEABLE … would let a corpus split silently".

The script had no review. This round also swept the scripts that run git in `villa/` for the hazard #124 and #129
fixed: in an empty directory, an uninitialised submodule, git answers for the repository around it.

## What changed

- **Every failure read as the permissive verdict.**
  - Its `git()` returned `""` on any failure:
    - a tree lookup that failed matched one that failed at the other ref;
    - a `git show` that failed gave an entry point no imports;
    - a `git diff` that failed gave no changed files.
  - Reproduced with main's script. The new tests cover each case:
    - **An empty `villa/`.** Run here on an empty directory inside this checkout, it compared this repository's own
      commits (`89ab4b6ee -> 6316c9bf9`), found none of the three trees at either ref, and printed "INTERCHANGEABLE
      — every extracted path is the same tree object … No render can differ", with exit 0.
    - **An inherited `GIT_DIR`** (a hook's): INTERCHANGEABLE, for a range that changes a module `render_ink.py`
      imports.
    - **A tree at neither ref** (no `lasagna/`): RENDER-INERT.
    - **An entry point at neither ref:** RENDER-INERT. Its imports read as none.
    - **A ref that does not resolve:** exit 1, as from the other errors.
  - In villa's blob:none clone, a `git show` reads a blob that may not be there locally. For example, `render_ink.py`
    at `9afddaf0f` is not. Offline, that fetch fails, and the entry point's imports read as none.
- **The script now uses `check_villa_render_path`'s `git` and `not_own_repository`.**
  - It imports them as `build_stripmatch_dataset.py` imports a sibling check.
  - A git call that fails exits 2, with git's message, and git's locator and pathspec variables are dropped.
  - A directory that is not a repository of its own exits 2.
- **A path at neither ref exits 2.** That covers the three extracted trees and the two entry points.
  - `tree()` reads each from its parent tree's entry, so it returns None for an absent path rather than an empty
    string that equals another.
  - A path at one ref only still compares as different, as before.
- **The changed-file listing uses `--no-renames -z`.** Each extracted tree is diffed under its own pathspec, so a
  move out of it already showed as a deletion there. This makes the listing read trees only, and keeps names git
  would quote.
- **Docs.** The docstring says when it exits 2, and why.
- **Tests** (`tests/test_check_render_equivalence.py`, 6 new), against a throwaway villa-shaped repository:
  - an imported module's change still NEEDS A HUMAN;
  - the empty directory;
  - a tree at neither ref;
  - an entry point at neither ref;
  - an unresolvable ref;
  - an inherited `GIT_DIR`.

  The five behavioural tests fail with main's script.

## Verified, no change needed

- **The verdicts on real ranges are unchanged.** Main's script and this one print identical output, exit 0, for 12
  ranges:
  - the four refs cleared by hand on 2026-09-14 against `be09a8503` (INTERCHANGEABLE);
  - `d9d70bef1`, `1f544fa71` and `0e01fe1c7` against `be09a8503` (NEEDS A HUMAN);
  - `d8c5f488a..be09a8503`, the 09-11 split (NEEDS A HUMAN);
  - `d8c5f488a..d82e13edf`, the report's comparison (NEEDS A HUMAN);
  - `be09a8503..9afddaf0f` (RENDERS MAY DIFFER);
  - `ccb431818..b29f3109` (INTERCHANGEABLE);
  - a ref against itself.
- **The one-level import trace is complete at the pin.** The entry points import three local modules:
  `surface_orientation`, `tifxyz` and `make_ink_report`. Of those, only `tifxyz` imports another local module,
  `surface_orientation`, which the entry points import directly.
- **The other scripts that run git in villa** fail loudly or check first:
  - `repro/spiral_render/setup_workdir.sh`: in an empty `villa/`, `git archive` names paths this repository lacks,
    and `set -euo pipefail` stops it;
  - `preflight.sh` and `watch_villa_upstream.sh` check for villa's `.git`;
  - the audit, the component coverage report and the gate check the repository itself (#114, #124, #129);
  - `scripts/identify_fit_tree_provenance.py`'s docstring records the hazard.

## Observations for the owner (not changed)

- **`scripts/reconstruct_render_provenance.py`** reads `git -C <villa> reflog show origin/main` without checking that
  villa is its own repository. In an empty `villa/` it would read this repository's reflog. It validates itself
  against the arms that logged a `VILLA_SHA`, so the mismatch would show there; it is a tool for arms from before
  2026-09-14.
- **The import trace is one level deep, and matches changed files by base name against top-level import names.**
  - A module imported only through another, or a change inside the `vesuvius` package (which the entry points do
    not import at the pin), is therefore never a suspect.
  - It is complete at the pin, as above. A deeper trace would be a change to the tool's method, so it is left.
- **All four verdicts exit 0.** Only errors exit nonzero (now 2). Nothing reads the code; the verdict is in the
  output.

## Verification

Environment: CPython 3.10 venv, git 2.43. Villa at the pin, in a sparse blob:none checkout.

- `pytest tests/test_check_render_equivalence.py`: 21 passed (15 before, 6 new). With main's script, the 5
  behavioural tests fail.
- **Main's verdict for each new case**, recorded above, run against main's script.
- **Mutation check.** Each mutation fails its test:
  - no own-repository check;
  - no check for a path at neither ref, or one for the trees only;
  - `GIT_DIR` inherited.
- The output comparison on the 12 real ranges above.
- Ruff and mypy clean on the changed files.
- The standard suite: see the PR.
