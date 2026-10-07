# Surface-volume renderer

`repro/sota_data/render_surface.py` + `repro/sota_data/render_cli.py`

## Prior art — read this first (added 2026-08-07)

**villa already renders surface volumes, and does it better.** `vc_obj2tifxyz` converts an
obj with UVs into a tifxyz grid; `vc_render_tifxyz` samples N slices along the surface
normal and writes tif/zarr. Together they cover **both** of this tool's input paths and add
capabilities it does not have: remote zarr streaming and prefetch, multi-VM part rendering,
pyramid generation, composite/accumulation modes, affine chaining. Both are in
`villa/volume-cartographer/apps/src/`.

This was previously written up as filling a gap in the ecosystem ("no one can run ink
detection on them without first rendering the surface"). That framing was wrong and has
been removed — the objection was raised by `erdpx` when closing villa PR
[#1280](https://github.com/ScrollPrize/villa/pull/1280) and it checked out.

What this tool actually offers over the villa path is narrower and worth stating plainly:

- **no C++ build** — pure Python, `pip`-installable, runs where volume-cartographer isn't built;
- **detector-format output** — emits `layers/17..42.tif` + `mask.png` directly consumable by
  `vesuvius_autoresearch.detector`, with no conversion step;
- **`--scale auto`** — infers the obj coordinate convention teacher-free on scrolls with no
  released surface volume to calibrate against.

Those are convenience, not capability. If you have volume-cartographer built, use it.

## What it does

The open bucket (`s3://vesuvius-challenge-open-data/`) ships some segments as **mesh-only**:
an `original.obj` and a volume zarr, but **no surface volume and no predictions**. The two
PHerc0332 (Scroll 3) segments — on the live First-Letters scroll — are exactly this, so the
surface has to be rendered before any ink detection can run on them.

This tool rebuilds the surface volume from the mesh:

1. **point map** — interpolate the obj's 3D vertices over their flattened UV coords
   (`vt → xyz`, `scipy.LinearNDInterpolator`) onto a regular grid;
2. **normals** — cross-product of the two grid tangents;
3. **sample** — tile-wise trilinear sampling of the volume along `± normal` for 26 depth
   layers around the surface;
4. **write** — a detector-format fragment (`layers/17..42.tif` + validity `mask.png` +
   `render_provenance.json`). **No ink label is written** — the render is label-free; nothing
   fabricates ground truth for an unread scroll.

## Historical validation status (read this)

The measurements below describe the earlier renderer. The October 5 review
corrected cropped OBJ regions, indexed UV pairing, intensity conversion, and the
validity mask, and versioned the rendering contract as 2. These synthetic-data
repairs have not been revalidated on real scrolls; rerun the released-volume
comparisons before treating new renders as evidence for these NCC results. See
the [design and architecture review](DESIGN_ARCHITECTURE_REVIEW_2026-10-05_SURFACE_RENDERER.md).

Validated on **two scrolls** against **released** surface volumes, using clean triples
where geometry, volume, and reference share one scan frame:

- **Scroll 1** (`20230702185753`): center-layer **NCC ~0.59**, just under the
  pre-registered 0.60 gate — placement-correct (a wrong axis/scale would score ~0), with
  the residual attributed to a resolution-mismatched comparison
  (`reports/detector/render_validation.md`).
- **PHerc 1667** (`20260108140509-w011`, tifxyz path): center-layer **NCC 0.78 — gate
  PASS** at near-matched comparison resolution
  (`reports/detector/render_validation_1667.md`). The jump from 0.59 with the *same*
  sampler and conventions confirms the Scroll-1 residual was the comparison, not
  placement.
- **Depth (full stack), PHerc 1667**: every rendered layer matched against every released
  depth slice — all 26 layers at **NCC 0.84–0.89**, perfectly monotonic mapping (rank
  corr 1.000) at **slope exactly 4.00** released slices per layer (= correct level-2
  depth scaling), and **sign=+1 confirmed as the released convention**
  (`reports/detector/render_validation_1667_depth.md`). The emitted stacks are
  full-3D-validated: placement, depth direction, and depth spacing.

Outputs are still independent renders, not reproductions of the core team's pipeline —
for detector consumption treat them qualitatively.

## Usage

```bash
# render a mesh-only segment, inferring the obj coordinate scale teacher-free
uv run python -m repro.sota_data.render_cli \
  --obj    vesuvius-challenge-open-data/PHerc0332/segments/<seg>/mesh/intermediate/<seg>_original.obj \
  --volume vesuvius-challenge-open-data/PHerc0332/volumes/<vol>.zarr \
  --out    local_data/rendered --frag-id <seg> --scale auto
```

```bash
# render from a released tifxyz geometry grid (most bucket segments ship one) —
# no scale inference needed: tifxyz coords are level-0 voxels by validated convention
uv run python -m repro.sota_data.render_cli \
  --tifxyz vesuvius-challenge-open-data/PHerc1667/segments/<seg>/mesh/<seg>-on-<scan>.tifxyz \
  --volume vesuvius-challenge-open-data/PHerc1667/volumes/<vol>.zarr \
  --out    local_data/rendered --frag-id <seg> --region 512 11888 1024
```

- `--obj` accepts a local path or an anonymous-S3 key (auto-downloaded).
- `--tifxyz` renders directly from the released grid geometry; `--region` is then in
  tifxyz grid pixels and `--scale` is ignored.
- `--scale auto` renders a small probe at each candidate obj-level-div and keeps the one
  with the largest nonzero high-pass texture score. Empty/flat probes are rejected;
  this remains a coherence heuristic and does not prove the coordinate scale. Probes
  use the final UV-grid resolution, support rectangular crops, and are cleaned up.
  Pass a number (e.g. `--scale 1`) to fix the divisor explicitly.
- `--region Y0 X0 SIZE` or `--region Y0 X0 H W` selects a square or rectangular
  region. Origins must be nonnegative and both dimensions at least 2. tifxyz crops
  must fit the released grid exactly; `--region 0 0 0` selects its whole grid.
- For OBJ input, `--obj-grid-size H W` fixes the **full** resampled UV-grid
  resolution. Nonzero origins require this option. With zero origins and no
  full-grid option, the requested size still spans the full UV bounding box.
- `--level` is a nonnegative pyramid level up to 30, and `--sign` is exactly
  `+1` or `-1`. Explicit divisors must be finite and positive.

For example, this selects rows 100..611 and columns 200..967 from a 2048² OBJ grid:

```bash
uv run python -m repro.sota_data.render_cli \
  --obj original.obj --volume s3://bucket/volume.zarr \
  --obj-grid-size 2048 2048 --region 100 200 512 768 \
  --scale 2 --out local_data/rendered --frag-id region_v2
```

## Output and input contracts

`valid_frac` and the saved mask now mean **all 26 depth samples are supported**.
The center surface must fit the source volume. Invalid geometry, undefined normals,
and depth coordinates outside `[0, shape-1]` are excluded from the final mask;
masked-out pixels are zeroed across the stack. A region with no fully supported
pixels fails before publication. `geometry_valid_frac` records the earlier point-map
coverage, while `clamped_frac` is the fraction of unsupported depth samples among
geometry-valid pixels, including nonfinite normals.

The source must be a 3D Zarr v2 pyramid level with supported compressor metadata
and no filters. uint8 source intensity 1 stays 1; uint16 is divided by 256 before
interpolation; floating CT values must already be finite byte-range `[0,255]`
intensities. Rendered values are quantized once to uint8. Only genuinely missing
chunk keys use the declared fill value. Permission, network, and corrupt-chunk
failures abort the run. The reader bounds decoded cache storage and each dense
slice to 512 MiB by default, and separately caps chunk-index counts. This is not a
limit on total process memory, which also includes output layers and geometry.
The Python reader's `max_cache_bytes` constructor argument is configurable.

OBJ face texture indices define vertex/UV pairing; negative indices and seams
with distinct UV coordinates are supported. Duplicate UV coordinates with
conflicting 3D positions fail. The interpolation still spans the UV convex hull:
use a single regular UV patch or released tifxyz geometry. It does not reconstruct
mesh holes or overlapping UV islands; use villa for those cases.

Fragments are staged beside the destination and published with a directory rename
after every layer, mask, optional supplied label, and JSON write succeeds.
Existing fragment ids are refused; use a fresh id or output root for reruns.
This applies to the converter, qualitative, distillation, and registered-label
adapters too. Qualitative fragments have **no** synthetic ink label; prediction
loads them through the detector's label-free path, while supervised loading still
requires a real supplied label. Disk write failures leave no final fragment.

Provenance records `render_contract_version: 2`, the source geometry, OBJ divisor,
full grid and UV bounds, region, volume, level, depth offsets, sign, intensity units,
and coverage. Caller annotations are nested under `extra` and cannot replace those
facts. CLI OBJ provenance also includes the original source argument there.
Remote OBJ downloads use a cache namespace derived from the whole S3 key, with
temporary-file publication. Cached keys are assumed immutable; remove a cached
entry explicitly if the remote object has changed. Legacy basename-only entries
are not reused.

**Runtime expectation (measured):** a full-surface 1024² render of a Scroll-3 segment takes
~8 minutes at ~35 MB/s effective S3 throughput (the fetch layer decodes exactly the zarr
chunks the surface touches, deduplicated per tile group, in concurrent batches — measured
2.2× over naive per-tile reads; the residual cost is bandwidth-bound, so a faster pipe
scales it down). Budget accordingly for larger sizes.

The output fragment is directly consumable by the detector
(`vesuvius_autoresearch.detector`) — e.g. run a model over a Scroll-3 render (note: a
cross-scroll model reads that segment's **texture, not ink** — see
`reports/detector/scroll3_first_look.md`).

## Coordinate-scale caveat

The obj's coordinate convention (level-0 voxels? a fixed offset?) is not documented and, on a
scroll with no released surface volume, cannot be calibrated against ground truth. `--scale
auto` infers it from surface coherence; the chosen value is recorded in the provenance JSON.
For Scroll 3 this resolves the scale up to a residual 2× ambiguity (both `div=1` and `div=2`
render coherent papyrus; `div=4` renders empty and is rejected).
