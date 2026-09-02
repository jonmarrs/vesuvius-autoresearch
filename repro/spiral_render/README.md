# Rendering ink from a spiral fit, using only published artifacts

**Status: this works.** `./setup_workdir.sh <work> <fitted_meshes>` then `./run_render.sh <work>`
renders legible Greek from our own 30k-step fit, ten windings, against the published ink-3d volume.
Lasagna flatten 1m34s on one 4090, render about 8 minutes streaming from S3.

**Read this first: use the LASAGNA path, not flatboi.** `run_single.py` passes no `--strips`, so
villa's real pipeline is the default full-scroll concat flattened by `lasagna/fit.py`. The
`--strips` path uses flatboi instead and is a dead end here: on a clean mesh (12,521 verts,
manifold, single component, zero degenerate faces) flatboi ran **9h12m without converging**, at both
`--flatten-keep 100` and the decimated default. Everything in section 2 below concerns tools only
the flatboi path needs, so it is real but not on the critical path.

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

## 2. That image cannot render, and `Dockerfile` here fixes it

`:edge` and `:main` are the same digest
(`sha256:bad516f66001abca759454cc43e4fd11e5b19aa55d36bdc2043817291c8083c4`, built 2026-05-13) and
are older than `render_ink.py`. Two tools are wrong:

* **`vc_obj_uv_lift` is absent.** `render_ink.py` invokes it whenever `--flatten-keep < 100` (the
  default is 6.25). It is 381 lines depending only on header-only libigl, Eigen and OpenMP, so it
  builds standalone in seconds.
* **`vc_tifxyz2obj` predates `--keep`**, and answers `error: unknown option '--keep=6.2500'`.

The second is the fatal one. Without `--keep` the only accepted setting is `--flatten-keep 100`,
which is the case the option's own help warns about ("smaller mesh is less prone to SLIM
divergence"), and it does not converge:

| windings | vertices into flatboi | `--flatten-iters` | result |
|---:|---:|---:|---|
| 10 | 200,196 | 50 | killed at 1h51m, still running |
| 3 | ~60,000 | 10 | killed at 1h13m, still running |

`Dockerfile` rebuilds `vc_tifxyz2obj` from villa source pinned by `VILLA_SHA` and grafts it plus
its five shared libraries onto the published runtime image, shadowing the stale binary on PATH. The
key economy is building **one CMake target**, not VC3D: `--target vc_tifxyz2obj` pulls in
`libvc_core` and skips the Qt UI, flatboi, python bindings and tests, so configure takes seconds and
the compile a few minutes rather than the hour a full build costs. The `builder-ubuntu-24.04` image
supplies Ceres, OpenCV, CGAL and Boost, so no root and no apt on the host.

The build asserts `vc_tifxyz2obj` accepts `--keep` and fails if not, so it cannot silently revert to
the broken path.

With that in place `--keep` does what it exists to do, emitting the coarse/fine pair:

```
w010-019_coarse.obj    12,521 verts   <- flatboi flattens this
w010-019.obj          200,196 verts   <- vc_obj_uv_lift lifts the UVs back onto this
```

Reported upstream as ScrollPrize/villa#1660; a refreshed published image would make this whole
directory unnecessary.

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

## 4. `lasagna/fit.py` imports a module that is not in `lasagna/`

```
ModuleNotFoundError: No module named 'vc3d_fiber_format'
```

It lives in villa's `vesuvius/src/vc3d_fiber_format/`, so the flatten dies on import unless
`vesuvius/src` is on `PYTHONPATH`. `setup_workdir.sh` extracts it alongside `lasagna`.

## 5. GPU: split host and container

There is no nvidia container runtime here, so lasagna cannot use the GPU from inside the image.
`run_render.sh` runs the python on the HOST (its venv has torch 2.11.0+cu128 on a 4090) and calls
the native binaries in the container through `bin/` wrappers. Those mount the workspace at an
**identical** path so absolute arguments need no translation, and pass `--user` so outputs are not
root owned.

## 6. The ink volume is streamable, no bulk download

`--volume <empty local cache dir> --remote-url <the s3 zarr url>`. Level 0 is 75784 x 32693 x
32693 uint8 in 256^3 chunks, so only the chunks under the mesh are fetched.

## Putting it together

```sh
docker build -t vc-render:local .            # ~5 min: one CMake target, not all of VC3D
docker run --rm -v "$WORK":/work --entrypoint sh vc-render:local -c "
  cd /work/sf_main && python3 -u render_ink.py /work/meshes \
    --volume /work/inkcache --remote-url '$INK_URL' \
    --vc-render-bin /work/bin/vc_render_scaled \
    --strips --no-full-scroll --num-processes 1"
```

`--flatten-keep` is left at its documented default, which the rebuilt `vc_tifxyz2obj` accepts.
`sf_main` must be a `spiral-fitting` tree recent enough to have `--remote-url`; the checkout in
`villa-spiral` was 13 commits behind and did not.

Two costs worth knowing before starting. flatboi is single threaded and still slow even on the
decimated mesh, so a full 120 winding fit is a long job on a 4 core box. And `vc_render_scaled` must
be on a path visible inside the container.

## 7. Scoring an OUTER-winding strip OOMs the stock scorer

The four obstacles above are about getting a render at all. A fifth appears only at the outer
windings, because those strips are an order of magnitude bigger:

| arm | flat grid | rendered strip |
|---|---|---|
| w010-w019 (inner) | 881 x 304 | 8,810 x 3,040 = 26.8M px |
| w120-w129 (outer) | 8267 x 426 | 82,670 x 4,260 = 352M px |

`get_ink_metrics.py` launches one subprocess per fold and waits for all three, so at 352M px three
copies of the strip's logits are live at once. On a 32GB box that is fatal, and it is fatal in a way
the fold logs do not explain:

```
[mem] used= 8706MB avail=23386MB    <- before launch
[mem] used=30878MB avail= 1214MB    <- three folds live
  fold 0 (GPU 0) FAILED (rc=1)
  fold 1 (GPU 0) FAILED (rc=-9)     <- SIGKILL, the OOM killer
```

`serial_folds.patch` adds an opt-in `INK_METRIC_SERIAL_FOLDS=1`: folds run one at a time, and the
ensemble accumulates in place rather than stacking three arrays and calling `np.mean`. The default
path is untouched. `score_arms.sh` sets the variable and traces memory alongside, because an OOM is
otherwise silent.

**The scorer is not bit-deterministic, patched or not.** Three runs over one fixed strip:

| run | `total_fg_pixels` | `line_score` |
|---|---:|---|
| on record | 249,913 | 0.40331167445607574 |
| stock path, re-run | 249,905 | 0.40331167445607574 |
| serial path | 249,906 | 0.40331167445607574 |

The **stock** path also fails to reproduce its own earlier number, so the drift is nnU-Net run-to-run
nondeterminism on GPU and not the patch. The spread is 0.0032%, against a documented **1.42%**
floor for a full render+score re-run on identical meshes: essentially all of that 1.42% is the
render, and a re-score is close to free of noise. `line_score` is bit-identical across all three,
being computed the same way from the averaged probabilities.

Rendering an outer strip is also slow for the same reason. `vc_render_tifxyz` reached 26.1GB RSS and
the box began swapping, taking band times from 26s to 18m; the ten outer windings took **2h02m**
against about 8 minutes for ten inner ones.
