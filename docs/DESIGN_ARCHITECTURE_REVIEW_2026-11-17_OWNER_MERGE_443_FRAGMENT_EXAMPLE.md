# Design and architecture review — the owner's #443, the official fragment example

Date: 2026-11-17. Baseline: `f867a8f` (main after #442).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 00:12 UTC firing on 2026-11-17. Main moved before the round began, with #442, which this
round merged and did not review.

It takes **#443**, merged at 17:58 UTC on 11-16. #443 adds
`src/vesuvius_autoresearch/core/fragment_example.py` and its command,
`scripts/training/fetch_fragment_example.py`. They download a pinned public surface-fragment example from the
official host, with every file pinned by size and SHA256, and turn its ink labels and mask into plain black and
white PNGs. The module is not registered.

## What changed

### Twenty-eight guards of the fragment example are now held one by one (`tests/test_fragment_example.py`)

The module fails closed throughout, and this round found no defect in it. Several of its guards are doubled:
- the download and the later read-back both check the hash;
- a refused manifest is refused by some rule even when another rule is removed.
So a guard could be removed without any test noticing. This round made 39 mutants. #443's tests killed 9. Twelve
new test functions (27 cases) kill 28 of the other 30:
- **Each manifest rule refuses with its own reason.** Each case names the message it expects: an extra key, a
  schema or kind that is not the supported one, a fragment ID with a slash, a layer range that starts below zero,
  is empty or is longer than 512, a depth that differs from the range, a scale of 0 or `true`, other label
  semantics and a blank pin basis.
- **The source directory is HTTPS and has no empty component.**
- **The size limits are inclusive.** A grid of exactly the largest allowed size passes, and one more pixel does
  not. Each byte limit passes at the pinned total and largest file and refuses one byte under. The metadata JSON
  may be exactly 2 MiB.
- **A repeated key, a non-finite token and an uppercase digest are refused.**
- **The downloader stops at the pinned size and checks the digest itself.** A response 5 MB too long leaves at
  most the pinned bytes on disk.
- **The read-back checks the digest itself**, against a file changed after download to bytes of the same length.
- **A real redirect is refused without asking for its target.** A local HTTP server answers 302. The module's
  own opener raises the 302, and the server is never asked for the target. #443's tests replace the opener, so
  its no-redirect handler had never run under test.
- **The official metadata must match the pinned scale, layer count and grid**, and a layer of another size is
  refused.

No code changed.

## Verified, no change needed

- **The manifest check is exact.** It allows exactly the expected keys. It needs an official HTTPS fragment
  export path whose fragment ID matches, and it pins every requested layer, the labels, the mask and the
  metadata, each once, with a lowercase SHA256. It refuses a duplicate key and a non-finite token. A scale of
  `10**400`, which JSON reads as an integer, raises `OverflowError` in the finiteness test, and the command reports
  it and exits 2.
- **Nothing is published unless every check passes.** Files are written with exclusive create into a staging
  directory and published only at the end. #443's tests cover truncated, long, corrupted and redirected
  responses, a non-200 status, network and protocol errors, and corruption after download.
- **Labels are read by their displayed colours, not their palette indices.** Only exact black and white are
  accepted, with no transparency.
- **The bundled manifest passes the default checks without the network.** #443's test covers it.

## Observations for the owner (not changed)

- **Two guards cannot be reached, so no test can hold them.**
  - The RGB-palette check comes after the transparency check. A PNG palette with alpha is read back as an RGB
    palette with a transparency chunk, so the transparency check always fires first.
  - The receipt is written with `allow_nan=False`. No value that reaches it can be non-finite.
  Both are harmless.
- **The download was not run here.** The tests stub the network, and the redirect test uses a local server.

## Verification

- **The touched module.** `test_fragment_example.py` gives 64 passed, against 37 on `f867a8f`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,023 files, with `--python-executable ./.venv/bin/python`.
- **The suite's guard against bare file names** in tests passes.
- **The standard suite.** The 226 modules give the same 234 failing ids as round #177's run.
- **The test modules outside the suite.** The 264 modules give the same 23 failing ids as round #177's run, and
  2,716 passed. The two modules #442 added pass.
- **The doc audit**, run alone, lists the same unresolved references as on `f867a8f`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Not reviewed in #443:** the documents (`README.md`, `docs/OFFICIAL_FRAGMENT_EXAMPLE.md`,
  `docs/TRAINING_DATA_IMPORT.md` and the audit), the owner's own review record, and how the prepared labels feed
  the surface-volume importer beyond #443's own test.
- **Still not reviewed:** #442, #433, #436 and #437, #422, #424 and #428, the rest of #390, #396 and #411, and the
  parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample** of the module. Its tests passed here before the mutants were run. The 30
  survivors were run again against the new tests; the 9 that #443's tests killed were not.
