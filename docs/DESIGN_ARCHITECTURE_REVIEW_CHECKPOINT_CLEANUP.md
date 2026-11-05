# Design and architecture review — checkpoint cleanup

Baseline: `5142a9d5`. Scope: the reference-based pruner, protected-arm reclaimer,
their filesystem checks, and operator-facing plans/results.

## Findings and fixes

1. **Unknown reference state permitted deletion.** The pruner treated missing
   search directories and failed grep commands as no match. It now requires an
   accessible Git worktree root and a valid HEAD. Search errors, timeouts,
   unavailable objects and inconsistent command results abort the plan.
2. **Committed references could disappear from the check.** Despite its stated
   policy, the pruner searched only filesystem contents. An uncommitted removal
   of a citation could allow its checkpoint to be deleted. It now checks HEAD,
   the index and current tracked/nonignored untracked files. The scope also
   includes top-level Markdown and config.json, which the old directory-only
   search missed. Inherited pathspec settings cannot narrow that scope. Full
   names and short tags remain literal substring patterns.
3. **Aliases and replacement could redirect cleanup.** Both commands followed
   symlink arm directories. The pruner could also unlink a new checkpoint at a
   previously planned path. A shared stat-only helper now discovers direct
   nonsymlink arm directories, requires regular nonsymlink checkpoint files,
   and records parent/file identities, sizes and change times. Both commands
   recheck those observations before unlinking. This detects observed drift;
   it is not an atomic concurrent-writer transaction.
4. **Failure reporting was incomplete.** The pruner now offers a JSON preview
   and action result with reference commit/scope, per-file decisions, errors and
   actual deleted counts. Failed preflight removes nothing; a later failure
   stops further removals and reports PARTIAL with exit 1. The reclaimer also
   returns nonzero for refusals/removal errors and rechecks its mesh gate before
   unlinking. Byte counts are explicitly logical sizes, not measured free space.

Filesystem discovery and drift validation are shared; retention policies remain
separate. The pruner protects scoped literal references. The reclaimer retains
its protected tags, explicit --also releases and sibling mesh-directory gate.
Neither policy determines whether a fit is active or whether resuming it will be
needed. Both remain dry-run by default with their existing explicit action flags.

Local Git queries ignore inherited repository/index/object and pathspec
overrides, disable lazy fetching and optional locks, and bypass text conversion.
The checker does not load checkpoint contents. The two cleanup test modules are
now in the curated runner; their CLI argument fixtures restore sys.argv after
each test.

## Verification

- The initial pruner selection produced **12 failed, 9 passed** on the old code,
  reproducing reference loss, failed-search deletion and path replacement, plus
  the missing JSON interface. Two original reclaimer regressions also failed,
  reproducing symlink redirection and deletion of a changed checkpoint.
- Final selection: **131 passed** across 7/177 curated modules, including both
  cleanup modules, file modes, validation-runner/coverage guards, workspace status
  and text capture. There are **34 new cleanup cases**; all deletion tests use
  disposable files and Git repositories.
- Real Git tests cover committed, staged and untracked references, top-level
  documents/configs, moved HEAD, inherited locators, missing promisor blobs,
  literal leading-dash patterns and excluded logs. The missing-blob case also
  verifies that the check did not fetch the object.
- The final review reproduced deletion despite a committed README reference
  when `GIT_LITERAL_PATHSPECS=1` hid the top-level Markdown pathspec. Clearing
  inherited pathspec overrides fixes that case; three settings are exercised.
- Filesystem tests cover alias directories, replacement, special checkpoint
  files, late preflight failure, actual partial-action accounting and the final
  mesh gate. Both CLI help paths work from another cwd without ML imports.
- CPU smoke: **8 passed, 3 skipped, 0 failed**. Skips are two absent local data
  inputs and the unavailable legacy augmentation entry point.
- Ruff check/format and scoped Mypy pass on the six changed Python files.

Validation used Python 3.10.21, Git 2.52.0 and Torch 2.9.1 on CPU. Exact commands
and captured output are in the PR test report. No live fit cleanup was run.
Main's changes through `836a00e9` were integrated before final validation.

## Limits

The reference policy is a scoped text search, not dependency analysis. Ignored
untracked data, external references and names constructed at runtime require
operator judgment. Keep references and paths stable; there is no lock protocol,
snapshot or rollback across unlinks. A changed target is refused when observed,
but a mutation after the final check remains outside this contract. Already
removed resume checkpoints cannot be restored by the tool.

The full repository suite, repository-wide documentation audit, Windows behavior
and live/remote fit stores were not tested. No research measurements, models or
training policy were changed. See the [cleanup guide](CHECKPOINT_PRUNING.md).
