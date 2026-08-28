# The published spiral dataset cannot run the fit's default configuration

**Measured 2026-08-28** against villa `6847063ff` and
`dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/`. Not yet reported upstream.

## The finding

`dense_spacing_mode` defaults to `"phase"` (`fit_session.py:261`). Phase mode requires the surf-SDT
store, and `prepare_surf_sdt_volume` opens the **source OME-Zarr**:

```python
root = zarr.open_group(sdt_zarr_path, mode='r')      # lasagna_data.py:338
...
raise RuntimeError(f'no OME multiscales scale for group {group_name!r} in {sdt_zarr_path}; '
                   'the fitter refuses to infer the store geometry')
```

**That store is not published.** `lasagna_inputs/` ships exactly three entries, all resident-pool
sidecars:

```
las_008_grad_mag.ome.zarr.respool_g4/
las_008_nx.ome.zarr.respool_g4_pair/
las_008_surf_sdt.ome.zarr.respool_g1/
```

and a bare `las_008_surf_sdt.ome.zarr/`, its `.zattrs`, and its `zarr.json` all return 404.

## Why this looks like an inconsistency rather than a missing download

The two paths treat geometry differently:

| store | how geometry is obtained | works from published data |
|---|---|---|
| normals, grad_mag | `_require_sidecar` + `_read_sidecar_meta`, i.e. the sidecar's own `meta.json` | yes |
| surf_sdt | `zarr.open_group(sdt_zarr_path)`, OME attrs, `array.shape[0]` | **no** |

`ensure_fit_sparse_stores` shows the same split: the normals and grad_mag branches check only that
the path *string* is set, while the SDT branch alone calls `os.path.exists(sdt_zarr_path)`
(`lasagna_data.py:115`).

The data itself is not the problem. `prepare_surf_sdt_volume` reads the raw zarr only for geometry
and coverage, then calls `_require_sidecar(...)` and takes the voxels from the sidecar. So the
32.58 GiB SDT sidecar that ships publicly is the real payload and is usable; what is absent is
metadata.

## Why I did not synthesise the metadata

A metadata-only zarr would satisfy it: a group `1`, an array of shape `[9473, 4087, 4087]`, OME
multiscales attrs giving the scale, and either `complete: true` or `built_z_ranges_working`
covering the fit range.

Three of those four I can state from measurement. `complete` I cannot. The fitter's own error says
what a wrong answer costs:

> unbuilt tiles read as no-data and would silently disable the SDT losses there

Stamping a trust flag to get past a check, where being wrong degrades the fit silently, is the exact
failure this project keeps recording. The honest version would declare `built_z_ranges_working` from
the sidecar's measured occupancy (occupied brick-z 56 to 288, so pool z 1792 to 9216, working z 3584
to 18432 at the factor 2), and even that asserts a correspondence between two coordinate systems
that has been confirmed but never exercised by a fit.

## What this means for the work here

The baseline fit should run with `dense_spacing_mode` set to `grad_mag`, which uses only
sidecar-native paths and requires no fabricated metadata. `use_sdt` is gated on
`phase_bundle_enabled(config)`, which is `_dense_spacing_mode(config) == "phase"`, so a non-phase
mode skips the SDT branch entirely.

That is a deviation from villa's default and is one more reason our numbers are not comparable to
theirs, on top of the reduced z-ROI. Recorded so the deviation is visible rather than discovered
later in a result.

## Limits

Read from source and from HTTP status codes; **no fit has been run**, so this is a code-and-
availability claim, not an observed failure. The obvious way it could be wrong is a path override or
an alternate layout that supplies the source zarr from elsewhere, which is exactly what
`path_overrides` in `spiral-scroll.json` exists for. Before reporting this upstream, run the fit and
show the actual error.
