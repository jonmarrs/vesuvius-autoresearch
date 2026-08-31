# RECORD, POSTED 2026-08-30

Posted as ScrollPrize/villa#1660: https://github.com/ScrollPrize/villa/issues/1660

A record of what was said, not a draft. Corrections go to the thread as a new comment, never as a
silent edit here. No nudges: await a reply.

---

Following on from #1655. Trying to get from a fit to `total_fg_pixels` using only published artifacts, I hit two things. The first is a silent wrong answer rather than a failure, which is why I am reporting it even though the underlying cause may be my own configuration.

## 1. A mesh/volume frame mismatch renders a black strip and exits 0

`render_ink.py` assumes the fitted mesh coordinates are already in the ink volume's level-0 frame. It exposes `--scale` and `--group-idx`, which choose the pyramid level and pixels-per-voxel, but nothing that says the mesh is in a different frame.

When the assumption does not hold, the run completes normally. It writes a strip, exits 0, and the only trace is `p95=0.0` in one line of output:

```
rendering 1915x712 at scale 0.25 crop [1915x712 from (0,0)]
[1/1] wrote /work/meshes/ink/w010-019.jpg (1915px wide, p95=0.0)
Done. Strips in /work/meshes/ink
```

The strip is entirely black. Scored, that is `total_fg_pixels = 0` reported as a successful render.

In my case the mesh frame is 4x coarser than the volume. Sampling the published ink volume directly at the mesh's own vertices, 200 valid vertices from one `_spliced` winding:

| coordinate scale | in bounds | nonzero | mean | max |
|---|---:|---:|---:|---:|
| 1 (as rendered) | 100.0% | 0.0% | 0.00 | 0 |
| 2 | 100.0% | 66.5% | 12.04 | 250 |
| 4 | 100.0% | 90.0% | 19.64 | 250 |

Note that every scale is "in bounds", so a bounds check cannot catch this. Note also that scale 2 reads 66.5% nonzero: the scroll is dense enough that a wrong-but-close scale still lands on papyrus, so a nonzero-fraction heuristic would not be reliable either.

Where the 4x comes from, for my setup: `spiral_datasets/PHercParis4/lasagna_inputs/las_008_surf_sdt.ome.zarr.respool_g1` reports `array_shape [9473, 4087, 4087]` over channel `las_008_surf_sdt.ome.zarr/1`, so that zarr's level 0 is about `[18946, 8174, 8174]`. The published ink volume `representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr` has level 0 `[75784, 32693, 32693]`, matching `volumes/20260411134726-2.400um-...-masked.zarr` exactly. That is a factor of 4.

`vc_render_tifxyz` already has `--scale-segmentation` and passing it as 4 fixes the sampling. `render_ink.py` does not pass it through, so it has to be injected with a wrapper via `--vc-render-bin`.

**The question behind this:** is the intended workflow to supply an ink volume already in the fit's frame? If so the mismatch is mine. Either way, a mesh that lands nowhere in the volume seems worth a loud failure rather than a black strip and exit 0, since the failure mode looks exactly like "this fit recovered no ink".

The published spiral dataset ships no scroll json, so I wrote my own, and I may have set the frame differently from how you do.

## 2. The published container cannot complete a render

`ghcr.io/scrollprize/villa/volume-cartographer:edge` and `:main` are the same digest, `sha256:bad516f66001abca759454cc43e4fd11e5b19aa55d36bdc2043817291c8083c4`, built 2026-05-13. Two consequences:

**`vc_obj_uv_lift` is absent.** `render_ink.py` invokes it whenever `--flatten-keep < 100`, and the default is 6.25. Its source is in current main, so the image predates it. This one is easy to work around: it is 381 lines depending only on header-only libigl, Eigen and OpenMP, so it compiles standalone in seconds.

**The image's `vc_tifxyz2obj` does not accept `--keep`:**

```
error: unknown option '--keep=6.2500'
```

so `--flatten-keep 6.25` cannot work with this image regardless, and the only setting it accepts is `--flatten-keep 100`. That is the case the option's own help warns about, "smaller mesh is less prone to SLIM divergence". Measured, single threaded:

| windings | vertices | `--flatten-iters` | flatboi |
|---:|---:|---:|---|
| 10 | 200,196 | 50 | killed at 1h51m, still running |
| 3 | ~60,000 | 10 | killed at 1h13m, still running |

Three windings at ten iterations not finishing in an hour is the divergence the flag exists to avoid, not slowness. So with the published image there is no working setting: the documented default is rejected, and the only accepted value does not converge.

Rebuilding `vc_tifxyz2obj` is not standalone the way `vc_obj_uv_lift` is. It includes `vc/core/util/{Geometry,InpaintSurface,Slicing,Surface,QuadSurface}.hpp` and `vc/core/types/VcDataset.hpp`, and the runtime image carries no VC headers and no `libvc_core`, so it needs the builder image and a full VC3D build. A refreshed published image would remove the need for any of that.

## Everything else worked

The ink volume streams straight from S3 with `--volume <empty cache dir> --remote-url <url>`, no bulk download, and `scrollprize/ink-coverage-32um` is public and ungated. Once the frame is corrected the mesh path itself is fine: concat, cleanup and the tifxyz write all behave.
