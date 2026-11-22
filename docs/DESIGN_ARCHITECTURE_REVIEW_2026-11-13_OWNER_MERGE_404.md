# Design and architecture review — the owner's #404

Date: 2026-11-13. Baseline: `5ce1a49` (main after round #165's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the hourly firings from 06:13 to 08:13 UTC on 2026-11-13. Main had not moved, so it takes another
of the audit merges that earlier rounds left: **#404**, merged on 11-12 at 17:07 UTC. Among other things #404 adds two
guards that the training script runs before it reads data or writes a checkpoint:
- `scripts/training/data_split.py` refuses training or active unlabeled volumes that observably overlap the
  held-out validation volume;
- `scripts/training/checkpoint_paths.py` refuses experiment outputs that would replace the loop's state or a
  training input.

This round reviewed those two modules. The last section lists what it did not.

## What changed

### Thirteen guards of the two modules are now tested

This round made 41 mutants: 18 of the split guard and 23 of the checkpoint guard. #404's three test modules killed
28. Twelve new test functions (20 cases) kill the other 13. Each passes on the code as merged and fails with its
mutant.

In `tests/test_training_split.py`:
- **A file URI is local only on this host.** `file://localhost/...` naming the validation volume is refused. A file
  URI on another host is a remote address and is not compared with a local path.
- **A local file URI with a query or a fragment is refused.**
- **A percent-encoded file URI is the path it spells**, so `val%20set.zarr` is refused as `val set.zarr`.
- **Remote addresses overlap only when they are the same address.** The same address is refused. A different
  query, a different host and the address without its query are allowed, as the module's comments say.
- **A symlink to the validation volume's parent directory is refused.** #404's symlink test links to the volume
  itself, which the same-file check also catches. Only resolving the link catches the parent.
- **The training volumes must be a nonempty list**, each identifier a nonempty string, and the active unlabeled
  volumes a list.

In `tests/test_training_checkpoint_paths.py`:
- **A blank output path is refused.**
- **An existing output must be an ordinary file.** A link to an unprotected file and a directory are refused, and
  the linked file is left as it was. A plain existing file may be replaced.
- **The default names are checked when no output is configured.** The trainer then writes `long_model.pt`'s curve
  and step snapshots, and the guard checks those names. `scripts/training/train.py` uses the same default.
- **An active unlabeled volume is a protected input**: an output inside it is refused.

No code changed. `scripts/training/` is the training loop's code, which these reviews do not edit.

## Verified, no change needed

- **Both guards do what their docstrings say** on every case this round probed: an existing local path wins over a
  URL reading of the same string; relative paths resolve from the given base; a local alias by spelling, ancestry
  or link is refused; the root and level-zero spellings of one remote address are the same address.
- **The checkpoint guard protects each input it names.** Removing any one of them fails #404's tests: the volume
  tree, its labels, mask and patch catalogue, the pseudo-label, the foundation weights, the active config, the
  validation volume, and each of the four loop-state names sampled.
- **Neither guard creates anything.** The tests that expect a refusal find the directory as it was.

## Observations for the owner (not changed)

- **A remote training volume that is another level of the validation volume is allowed.** With `val_uri`
  `s3://bucket/val.zarr`, a training volume `s3://bucket/val.zarr/1` passes. The same spelling as a local path is
  refused, because a child of the validation path overlaps it. The module says it recognises only identical remote
  addresses and the level-zero spelling, so this is its stated limit, but it is the one remote case where the
  overlap is visible in the address itself.
- **An output name with a colon can be refused as a URL.** `run-08:00.pt` and `a:b.pt` are refused with
  "checkpoint outputs must be nonempty local filesystem paths", because the text before the colon parses as a URL
  scheme. `exp_2026-11-13T08:00.pt` is accepted, because an underscore cannot be part of a scheme. The split
  guard handles the same ambiguity for inputs by letting an existing path win. It fails closed, but the message
  does not say why.
- **Host names are compared as written.** `https://Host/val.zarr` and `https://host/val.zarr` are treated as
  different addresses, though host names are not case-sensitive. The scheme is compared without case.
- **#404's slowest test module takes over a minute.** `tests/test_training_data_sources.py` runs in 66 s here. It
  killed none of the 13 mutants above.

## Verification

- **The touched modules.** `test_training_split.py` and `test_training_checkpoint_paths.py` give 79 passed, against
  59 on `5ce1a49`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    two changed test files.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 216 modules give the same 171 failing ids on `5ce1a49` and on this branch.
- **The test modules outside the suite.** The 250 modules give the same 23 failing ids on `5ce1a49` and on this
  branch.
- **The doc audit**, run alone, lists the same unresolved references as on `5ce1a49`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

The baseline figures for `5ce1a49` are round #165's runs of its branch head, whose tree is identical. The failing
ids are this container's: it has no villa checkout.

## A note on this round's work

- **The usage limit interrupted the round once**, before any work was done.
- **Only the two guard modules were reviewed.** #404 also changes `scripts/training/config.py`, `train.py`,
  `scripts/workspace_status.py`, `fragment_conversion.py` and the repository audit document. I did not review
  those, nor how `train.py` calls the two guards.
- **Still not reviewed:** #396, and the estimator and resampler of #390.
- **The mutants are a sample** of the two modules' checks. All three of #404's test modules passed here before the
  mutants were run.
