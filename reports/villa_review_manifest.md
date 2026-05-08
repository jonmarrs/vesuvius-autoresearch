# Villa Review Manifest

This manifest maps GPU-ready Autoresearch candidates to official Villa review workflows.

## Official Villa Context

- Villa local ref: `4b7c5c20d95b404b7e92dc70606a1b1ed8648fd3`
- Villa upstream ref: `ad4e1b7d8a85c553c0b135b5f02ef98af9a9e923`
- GPU-ready candidates: `2`
- Source queue: `reports/scroll23_gpu_inference_queue.tsv`

## Ready Villa Hooks

- `villa-issue-191` `first_letters`: Surface and fiber predictions in compressed or highly curved areas -> reports/lasagna_fiber_worklist.tsv
- `villa-issue-193` `progress_and_first_letters`: Methods for generating surface, fiber, or ink labels -> reports/lasagna_fiber_worklist.tsv
- `villa-issue-369` `progress_prize`: VC3D integrate fiber predictions -> VC3D overlay path in prediction metadata
- `villa-issue-203` `progress_prize`: Whole-volume deformation from vertical fibers and large meshes -> VC3D overlay path in prediction metadata
- `villa-issue-201` `progress_and_first_letters`: Scroll-specific 3D augmentations for model training -> sprint_logs/

## Candidate Review Queue

### Candidate 000: `pred_18176_4128_4128_64x64`

- Location: Scroll 2 div_90 z=18176 y=4128 x=4128
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_000/preflight_report.json`
- Expected prediction image: `predictions/pred_18176_4128_4128_64x64.png`
- Expected prediction metadata: `predictions/pred_18176_4128_4128_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --candidate-index 0 --out-dir reports/scroll23_evidence/candidate_000 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata predictions/pred_18176_4128_4128_64x64_meta.json --out reports/scroll23_evidence/candidate_000/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 001: `pred_18176_4128_4000_64x64`

- Location: Scroll 2 div_90 z=18176 y=4128 x=4000
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_001/preflight_report.json`
- Expected prediction image: `predictions/pred_18176_4128_4000_64x64.png`
- Expected prediction metadata: `predictions/pred_18176_4128_4000_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --candidate-index 1 --out-dir reports/scroll23_evidence/candidate_001 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata predictions/pred_18176_4128_4000_64x64_meta.json --out reports/scroll23_evidence/candidate_001/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`
