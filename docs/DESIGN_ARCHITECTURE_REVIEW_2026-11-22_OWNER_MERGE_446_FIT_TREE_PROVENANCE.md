# Design and architecture review — the owner's #446, the fit tree's provenance check

Date: 2026-11-22. Baseline: `2f128c5` (main after #496, which followed round #189's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 22:12 UTC firing on 2026-11-22. Main had moved once since round #189's merge, with the owner's
#496, a README change.

It takes **#446**, which fixes the summary of `scripts/identify_fit_tree_provenance.py`. That script recovers which
upstream villa commit each subtree of a copied fit tree matches, by comparing tracked files byte for byte. #446 makes
the summary report each subtree separately and say when only some subtrees matched. It also stops it claiming a
"whole tree" match.

## What changed

### A tracked file named like a skipped directory is now compared (`scripts/identify_fit_tree_provenance.py`)

The script skips generated directories: `.venv`, `__pycache__`, `build` and `.pytest_cache`. It tested each tracked
path with `any(s in f for s in SKIP)`, a substring match. Any tracked file whose path merely contained one of those
names was therefore dropped from the comparison. A differing source file such as `lasagna/build_mesh.py` was never
compared, and its subtree could be reported as an exact match. The skip now matches whole path components, so only
those directories are skipped.

### An unknown commit is an error, not an absent subtree

`git ls-tree` on a commit the repository does not have fails with no output. The script ignored the failure and
reported "subtree absent at this commit", so a mistyped candidate looked like a commit without that subtree. A failed
`ls-tree` now stops the run with git's message. A known commit without the subtree is still reported as absent.

### Tests (`tests/test_fit_tree_provenance.py`)

Three new test functions build a small repository of their own:
- **A tracked file named like a skipped directory is still compared, and one matching file of two is not a match.**
  `lasagna/build_mesh.py` differs in the copy while `lasagna/build/` is skipped. The comparison counts 1 of 2. The
  command reports the subtree as matching none of the candidates.
- **An unknown commit stops the run**, naming the commit, while a known commit without the subtree is still reported
  as absent there.
- **A tracked file missing from the copy is named** as absent locally.

The first two fail on the old script. Of 11 mutants of the script, 10 are killed. The survivor would count an
unreadable blob as identical. That needs `git show` to fail for a blob that `git ls-tree` has just listed and that
exists locally as a file.

## Verified, no change needed

- **#446's summary never certifies more than was compared.** It names each subtree's match, says when only some
  subtrees matched, and states that extra local files and absent local subtrees were not checked. #446's tests cover
  each of its four verdicts.
- **The first exact candidate is kept.** A later exact candidate does not replace it, and a partial match is never
  chosen.

## Observations for the owner (not changed)

- **`reports/fit_tree_provenance.md` was produced with the substring skip.** Its matches for `spiral-fitting` and
  `lasagna` hold unless a tracked file there has `build` or one of the other names inside a path component, such as
  `build_mesh.py` or `rebuild.py`. Re-running the script with this fix on the original tree and villa checkout would
  confirm them. Neither is present in this container, and the dated report is left as it is.
- **Only tracked files are compared**, as #446's summary now says. A local file that the candidate commit does not
  track is not looked at.

## Verification

- **The touched module.** `test_fit_tree_provenance.py` gives 10 passed and 7 skipped, against 7 and 7 on
  `2f128c5`. The skipped tests need the original fit tree and the villa checkout.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    two changed files.
  - Mypy is clean over the whole repository, 1,106 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The same 269 failing ids as round #189's run.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,782 passed. That
  is round #189's 2,779 and this round's 3.
- **The doc audit**, run alone, lists the same unresolved references as on `2f128c5`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **The script is not registered.** A dated report cites it, but no registration does, so it was changed here.
- **Still not reviewed from the owner's merges since round #182:** #398, #400, #416, #419, #438, #447, #448, #450,
  #453, #456, #458, #461, #463, #465, #468 to #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
