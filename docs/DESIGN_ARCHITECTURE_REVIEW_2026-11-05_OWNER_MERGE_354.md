# Design and architecture review — the owner's #354

Date: 2026-11-05. Baseline: `9763f9b2` (main after #354).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 17:13 UTC firing.
- **#354 guards checkpoint cleanup.**
  - Both cleanup commands now share `scripts/checkpoint_cleanup.py`. It discovers checkpoints by `lstat` only and
    records each one's identity: device/inode, mode, size, mtime and ctime, plus its two parent directories.
    `require_unchanged` refuses on any change.
  - `prune_fit_checkpoints.py` searches HEAD, the index and nonignored untracked files with `git grep`, under a
    sanitized Git environment. Any search error counts as unknown, never as no match.
  - In `--delete` mode the pruner checks the whole candidate set before its first removal, then each identity again
    before its own removal.
  - `reclaim_fit_checkpoints.py` checks identities and its `meshes/` gate twice.
  - It adds `docs/CHECKPOINT_PRUNING.md` and the owner's own review notes.

This round changes no script. It adds three tests for promises that `docs/CHECKPOINT_PRUNING.md` makes but no test
held.

## What changed (`tests/test_prune_fit_checkpoints.py`)

I made 15 mutants of the two commands and the shared helper. #354's 48 tests catch 11. Three of the four survivors
break a documented promise:
- **Each removal rechecks its own identity.**
  - The doc says each identity "is checked immediately before its own removal". With that check removed, every test
    passed: the preflight had already checked the whole set.
  - The new test has two unreferenced checkpoints. Removing the first replaces the second. The run must stop
    `PARTIAL`, with one removal and the replaced file intact.
- **The identity includes the change time.** The doc says "change times are captured". With `ctime_ns` dropped from
  the identity, every test passed.
  - The new test rewrites a checkpoint with bytes of the same size and restores its mtime. Only the change time then
    differs, and `require_unchanged` must refuse.
  - It skips on a filesystem whose change time did not advance. Here it ran.
- **A dry-run plan whose HEAD moves is blocked.**
  - The doc counts "changing HEAD" as an error. With the HEAD check after planning removed, every test passed.
    #354's own test commits during a `--delete` run, where the preflight's checks catch it anyway.
  - The new test commits after a dry-run plan's last reference check. The plan's `reference_commit` would otherwise
    no longer be HEAD, so it must end `BLOCKED`.

Each new test passes as merged and fails against its mutant.

## Verified, no change needed

- **The 11 caught mutants:**
  - each of the three `git grep` selections dropped: HEAD, the index and untracked files;
  - the stderr test dropped from search-failure detection;
  - the preflight's reference recheck removed;
  - the Git environment left unsanitized;
  - top-level Markdown dropped from the scope;
  - the regular-file check removed;
  - the arm-directory skip removed;
  - the reclaimer's second mesh check removed;
  - the reclaimer's second identity check removed.
- **The fourth survivor is redundant, not missing.** `checkpoint_identity`'s parent-directory check never decides
  alone:
  - discovery already skips non-directory arms and requires a nonsymlink root;
  - a parent replaced later, by a symlink or anything else, changes the parent inode the identity records.
- **The reference scope is complete.** `git grep` runs once per selection. HEAD, `--cached`, and `--untracked
  --exclude-standard` together cover the committed, staged and working-tree states the doc lists. Exit 1 with output,
  or exit 0 without it, is refused as inconsistent.
- **Compatibility.** `find_checkpoints` and the reclaimer's `find` keep their signatures. A symlinked or special
  checkpoint now blocks discovery instead of being listed, as the doc says.

## Observations for the owner (not changed)

- **The last check and the unlink are not atomic.** A file swapped between `require_unchanged` and `os.remove` would
  still be removed. The doc's "Concurrency and recovery limits" section states this, so it is left as documented.

## Verification

- **The touched modules**, `test_prune_fit_checkpoints` and `test_reclaim_fit_checkpoints`, pass: 51 with the added
  tests.
- **Ruff and mypy.**
- **The standard suite.**
- **The test modules outside the suite.**
- **The doc audit**, run alone.
