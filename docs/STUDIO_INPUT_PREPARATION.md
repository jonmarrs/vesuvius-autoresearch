# Prepare a cropped render for the released Studio reader

`python scripts/prepare_studio_input.py --help`

This CPU-only adapter bridges the campaign's local Zarr renders and the released
Studio reader's NumPy input. It exports exactly 16 consecutive planes and an
explicit rectangular crop, in caller-specified depth order, into a **new** directory:

- `planes.npy`: uint8 `[16, height, width]`, C order;
- `input.json`: source path/key/shape, ordered plane indices, half-open crop,
  caller's depth-order explanation, selected-payload/plane hashes and output-file hash.

It does not load weights, import Torch, run inference, render CT, download anything,
select a surface, discover ink or certify geometry/legibility. No existing campaign
launcher, frozen record, model policy or publication gate is changed.

## Input contract and depth order

The [pinned upstream interface](https://github.com/priyankaranke/vesuvius-studio-multiscroll-cpt/blob/235e3be8a06749344862c89a1e52c81d90b15e0e/README.md)
requires uint8 `[16,H,W]` in model depth order. Its example stacks planes **23 down
to 8 from the supplied 31-plane surface**. That is **not** a universal mapping for
other renders, especially the campaign's 66-layer stacks. Establish native slice
spacing, surface-normal direction, origin and side for the particular render first.
The note records the caller's reasoning; this adapter cannot verify it.

The exporter does not transpose axes, reverse rows/columns, interpolate, normalize,
clip, downsample, pad or convert dtype. Upstream inference applies its own intensity
clipping/normalization. Non-uint8 arrays must be dealt with explicitly outside this
utility, not silently cast. A structurally valid stack is not a validated model input.

## Local example

For an **already verified** 31-plane render matching the upstream example, select a
small known crop. These are illustrative paths/crop coordinates, not a target or
registration:

```sh
python scripts/prepare_studio_input.py \
  --source /local/verified-render.zarr --array-key 0 \
  --output /local/studio-control-input \
  --first-plane 23 --depth-step -1 --crop 100 612 200 712 \
  --depth-order-note 'Verified 31-plane render: model depth maps from 23 down to 8'
```

`--crop ROW0 ROW1 COL0 COL1` uses half-open bounds. `--depth-step` must be `-1` or
`1`; the exporter takes 16 consecutive planes beginning at `--first-plane`.
For a local NumPy render, pass its `.npy` path and omit `--array-key`. For Zarr,
pass the local store root and explicitly name its array (for example `0`). A direct
array directory is also accepted without a key. No group/scale selection is guessed;
ensure the chosen array is at the required native spatial resolution.

Only Zarr v2 with canonical uint8 metadata, no filters, and raw or standard Blosc
compression is accepted. Metadata is bounded and checked before codec construction;
the checked metadata bytes are reused by the reader. Other filters/codecs, including
Pickle even on a numeric array, are refused rather than decoded. This narrow format
support is not a sandbox for arbitrary untrusted data.

The output parent must already exist. Existing destinations, including dangling
symlinks, are refused. Outputs inside the supplied Zarr source hierarchy are refused.
Use immutable local inputs while exporting: hashes bind the selected bytes read,
not an atomic snapshot or a hash of the entire source volume. The script does not
write source data. Local filesystem inputs only; no URLs or remote store dispatch.

Only consume the output after the command succeeds and `input.json` is complete.
Ordinary failures remove the files created by the command. Abrupt process termination
or power loss can leave an incomplete directory; it will be refused on retry rather
than overwritten. Concurrent mutation, malicious filesystem races and crash durability
are not guaranteed. Use a distinct directory for another attempt.

## Bounded preparation, not a memory guarantee

Default selected-payload cap: 256 MiB. Default logical read-block cap: 8 MiB.
`--max-output-bytes` and `--max-block-bytes` can change these limits. Oversized rows
and decoded Zarr chunks are refused before export. Logical copies are bounded;
codec overhead, metadata and operating-system page cache are additional. The limits
are not hard RSS limits. The output also includes its small NumPy header and JSON.

This first integration was exercised with synthetic NumPy and compressed Zarr
arrays only, including the actual CLI and NumPy's upstream-compatible loader
(`mmap_mode='r', allow_pickle=False`). It has not prepared a real scroll stack,
run an upstream model, established 24 GB inference feasibility or improved reading.
The NumPy tests run in portable CI; the actual Zarr tests need the project Zarr
package and run separately in the curated registry. A separate two-case CPU smoke
feeds the exported bytes through a tiny 17-parameter dummy tensor consumer, checking
both depth directions against direct array arithmetic. It uses no trained weights
and does not execute the released Studio architecture or its inference pipeline.
That Torch-dependent test is curated-only and is not part of portable CI.

## Later use and publication

Once separately authorized, `planes.npy` is the input file for the released Studio
entrypoint. This utility deliberately does not invoke that entrypoint: its wrapper
can install packages, download weights and start a model. Follow the
[strategy review](STRATEGY_REVIEW_2026-11-16.md) for positive-control exposure,
licensing and inference prerequisites. Code availability is not license clearance
for model weights/data or a prize submission.

Keep both exported bytes and `input.json` private when the source is private or
prize-eligible: paths, plane/crop indices and notes can disclose locations. This PR
publishes code and synthetic tests, not any real render, location or discovery.
The existing model/checkpoint, GPU, experiment and publication holds remain in place.
