# Running villa's spiral fit from public data, on one consumer GPU

Everything below was executed, not inferred. Measured on a single RTX 4090 (24 GB) against villa
`6847063ff` and `dl.ash2txt.org/datasets/spiral_datasets/PHercParis4` (Scroll 1), 2026-08-28.

**Result: a converged 30,000-step fit in 1h 34m, 65.4% satisfied patches, from published data
alone.** No private inputs, no institutional access.

The point of this document is that four things stand between the published dataset and a running
fit, none of them documented anywhere, and one of them is a 33 GB download you do not need.

---

## 1. Do not download the surf-SDT store

The dataset's `lasagna_inputs/` holds three resident-pool sidecars totalling 47.5 GiB. **For the
default configuration only one of them is loaded.**

| sidecar | size | loaded by the default config |
|---|---:|---|
| `las_008_nx.ome.zarr.respool_g4_pair` (normals) | 11 GB | **yes** |
| `las_008_grad_mag.ome.zarr.respool_g4` | 4.8 GB | no |
| `las_008_surf_sdt.ome.zarr.respool_g1` | 33 GB | no |

Why: `dense_spacing_mode` defaults to `winding_model`, so `_grad_mag_required()` is `False`; and
`input_use_surf_sdt` defaults to `False`, so `_phase_bundle_enabled()` is `False`. Confirmed twice,
by evaluating those predicates and by grepping a completed run's log, where `surf_sdt` and
`grad_mag` each appear **zero** times.

With patches and the winding model, a working fetch is **about 13 GB**, not 48. We downloaded all
47.5 GiB before checking, which is the mistake this section exists to save you.

> Beware the same trap we fell into: `_dense_spacing_mode` reads
> `config.get("dense_spacing_mode", "phase")`. That `"phase"` is the fallback for an *absent* key,
> not the default. Instantiate `Config()` and print the value.

## 2. `spiral-scroll.json` is required and is published nowhere

`fit_spiral.py` refuses to start without `<dataset>/spiral-scroll.json`. It 404s on every dataset
we checked (PHercParis4, PHerc0125, PHerc0332). You must write it. Four keys suffice:

```json
{
    "schema_version": 1,
    "name": "s1",
    "voxel_size_um": 9.6,
    "spiral_outward_sense": "CW",
    "paths": { "winding_inference": "winding_model" }
}
```

Everything else has a default, and **the defaults already match the published directory names**
(`normal_zarr_group` `"4"` against `...respool_g4_pair`, `surf_sdt_zarr_group` `"1"` against
`...respool_g1`). Setting them explicitly adds nothing and can drift.

* `voxel_size_um: 9.6` is corroborated by `find_inconsistent_windings.py:203` and the upstream test
  fixture. It feeds flattening and publishing, not fit geometry.
* `spiral_outward_sense: "CW"` is the weakest value here, a binary with no independent
  corroboration. Our converged fit reaching 65.4% satisfaction while driving `abs_winding` from
  888.1 to 2.3 is strong evidence it is right, since an inverted sense would fight the absolute
  annotations rather than fit them. **If your fit winds backwards, flip this first.**
* Do **not** copy `base_shape_zyx` from the upstream test fixture. That test is
  `test_unknown_top_level_keys_are_ignored`; the key is ignored. It is still useful as evidence:
  its value `[18946, 8174, 8174]` is exactly 2x the respool `array_shape`, which is how the
  patch-to-pool coordinate factor is established.
* `umbilicus_coordinate_scale` stays at its default `1.0`. The published `umbilicus.json` spans
  y 3295 to 5965, which cannot exist on a 4087-wide pool axis, so it is already in the fit's space.
  A wrong value here silently misplaces the spiral centre.

## 3. `winding_inference` ships under a different name

The default `winding_model` mode requires the `winding_inference` input at conventional relative
`winding_inference`. The dataset publishes it as **`winding_model/`** (seven shards plus a
manifest). What identifies it is not the directory name but
`manifest.json → artifact_type: "winding_inference_crossings"`.

Bridge it with the `paths` override above rather than renaming: `winding_inference` is one of
eleven allow-listed keys in `SCROLL_SPEC_PATH_OVERRIDE_KEYS`. 201 MiB.

