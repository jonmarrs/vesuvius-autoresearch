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

When `progress.json` exists, the checker validates its CT/label paths, shape,
patch size, output directories and coordinate system against the receipt. It
checks logged status names, bounds, indices and percentages and reports counts
for `approved`, `skipped`, `auto-skipped` and `pending`. If progress is absent,
it reports `present: false`; unchanged inputs do not imply that work was saved.
The JSON includes hashes of the receipt and present progress file, calculated
from the same captured bytes that were parsed.
Approval counts describe the log, without authenticating approvals or verifying
the TIFFs, edited-label Zarr, or the progress file's approved-patch export list.

The JSON always reports:

- `resume_supported: false`
- `approved_patch_files_verified: false`
- `ink_training_ingestion_supported: false`

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

Record/progress JSON and the proofreader source file have a separate 2 MiB cap.
Hashing reads all source bytes each time; use a bounded crop or explicitly raise
limits on both commands after checking the host. Hash buffers, tree inventories,
pre-existing label-range scans, JSON and GUI allocations also consume resources.
These are acceptance limits, not total memory, free-space or runtime guarantees.
Publication uses the existing staged new-file writer; concurrent writers and
crash durability are not guaranteed. No existing receipt is overwritten.

CPU regression tests are in `tests/test_proofreader_session.py` and
`tests/test_proofreader_launcher.py`. They use small synthetic Zarrs and execute
the pinned `update_progress` serializer in isolation. They do not start Napari,
exercise interactive edits or validate real annotation data.
