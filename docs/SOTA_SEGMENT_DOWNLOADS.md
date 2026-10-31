# Plan and download a raw TIFF segment

This command supports a public bucket prefix containing direct numeric
`layers/NN.tif` files, exactly one `*inklabels*` file, and at most one distinct
`*mask*` file. It preserves the raw layout consumed by
`repro.sota_data.convert.convert_surface_volume`.

Inspect the selected objects and byte budget first:

```bash
python -m repro.sota_data.fetch "<segment-prefix>" /data/downloads/segment-run \
  --center-layers 26 --dry-run
```

Remove `--dry-run` to download. The prefix may be bucket-relative, prefixed with
`vesuvius-challenge-open-data/`, or its `s3://` URI in that same bucket. Output must
be a **new local directory**. Existing directories, files and symlinks are refused
before remote access; a rerun needs another destination. Interrupted directories
created by the old downloader are not repaired or overwritten.

`--dry-run` lists metadata and prints JSON with selected source keys, original
depth indices, object sizes, ETags when available and total bytes. It reads no
object bodies and creates no output directories. Help imports neither S3 nor ML
packages. Downloads are anonymous; no credentials or interactive login are needed.

`--center-layers 26` selects the center 26 numerically sorted layers using
`floor((available - count) / 2)`, the converter's existing rule. Source filenames
and original indices are preserved. Downloading 41 layers and downloading just
the center 26 produced identical converted planes in the synthetic integration
test. The converter must use that same layer count. Omitting the flag downloads
all direct numeric layers. No surface-plane alignment is inferred.

Limits are checked before payload transfer:

| Setting | Default | Maximum |
|---|---:|---:|
| `--max-bytes` | 4 GiB | 64 GiB |
| `--max-file-bytes` | 512 MiB | 2 GiB |
| `--max-files` (includes label/mask) | 512 | 1024 |
| `--max-entries` (combined direct listings) | 4096 | 4096 |

These flags take integer bytes/counts. A larger declared object or selected total
fails before transfer. Budgets cover selected remote payloads, not HTTP metadata,
headers or retry traffic; the local manifest and tool copies are extra small files.
Listings are direct and never recurse, but the filesystem
SDK can buffer listing responses before the entry cap is checked. This is not a
hard bound on SDK metadata memory. Disk space and a total wall-clock deadline are
not reserved. Smaller selections can reduce transfer volume; no general speed or
peak-memory benchmark is claimed.

Nested caches, Zarr trees and unrelated files are not downloaded. Layer indices
must be unique and the selected indices consecutive. Root label/mask matching
uses the converter's case-sensitive, non-hidden filename behavior. Ambiguous
labels/masks and matching directory entries fail before any payloads. Missing
masks remain explicitly absent; the download does not invent one.

S3 objects require ETags. Each payload request uses an explicit `GetObject` range
of at most 1 MiB with `IfMatch` set to the planned ETag. Response identity, range,
total length and body lengths must agree. Remote selections and object identities
are relisted after transfer. Local payload hashes, exact directory contents,
copied tool sources and original tool files are rechecked before completion.
The implementation avoids `s3fs.open(size=...)`, which can bypass that SDK's
automatic ETag condition.

The completed directory contains raw layers, the selected label/mask,
`download.json`, and `sources/` with three tool-source captures. The JSON records
SHA-256 hashes of the actual downloaded bytes, source identities, original indices,
selection settings and runtime versions. ETags are object identifiers, not assumed
to be MD5 or authenticated content checksums. A local SHA-256 records observed
bytes; it does not authenticate a scientific release.

Only a complete new directory is published. Caught failures discard staging and
return a nonzero result. A killed process can leave a hidden staging directory;
it is not the final destination. There is no partial-transfer resume. Serialize
local writers and keep sources/code stable. Per-object conditions and rechecks
are not a global S3 snapshot or a power-loss durability guarantee.

Exit 0 means a plan or transfer completed; input/transport/publication failures
exit 1 and usage errors exit 2. Image decoding, CT registration, annotation quality
and training readiness remain unverified. The downloader performs no conversion,
training or GPU work, and does not adopt a checkpoint or alter a study.

Use the [conversion preflight](SOTA_SEGMENT_CONVERSION.md) next. Conversion checks
consumed raw files against this download record when present, catching later edits.

Modern bucket segments often have `surface-volumes/`, `mesh/` and `ink-labels/`
instead of this legacy TIFF layout. For example, the public segment
`PHercParis4/segments/20230702185753` lacked `layers/` during this review. A clear
`no layers/ to fetch` failure is intentional; increasing budgets does not convert
that layout. Use the project's separate OME-Zarr extraction or
[surface-rendering workflow](SURFACE_RENDERER.md) for those inputs.
