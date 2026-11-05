# Plan checkpoint cleanup

These commands remove only `checkpoint_fitted.ckpt` from direct arm directories.
Removal discards the ability to resume that fit. Meshes, metrics and rendered
outputs are not deletion targets. Run cleanup on finished fits with stable paths
and repository references; neither command determines whether a job is active or
whether you will need to resume it.

## Reference-based pruning

Inspect a plan first. Both arguments must identify existing directories, and
`--repo` must be the root of a Git worktree with a valid commit:

```sh
python scripts/prune_fit_checkpoints.py \
  --repo /path/to/checkout --spiral-out /path/to/finished-fits --json
```

The reference check searches literal full arm names and their nonempty short
tags after `-patch_`. It checks HEAD, the index, and current tracked/nonignored
untracked files. The scope is `reports/`, `docs/`, `scripts/`, `repro/`, `tests/`,
top-level Markdown files and `config.json`. Logs outside those paths are excluded.
Any match keeps the checkpoint. This is a conservative text check, not a program
dependency graph: dynamically constructed references, ignored untracked files
and external dependencies need the operator's judgment.

Missing repositories, unreadable or inconsistent search results, unavailable Git
objects, timeouts and changing HEAD are errors. They never mean "unreferenced."
Local Git commands disable optional locks, lazy fetching and text conversion;
inherited Git directory/index/object locators cannot redirect the selected repo,
and inherited pathspec settings cannot narrow the stated search scope.

The JSON records the reference commit and scope, selected paths, observed file
identities, retention decisions and logical byte counts. To remove eligible
checkpoints, use the explicit action flag:

```sh
python scripts/prune_fit_checkpoints.py \
  --repo /path/to/checkout --spiral-out /path/to/finished-fits --delete --json
```

This creates a fresh checked plan; a saved dry-run JSON is not an apply token.
Every deletion candidate is checked again for references and filesystem drift
before the first removal, then its identity is checked immediately before its
own removal. A failure during execution stops further removal and returns the
actual completed count.

| Status | Meaning | Exit |
| --- | --- | ---: |
| `COMPLETE` | The plan or selected removals completed | 0 |
| `BLOCKED` | Validation failed before any removal | 1 |
| `PARTIAL` | An error stopped execution after one or more removals | 1 |

Usage errors exit 2. JSON errors are in the `errors` array; human output also
reports refusals. Checkpoint bytes are logical file lengths, not a measurement
of physical free space or an assertion that a resume checkpoint is dispensable.

## Protected-arm reclaimer

`scripts/reclaim_fit_checkpoints.py` retains its separate policy: protected arm
tags from `PROTECTED` are kept, `--also` explicitly releases selected tags, and
each selected arm needs a sibling `meshes/` directory. It remains a dry run until
`--apply` is given. Its policy does not perform the pruner's repository reference
scan. Mesh-directory presence does not validate the mesh contents.

Both commands share filesystem discovery and drift checks. The chosen root must
be a nonsymlink directory; symlink arm directories are skipped, and symlink or
special checkpoint files block discovery. Device/inode, mode, size and change
times are captured without reading checkpoint contents, together with parent
directory identities. The reclaimer checks identities before selecting removals
and again before unlinking, rechecks the mesh gate, and returns nonzero for a
refusal or removal error. Its counts also describe logical bytes.

## Concurrency and recovery limits

Keep writers and paths stable while planning and applying. Metadata checks do
not make multiple unlinks atomic and do not lock out a writer or an adversarial
path replacement after the final check. A partial action cannot restore files
already removed. Resolve the reported error, review remaining files and generate
a fresh plan. Neither command changes fit settings, launches jobs, inspects model
weights or edits study measurements.
