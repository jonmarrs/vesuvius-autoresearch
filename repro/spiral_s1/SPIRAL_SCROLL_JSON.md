# `spiral-scroll.json`: constructed, not downloaded

`fit_spiral.py` requires `<dataset>/spiral-scroll.json`. **No published dataset ships it** (404 on
PHercParis4, PHerc0125, PHerc0332). This file records how each value was chosen, because writing it
is an interpretation of someone else's format and should be auditable rather than trusted.

```json
{"schema_version": 1, "name": "s1", "voxel_size_um": 9.6, "spiral_outward_sense": "CW"}
```

## Why only four keys

`ScrollSpec` (`fit_session.py:581`) requires exactly `name`, `voxel_size_um`,
`spiral_outward_sense`, plus `schema_version`. Everything else has a default, and **the defaults
already match the published dataset**, which is the strongest evidence that they are the intended
values:

| field | default | published dataset |
|---|---|---|
| `normal_zarr_group` | `"4"` | `las_008_nx.ome.zarr.respool_g4_pair` |
| `surf_sdt_zarr_group` | `"1"` | `las_008_surf_sdt.ome.zarr.respool_g1` |
| `lasagna_scale` | `4` | consistent with the `g4` normals |
| `umbilicus_coordinate_scale` | `1.0` | see below |

Setting them explicitly would add nothing and could drift from upstream defaults, so they are
omitted deliberately.

## `base_shape_zyx` is NOT a field

It appears in `tests/test_spiral_headless.py` and is tempting to copy, but that test is
`test_unknown_top_level_keys_are_ignored`: it is an *ignored* key, present to prove ignoring works.
Including it would look authoritative and mean nothing. It is still useful as evidence, since its
value `[18946, 8174, 8174]` is exactly 2x the respool `array_shape` `[9473, 4087, 4087]` on every
axis, which is how the patch-to-pool coordinate factor was confirmed.

## `umbilicus_coordinate_scale` stays at the default 1.0

This is the one field where a wrong value silently produces a geometrically wrong fit, since it
places the spiral centre. It is decided by data, not by preference:

`umbilicus.json` holds 146 control points spanning z 563 to 18240, y 3295 to 5965, x 3142 to 4908.
Those are patch-space coordinates (0 to 18946), not pool-space (0 to 9473 by 0 to 4087): a y of 5965
cannot exist in a 4087-wide axis. `json_umbilicus_z_to_yx` multiplies the control points by
`coordinate_scale`, so the published file is already in the space the fit works in, and the shipped
default of 1.0 is consistent with the shipped data. Any other value would move the scroll centre.

## `voxel_size_um = 9.6` is the one value taken on authority

Two independent upstream sources agree, and neither is ours:

* `find_inconsistent_windings.py:203` hardcodes `voxel_size_um=9.6` as its default for this dataset.
* `tests/test_spiral_headless.py:47` uses `9.6` for a scroll named `s1`.

It is consumed by flattening and publishing (`flatten_spiral_checkpoint.py`, `lasagna_publish.py`)
rather than by the core fit geometry, so an error here would mis-scale physical-unit reporting
rather than corrupt a fit. That is the reason it is acceptable to take on authority; it would not be
if it entered the geometry.

## `spiral_outward_sense = "CW"`

`parse_scroll_spec` accepts only `CW` or `ACW`. `CW` is the value used for `s1` in the upstream test
fixture. **This is the weakest of the four**: it is a binary with no independent corroboration, and
a wrong sense would mirror the winding direction. If a first fit produces windings that count in the
wrong direction, this is the field to flip before suspecting anything else.
