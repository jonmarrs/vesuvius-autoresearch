# Villa Autoresearch Prize Action Matrix

This matrix joins official `ScrollPrize/villa` opportunity tracking with the current Autoresearch evidence queue.

## Current State

- Villa local ref: `b01e0e050b8ab498d5b9166b33cbf2e8f535e690`
- Villa upstream ref: `f037ffb5b236dcb74112ec33c8843eaa15ff5a85`
- Villa behind upstream: `False`
- Villa diverged with local patches: `False`
- Evidence preflight candidates: `12`
- GPU-ready evidence candidates: `12`
- Blocked evidence candidates: `0`
- GPU queue: `reports/scroll23_gpu_inference_queue.tsv`

## Ranked Actions

| Rank | Official Villa hook | Track | Readiness | Autoresearch action | Evidence gate |
| --- | --- | --- | --- | --- | --- |
| 1 | [villa-issue-191](https://github.com/ScrollPrize/villa/issues/191) Surface and fiber predictions in compressed or highly curved areas | `first_letters` | `ready_now` | Route ready Scroll 2/3 windows through Lasagna/fiber preprocessing before the next ink pass. | Use GPU-ready preflight candidates with occupied CT chunks. |
| 2 | [villa-issue-193](https://github.com/ScrollPrize/villa/issues/193) Methods for generating surface, fiber, or ink labels | `progress_and_first_letters` | `ready_now` | Route ready Scroll 2/3 windows through Lasagna/fiber preprocessing before the next ink pass. | Use GPU-ready preflight candidates with occupied CT chunks. |
| 3 | [villa-issue-201](https://github.com/ScrollPrize/villa/issues/201) Scroll-specific 3D augmentations for model training | `progress_and_first_letters` | `training_ablation` | Use official 3D decoder changes to prioritize cross-scroll augmentation ablations. | Require a sprint log entry that records scroll-specific augmentation settings. |
| 4 | [villa-issue-369](https://github.com/ScrollPrize/villa/issues/369) VC3D integrate fiber predictions | `progress_prize` | `ready_now` | Export ink and fiber maps as VC3D-compatible OME-Zarr overlays for surface review. | Require prediction Zarr metadata and scale metadata to validate cleanly. |
| 5 | [villa-issue-203](https://github.com/ScrollPrize/villa/issues/203) Whole-volume deformation from vertical fibers and large meshes | `progress_prize` | `ready_now` | Export ink and fiber maps as VC3D-compatible OME-Zarr overlays for surface review. | Require prediction Zarr metadata and scale metadata to validate cleanly. |

## Villa Baselines & Lanes

| ID | Status | Purpose | Marker | Launcher |
| --- | --- | --- | --- | --- |
| gp_winner_baseline | `dry_run` | fixed research-only comparator (patch 16x256x256, not submittable) | `reports/gp_winner_baseline.json` | `scripts/launch_gp_winner.py` |
| mutex_affinity | `dry_run` | Grand-Prize-aligned lane; submittable when patch<=64 | `reports/mutex_affinity_run.json` | `scripts/launch_mutex.py` |
| neural_tracing_service | `dry_run` | Review-time tracing daemon for VC3D / Crackle Viewer | `reports/neural_tracing_service.json` | `scripts/launch_neural_tracing.py` |
| finetune_lejepa | `ready` | Convert pretrained LeJEPA encoder into a submittable ink model (patch 64) | `reports/finetune_lejepa_run.json` | `scripts/launch_finetune_lejepa.py` |

## Top GPU-Ready Candidates

- `pred_18176_4128_4128_64x64`: Scroll 2 div_90 z=18176 y=4128 x=4128, review_score=2.791621, report=`reports/scroll23_evidence/candidate_000/preflight_report.json`
- `pred_18176_4128_4000_64x64`: Scroll 2 div_90 z=18176 y=4128 x=4000, review_score=2.582762, report=`reports/scroll23_evidence/candidate_001/preflight_report.json`
- `pred_18176_4000_4128_64x64`: Scroll 2 div_90 z=18176 y=4000 x=4128, review_score=2.496840, report=`reports/scroll23_evidence/candidate_002/preflight_report.json`
