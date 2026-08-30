# RECORD, POSTED 2026-08-30

Posted as ScrollPrize/villa#1655: https://github.com/ScrollPrize/villa/issues/1655

A record of what was said, not a draft. Corrections go to the thread as a new comment, never as a
silent edit here. No nudges: await a reply.

---

Running `spiral-fitting` from published data alone: four obstacles that are not documented anywhere.

I got a converged 30,000 step fit on `spiral_datasets/PHercParis4` using only public data, on a single RTX 4090, in 1h34m. Four things stood between the published dataset and a running fit, and none of them is written down. Posting the measurements in case they are useful, either as documentation or as a signal about where the friction is.

**1. Most of the download is not needed.** `lasagna_inputs/` ships 47.5 GiB of resident-pool sidecars and the default configuration loads one of them:

| sidecar | size | loaded by default |
|---|---:|---|
| `las_008_nx.ome.zarr.respool_g4_pair` | 11 GB | yes |
| `las_008_grad_mag.ome.zarr.respool_g4` | 4.8 GB | no |
| `las_008_surf_sdt.ome.zarr.respool_g1` | 33 GB | no |

`dense_spacing_mode` defaults to `winding_model`, so `_grad_mag_required()` is False, and `input_use_surf_sdt` defaults to False, so `_phase_bundle_enabled()` is False. Confirmed by evaluating the predicates and by grepping a completed run's log, where `surf_sdt` and `grad_mag` each appear zero times. A working fetch is about 13 GB. I downloaded all 47.5 before checking.

A trap worth naming: `_dense_spacing_mode` reads `config.get("dense_spacing_mode", "phase")`, and that `"phase"` is the fallback for an absent key rather than the default. The default is `winding_model`.

**2. `spiral-scroll.json` is required and is published nowhere.** `fit_spiral.py` refuses to start without it, and it 404s on PHercParis4, PHerc0125 and PHerc0332. Four keys are enough, since every other default already matches the published directory names:

```json
{"schema_version": 1, "name": "s1", "voxel_size_um": 9.6,
 "spiral_outward_sense": "CW",
 "paths": {"winding_inference": "winding_model"}}
```

**3. `winding_inference` ships under a different name.** The default `winding_model` mode needs the `winding_inference` input; the dataset publishes it as `winding_model/`, identified by its manifest `artifact_type: "winding_inference_crossings"` rather than by the directory name. `winding_inference` is in `SCROLL_SPEC_PATH_OVERRIDE_KEYS`, so the `paths` override above is the supported bridge.

**4. Three default-on inputs have to be turned off**, because `drawn_control_points.json` is 404 on every dataset, `tracks/` is 35+ GB, and there is no published directory under the conventional name `fibers`.

Measured cost once running: 38,442 patches load in ~90s, theta topology ~114s, 30,000 steps in 1h34m at 5.3 it/s average, 65.4% satisfied patches, peak host RSS 7.78 GiB, and only 2.85 GiB of resident pool actually resident because of the z-ROI restriction. VRAM was never the binding constraint.

Full write-up with the scripts: https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/RUNNING_THE_SPIRAL_FIT.md

One caveat on my own numbers: `spiral_outward_sense` is the weakest value in that manifest. It has no independent corroboration beyond a test fixture, and a converged fit reaching 65.4% while driving `abs_winding` from 888.1 to 2.3 is evidence for it rather than proof.
