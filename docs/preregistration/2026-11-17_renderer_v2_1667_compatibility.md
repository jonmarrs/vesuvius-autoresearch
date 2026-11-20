# Renderer-v2 compatibility check on one fixed PHerc1667 region

Written before this pass downloads geometry/CT/reference payloads or calculates
any correlations. Only the three source metadata objects have been inspected.
Commit this registration, the [machine plan](../../configs/studies/render_1667_v2_2026-11-17.json)
and the tested [runner](../../repro/sota_data/revalidate_render_1667_v2.py) before
executing the measurement. The plan binds selected helper source bytes; it is
not a fingerprint of the complete dependency or operating-system environment.

## Question and limits

Does the current Python renderer's floating-point center plane agree with the
released PHerc1667 w011 surface volume on a small fixed interior crop when the
comparison uses the corrected full-depth support mask?

The older [center](../../reports/detector/render_validation_1667.md) and
[depth](../../reports/detector/render_validation_1667_depth.md) results use the
as-run scripts and remain historical evidence. Their scripts are preserved.
This is a new compatibility measurement, not a repeat of either whole experiment,
an independent held-out test or evidence for ink accuracy. The crop is inside
the historical depth experiment's chosen interior region. No model is run.

## Fixed inputs and geometry

All three sources are under the public `PHerc1667` open-data prefix and declare
scan `20251217075048`, 2.399 micrometre CT:

- Segment `20260108140509-w011_20260108140509268_flatboi`;
  mesh `20260108140509-on-20251217075048-2.399um.tifxyz`.
  Its three float32 planes are 1975 × 736 with declared scale `[0.05, 0.05]`.
- Raw `20251217075048-2.399um-0.2m-78keV-masked.zarr`, level 2;
  metadata shape `[9269, 3808, 3808]`.
- The segment's released
  `2.399um-0.22m-78keV-volume-20251217075048.zarr`, level 4;
  metadata shape `[109, 2469, 920]`.

Both volume levels must retain their discovered uint8 dtype; shape/dtype
changes refuse the measurement instead of reinterpreting a new source.

The tifxyz crop is **y=736, x=112, height=128, width=128**. Its origin and
dimensions are multiples of four so the corresponding 1.25× reference crop
has integer boundaries: **y=920, x=140, height=160, width=160**. This is the
declared grid-scale relation, not registration estimated from the new images.
Preserve a one-pixel geometry halo, compute centered normals on the haloed
grid, then sample only the inner crop. Convert xyz to zyx and divide coordinates
by four, with normal sign +1. Render 26 layers at offsets -13 through +12 using
the maintained sampler, known volume bounds, tiles of 32 and groups of two.
The primary plane is index 13, offset zero, before byte quantization.

## Comparison and gate

Use only pixels that the maintained sampler reports supported at **every one
of the 26 depths**, for every comparison. Do not substitute the geometry-valid
mask, drop reference-specific pixels, shift the crop or infer a new transform.

Read the five preselected released depths **50, 52, 54, 56, 58** around its
midpoint, as in the historical center comparison. Resize each 160 × 160
reference plane to 128 × 128 with OpenCV `INTER_AREA`. Report all five
double-precision centered normalized cross-correlations. The primary reading
is their maximum, with the first listed depth retained on an exact tie.

- At least **90%** of the crop and at least **1024 pixels** must have complete
  depth support. Constant render/reference pixels or inadequate support produce
  `INDETERMINATE`; no unusable reference can be silently removed.
- `PASS` requires a computed maximum NCC **>= 0.60**, without rounding. Otherwise
  the compatibility gate is `FAIL`. There is no hypothesis-test p-value or
  claimed confidence interval from this single spatial crop.
- Publish either verdict without choosing another crop, sign, level or depth
  window in response. Fetch/shape/source failures mean the procedure did not
  run; do not reinterpret them as NCC failures or change the design silently.

## Source capture, resources and publication

Use HTTPS objects from the exact bucket endpoint, without redirects. Retain
the complete bytes of every accessed metadata/TIFF/chunk object, its URL, byte
count, SHA-256 and available response validators. These identify retrieved
bytes, not separately published upstream checksums or signed provenance.
An unavailable chunk is an error in this check, even though ordinary Zarr
readers permit absent fill chunks. Recheck all captured bytes and the plan
before publishing the report and arrays.

Cap downloaded objects at 16 MiB each and all source payloads at **192 MiB**.
Decoded chunk-cache/bbox storage is capped at 128 MiB per reader; this is not
a bound on total process RSS. Geometry, decoded arrays and Python overhead are
additional. No GPU or training process is needed. There are no automatic
download retries. Failed/partial runs clean staging and publish no measurement;
existing output directories are refused.

Run from the checkout with a new directory outside it:

```sh
env PYTHONPATH=src CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /workspace/.vesuvius-review-env/bin/python -m repro.sota_data.revalidate_render_1667_v2 \
  --out /tmp/vesuvius-renderer-v2-1667-2026-11-17
```

Copy only the resulting JSON receipt into the repository; retain data arrays
and source payloads outside Git. Record the registration commit, exact command,
runtime, output hashes, all five NCCs, support and any failed attempts in the
follow-up. No result upgrades the historical depth-direction or full-scroll
claims, closes the confidence-analysis rerun, establishes physical registration
independently or certifies the OBJ auto-scale path.