## 4. Three default-on inputs have to be turned off

| input | why |
|---|---|
| `input_use_pcl_drawn_control_points` | `drawn_control_points.json` is **404** on every dataset |
| `input_use_tracks` | `tracks/` is 35+ GB (`.dbm.db` 12.9, `m7_..._surf.dbm` 18.5, `.crossings.npz` 3.1, plus two directories) |
| `input_use_fibers` | no published directory under the conventional name `fibers` |

Upstream ships `spiral-fitting/configs/no_fibers.json` and `spiral-fitting/configs/no_tracks.json` as ablations, so this is a
supported configuration. It is still a deviation from the default, and any numbers you get are not
comparable to villa's.

## 5. Configuration is by environment, not CLI

`fit_spiral.py` takes only `--dataset`, `--scroll-spec` and `--cache`. Everything else arrives as
JSON in `FIT_SPIRAL_CONFIG_OVERRIDES`. Unknown keys **raise**, so typos fail loudly.

```bash
export CUDA_VISIBLE_DEVICES=0
export FIT_SPIRAL_OUT_DIR=/path/to/output
export FIT_SPIRAL_RUN_TAG=baseline01
export FIT_SPIRAL_CONFIG_OVERRIDES='{
  "z_begin": 13056, "z_end": 18432,
  "input_use_fibers": false,
  "input_use_tracks": false,
  "input_use_pcl_drawn_control_points": false
}'
python fit_spiral.py --dataset /path/to/spiral_s1
```

`optimizer_num_training_steps` may be *reduced* for a smoke run but never raised above its default
30,000, per upstream's `autoresearch.md`.

The run directory encodes the configuration (`s1_slice-13056-18432_38442-patch_baseline01`), but two
runs differing only in a config override are separated **solely by run tag**. Give every variant its
own tag.

## 6. Patches: 89,237 directories, no archive

`verified_patches/` is 89,237 directories of 4 to 5 small files, with no tarball, so fetching all of
it over HTTP is impractical. The fit filters host inputs by z, so fetch only what intersects your
ROI: each patch's `meta.json` carries a z-bearing `bbox`, in **patch coordinates, which are 2x the
resident-pool coordinates**.

Our ROI (working z 13056 to 18432) selected 38,616 patches, 2.1 GB. `generations.tif` is **optional**
and absent for many patches; treating its absence as an error buries real failures.

`scripts/select_spiral_patches.py` does the selection; `repro/spiral_s1/` holds the fetch scripts.

## 7. Build notes

Python >= 3.14 and `uv sync` in `spiral-fitting/`. Two snags:

* the build looked for `CXX=g++-12`, absent on our box. `CXX=/usr/bin/g++-13 CC=/usr/bin/gcc-13`
  works. **We never found where `g++-12` came from** — not `pyproject.toml`, not the CMakeLists,
  not uv's config, not the shell environment. A working workaround over an unexplained cause.
* a sparse checkout of `spiral-fitting/` alone is not enough: `spiral_helpers.py` imports
  `vc3d_fiber_format` from `vesuvius/src`. Include both.

## What to expect

```
patch loading            ~90s for 38,616 patches
theta topology           ~114s
trainable parameters     180,039,389 (720 MB)
30,000 steps             1h 34m, 5.3 it/s average including startup
peak host RSS            7.78 GiB
resident pool loaded     2.85 GiB (46,769 of 166,244 normals bricks, ROI-restricted)
satisfied_patches        25,148/38,439 (65.4%)
loss                     3182.7 -> 43.5
```

VRAM was never close to binding. The ROI restriction, not the card, is what bounded this run, and
the bound came from how many patches we chose to fetch.

## Provenance

Scripts and the exact configurations are in `repro/spiral_s1/`. Results and their limits are in
`reports/spiral_baseline_fit_2026-08-28.md` and `reports/spiral_smoke_run_2026-08-28.md`. Several
claims in this document replaced earlier wrong ones of ours; the retractions are in
`reports/spiral_published_dataset_cannot_run_default_mode.md` and
`reports/spiral_roi_constraint_corrected.md`, kept rather than deleted.
