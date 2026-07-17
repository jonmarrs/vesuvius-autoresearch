# Surface-volume renderer

`repro/sota_data/render_surface.py` + `repro/sota_data/render_cli.py`

## What it does

The open bucket (`s3://vesuvius-challenge-open-data/`) ships some segments as **mesh-only**:
an `original.obj` and a volume zarr, but **no surface volume and no predictions**. The two
PHerc0332 (Scroll 3) segments — on the live First-Letters scroll — are exactly this, so no
one can run ink detection on them without first rendering the surface.

This tool rebuilds the surface volume from the mesh:

1. **point map** — interpolate the obj's 3D vertices over their flattened UV coords
   (`vt → xyz`, `scipy.LinearNDInterpolator`) onto a regular grid;
2. **normals** — cross-product of the two grid tangents;
3. **sample** — tile-wise trilinear sampling of the volume along `± normal` for 26 depth
   layers around the surface;
4. **write** — a detector-format fragment (`layers/17..42.tif` + validity `mask.png` +
   `render_provenance.json`). **No ink label is written** — the render is label-free; nothing
   fabricates ground truth for an unread scroll.

## Validation status (read this)

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
  whose surface shows real papyrus texture (high-pass std) — the honest, teacher-free
  substitute for ground truth on unread scrolls; an empty/wrong scale is rejected. Pass a
  number (e.g. `--scale 1`) to fix it.
- `--region Y0 X0 SIZE`, `--level`, `--sign` tune the render.

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
