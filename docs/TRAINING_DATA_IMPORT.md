# Import local fragment CT for training

The maintained CPU command `scripts/training/prepare_surface_volume.py` converts
already-downloaded TIFF layers and aligned binary PNG labels into a **new**
training-fragment directory. It preserves CT values, records source hashes and
can verify the prepared fragment against its receipt.
It needs the checkout's NumPy, Pillow, OpenCV and Zarr 2 dependencies; `--help`
works without importing them. It does not use CUDA or train a model.

This closes the local conversion gap in the [quick start](../README.md).
A [pinned official Frag1 example](OFFICIAL_FRAGMENT_EXAMPLE.md) now supplies
download provenance, explicit palette-label preparation and a two-layer real-data
check through this importer and the strict reader. Routine tests remain synthetic.
Source/grid consistency does not independently establish physical alignment,
annotation quality or scientific performance. Archived downloaders are not a
supported preparation recipe.

## Input contract

- Consecutive, single-frame, scalar **uint16 TIFF** planes named `00.tif`,
  `01.tif`, etc. Names use at least two digits; indices above 99 keep all digits.
  Specify the start and exclusive stop; missing planes fail instead of producing
  placeholders. At most 512 planes are accepted.
- One grayscale, uint8 PNG label image containing only **0 and 255**. Here 0
  means non-ink and 255 means ink. Palette PNGs, soft targets, pseudo-label 128,
  0/1 encodings and multi-channel images are refused. Resolve uncertain labels
  separately using the [label proposal workflow](LABEL_EDIT_PROPOSALS.md).
- An optional mask with the same PNG contract: 255 includes pixels and 0 excludes
  them from the mask's eligible area. No mask is invented if it is absent.
  The training loader uses thresholded patch selection, so a selected patch may
  overlap zero-mask pixels. Ink-based selection and an explicit patch catalogue
  can override the mask; the mask is not a per-pixel loss exclusion map.
- TIFF and PNG orientation metadata must be absent or identity (EXIF orientation
  1). Other values are refused: Pillow otherwise rotates TIFFs
  automatically, including shape-preserving turns that evade dimension checks.
  Independently align and export images on the intended grid before importing;
  removing a tag alone does not establish registration.
- All images must have exactly the same Y/X dimensions. Independently verify
  their physical crop, scale, orientation and registration, then declare
  `--aligned-labels`. Equal shapes and that declaration do not prove alignment.

No resampling, inversion, intensity scaling, label filling or automatic label
refinement takes place. Big-endian uint16 TIFF values are preserved in
little-endian output. This is separate from the detector's older TIFF-to-uint8
high-byte conversion; the two numerical input recipes are not interchangeable.

## Plan, inspect and build

From an editable research checkout, with the project interpreter active:

```sh
python scripts/training/prepare_surface_volume.py plan \
  --layers /path/to/fragment/layers \
  --labels /path/to/fragment/inklabels.png \
  --mask /path/to/fragment/mask.png \
  --z-start 0 --z-stop 32 --aligned-labels \
  --output /path/to/new-fragment-plan.json

python scripts/training/prepare_surface_volume.py build \
  --manifest /path/to/new-fragment-plan.json \
  --output /path/to/new-fragment
```

Remove `--mask` if no independently verified mask exists. Replace all example
paths and the Z range with your actual inputs; this example does not download
data. Both output paths must be new, local and separate from all inputs. The
commands return JSON with the completed path, or exit 2 with a diagnostic.
Neither changes the training configuration, checkpoint or existing fragment.

Planning decodes every input and records absolute resolved paths, byte counts,
SHA256 digests, shape, original Z indices and resource limits. Inspect that JSON
before building. Building captures and hashes each input again, checks its
dimensions/type, writes one CT plane at a time and compares every CT plane with
its readback. A changed input refuses publication. The parsed manifest and its
recorded hash come from the same capture; manifest changes during building also
refuse publication.

The new directory contains:

| Artifact | Contract |
| --- | --- |
| `surface_volume.zarr` | Bare Z/Y/X uint16 array, uncompressed, chunks up to 1×128×128. |
| `inklabels.png` | Original binary label PNG bytes, unchanged. |
| `mask.png` | Original binary mask PNG bytes, only if supplied. |
| `import.json` | Full input manifest, its captured hash, effective budgets, decoded CT digest and validation scope. |

The array records its source origin in `source_origin_zyx`. Output Z starts at
zero: source slice 16 becomes output slice 0 when `--z-start 16` is used.
Training `depth_band` and patch coordinates use **output** indices; the loader
does not apply that origin attribute automatically. Recheck the configured band,
number of layers, patch size and training/validation independence before using
the new path. The reader normalizes this uint16 CT by 65535. Reevaluate the
incumbent under the resulting inputs/protocol before restarting the research
loop; see the [quick start](../README.md).

## Verify a prepared fragment

Run this check after moving a fragment or before reusing a stored copy:

```sh
python scripts/training/prepare_surface_volume.py verify \
  --fragment /path/to/prepared-fragment
```

Keep `import.json` with the fragment. The checker uses the existing contract 1
receipt and can run after the original TIFFs and manifest have been removed.
Verification accepts recorded Windows and POSIX source paths for copied fragments.
It checks the importer's uncompressed Zarr layout, axes and source origin, then
reads each expected chunk at its full encoded size. Each chunk must exist even
if its voxels are all zero. A normal Zarr read can substitute a fill value for
a missing chunk.

