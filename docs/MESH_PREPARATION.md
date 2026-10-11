# Mesh preparation

## Stored Tifxyz grid sampling

~~~bash
.venv/bin/python scripts/subsample_mesh.py /data/segment /data/segment_coarse 4
~~~

This creates a new **geometry-only** Tifxyz directory. At positive integer
stride s, output point (row, column) samples source (s*row, s*column).
Valid XYZ coordinates are unchanged. Both metadata scale entries are divided
by s, in the native **x/y order**. This samples an existing surface; it does
not flatten, interpolate, register or measure its accuracy.

The source must contain local regular nonsymlink files x.tif, y.tif, z.tif
and meta.json. Coordinates must be matching 2D float32 planes, with both
dimensions at least two. The output must also retain at least a 2x2 grid.
All source coordinates, including discarded points, must be finite and
nonnegative or share the full (-1, -1, -1) invalid sentinel. A coarse grid
with no usable retained point fails.

An optional mask.tif must match the source grid and use boolean or uint8
binary values (0, 1 or 255). Its nonzero points are intersected with valid
coordinates. Without a mask, the pinned Python reader's z > 0 convention
is used. The output always includes a canonical uint8 validity mask:
0 invalid, 255 valid. Masked sampled coordinates become (-1, -1, -1),
so consumers relying on sentinel coordinates cannot restore excluded points.

Metadata must be a JSON object without duplicate keys or nonfinite numbers.
It needs exactly two finite positive numeric scale entries; the divided
scales must remain finite and positive when represented as native float32.
Explicit format/type declarations must be tifxyz/seg; omitted declarations
are accepted for older coordinate-only directories.

The derivative receives a new UUID, actual TIFF dimensions in width/height
order, and the bounding box of its valid retained points. Source area and
other geometry-derived fields are not promoted to output measurements.
Source metadata, absolute path, stride, source shape, valid output count,
and source component sizes/SHA-256 hashes are recorded under subsampled_from.
Nested source metadata describes the original surface.

Labels, UV channels, corrections and other auxiliary files are not transferred;
their grid semantics need a separate validated resampling recipe. Source
channel declarations remain only in nested provenance. This is not a general
segment-directory copier or a training-label handoff.

The uncentered grid-index relation is:

~~~text
output_column / output_scale_x = source_column / source_scale_x
output_row    / output_scale_y = source_row    / source_scale_y
~~~

The tool keeps every s-th point from index zero and does not append the last
edge point when dimensions are not divisible by s. Output dimensions use
ceil(source_dimension / s), so their derived canvas dimensions and the
renderer center can change. Coarsening also changes interpolation, normals
and edge support. Check actual renderer alignment/coverage before comparing
pixels or claiming equivalent reading quality. No fixed output-size or
physical-registration guarantee follows from dividing the scale.

## Bounds and publication

By default the source grid is limited to 16,777,216 points and the sum of
decoded coordinate/mask plane sizes to 268,435,456 bytes (256 MiB).
TIFF shapes and dtypes are inspected before payload decoding.
Use --max-points and --max-decoded-bytes to choose explicit larger limits
for a suitable machine. These are decoded-source bounds, not limits on
total process memory, compressed file size or execution time.
Metadata is capped at 1 MiB. Whole source planes are read and validated;
this is not a streaming whole-scroll adapter.

Destination paths must be new and disjoint from the source, including aliases
through parent symlinks. Existing files/directories and broken output symlinks
are refused. Validated files are written in an adjacent temporary directory
and published by rename after all writes complete. Ordinary read, validation,
serialization, write and rename failures produce no final partial mesh.
An output appearing before publication is preserved.

Serialize writers and keep sources stable throughout the operation. Ordinary
source size, identity, modification/change-time changes are rejected; access-time
changes caused by reads are allowed. Hashes record component bytes but do not
make multiple mutable files an atomic snapshot. Abrupt termination may leave
a hidden staging directory. A successful CLI execution exits zero and names
the published mesh; failures exit nonzero with a diagnostic.

The script remains self-contained with its existing three positional arguments.
The coarse-grid driver copies it into a frozen work directory; no repository
helper imports or upstream checkout are required to run that copy. Historical
coarse-grid results and preregistered comparisons are unchanged by this review.

## Legacy automatic flattening selection

~~~bash
.venv/bin/python scripts/automate_arap_flattening.py --input /data/segment --output /data/sweep
~~~

This entry point exits 1 with an unsupported-workflow message. It launches no
producer and writes no selected configuration or mesh. Help exits zero.

The previous sweep sent OBJ paths and a nonexistent --method option to the
pinned native vc_flatten, attempted a deprecated SLIM module from a stale
path, substituted file size when quality scoring failed, and recorded a
winner inside a temporary directory that it then removed. Neither file size
nor a bounding-box/area ratio establishes UV distortion or reading quality.
A reliable automatic selection metric has not been implemented.

The pinned [native CLI source](../villa/volume-cartographer/apps/src/vc_flatten.cpp)
accepts **Tifxyz directories** and supports --iterations and --lscm-only;
the default performs ABF++ followed by LSCM parameterization. Inspect the installed
binary's --help before direct use and independently validate saved geometry,
UV distortion, rendered alignment and reading quality. This repository does
not claim a validated automatic ARAP parameter search or prize eligibility.

For coordinate access and probability-grid OBJ previews, see
[Geometry handoffs](GEOMETRY_HANDOFF.md); for actual supported surface rendering,
see [Surface renderer](SURFACE_RENDERER.md).

See the [design and architecture review](DESIGN_ARCHITECTURE_REVIEW_2026-10-11_MESH_PREPARATION.md)
for reproduced defects and validation evidence.
