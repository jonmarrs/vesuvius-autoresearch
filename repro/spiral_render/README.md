# Rendering ink from a spiral fit, using only published artifacts

What this directory is for: `render_ink.py` and `get_ink_metrics.py` turn a spiral fit into
`total_fg_pixels`, the number villa's spiral autoresearch loop optimises. Getting there from
published data alone takes four things that are not written down anywhere, recorded here so the
next person does not rediscover them.

## 1. The native binaries come from the published container, not a source build

Building VC3D from source pulls Ceres, OpenCV, CGAL and Qt. The published image has the tools
already:

```
docker pull ghcr.io/scrollprize/villa/volume-cartographer:edge
```

It ships `vc_render_tifxyz`, `vc_tifxyz_trim`, `vc_tifxyz2obj`, `vc_obj2tifxyz` and `flatboi`.

## 2. That image is missing `vc_obj_uv_lift`, and is older than `render_ink.py`

`:edge` and `:main` are the same digest
(`sha256:bad516f66001abca759454cc43e4fd11e5b19aa55d36bdc2043817291c8083c4`, built 2026-05-13).
Neither carries `vc_obj_uv_lift`, which `render_ink.py` invokes whenever `--flatten-keep < 100`
(the default is 6.25). Its source is in current `main`, so the image predates it.

`Dockerfile` here builds it. Unlike the rest of VC3D it is 381 lines depending only on
header-only libigl plus Eigen plus OpenMP, so it compiles on its own in seconds.

**That is not sufficient to reach the documented default.** The same image's `vc_tifxyz2obj`
rejects `--keep`:

```
error: unknown option '--keep=6.2500'
```

so `--flatten-keep 6.25` cannot work with this image whatever else is present, and the only
usable setting is `--flatten-keep 100`. That leaves flatboi flattening a full-resolution mesh:
200,196 vertices ran over 20 minutes single-threaded for ten windings.

## 3. The published mesh frame and the published ink volume differ by exactly 4x

```
spiral_datasets/PHercParis4/lasagna_inputs/las_008_*   level 0 = [18946,  8174,  8174]   9.6 um
representations/predictions/ink-3d/...v3-78k-fullsup   level 0 = [75784, 32693, 32693]   2.4 um
```

The ink volume's level 0 matches `volumes/20260411134726-2.400um-...-masked.zarr` exactly, so it
is the 2.4 um scroll frame. A fit run on the published lasagna inputs emits meshes in the 9.6 um
frame.

`render_ink.py` assumes the mesh is already in the volume's level-0 frame and offers no way to say
otherwise. **Unscaled, the render exits 0 and writes an entirely black strip**, reported only as
`p95=0.0` in passing. Verified by sampling the ink volume at the mesh's own vertices
(`scripts/probe_ink_volume_frame.py`):

```
 scale   in bounds  sampled   nonzero     mean   max
     1      100.0%      200      0.0%     0.00     0
     2      100.0%      200     66.5%    12.04   250
     4      100.0%      200     90.0%    19.64   250
```

Note scale 2 reads 66.5% nonzero: the scroll is dense enough that a wrong-but-close scale still
lands on papyrus often, so the nonzero fraction alone does not identify the scale. The array-shape
ratio does, and 4 agrees with it.

`vc_render_tifxyz` has `--scale-segmentation` for exactly this, but `render_ink.py` does not pass
it. Inject it with a wrapper via `--vc-render-bin`:

```sh
#!/bin/sh
exec vc_render_tifxyz --scale-segmentation 4 "$@"
```

## 4. The ink volume is streamable, no bulk download

`--volume <empty local cache dir> --remote-url <the s3 zarr url>`. Level 0 is 75784 x 32693 x
32693 uint8 in 256^3 chunks, so only the chunks under the mesh are fetched.

## Putting it together

```sh
docker build -t vc-render:local .
docker run --rm -v "$WORK":/work --entrypoint sh vc-render:local -c "
  cd /work/sf_main && python3 -u render_ink.py /work/meshes \
    --volume /work/inkcache --remote-url '$INK_URL' \
    --vc-render-bin /work/bin/vc_render_scaled \
    --strips --no-full-scroll --flatten-keep 100 --num-processes 1"
```

`sf_main` must be a `spiral-fitting` tree recent enough to have `--remote-url`.