The checker recomputes the decoded CT digest one plane at a time and verifies
the original `inklabels.png` and optional `mask.png` against their recorded
file hashes. A saved fragment with no mask must still have no `mask.png`.
On success, it prints `status: verified`, the receipt hash, CT hash and chunk
count, and the image hashes. On failure it prints a diagnostic and exits 2.
Run it with a stable fragment and serialize verification with writers.

The receipt is a local record of the original import. Physical alignment, label
quality, additional refined labels and training split independence require
their own checks. The verifier covers the importer's dense layout and its
original PNGs. Copy the uncompressed store and receipt together.

## Choose the training read policy

For an experiment that must stop on failed or malformed CT reads, set
`"strict_training_reads": true` in its configuration. Both labeled training
and active UA-MT readers then abort on read failures, CT chunks with the wrong
shape or non-finite values, unsupported dtypes and failed requested preprocessing. Valid CPU ridge
preprocessing remains supported. Strict UA-MT rejects Lasagna because that
reader does not implement it; the configuration fails before training starts.

The default is `false`, preserving the existing counted permissive fallbacks.
Validation always uses strict reads, including the underlying CT reader. The
chosen `data_read_policy` is recorded in successful checkpoints and run results;
`loader_warnings` still reports fallbacks used in permissive mode. An aborted
run may leave earlier artifacts; this setting adds no rollback or cleanup.

Inspect an experiment configuration without reading arrays or starting training:

```sh
python3 scripts/workspace_status.py --config your-experiment.json --json
```

The report includes the selected read policy. It does not establish that the
data are readable or correctly registered. A policy default change, failure
budget, retry/skip behavior and real-data failure-rate measurements remain
separate decisions in the [audit](REPOSITORY_AUDIT.md#items-for-owner-review).
The training policy checks returned values. Use `verify` separately to confirm
the original layout and stored chunk presence for fragments from this importer.

Validation checks the exact encoded bytes it decodes for its selected labels
and optional mask. Each selected image must fit within 512 MiB of encoded data.
Fingerprinting enforces the limit before reading the payload and hashes accepted
files in blocks.
A file that differs from the initial fingerprint stops dataset construction,
even if the original is restored before the final on-disk check. Unchanged
files retain their existing validation fingerprint and sampling behavior.

## Check depth for training and validation

Each labeled training source and active UA-MT source must provide at least
`num_layers` CT slices. The trainer requests up to eight extra slices of
context. When a read has less context, it draws an offset that fits a full
model window in both the labeled and any active unlabeled batch. A batch that
can combine patches from several sources requires matching read depths within
that group. With a batch size of one, sources may have different read depths.

Validation retains its fixed four-slice offset. A validation source must
provide at least `num_layers + 4` slices, and the scorer marks a short batch
as incomplete before evaluation. Review `depth_band` in output-volume
coordinates. The two-slice Frag1 example exercises the low-level reader.

## Supply an explicit patch catalog

An optional `patches.json` beside the volume replaces automatic patch discovery
for labeled training and validation. Generate one with `scripts/find_patches.py`
when you want to reuse coordinates selected for a particular volume and patch size.
The reader accepts catalogs up to 16 MiB. The JSON must contain a nonempty
`patches` list, with integer `y` and `x` origins whose full patch fits on the CT
grid. If present, `patch_size` must match the experiment and `num_patches`
must match the list length. Order and repeated origins are preserved for the
sampler. The source paths written by the generator are descriptive and can
refer to an earlier checkout.

The loader rejects malformed catalogs in both training read modes before
sampling any patches. Check the named file and entry in the error. The existing
jitter still applies to accepted origins. Validation checks the SHA-256 of the
bytes parsed by the dataset against the catalog in its input fingerprint, even
if a file was rewritten during construction and then restored. Keep the catalog
and its source data together and confirm alignment as part of split review.

## Resource and publication limits

The three subcommands accept these defaults:

| Flag | Default | Scope |
| --- | --- | --- |
| `--max-file-bytes` | 536870912 (512 MiB) | Maximum encoded bytes per source file or verified PNG. |
| `--max-pixels` | 167772160 | Maximum decoded Y×X pixels per image; also the hard supported ceiling. |
| `--max-volume-bytes` | 1073741824 (1 GiB) | Padded, uncompressed CT chunk storage. |

Geometry and chunk padding count toward the CT storage budget before creating
the array. Compressed-source buffers, decoded planes, readback temporaries,
PNGs, JSON and filesystem overhead also consume memory/disk. These budgets are
input acceptance limits, not measured total RAM, free-space or runtime guarantees.
A full fragment may need substantially larger storage; supply an explicit larger
budget on **both** `plan` and `build` after checking the host. Build uses the
smaller of its own limits and the manifest's, so editing a manifest cannot raise
the command's configured limits. Verification uses the smallest of its own limit,
the manifest limit and the effective build limit for each budget. The manifest
has a 2 MiB cap. Verification reads the receipt and each Zarr header with an
8 MiB cap, and captures each CT chunk at its expected size.

The directory is staged beside its destination and published only after all
checks succeed. Caught failures clean staging and leave no published fragment.
Keep inputs stable and serialize writers; stat checks detect ordinary changes
but do not lock sources. Publication is not a concurrent-writer or crash-durable
transaction. An interrupted process may leave a hidden staging directory; inspect
it before removing it, and never use an incomplete staging path as training data.

For CPU regression checks in the full project environment:

```sh
python -m pytest tests/test_surface_volume_import.py tests/test_detector_conversion_contracts.py tests/test_convert_fragment.py -q
```

These importer checks are part of the curated validation suite, separate from
the smaller dependency-minimal portable CI profile.
