# Design and architecture review — the owner's #458, the pickle audit before the Grand Prize checkpoint

Date: 2026-11-23. Baseline: `77ffae8` (main after round #199's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 08:12 UTC firing on 2026-11-23. Main had not moved since round #199's merge.

It takes **#458**, finding 122, which runs the 2023 Grand Prize TimeSformer on finding 118's render of the winning
PHerc. 211 surface. The winners' script unpickles the checkpoint in full, and Torch's weights-only loader cannot
rebuild the `collections.defaultdict` its optimizer state holds. So the run first checks the file's SHA-256, then
runs `repro/first_letters/pherc0211_control/audit_pickle.py`. That script walks the pickle's opcodes without
running them, lists every global it imports, and refuses the file unless all are allowed. Its docstring says a file
that passes "can only rebuild tensors, plain containers and the classes allowed, so a full torch.load of it runs no
other code". The script is registered, so this round adds tests only.

## What changed

### Each opcode rule of the audit is tested (`tests/test_first_letters_0211_gp_timesformer.py`)

This round made 19 mutants of `audit_pickle.py`, and #458's tests killed 2. Eight new test functions, 21 cases,
kill the other 17. They build pickles by hand, opcode by opcode:
- **STACK_GLOBAL names pushed by each of the seven string opcodes are read.** #458's tests used only
  `SHORT_BINUNICODE`.
- **A module name fetched back from the memo is read**, through `MEMOIZE`, `BINPUT`, `LONG_BINPUT` and `PUT`, and
  a name imported twice is counted twice.
- **Two strings no longer on top of the stack name nothing**, and neither do two strings with a non-string memo
  entry fetched between them. Both refuse the file rather than guess.
- **`INST` names a class inline**, and the file is refused.
- **`EXT2` and `EXT4` refuse the file as `EXT1` does**, `passes` is false on a refused opcode alone, and `main`
  exits 1.
- **Only a storage class of `torch` itself passes as a storage.** `torch.FloatStorage.__class__` and
  `torch.serialization.Storage` are refused.
- **`main` takes exactly one checkpoint.**

No code changed.

### Two gaps are marked by strict xfail tests

The audit's guarantee does not hold for two kinds of file, below. A strict xfail test for each asserts that such a
file is refused. Each fails today. Once the audit is fixed, each will pass unexpectedly and fail its module's run,
so the marker can then come off.

## Observations for the owner (not changed)

- **A legacy torch file is audited only to its first `STOP`.** `pickletools.genops` stops at the first `STOP`.
  A legacy (non-zip) torch file holds a magic number, a protocol version and system information as three pickles
  before the object, so the audit reads only the magic number. In a scratch probe, a legacy file whose object makes
  a directory passed the audit with no names. `torch.load(..., weights_only=False)` then made the directory.
- **A pickle placed before a zip archive is never read.** `zipfile.is_zipfile` finds an archive at the end of a
  file, but Torch takes a file as a zip only when it starts with `PK\x03\x04`. In the same probe, a pickle that
  makes a directory, followed by a Torch archive of one tensor, passed: the audit read the archive's `data.pkl`.
  `torch.load` ran the leading pickle, which made the directory, and only then failed with "Invalid magic number".
- **What would close both.** Read a file as a zip only when it starts with the signature, as Torch does. Refuse
  bytes before the first member. Audit every pickle of a non-zip file until the data runs out, or refuse non-zip
  files, since the registered checkpoint is a zip.
- **The registered run is very likely unaffected.** Its record lists the audited member as `archive/data.pkl`, so
  Python read the checkpoint as a zip. A checkpoint that `torch.save` writes in its default format starts with the
  signature. That cannot be checked here: the file is not in this repository.
- **A bfloat16 checkpoint is refused.** Torch pickles its storage as `torch.BFloat16Storage`, and the storage
  pattern `[A-Za-z]*Storage` admits no digits. That errs on the safe side, but the audit would refuse a bfloat16
  checkpoint that holds nothing but tensors.

## Verified, no change needed

- **The run checks before it loads.** `run_gp_timesformer.sh` runs the checksum, then the audit, as steps that stop
  the chain on a non-zero exit, before villa's script loads the checkpoint. The allowlist the run passes is the one
  the registration names: `AdamW`, `CosineAnnealingLR` and `defaultdict`.
- **The registered audit passed on exactly those names.** The record lists `OrderedDict`, the tensor and parameter
  rebuilders, `torch.FloatStorage`, `AdamW`, `CosineAnnealingLR`, `defaultdict` and `__builtin__.dict`.

## Verification

- **The touched module.** `test_first_letters_0211_gp_timesformer.py` gives 35 passed and 2 xfailed, against 14
  passed before. The torch cases ran on the installed Torch 2.9.1.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #199's run.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #199's run, and 3,211 passed:
  round #199's 3,190 and the 21 new cases, with the 2 strict xfails. One of the 24 is the free-disk case round #196
  described.
- **The doc audit**, run alone, lists the same unresolved references as on `77ffae8`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`audit_pickle.py` is registered and unchanged.** Its mutants were run in a worktree. The probe that loaded the
  two files ran in scratch, and made its directories there.
- **`gp_timesformer.py`, the rest of #458, was not mutation-tested this round.**
- **Still not reviewed from the owner's merges since round #182:** the rest of #458, #461, #465, #468 to #478, #480,
  #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 19 were run again with the new tests, and all 19 are killed.
