# Design and architecture review — the owner's #481, the validation image check

Date: 2026-11-22. Baseline: `2d7463c` (main after round #183's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 15:12 UTC firing on 2026-11-22. Main had not moved since round #183's merge.

It takes **#481**, which landed during round #183. #481 makes validation hash the label and mask PNGs it selects,
and decode only the bytes whose hash matches. The work is in three places:
- `src/vesuvius_autoresearch/core/file_capture.py` splits the bounded capture into `_open_bounded_file` and adds
  `capture_sha256`, which hashes in blocks;
- `src/vesuvius_autoresearch/core/vesuvius_loader.py` adds `_read_validation_image`;
- `scripts/training/promotion.py` fingerprints the images with `capture_sha256` under a 512 MiB cap.

## What changed

### Six guards of the capture and the image check are now tested

This round made 26 mutants: 16 of `file_capture.py`, 7 of the loader and 3 of `promotion.py`'s image hash. The
existing tests of seven modules killed 19, and one cannot be killed (below). Five new test functions, 8 cases,
kill the other six.

In `tests/test_text_snapshot.py`, for both `capture_bytes` and `capture_sha256`:
- **A capture names the file a link resolves to.** The importer records that path as the source.
- **A file growing while it is captured is read one byte past its size.** It is reported as changed, not read on to
  the end and reported as oversized.
- **A same-size rewrite with its mtime restored is still seen**, through the change time. Copy tools that keep
  timestamps leave only the change time to show it.

In `tests/test_autoresearch_measurement.py`, for `_read_validation_image`:
- **A validation image is decoded only with its recorded digest.** A wrong digest is refused, and so is an image that
  was absent when the inputs were fingerprinted but is present when read.
- **A fingerprinted image cannot be passed over.** No path with a recorded digest is refused. No path and no digest
  gives no image.
- **The image is read within the fingerprint's byte cap.**

No code changed. No defect was found.

### One mutant no test can kill

**Dropping the modification time from the change check.** On Linux, any write or `utime` that moves the
modification time also sets the change time. The change time is still checked, so it sees the same edits.

### Why the image check survived #481's own tests here

#481 tests the check by replacing an image during `build_validation_dataset`. That test needs villa's patch finder,
which this container does not have. The new tests call `_read_validation_image` directly, so they run without villa.

## Verified, no change needed

- **Unchanged images keep their fingerprint.** `capture_sha256` hashes the same bytes that `_file_sha256` hashed,
  and the record's keys are unchanged, so an incumbent's recorded fingerprint still compares. #481's record reports
  the same fingerprint as the parent implementation on a copy of the Frag1 import.
- **The 512 MiB cap is checked before any byte is read**, from the opened file's size, in both the fingerprint and the
  loader. #481's test covers the fingerprint, and this round's covers the loader.
- **The capture still refuses what it refused before #481:**
  - a path that is not a regular file, before and after opening it;
  - a file over the limit;
  - a file whose size, modification time or change time moves during the read.
  The existing tests cover these.
- **Train's mask choice still covers a mask that appears late.** A mask absent at fingerprinting but present at
  construction is passed with no digest, and the reader refuses it as changed.
- **The documentation matches the code.** `docs/TRAINING_DATA_IMPORT.md` says each selected image must fit in
  512 MiB, the limit is enforced before the payload is read, and accepted files are hashed in blocks. All three hold.

## Observations for the owner (not changed)

- **A missing selected label is refused with the capture's message.** The validation dataset always passes the label
  path, so an absent label reaches `capture_bytes` and is refused as "input must be a regular file", not with the
  reader's "selected validation image is missing". Only the wording differs; validation still stops.

## Verification

- **The touched modules.** `test_text_snapshot.py` gives 23 passed, against 18 on `2d7463c`.
  `test_autoresearch_measurement.py` gives 133 passed and 3 failed, against 130 and 3. The three failures need villa.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    two changed test files.
  - Mypy is clean over the whole repository, 1,091 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** 251 failing ids: round #183's 249 and #481's two
  `test_validation_rejects_an_image_rewrite_reverted_after_decoding` cases, which round #183 ran before #481 was
  merged. Both stop at villa's patch finder, as they do on `2d7463c`.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,744 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `2d7463c`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`train.py` and `promotion.py` are in `scripts/training/`**, where only tests may be added. Their #481 changes were
  read and three of `promotion.py`'s lines mutated. `build_validation_dataset`'s own changes are bound by #481's
  tests, two of which need villa.
- **Still not reviewed from the owner's merges since round #182:** #447, #448, #450, #453, #456, #458, #461 to #463,
  #465, #466, #468 to #478 and #480.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 26 were run again with the new tests: 25 are killed and the one above survives.
