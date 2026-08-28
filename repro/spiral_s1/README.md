# Reproducing the s1 spiral-fitting dataset fetch

What these scripts fetch, why, and what is still missing. Nothing here modifies `villa/`.

## Why

villa deprecated `ink-detection/` (moved to `deprecated/`) and its live geometry work is
`spiral-fitting/`, which runs its own LLM research loop against a frozen ink-coverage objective
(`spiral-fitting/autoresearch.md`). Assessing whether that loop is runnable here needed the real
data, not an estimate. `scripts/size_spiral_roi.py` consumes what these scripts download.

## The two scripts

- `fetch_lasagna.sh` fetches the resident-pool sidecars and the small annotation JSONs.
  **47.5 GiB**, 13 files. Resumable (`wget -c`), safe to re-run.
- `fetch_metas.sh` fetches `verified_patches/*/meta.json` only, so patches can be selected by
  z-ROI before committing to their full payload. 89,237 requests at 10 concurrent, roughly two
  hours. Resumable (skips non-empty files), records misses to `metas_misses.txt`.

Both take the dataset root from their own location. Default target used here:
`/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1`, deliberately outside this repository so
48 GB cannot wander into git.

Source: `https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/` (PHercParis4 is Scroll 1).
The sidecars ship pre-packed, so `pack_resident_pools.py` is not needed.

## Verification

After `fetch_lasagna.sh`, every `channel_*.u8` was checked against the server's `content-length`
and matched exactly:

```
surf_sdt/channel_0.u8   34981052416
nx/channel_0.u8          5447483392
nx/channel_1.u8          5447483392
grad_mag/channel_0.u8    5105582080
```

## What is NOT here, and has to be constructed

`fit_spiral.py` requires `<dataset>/spiral-scroll.json`. **It is not published**: it 404s on
PHercParis4, PHerc0125 and PHerc0332. The schema is named in `ScrollSpecError`:
`schema_version`, `name`, `voxel_size_um`, `spiral_outward_sense`, plus optional path overrides.

Values that can be justified rather than guessed:

- `base_shape_zyx = [18946, 8174, 8174]`, which is exactly 2x the respool `array_shape`
  `[9473, 4087, 4087]` on every axis. This is also the fixture value in
  `tests/test_spiral_headless.py`, and it independently confirms that patch bbox coordinates are
  2x resident-pool coordinates.
- `voxel_size_um = 9.6`, corroborated by upstream's own `find_inconsistent_windings.py:203`, which
  hardcodes that default for this dataset. It feeds flattening and publishing rather than core fit
  geometry.
- `name = "s1"`, `schema_version = 1`, `spiral_outward_sense = "CW"` follow the same fixture.

Writing this file is still an interpretation of someone else's data format, not a lookup. It is
left unwritten here deliberately.

## Environment

Built from a SEPARATE sparse checkout of `ScrollPrize/villa` at `6847063ff`
(`spiral-fitting` and `vesuvius`; the latter is required because `spiral_helpers.py` imports
`vc3d_fiber_format` from `vesuvius/src`). The `villa/` submodule in this repository stays pinned
at `ced62390e` and is never touched.

`uv sync` needs an explicit `CXX`: the build looks for `g++-12`, which is absent here. Setting
`CXX=/usr/bin/g++-13 CC=/usr/bin/gcc-13` works. **The source of that `g++-12` was never found**:
it is not in `pyproject.toml`, `cpp/CMakeLists.txt`, uv's config, or the shell environment in
either sandboxed or unsandboxed shells. A working workaround over an unexplained cause.
