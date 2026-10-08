# Coordinate and geometry handoffs

These local research tools expose three separate operations: reviewing an affine
registration, exporting a probability-grid isosurface, and reading Tifxyz tiles.
None automatically registers a flattened UV prediction to CT, resamples training
data, establishes alignment accuracy, or certifies a prize submission.

## Manual volume registration

```bash
# Validate inputs and print the command; do not open a viewer.
.venv/bin/python scripts/register_volumes.py \
  --fixed /data/fixed.zarr --moving /data/moving.zarr \
  --fixed-voxel-size 7.91 --moving-voxel-size 3.955 \
  --output-transform local_data/transforms/reviewed.json

# In an interactive terminal, add --execute to start the pinned viewer.
```

Both inputs must be separate local Zarr **groups with a nonempty real 3D array
`0`**, in ZYX order. Bare arrays and 4D inputs cannot be consumed by the pinned
registration tool. Declare the isotropic voxel size of each source in micrometers;
there is no guessed 7.91-micrometer default. If scan `metadata.json` supplies
`scan.tomo.acquisition.detector.samplePixelSize` in millimeters, it must agree with
the declaration. Malformed metadata is an error. General OME coordinate
transforms are outside this wrapper's supported subset: prepare a verified
registration-compatible export rather than silently discard scale or origin.
Source ordering, isotropy, and frame identity remain caller obligations.

Dry run is the default and creates no transform. Execution requires a terminal
and first probes the optional registration imports in a separate interpreter.
The current environment lacks `neuroglancer`; no package is installed
automatically. The active Python interpreter and absolute pinned script path
are used, including the correct moving voxel size option.

In the viewer, **press W to write the current transform**. Then exit the Python
REPL with Ctrl+D in the terminal. **Ctrl+D does not save**. The upstream viewer
supports coarse alignment, paired landmarks, and manual refinement; consult its
[guide](../villa/foundation/volume-registration/README.md) for platform-specific
modifier keys. Fitting or saving a transform does not prove registration quality.

The wrapper passes a temporary JSON output path to the viewer. A zero process
exit is insufficient: the saved payload must satisfy the actual pinned
`transform_schema.json`, have a finite nonsingular 3x4 affine, identify the
expected fixed volume, and contain equal counts of finite in-bounds XYZ
landmarks. A coarse transform with zero landmark pairs is structurally valid;
its accuracy is unverified. Empty, missing, truncated, singular, wrong-volume,
or malformed results are refused.

The published JSON retains the upstream schema:

```text
p_fixed_xyz = M_3x4 @ [p_moving_x, p_moving_y, p_moving_z, 1]
```

Both sides are their respective native volume **voxel coordinates**, not
micrometers. The affine can contain the voxel-size ratio. The schema stores a
fixed-volume identifier but no moving-source path, voxel sizes, or immutable
source hashes. Keep the exact input/command context alongside a reviewed
transform; the file alone is not a complete alignment evidence record.
The wrapper does not apply this matrix to `vesuvius_loader.py` or integrate it
into training. Resampling and independent registration-quality measurements
require a separate verified workflow.

## Probability grid to OBJ

```bash
.venv/bin/python scripts/voxelize_predictions.py \
  --input /data/probability_fragment.zarr \
  --output-obj local_data/geometry/preview.obj --threshold 0.5

# Optional explicit origin/spacing for a declared reference frame:
.venv/bin/python scripts/voxelize_predictions.py \
  --input /data/probability_fragment.zarr \
  --output-obj local_data/geometry/physical_preview.obj \
  --origin-zyx 100 200 300 --spacing-zyx 7.91 7.91 7.91 \
  --units micrometer
```

Input must be a nonempty 3D probability grid, either a bare array or a group with
array `0`. Every dimension must be at least 2. Values must be finite real numbers
in `[0, 1]`; integer instance labels with IDs above 1 are not probabilities.
Threshold must lie strictly inside `(0, 1)` and cross the actual input range.
Uniform/empty results fail rather than publish an empty mesh.

