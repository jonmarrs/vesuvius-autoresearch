# Villa Autoresearch Prize Action Matrix

This matrix joins official `ScrollPrize/villa` opportunity tracking with the current Autoresearch evidence queue.

## Current State

- Villa local ref: `4b7c5c20d95b404b7e92dc70606a1b1ed8648fd3`
- Villa upstream ref: `ad4e1b7d8a85c553c0b135b5f02ef98af9a9e923`
- Villa behind upstream: `True`
- Villa diverged with local patches: `True`
- Evidence preflight candidates: `2`
- GPU-ready evidence candidates: `2`
- Blocked evidence candidates: `0`
- GPU queue: `reports/scroll23_gpu_inference_queue.tsv`

## Ranked Actions

| Rank | Official Villa hook | Track | Readiness | Autoresearch action | Evidence gate |
| --- | --- | --- | --- | --- | --- |
| 1 | [villa-issue-191](https://github.com/ScrollPrize/villa/issues/191) Surface and fiber predictions in compressed or highly curved areas | `first_letters` | `ready_now` | Route ready Scroll 2/3 windows through Lasagna/fiber preprocessing before the next ink pass. | Use GPU-ready preflight candidates with occupied CT chunks. |
| 2 | [villa-issue-193](https://github.com/ScrollPrize/villa/issues/193) Methods for generating surface, fiber, or ink labels | `progress_and_first_letters` | `ready_now` | Route ready Scroll 2/3 windows through Lasagna/fiber preprocessing before the next ink pass. | Use GPU-ready preflight candidates with occupied CT chunks. |
| 3 | [villa-issue-369](https://github.com/ScrollPrize/villa/issues/369) VC3D integrate fiber predictions | `progress_prize` | `ready_now` | Export ink and fiber maps as VC3D-compatible OME-Zarr overlays for surface review. | Require prediction Zarr metadata and scale metadata to validate cleanly. |
| 4 | [villa-issue-203](https://github.com/ScrollPrize/villa/issues/203) Whole-volume deformation from vertical fibers and large meshes | `progress_prize` | `ready_now` | Export ink and fiber maps as VC3D-compatible OME-Zarr overlays for surface review. | Require prediction Zarr metadata and scale metadata to validate cleanly. |
| 5 | [villa-issue-201](https://github.com/ScrollPrize/villa/issues/201) Scroll-specific 3D augmentations for model training | `progress_and_first_letters` | `training_ablation` | Use official 3D decoder changes to prioritize cross-scroll augmentation ablations. | Require a sprint log entry that records scroll-specific augmentation settings. |

## Top GPU-Ready Candidates

- `pred_18176_4128_4128_64x64`: Scroll 2 div_90 z=18176 y=4128 x=4128, review_score=2.350000, report=`reports/scroll23_evidence/candidate_000/preflight_report.json`
- `pred_18176_4128_4000_64x64`: Scroll 2 div_90 z=18176 y=4128 x=4000, review_score=2.350000, report=`reports/scroll23_evidence/candidate_001/preflight_report.json`
