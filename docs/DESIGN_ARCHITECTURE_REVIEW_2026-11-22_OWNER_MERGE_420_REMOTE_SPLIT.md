# Design and architecture review — the owner's #420, remote spellings of the held-out volume

Date: 2026-11-22. Baseline: `0dd7e98` (main after round #187's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 20:12 UTC firing on 2026-11-22. Main had not moved since round #187's merge. That merge
brought in twelve of the owner's merges, some of them opened in mid-November: #398, #400, #405, #416, #419, #420, #438,
#446, #451, #485, #488 and #489.

This round takes **#420**, which extends `scripts/training/data_split.py`. That check refuses training inputs that
observably overlap the held-out CT volume. Before #420 it compared remote addresses as the shared volume identity
spells them, query and fragment included, so only identical spellings matched. It now normalizes them first:
- scheme and host case, a trailing dot on the host, credentials, default ports, `http` with `https`, and `s3a` and
  `s3n` with `s3`;
- repeated percent-encoding, backslashes, path parameters, and `.` and `..` segments;
- query and fragment, which are ignored.

It also counts a key nested inside the held-out key, a sibling pyramid level, and the bare bucket as overlaps.

## What changed

### Nine more spellings are tested (`tests/test_training_split.py`)

This round made 45 mutants of the remote comparison. #420's tests, already 104 cases, killed 33. Two new
parametrized tests, 11 cases, kill nine of the other twelve.

These spellings are now refused as the held-out volume:
- credentials before the host, including a password with an unencoded `@`, where the host follows the last `@`;
- a full-width host, which is the same host after NFKC;
- an IPv6 host with its scheme's default port, and an IPv6 host in another letter case;
- a space before path parameters.

These stay unverified, as distinct addresses:
- an IPv6 host on a non-default port;
- an Arabic-Indic digit, which is a key and not a pyramid level, both under a name and as the whole key;
- a `..` inside a path parameter, which is one key and not the bucket root;
- two unclosed, percent-encoded bracket hosts, each kept whole.

No code changed. No defect was found.

### Three mutants are not killed

- **Dropping `bool(parent)` from `_path_contains`.** This is equivalent. A joined key never starts with `/`, so an
  empty parent contains nothing either way.
- **Letting the bare root contain a key that resolves to empty.** This is equivalent. Such a key folds to the same
  empty string as the root, and the folded comparison already returns True.
- **Splitting a host at its last colon when it has several.** Only a malformed authority reaches this, such as a bare
  IPv6 address without brackets, which `urlsplit` accepts. It is left untested.

## Verified, no change needed

- **The volume reader refuses every remote URI**, as the module says.
  - `volume_cartographer_wrapper.local_volume_path` refuses `http`, `https` and `s3` by name, and any other `://`
    address.
  - So `s3a` and `s3n` addresses are refused as well, and the split check is the spelling check a later remote reader
    would face.
- **Local paths still follow the shared identity.** `volume_location` decides which identifiers are local, and its
  existing-path-first rule is unchanged.
- **A local identifier and a remote one are never counted as overlapping.** Only two remote identifiers are
  compared by spelling.
- **A year under a name is not a level, but any integer that is the whole key is one.** #420's tests cover both,
  with `scroll/2024` and the root key `100`.

## Observations for the owner (not changed)

- **The loader's import fallback would not refuse a remote URI.** If `volume_cartographer_wrapper` cannot be
  imported, `vesuvius_loader` defines its own `FastLocalVolume`, which passes the identifier straight to `zarr.open`.
  Zarr 2 sends a `://` address to fsspec, and s3fs is installed. The wrapper is packaged and needs only NumPy and
  Zarr, so this path runs only where the wrapper is not on the import path at all. In that case the module's "the
  volume reader refuses every remote URI" would not hold.
- **Normalization errs towards refusing.** Stripping spaces and dropping path parameters can merge two S3 keys that
  differ only in those characters. They are then refused as one volume, which is the conservative direction.

## Verification

- **The touched module.** `test_training_split.py` gives 115 passed, against 104 on `0dd7e98`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,104 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** 269 failing ids. That is round #187's 268 plus one test #398 added,
  `test_real_source_augmentation_executes_without_fallback_or_cuda`, which round #187's suite run predates. It stops
  at "No module named 'vesuvius'", the package from villa.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,771 passed. The
  count rose from 2,744 with tests that main's merges added to those modules.
- **The doc audit**, run alone, lists the same unresolved references as on `0dd7e98`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`data_split.py` is in `scripts/training/`**, where only tests may be added. Its mutants were run in a worktree.
- **Still not reviewed from the owner's merges since round #182:** #398, #400, #405, #416, #419, #438, #446, #447,
  #448, #450, #451, #453, #456, #458, #461, #463, #465, #468 to #478, #480, #483, #485, #488 and #489.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 45 were run again with the new tests: 42 are killed and the three above are not.
