# Villa Review Manifest

This manifest maps GPU-ready Autoresearch candidates to official Villa review workflows.

## Official Villa Context

- Villa local ref: `e67fa7425a31f73ec48eeae14b8d7d53b782c2b0`
- Villa upstream ref: `c33fc11f09e0f65ce3c1c267f46a311104902055`
- GPU-ready candidates: `2`
- Source queue: `reports/scroll23_gpu_inference_queue.tsv`

## Ready Villa Hooks

- `villa-issue-191` `first_letters`: Surface and fiber predictions in compressed or highly curved areas -> reports/lasagna_fiber_worklist.tsv
- `villa-issue-193` `progress_and_first_letters`: Methods for generating surface, fiber, or ink labels -> reports/lasagna_fiber_worklist.tsv
- `villa-issue-201` `progress_and_first_letters`: Scroll-specific 3D augmentations for model training -> sprint_logs/
- `villa-issue-369` `progress_prize`: VC3D integrate fiber predictions -> VC3D overlay path in prediction metadata
- `villa-issue-203` `progress_prize`: Whole-volume deformation from vertical fibers and large meshes -> VC3D overlay path in prediction metadata

## Candidate Review Queue

### Candidate 000: `pred_18176_4128_4128_64x64`

- Location: Scroll 2 div_90 z=18176 y=4128 x=4128
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_000/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_000/predictions/pred_18176_4128_4128_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_000/predictions/pred_18176_4128_4128_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python3 scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 0 --out-dir reports/scroll23_evidence/candidate_000 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python3 scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_000/predictions/pred_18176_4128_4128_64x64_meta.json --out reports/scroll23_evidence/candidate_000/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python3 scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python3 scripts/launch_vc3d.py`

### Candidate 001: `pred_18176_4128_4000_64x64`

- Location: Scroll 2 div_90 z=18176 y=4128 x=4000
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_001/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_001/predictions/pred_18176_4128_4000_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_001/predictions/pred_18176_4128_4000_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python3 scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 1 --out-dir reports/scroll23_evidence/candidate_001 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python3 scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_001/predictions/pred_18176_4128_4000_64x64_meta.json --out reports/scroll23_evidence/candidate_001/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python3 scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python3 scripts/launch_vc3d.py`
