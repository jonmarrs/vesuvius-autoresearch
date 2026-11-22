# Design and architecture review — the owner's #400, refusing a cut-short Blosc chunk

Date: 2026-11-22. Baseline: `36cb2ba` (main after round #190's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 23:12 UTC firing on 2026-11-22. Main had not moved since round #190's merge.

It takes **#400**, which adds a frame check to `repro/sota_data/pyramid_depth.py`. A Blosc chunk whose file is shorter
than the frame size in its own header can still decode to a full chunk of the wrong bytes. Before any chunk in the
compared window is read, `_complete_blosc_frame` now checks four things:
- the first byte is a Blosc format version, 1 or 2;
- the header declares a nonzero uncompressed size;
- the declared frame size is at least the 16-byte header;
- the declared frame size is exactly the file's size.

The script's earlier checks were reviewed in
`docs/DESIGN_ARCHITECTURE_REVIEW_2026-11-10_PYRAMID_DEPTH_FOLLOW_UP.md`.

## What changed

### Four more ways a chunk can miss its frame are tested (`tests/test_ink_pyramid_depth.py`)

This round made 14 mutants of the frame check and the branch that applies it. #400's tests killed five of them.
They cut only the window's first chunk short. One parametrized test with four cases kills five more. The first
commit's message says four of ten; the count is five of nine. Each case is refused by the frame check, naming the
chunk, before the codec is asked to decode it:
- **an unknown version byte**;
- **a header that declares no bytes**;
- **a byte past the declared frame.** The codec would ignore it and return the right data, so only the check sees
  it;
- **a later chunk in the window cut short.** The check runs over every chunk the window needs, not only the first.

No code changed. No defect was found.

### Four mutants are not killed

- **Three are equivalent.** Lowering or removing the `size < 16` test changes nothing, because a file under 16
  bytes already fails the header-length check. Dropping `cbytes >= 16` also changes nothing, because the frame size
  must equal a file size that is already at least 16.
- **Accepting only version 2 changes where a version-1 frame is refused, not whether.** This environment's c-blosc
  refuses to decode a frame whose version byte is 1. The check lets such a frame through, and decoding then fails
  with the codec's error.

## Verified, no change needed

- **The check applies only to Blosc arrays.** Other codecs keep their own decode errors. The module's tests cover
  those for zstd, zlib, gzip and LZMA.
- **The refusal exits with status 2** and names the level and chunk, as the docstring's exit-status paragraph now says.
- **The frame size is read from bytes 12 to 16, little-endian.** That is where the Blosc 1 header keeps it. A frame
  written by numcodecs carries version byte 2 and its own length there.

## Observations for the owner (not changed)

- **Version 1 is accepted by the check but refused by the codec here.** A version-1 frame from an older Blosc would
  reach decoding and stop with the codec's error rather than the frame message. It is refused either way.
- **The declared uncompressed size is not compared with the chunk's shape.** A frame from another array with a
  matching frame size would pass this check. Decoding it would then give the wrong number of bytes, and Zarr
  refuses that.

## Verification

- **The touched module.** `test_ink_pyramid_depth.py` gives 90 passed, against 86 on `36cb2ba`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,106 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, which holds the touched module, gives the same 269 failing ids as round #190's run.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,782 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `36cb2ba`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Still not reviewed from the owner's merges since round #182:** #398, #416, #419, #438, #447, #448, #450, #453,
  #456, #458, #461, #463, #465, #468 to #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 14 were run again with the new test: 10 are killed and the four above are not.
