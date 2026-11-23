# Design and architecture review — the owner's #416, the PHerc. 343 checkpoint report

Date: 2026-11-23. Baseline: `fa6701b` (main after round #193's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 02:12 UTC firing on 2026-11-23. Main had not moved since round #193's merge.

It takes **#416**, which corrects how the PHerc. 343 reproduction reports its checkpoint check.
- `repro/first_letters/pherc343/check_ckpt_safe.py` exits 2 when given nothing to check. It exits 1 when any
  restricted load is refused, and it keeps checking the rest. A scalar tensor no longer stops its layout report.
- `make_record.py` no longer writes `all_load_with_weights_only: true`. Nothing it consumes records a per-file
  result, so it writes `null` with `unverified_no_identity_bound_receipts`.
- The script README and the dated report mark the correction, and keep the original claim as history.

## What changed

### The checker is now checked against the real Torch loader (`tests/test_first_letters_checkpoint_real_torch.py`)

This round made 12 mutants of the checker and the record builder, and #416's tests kill all 12. Those tests replace
Torch with a stub, so they show what the checker asks for, including `weights_only=True` and `mmap=True`. They do not
show what the installed loader does with that request. A new test module, in the standard suite and skipped where
Torch is absent, runs the checker on three real checkpoints:
- **A tensor-only checkpoint loads**, and the checker exits 0.
- **A pickle that would call `print` is refused, and the call never runs.** The checker exits 1.
- **A legacy-format checkpoint is refused because it cannot be memory-mapped.** The checker exits 1 and the reason
  names `mmap`.

On its own the new module kills four of the mutants: the `weights_only`, `mmap`, failure-flag and exit-status ones.
The module is listed in `scripts/run_validation_tests.py` next to #416's.

No code changed. No defect was found.

## Verified, no change needed

- **The record builder no longer claims what it did not consume.** The README's correction note matches the code.
  It states that the old `true` was hardcoded and that no checkpoint was rerun.
- **The installed Torch refuses code in a pickle under `weights_only=True`.** A `__reduce__` to `print` is refused
  with `UnpicklingError` before anything runs.

## Observations for the owner (not changed)

- **A safe legacy-format checkpoint is reported as `NOT_WEIGHTS_ONLY`.** The checker asks for `mmap=True`, and
  Torch maps only zip-format files. So a file of tensors saved in the old format fails the check, with a reason
  that names `mmap`. That fails closed, but the label says something other than the cause. The new test pins the
  current behaviour.
- **`collections.Counter` loads under `weights_only=True`** in Torch 2.9.1. This round's first probe used one as an
  "unsafe" object, and it was accepted. Torch's allowlist is wider than plain tensors and containers, so a pass
  means the file is restricted to that allowlist, not that it holds tensors only.

## Verification

- **The new module.** `test_first_letters_checkpoint_real_torch.py` gives 3 passed. #416's module still gives 10.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    new test module and the suite list.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The suite guard.** `test_validation_suite_covers_the_loop.py` and `test_validation_runner.py` pass with the
  new module listed.
- **The standard suite**, now 235 modules with the new one, gives the same 278 failing ids as round #193's run.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,782 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `fa6701b`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`repro/first_letters/pherc343/` was not changed.** Only a test module and the suite list were added.
- **Still not reviewed from the owner's merges since round #182:** #398, #447, #448, #450, #453, #456, #458, #461,
  #463, #465, #468 to #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