The exporter calls the existing scikit-image marching-cubes implementation with
a float32 field, step size 1, and degenerate triangles disabled. It neither
prunes segmentation branches nor calls villa's `voxelize_objs.py`: that tool
converts meshes **to** voxels. No thresholding, smoothing, component filtering,
or artificial zero padding is added. Surfaces touching a crop edge may remain
open; watertightness and biological validity are not guaranteed.

Mesh vertices are XYZ. Caller-supplied origin and spacing are ZYX:

```text
vertex_xyz = reverse(vertex_zyx * spacing_zyx + origin_zyx)
```

Spacing must be finite and positive; origin must be finite. Origin uses the
declared output units, and spacing is those units per input grid sample.
Defaults are origin zero, unit spacing, and voxel units: a mesh in the **local
input grid**, not registered CT or physical world coordinates. Reversing ZYX to
XYZ changes handedness, so triangle winding is reversed too. No source OME or
producer transform is applied implicitly. A UV/depth surface volume can produce
a grid preview but cannot thereby become a CT-space anatomical mesh.

The OBJ's first comment contains one `autoresearch_geometry` JSON record with
source path/shape/dtype/attributes, threshold, origin/spacing/units, frame basis,
algorithm, and vertex/triangle counts. Standard OBJ viewers can ignore this
comment; downstream consumers must retain it for provenance. Submission
eligibility is null, and accuracy is unverified.

Input is bounded before payload reads by default `--max-voxels 2097152`
(`128**3`). Generation materializes the selected grid and mesh arrays; underlying
chunks and complex topology can require considerably more memory. Increase the
bound explicitly only for an appropriately sized fragment. No whole-scroll
performance or memory measurement is claimed.

## Tifxyz coordinate tiles

```python
from scripts.labeling.tifxyz_wrapper import load_tifxyz_surface, extract_patch_coords

surface = load_tifxyz_surface("/data/segment", resolution="stored")
x, y, z, valid = extract_patch_coords(surface, y=100, x=200, h=64, w=64)
```

The helper lazily loads the actual pinned Tifxyz package without bootstrapping
the unrelated ML package. Missing API/dependencies or unreadable surfaces raise
errors; importing the wrapper itself remains safe. No package installation,
coordinate interpolation, or reader implementation is copied.

Choose `resolution="stored"` (default) or `"full"` explicitly. This sets the UV
indexing grid; full mode uses upstream interpolation and can have larger
dimensions. XYZ coordinate values keep their native source convention. The
helper does not apply scan scale, registration, or a physical-unit conversion.
Surface scales must be finite and positive.

Patch origins are nonnegative integers, sizes positive integers, and the entire
patch must fit the surface's **current** resolution. Negative indexing, implicit
clipping, and fractional coordinates are refused. The result preserves XYZ
order and the upstream validity mask, additionally masking nonfinite or negative
coordinates. Invalid coordinate values remain in the arrays; consumers must
honor `valid`. An entirely invalid tile is allowed and provides no usable
geometry. Reading a surface materializes its stored coordinate planes; this is
not a whole-scroll streaming adapter.

## Publication and migration

Mesh and transform destinations must be new and disjoint from source paths,
including resolved symlink aliases and ancestor/child overlap. Writes go to an
adjacent temporary file and rename only after processing and validation succeed.
Ordinary read, extraction, serialization, viewer, and write failures leave no
final output and exit nonzero. Existing results are preserved. Serialize writers
and keep inputs stable; an abruptly killed process may leave a hidden temporary
file. This local protocol does not attest source identity cryptographically.

Legacy `--output_obj` and `--output_transform` spellings remain accepted.
Registration now plans by default, requires both declared voxel sizes, and needs
`--execute` in a terminal. Saved transforms require independent accuracy review.
The old exporter never implemented the advertised volume-to-mesh direction;
new meshes use the documented research isosurface recipe and need their own
evaluation. Tifxyz load failures now raise instead of returning `None`.

See the [review report](DESIGN_ARCHITECTURE_REVIEW_2026-10-08_GEOMETRY_HANDOFF.md)
for regression, integration, and validation evidence.
