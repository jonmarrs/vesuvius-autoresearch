# Design and architecture review — the villa render-path gate and its watcher

Date: 2026-10-18. Baseline: `f211e2a4` (main after #128). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- `scripts/check_villa_render_path.py`, the gate a villa pin bump passes before renders are compared across it
  (`docs/RESUME_AFTER_RESTART.md` cites its exit code for each bump);
- `scripts/watch_villa_upstream.sh`, which runs it on each new upstream tip.

Neither had a dedicated review. The 2026-10-12 fiber-diagnostic review names the gate's tests only in a command
it ran.

## What changed

- **A file moved off the sampler's build path went unreported.**
  - The image-path check (the `vc_render_tifxyz` sampler and VC's `core/` and `utils/`) listed changes with
    `git diff --name-only`. That detects renames by default, so a moved file is listed only where it went.
  - A file moved out of `volume-cartographer/core/` was therefore listed outside the image path, and the gate said
    nothing about the sampler.
  - This is the defect fixed in the handoff's upstream audit (#124). It is latent here: an exact-rename diff
    (`-M100%`, object IDs only) finds no move across the boundary in `5479453a..ccb431818` or
    `ccb431818..b29f3109`.
  - The check now uses `--no-renames`, so both sides of a move are listed.
- **Names git quotes, or that contain a space, were missed.**
  - The output was split on whitespace, and `core.quotePath` writes a non-ASCII name as `"volume-cartographer/…\303…"`.
    So neither form matched a prefix.
  - The check now uses `-z`.
- **A removed tree ended the gate with a git error and no verdict.**
  - Each tree was listed as `ls-tree <ref>:<tree>`, which fails where the tree is absent. So the largest change the
    render path can have, villa dropping or moving `lasagna/`, say, printed `git ls-tree … failed`.
  - It is now listed as `ls-tree --full-tree <ref> -- <tree>`, which is empty where the tree is absent, so its files
    are reported REMOVED and the verdict is DIFFERS.
  - Both forms list the same files for all three trees at `5479453a`, `ccb431818` and `b29f3109`. The new form
    matches nothing for a partial name (`vesuvius/sr`).
- **A change of file mode was not a change.**
  - Files were compared by blob hash alone, which leaves out whether a file is executable or a link.
  - They are now compared by mode and hash. The docstring's scope is "everything executable under those trees".
- **The gate now exits 2 when it cannot compare.**
  - A failed git call (an unknown ref, a missing tree object) and a missing checkout exited 1, the code for "the
    render path differs". So a typo in a ref read as a difference.
  - Errors now exit 2 with the message on stderr. A difference still exits 1, and "identical" still exits 0.
  - The watcher prints the output, and the runbook cites "exits 1" only for real differences, so neither depends on
    the old code.
- **Stale comments.**
  - `RENDER_SOURCE_REF` (`5479453a`) was described as "the tree renders are actually built from; NOT this repo's
    villa submodule". Since 2026-09-19 `setup_workdir.sh` extracts from the submodule at `VILLA_REF`; `5479453a`
    is villa-spiral's `origin/main`, which the pinned-tier corpus's renders came from. The comment and the usage
    line say so.
  - The watcher's header said that fetching would change what future work dirs contain, as a reason it fetches
    only the submodule. Since 2026-09-19 it is the submodule's `origin/main` that unpinned renders follow.
    `setup_workdir.sh` warns about exactly this monitor, and `tests/test_villa_spiral_refs_pinned.py` records the
    decision that pinning `VILLA_REF`, not freezing the checkout, is what makes the fetch safe. The header now
    says that.
- **Tests** (`tests/test_check_villa_render_path.py`, 6 new), against a throwaway villa-shaped repository, so they
  run without villa:
  - a move off the sampler path;
  - a quoted name with a space;
  - a removed tree;
  - a mode-only change;
  - identical refs;
  - exit 2 for an unknown ref and for a missing checkout.

  The five behavioural tests fail with main's gate.

## Verified, no change needed

- **The verdicts on real ranges are unchanged.** Main's gate and this one print identical output, with the same
  exit code, for:
  - `5479453a..ccb431818` (1);
  - `be09a8503..origin/main` (1);
  - `ccb431818..b29f3109` (0);
  - `9afddaf0f..4eecd08fd` (1) and `be09a8503..9afddaf0f` (1), the two ranges the runbook cites.
- **The image-path prefixes still match files.**
  - `vc_render_tifxyz` and `vc_tifxyz` are file-name prefixes (`vc_render_tifxyz.cpp`, `vc_tifxyz.cpp`), not
    directories.
  - At the three refs above they match the sampler's sources. `core/` has 352 to 384 files and `utils/` 13 to 17.
  - `vc_tifxyz` also matches other tools (`vc_tifxyz2obj.cpp`, …), which errs towards reporting.
- **The hot-path files and the three extracted trees exist** at all three refs. The existing tests bind the trees
  to `setup_workdir.sh`'s `git archive` line.
- **The watcher checks for villa's `.git`** before it runs, so an uninitialised submodule, an empty directory in
  which git would answer for this repository, is refused. That is the hazard the audit had (#124). The gate it
  runs is standard-library only, as the watcher's `python3` requires.

## Observations for the owner (not changed)

- **The watcher compares villa's checked-out `HEAD`, not the commit this repository pins.** The two agree here.
  While a pin bump is under review they differ, as for the audit (#124's observations).
- **The gate's tests are outside the standard suite.** The gate is not the loop's code, so the suite's guard does
  not require them. The new tests need no villa and take under 10 s.
- **`run_autoresearch_loop.py` sets `end_hour` in its shift detection and never reads it.** The shift's end is
  decided later from the hour bucket (`_shift_over`), so it is dead code, not a missed check.

## Verification

Environment: CPython 3.10 venv, git 2.43. Villa at the pin, in a sparse blob:none checkout.

- `pytest tests/test_check_villa_render_path.py tests/test_check_villa_render_path_image.py`: 20 passed (14
  before, 6 new). With main's gate, the 5 behavioural tests fail.
- **Mutation check.** Each mutation fails exactly its own test:
  - no `--no-renames`;
  - no `-z`;
  - comparing by hash only;
  - errors exiting 1.
- The output comparison on real ranges above. The `ls-tree` forms compared on villa's refs. The exact-rename
  count.
- `bash -n scripts/watch_villa_upstream.sh`. Ruff clean on the changed files.
- The standard suite: see the PR.
