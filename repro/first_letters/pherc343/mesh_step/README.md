# PHerc. 343 mesh step (finding 110)

The kill test one folder up rebuilt the published image **from the published windings**. This folder runs the
half of the recipe that the kill test did not: making windings from public inputs (distance field, spiral fit,
snap, flatten), then asking whether those windings lie on the published sheets and carry the same ink. The
question, predictions and decision table are in
`docs/preregistration/2026-11-10_first_letters_343_mesh_step.md`.

PHerc. 343 is already awarded. Nothing here concerns a scroll that is still eligible for a prize.

The recipe is [Nieuwlaar/pherc343-first-letters](https://github.com/Nieuwlaar/pherc343-first-letters) at commit
`e8370f1f`. None of its code, meshes, images or its scroll-axis file is copied into this repository; the
scripts call it from the kill test's clone. villa is used at `0fb38c45`, unchanged except for the recipe's own
one-line patch (`mesh/fit_spiral_shell_optional.patch`), applied to an exported copy.

Paths are this host's and are set in `env.sh`: `R` is this step's run directory, `B` the kill test's, `V` a
villa checkout at the pinned commit. Everything large lives under `R`.

## Setup (once)

These six scripts were written after the fact from the commands that were run by hand. Each records what was
done; **none has been re-run as a script**. `make_dataset.sh` is the exception in one respect: the scroll
description it generates was compared with the one in use and is identical.

| Script | What it does |
|---|---|
| `setup/export_villa.sh` | exports villa's `volume-cartographer` Python sources at the pin into `R/villa_src` and applies the recipe's patch there |
| `setup/setup_spiral_env.sh` | builds `R/venv_spiral` from villa's own lock file |
| `setup/build_native.sh` | builds villa's three native modules (`track_store`, `track_crossings`, `spiral_sampling`) with `setup/native_CMakeLists.txt` |
| `setup/fetch_tracks.sh` | downloads the public PHerc. 343 spiral tracks |
| `setup/fetch_volumes.sh` | lists (`s3_plan.py`) and downloads (`s3_fetch.py`) the band's chunks of the surface prediction, the CT and the lasagna arrays |
| `setup/make_dataset.sh` | writes the dataset folder the fit reads, copying the recipe's scroll axis from the clone |

All downloads are anonymous HTTPS listing and GET from the public open-data bucket and `dl.ash2txt.org`.
Nothing is uploaded.

## The run

An arm is `recipe` (the registered fit, 30,000 steps), `reduced` (fewer steps, only under the registration's
reduced-fit rule) or `smoke` (a few hundred steps, to learn memory, time and layout; its windings are never
compared with the published ones, and the selection, P1 and comparison scripts refuse it). Each step writes
its exit code to `R/work/gate_ARM/`, and each refuses to overwrite an earlier run of itself.

| Order | Script | What it does | Device |
|---|---|---|---|
| 1 | `run_sdt.sh` | villa `make_surf_sdt.py`: the distance field of the surface prediction over the band | CPU |
| 2 | `run_fit.sh ARM` | villa `fit_spiral.py` with the recipe's overrides, seed 1 | GPU |
| 3 | `run_select.sh ARM` | picks, by geometry alone, the raw winding nearest each published winding | CPU |
| 4 | `run_snap.sh ARM` | fetches the level-0 surface chunks those windings can touch (`snap_chunks.py`), then the recipe's `snap_meshes.py` | CPU |
| 5 | `run_flatten.sh ARM W` | villa's lasagna flattening of one snapped winding | GPU |
| 6 | `run_p1.sh ARM` | P1 and P2: distance from each published winding to the final windings, and which way their normals point | CPU |
| 7 | `run_render.sh ARM W` | 66-layer render, flipped if step 6 says the normals point against the published ones | CPU |
| 8 | `run_ink.sh ARM W` | the four released ink models at depth +1, both sides (the recipe's `run_depth_sweep.sh`) | GPU |
| 9 | `run_compare.sh ARM` | gathers the gate, carries our ink into the published segment's frame (`transfer_maps.py`), applies the decision table | CPU |

The GPU steps need the training loop paused (`./stop.sh` from the project root, `./start.sh` afterwards).

`mesh_step_analysis.py` holds the measurements and the decision table; `transfer_maps.py` holds the file
reading for the ink comparison. Their tests are `tests/test_first_letters_343_mesh_step.py`.

## Why `snap_chunks.py` exists

The snap reads the surface prediction at level 0, and only level 1 was downloaded for the distance field. A
zarr chunk that is missing on disk reads as zeros, and zeros mean "no sheet here" to the snap: a chunk that
was needed but never fetched would move no node and raise no error. `snap_chunks.py` fetches every chunk the
snap can sample, records which chunks the bucket itself does not hold, and fails unless every needed chunk is
one or the other. `run_snap.sh` repeats the check offline immediately before the snap.

## Not committed

The recipe's code is MIT. Its meshes and images are CC BY-NC 4.0, and none is committed here, nor is its
scroll-axis file. The fitted windings, renders and ink maps stay under `R`.
