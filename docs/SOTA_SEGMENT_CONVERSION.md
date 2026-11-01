# Preflight and convert raw SOTA layers

Convert the legacy raw TIFF layout from the [segment downloader](SOTA_SEGMENT_DOWNLOADS.md)
into a fresh detector fragment. Inspect headers before decoding CT values:

```bash
python -m repro.sota_data.convert --src /data/raw/segment-run \
  --segment segment-run --out-root /data/converted --layers 26 \
  --float-encoding byte --dry-run
```

Choose the encoding from the release's documented units, then remove `--dry-run`
to convert. Output `/data/converted/segment-run` must not exist, including a file
or broken symlink. Use a fresh id or root for reruns. The output must be outside
the raw source directory. Sources must be regular nonsymlink files.

The plan is `HEADER_PLAN_ONLY`: it lists selected files, original depth indices,
shape, dtype, byte sizes and options. It creates no output directories and does
not decode pixel arrays, determine a float scale, check payload hashes, assess
label quality or establish CT registration. Help requires only Python's standard
library; planning/conversion needs NumPy, tifffile, OpenCV and Pillow, with no
Torch, CUDA or S3 imports.

## Intensity and depth rules

| Input | Mapping to uint8 |
|---|---|
| uint8 | unchanged |
| uint16 | high byte (`value // 256`) |
| float, `unit` | finite [0, 1], multiply by 255, truncate |
| float, `byte` | finite [0, 255], truncate |
| float, `auto` (default) | choose `unit` if the entire selected volume's maximum is <= 1; otherwise `byte` |

One float scale applies to every selected depth plane. Previously, each plane's
maximum chose its scale independently: the same value `0.5` became 127 in one
plane and 0 in another when a second plane contained a value above 1. Explicit
`unit` refuses an outlier above 1; it never silently switches to byte units.
`auto` preserves the range heuristic for compatibility and cannot infer physical
units. Regenerate affected old fragments in a new directory; this command does
not rewrite datasets or checkpoints. Mixed layer dtypes, signed integers, color
or multipage layers, empty inputs and nonfinite/out-of-range floats are refused.

Default depth selection is `floor((available - requested) / 2)` after numeric
sorting. Download, raw conversion and qualitative extraction use this same rule.
For 40 available planes and 25 requested, the selected positions are 7 through 31;
qualitative extraction previously began at 8. Duplicate indices and gaps within
the selected window fail. Default output filenames remain `17.tif` through
`42.tif` for 26 planes; `--start-idx` changes the first output filename. Source
indices are preserved in provenance. Default counts/start indices are unchanged.

The Python qualitative helper accepts an optional `z_center`: it places that
plane at position `count // 2` and now refuses a window that would exceed either
boundary. It previously clipped invalid centers silently. Pass a fitting center
or omit it to request the default centered window. Its `write_fragment` helper
also accepts `float_encoding=`; teacher-label conversion keeps the existing
single-image heuristic.

## Bounds and supervision

The selected volume is capped at **134,217,728 voxels** by default (enough for
26 x 2048 x 2048). `--max-voxels` can explicitly raise it up to 536,870,912.
There are at most 512 selected planes, 4096 candidate TIFF names and 512 MiB per
encoded input file. Headers and sizes are checked before pixel decoding; captured
bytes are checked again before decoding. These are accepted input limits, not a
hard bound on decoder/metadata allocations or process peak memory. For example,
float64 uses eight bytes per voxel plus decoder, validation and staging buffers.
Disk space is not reserved, and no large-volume performance benchmark is claimed.
The array-based qualitative/render publisher has no new allocation budget; its
caller owns array acquisition and memory limits.

Require one non-hidden `*inklabels*` file and at most one distinct `*mask*` file,
using case-sensitive names. Labels/masks must be single grayscale uint8 or 1-bit
images without transparency; RGB, palette, uint16 and multiframe supervision are
refused instead of silently reduced. This is stricter than the old OpenCV
grayscale coercion. Label/mask dimensions may differ from the layer grid by at
most two pixels per axis. They are cropped or zero-padded at the existing origin,
never resized. Label padding remains outside the validity mask. This tolerance
does not prove alignment. Missing masks use the labeled extent, and qualitative
fragments remain label-free unless a caller supplies a label.

## Completion and evidence

Each consumed source is hashed and decoded from the **same captured bytes**.
When `download.json` exists, its contract/status/path identities are validated and
each consumed layer/label/mask must match its recorded byte count and SHA-256.
The label/mask selection must also match the record; deleting a downloaded mask
cannot silently substitute an all-valid mask. The local layer files must be exactly
the recorded ones: the centered window is taken over all of them, so an added or
deleted layer would otherwise move it while every consumed file still verified.
Unconsumed layers' bytes and downloader tool captures are outside that check's
scope. Legacy sources without a download record remain supported and explicitly
record `download_consumed_hashes_verified: false`.

Raw conversion records source hashes, selection, dtype, options and download
record identity in `<id>_render_provenance.json`. This legacy filename also
remains unchanged for render callers. Every shared-publisher output now has a
`fragment.json` containing shape, encoding, label presence and file byte counts
and SHA-256 hashes. TIFF/PNG outputs are decoded and compared against intended
pixels; metadata is read back; sources, selection and staged output hashes are
rechecked before one directory rename publishes the complete fragment. Failure
discards staging and leaves no final fragment. A killed process can leave a
hidden staging directory. Serialize writers and keep inputs stable; this is not
a filesystem-wide snapshot or power-loss durability guarantee. Hashes record
observed bytes and do not authenticate a scientific release.

`alignment_verified`, `label_quality_verified` and `training_ready` remain false.
No training, study updates, checkpoint promotion or GPU work occurs. Exit 0 means
the requested plan or conversion completed, 1 means an input/I/O failure, and 2
means a usage error. Modern OME-Zarr-only layouts require the separate
[surface-rendering workflow](SURFACE_RENDERER.md).
