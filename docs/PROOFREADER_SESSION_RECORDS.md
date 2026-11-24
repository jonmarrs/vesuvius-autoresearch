# Record and check a 3D proofreading session

Use the existing [3D categorical-label launcher](CHECKPOINT_ANALYSIS.md#launch-the-3d-label-proofreader)
with `--record-session` to retain the configured input identity before opening
the GUI:

```sh
uv run --no-sync python scripts/launch_proofreader.py \
  --volume /path/to/ct.zarr --predictions /path/to/categorical_labels.zarr \
  --patch-size 64 --out-dir local_data/new_proofreading_session --record-session

# After closing the GUI; this command only reads files:
uv run --no-sync python scripts/check_proofreader_session.py \
  --session local_data/new_proofreading_session
```

The launch still requires a new or empty output directory and matching 3D CT and
integer labels in `0..255`. Independently establish their physical alignment.
One-plane regional uncertainty and probability maps are not volumetric labels.
The default launcher behavior is unchanged when the flag is absent. Both tools'
`--help` works without scientific or GUI dependencies. Launch requires Villa and
its GUI dependencies; verification requires NumPy/Zarr but does not import Napari.

## What is recorded

The new session contains an `autoresearch_session.json` initial-input receipt.
It stores the full initial configuration, CT shape, pinned proofreader source
digest, source paths, resource limits, and a content fingerprint for each selected
local array directory. An OME group's level-0 directory is selected before recording,
as it is for the actual GUI inputs. The complete selected directories are hashed,
including every encoded chunk and metadata file, not only Zarr metadata.

The tree fingerprint hashes sorted records of relative filename, encoded byte
count and SHA-256 of the captured file bytes. Source files must be regular and
have no symlinks or hard links within the selected tree. Inventory/stat checks
before and after capture detect ordinary mutation; they do not lock sources.
Keep inputs stable and serialize launch, GUI use and verification.
For a recorded launch, the source limits and fingerprints are checked before
opening the Zarr arrays for grid and label-range checks. The launcher rechecks
the input inventories and pinned proofreader source before publishing the
receipt and opening the GUI.

Recorded launches explicitly select `progress.json` and `edited_labels.zarr`
inside the session directory. Initial sampling is sequential with `min_z=0`,
the requested cubic patch size, a 1% nonzero-label threshold and no target-label
filter. These explicit destinations avoid Villa's filename-based selection of
old progress/output stores. The record is published before the child starts;
it remains an initial-input receipt if launch fails or the GUI exits without
saving progress. It is not a success, completion or approval receipt.

## What verification establishes

The checker exits zero with JSON only when the recorded configuration is
supported, the current pinned proofreader source matches, and both source
directories still match their complete file fingerprints and shapes. It uses
the stricter of its own and the recorded resource limits. Source changes, missing
files, malformed records and mismatched progress context fail with exit 1.
The checker repeats both source inventories after checking progress, including
in the default mode, to detect ordinary changes after either source was hashed.
It also rechecks the input receipt and pinned proofreader source before
reporting success.

When `progress.json` exists, the checker validates its CT/label paths, shape,
patch size, output directories and coordinate system against the receipt. It
checks logged status names, bounds, indices and percentages and reports counts
for `approved`, `skipped`, `auto-skipped` and `pending`. If progress is absent,
it reports `present: false`; unchanged inputs do not imply that work was saved.
The JSON includes hashes of the receipt and present progress file, calculated
from the same captured bytes that were parsed.
The default checker reports approval counts from the log and sets
`approved_patch_files_verified: false`.

## Verify saved TIFF pairs

Close the proofreader before running this check. Keep the source stores and
session stable until it finishes.

```sh
uv run --no-sync python scripts/check_proofreader_session.py \
  --session local_data/new_proofreading_session --verify-approved-patches
```

The optional check requires a saved progress log. It derives the expected
`imagesTr` and `labelsTr` filenames from the approved ZYX coordinates and
matches the export list and count against the log. It reports missing or
unlisted files and refuses repeated approvals at the same coordinates because
Villa uses the same filenames for both saves.
Villa's **Previous Patch** control can rewind the log while leaving a saved
pair on disk. If a rewound patch is later skipped, the checker reports the
leftover files as unlisted. Review those files before using the exports.

Each TIFF must be a complete uncompressed cube of the recorded patch size,
with strip byte counts that match the page dimensions.
The image must match the recorded CT crop voxel for voxel and preserve its
dtype. The labels must be integers or booleans in `0..255`. On success,
`progress.approved_exports` reports the pair count, coordinates, relative
paths, sizes and SHA-256 digests of the bytes decoded. A saved log with zero
approvals reports zero pairs. NumPy, Zarr and tifffile are sufficient for the
array checks alongside the pinned Villa source file.

This verifies file and CT consistency. Assess the edited categorical labels
with a separate review.

## Compare approved labels with the edited Zarr

Use this check before handing off the edited-label array. It includes the
approved TIFF pair checks above.

```sh
uv run --no-sync python scripts/check_proofreader_session.py \
  --session local_data/new_proofreading_session --verify-edited-labels
```

Villa can save both TIFFs and log approval even when writing
`edited_labels.zarr` fails. This check requires the recorded output directory
to hold a bare uint8 Zarr v2 array with the CT shape, positive 3D chunk sizes
and zero fill. It compares
every voxel of each approved label TIFF to the stored crop at the logged ZYX
coordinates. It reports the coordinates of a mismatch and exits 1.
An all-zero approved crop can use Zarr's sparse zero fill. If approved crops
overlap, both TIFFs must agree with the stored values in the overlap.

On success, `progress.approved_exports.edited_labels` reports the array path,
shape, dtype and number of approved crops compared. A log with zero approvals
still requires a compatible array and reports zero compared crops. The
comparison covers approved crop contents. Values elsewhere in the edited
array and whether the categories are correct still require review. The report
retains `resume_supported: false` and `ink_training_ingestion_supported: false`.

Existing sessions without the initial receipt cannot be adopted by this checker.
Receipts are editable local provenance, not signed evidence or protection against
someone deliberately rewriting both the record and inputs. Unchanged readable
source bytes do not prove complete CT acquisition, correct labels, physical
registration or scientific quality.

## Why resume remains disabled

Pinned Villa can choose prior progress by filename and snap its last logged
coordinate to another patch grid. Its progress metadata does not retain the
complete GUI-setting history: sampling, minimum Z, label filter and interactive
jumps can change during a session. Pending entries can also be present when
progress is saved. An input fingerprint alone cannot define a safe resume
position or establish how each patch was selected. This launcher continues to
refuse nonempty sessions, even when their input check passes. A future resume
contract must address those upstream behaviors and approved patch contents.

## Resource limits

Both commands accept these positive integer limits:

| Flag | Default | Scope |
| --- | --- | --- |
| `--max-source-bytes` | 8 GiB | Sum of encoded file bytes per selected input directory. |
| `--max-file-bytes` | 64 MiB | Maximum captured bytes for one source file. |
| `--max-entries` | 100,000 | Files and directories per selected source tree, including its root. |

With `--verify-approved-patches`, the checker also applies the effective limits
to the two export directories as a combined set. The per-file limit bounds the
decoded size of one TIFF, CT patch or CT chunk. The checker validates one pair
at a time and checks the CT, source labels and exports for ordinary changes
during the reads.
With `--verify-edited-labels`, the same limits apply separately to the encoded
edited-label directory, and the decoded size of one edited-label chunk must
fit the per-file limit. The checker checks the edited directory before and
after reading its crops.

Record/progress JSON and the proofreader source file have a separate 2 MiB cap.
Hashing reads all source bytes each time; use a bounded crop or explicitly raise
limits on both commands after checking the host. Hash buffers, tree inventories,
pre-existing label-range scans, JSON and GUI allocations also consume resources.
These are acceptance limits, not total memory, free-space or runtime guarantees.
Publication uses the existing staged new-file writer; concurrent writers and
crash durability are not guaranteed. No existing receipt is overwritten.

CPU regression tests are in `tests/test_proofreader_session.py` and
`tests/test_proofreader_launcher.py`. They use small synthetic Zarrs and execute
the pinned `save_current_patch` writer and `update_progress` serializer in
isolation with fixture label edits and an injected Zarr write failure.
