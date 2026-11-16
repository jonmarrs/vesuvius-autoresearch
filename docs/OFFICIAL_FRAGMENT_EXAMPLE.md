# A pinned official fragment example

This CPU recipe fetches two adjacent surface-volume layers of public fragment
**Frag1 / PHercParis2Fr47**, its supplied ink labels, mask and surface metadata.
It exercises source acquisition, canonical label preparation, lossless import
and the strict training reader. It does not train a model or provide an accuracy
measurement. Two slices are a data-plumbing example, not the research loop's
normal depth context.

The [source manifest](../configs/data/fr47_two_layers.json) pins complete encoded
file sizes and SHA-256 digests, observed on 2026-11-16 at the
[public surface export](https://dl.ash2txt.org/fragments/Frag1/PHercParis2Fr47.volpkg/working/54keV_exposed_surface/).
These are hashes of retrieved HTTPS bytes, not separately published upstream
checksums. ETags and Last-Modified headers are recorded as response context;
the pinned byte counts and digests control acceptance. New upstream bytes require
an explicitly reviewed new manifest.

## Fetch and inspect

Use an editable checkout and its project interpreter. NumPy, Pillow, OpenCV and
Zarr are needed; fetching does not require CUDA. `--help` works without scientific
imports. Choose new paths with room for roughly 400 MiB of source and prepared
CT, plus labels, temporary data and filesystem overhead:

```sh
uv run --no-sync python scripts/training/fetch_fragment_example.py \
  --output /tmp/fr47-example-download
```

The default manifest selects source TIFF layers **16 and 17**, each 103,571,722
bytes, on an **8181 × 6330** Y/X grid at nominal **3.24 µm** voxel size. All five
downloads total **207,294,186 bytes** (about 198 MiB).

The new directory contains:

| Path | Content |
| --- | --- |
| `raw/surface_volume/16.tif`, `17.tif` | Original big-endian uint16 TIFF bytes, unchanged. |
| `raw/inklabels.png`, `raw/mask.png` | Original palette PNGs, unchanged. |
| `raw/surface_volume/meta.json` | Original surface export metadata. |
| `labels/inklabels.png`, `labels/mask.png` | Canonical grayscale uint8 PNGs encoded as 0/255. |
| `source.json` | Captured manifest hash, source pins/response context and canonical PNG hashes. |

The source PNGs have palette indices 0/1, whose palette colors are black/white.
The adapter verifies the **used palette RGB colors** and maps black to 0 and
white to 255. It does not treat an arbitrary nonzero palette index as ink.
Reversed indices still follow their actual colors. Transparency, intermediate
gray/color labels, nonidentity orientation, multichannel inputs, incorrect
shapes and non-uint16 TIFFs are refused. No resampling, cropping, CT intensity
scaling, class filling or label refinement occurs. Original PNG profiles remain
in `raw`; canonical PNGs carry categorical values without those profiles.

The existing generic importer continues to reject palette PNGs. Use the
canonical `labels` directory for the next step.

## Import without changing a training configuration

The data are co-packaged on the official surface export's grid. Metadata and
all image dimensions must match. This checks source/grid consistency; it does
not independently prove physical registration or annotation quality. Inspect
the source, scale, crop and orientation for your purpose before declaring the
aligned-label contract:

```sh
uv run --no-sync python scripts/training/prepare_surface_volume.py plan \
  --layers /tmp/fr47-example-download/raw/surface_volume \
  --labels /tmp/fr47-example-download/labels/inklabels.png \
  --mask /tmp/fr47-example-download/labels/mask.png \
  --z-start 16 --z-stop 18 --aligned-labels \
  --output /tmp/fr47-example-import-plan.json

uv run --no-sync python scripts/training/prepare_surface_volume.py build \
  --manifest /tmp/fr47-example-import-plan.json \
  --output /tmp/fr47-example-prepared
```

See the [importer contract](TRAINING_DATA_IMPORT.md) for output files, readback
checks, masks, resource budgets and publication behavior. It verifies every CT
plane after writing, preserving uint16 values in little-endian Zarr. The prepared
volume has shape **[2, 8181, 6330]** and `source_origin_zyx: [16, 0, 0]`.

The strict reader uses **output-relative** indices: this example's `num_layers`
is 2 and its depth band is `[0, 2)`. `[16, 18)` refers to the original TIFF names
and is invalid for the prepared two-slice array. The loader does not apply the
origin attribute automatically. Preserve the nominal 3.24 µm scale separately
in any future experiment's settings; the existing importer does not infer a
training configuration from source metadata.

Do not point the existing loop configuration at this diagnostic subset. A real
training recipe needs its full depth/context, preprocessing, split review and
incumbent re-evaluation. This public fragment is not an independent holdout by
virtue of being downloaded again.

## Acquisition and validation limits

Both the source manifest and surface metadata JSON are limited to 2 MiB. The
command accepts `--max-download-bytes` (default 512 MiB across all pinned files)
and `--max-file-bytes` (default 128 MiB). Manifest geometry uses the importer's
160 Mi-pixel ceiling. Requests require HTTPS on the official fragment host,
HTTP 200 with no redirect, exact byte counts and matching digests. Missing,
truncated, oversized or changed responses fail the whole acquisition. Files
are recaptured and checked against their pins before decoding. Requests have a
30-second socket timeout; this is not a total job-duration limit.

Invalid manifests/images and HTTP transfer failures exit with code 2 and a
concise diagnostic. This includes interrupted chunked responses and malformed
HTTP replies; a partial download is never published as a completed example.

The complete directory is staged beside a new destination and published only
after source and decoded-contract checks. Existing destinations are refused.
Caught failures clean staging. Serialize writers; this is not a concurrent-writer
or crash-durable transaction. Encoded files, decoded planes, PNG buffers and
inventories also use memory/disk; acceptance budgets are not peak-memory or
free-space guarantees.

The [real-data verification record](../reports/official_fragment_example_review_2026-11-16.json)
records the actual source pins, lossless CT comparisons and a bounded strict
loader check. Routine regressions use synthetic responses and never download
these images. No dataset bytes are committed to the repository.
