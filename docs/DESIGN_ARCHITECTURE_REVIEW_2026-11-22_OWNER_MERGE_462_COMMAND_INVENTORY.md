# Design and architecture review — the owner's #462, the command inventory

Date: 2026-11-22. Baseline: `6c9cc70` (main after round #185's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 17:12 UTC firing on 2026-11-22. It was interrupted by a usage limit and a restart of the
session's worker, and finished after the 18:12 firing. Main moved once while it ran, with the owner's #487, and was
merged in.

It takes **#462**, merged on 2026-11-17. #462 adds `configs/command_inventory.json`, a reviewed list of the
repository's entry points and their runtime boundaries, and `src/vesuvius_autoresearch/core/command_inventory.py`,
which validates it. `scripts/list_commands.py` browses it without importing or running anything.

## What changed

### Command metadata now refuses C1 controls and Unicode line breaks (`core/command_inventory.py`)

The validator requires "nonempty single-line strings" for every metadata field and argument, but `_text` refused only
C0 controls and DEL. NEL (U+0085), the other C1 controls, and the line and paragraph separators U+2028 and U+2029
passed. `str.splitlines()` breaks at NEL, U+2028 and U+2029, and C1 controls are terminal controls.

`_text` now refuses Unicode categories Cc, Zl and Zp. Cc is exactly C0, DEL and C1, so nothing that was refused
before is accepted now. No string in `configs/command_inventory.json` uses any of these characters, so the shipped
inventory reads the same. Four new cases fail on the old code: NEL, CSI (U+009B), U+2028 in a summary and U+2029 in
an argument.

### Each of the inventory's rules is tested with its own edit and message (`tests/test_command_inventory.py`)

This round made 53 mutants of the validator and `select_commands`. #462's tests killed 13. Its malformed-inventory
test checks only that some `ValueError` is raised, and edits only the first command, a script. A failure for another
reason therefore passed for the rule under test, and the shell and module branches were never reached with a bad
entry.

A new parametrized test makes 42 edits, each matched to its own message. Two more tests cover the source identity
the reader reports and the message for an unknown stack. The edits cover these areas:
- **The top level**: a list, an extra key, schema 2, a blank scope, stacks given as a list, an extra or blank stack,
  commands given as a dict, no commands, and 101 commands.
- **Each command's text**: an extra field, blank or numeric metadata, DEL, and the four new characters.
- **The ID and classifications**: an ID starting with a digit, an unknown Villa value and an unknown effect.
- **The prefix and guide**: an `argv` that is a string, too short, too long or with a blank item, and guides with
  the wrong suffix, a space, `..`, `.` or a leading `/`.
- **Each kind's source rule**: a script whose source is not `.py`, a shell command naming another script or a `.py`
  file, a module with no package or run without `-m`, and an unknown kind.
- **The packaged layout**: a script, a script inside the package, and a module of another package.

With the fix, 53 of 54 mutants are killed. The `_text` mutants were restated for the category set.

### One mutant no test can kill

**Dropping the absolute-path check from `_path`.** An absolute POSIX path always has an empty first segment, and
the segment check refuses that. The `guide_absolute` case is kept as documentation.

## Verified, no change needed

- **The CLI reports every refusal as exit 2.** It catches `OSError`, `ValueError`, `TypeError` and `RuntimeError`.
  That covers a `RecursionError` from deep JSON, which is a `RuntimeError`, and a `UnicodeDecodeError`, which is a
  `ValueError`.
- **`unicodedata` keeps the listing's stdlib-only promise.** The test that runs the CLI from another directory with
  site packages disabled still passes.
- **The reported identity is the parsed capture.** The path is resolved, and the byte count and SHA-256 are taken
  from the bytes that were parsed. #462's test covers a file changed after capture.
- **The guide is unchanged.** `docs/COMMANDS.md` names the rules the schema enforces but not the character rule.

## Observations for the owner (not changed)

- **Format characters still pass.** Bidirectional overrides such as U+202E and zero-width characters are category
  Cf, not Cc. They do not break a line, but they can make a printed summary or command prefix read differently from
  what it is. The inventory is reviewed configuration, so this round left them alone.
- **The shell and module branches have only two and five live entries.** The new edits are the first bad entries of
  those kinds that the tests try.

## Verification

- **The touched module.** `test_command_inventory.py` gives 58 passed, against 16 on `6c9cc70`. After merging
  `4cc4316` it still gives 58.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it. `format` is clean on the two
    changed files.
  - Mypy is clean over the whole repository, 1,091 files, with `--python-executable ./.venv/bin/python`. That was
    run again after the merge.
- **The standard suite.** The same 265 failing ids as round #185's run.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,744 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `6c9cc70`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout. The suite was run before main's #487 was merged in;
#487 changes training depth handling and none of this round's files.

## A note on this round's work

- **Only the validator and `select_commands` were mutated.** `list_commands.py`, the probe and promotion changes in
  #462, and the inventory's individual entries were read, not mutated.
- **Still not reviewed from the owner's merges since round #182:** #447, #448, #450, #453, #456, #458, #461, #463,
  #465, #468 to #478, #480, #483 and #487.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
