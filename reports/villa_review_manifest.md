# Villa Review Manifest

This manifest maps GPU-ready Autoresearch candidates to official Villa review workflows.

## Official Villa Context

- Villa local ref: `666dec41597643884c87e97d817cdd8ceb8ed8e8`
- Villa upstream ref: `f037ffb5b236dcb74112ec33c8843eaa15ff5a85`
- GPU-ready candidates: `12`
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
- Review score: `2.791621`
- Preflight report: `reports/scroll23_evidence/candidate_000/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_000/predictions/pred_18176_4128_4128_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_000/predictions/pred_18176_4128_4128_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 0 --out-dir reports/scroll23_evidence/candidate_000 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_000/predictions/pred_18176_4128_4128_64x64_meta.json --out reports/scroll23_evidence/candidate_000/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 001: `pred_18176_4128_4000_64x64`

- Location: Scroll 2 div_90 z=18176 y=4128 x=4000
- Review score: `2.582762`
- Preflight report: `reports/scroll23_evidence/candidate_001/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_001/predictions/pred_18176_4128_4000_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_001/predictions/pred_18176_4128_4000_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 1 --out-dir reports/scroll23_evidence/candidate_001 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_001/predictions/pred_18176_4128_4000_64x64_meta.json --out reports/scroll23_evidence/candidate_001/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 002: `pred_18176_4000_4128_64x64`

- Location: Scroll 2 div_90 z=18176 y=4000 x=4128
- Review score: `2.496840`
- Preflight report: `reports/scroll23_evidence/candidate_002/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_002/predictions/pred_18176_4000_4128_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_002/predictions/pred_18176_4000_4128_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 2 --out-dir reports/scroll23_evidence/candidate_002 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_002/predictions/pred_18176_4000_4128_64x64_meta.json --out reports/scroll23_evidence/candidate_002/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 003: `pred_18176_4000_4000_64x64`

- Location: Scroll 2 div_90 z=18176 y=4000 x=4000
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_003/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_003/predictions/pred_18176_4000_4000_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_003/predictions/pred_18176_4000_4000_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 3 --out-dir reports/scroll23_evidence/candidate_003 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_003/predictions/pred_18176_4000_4000_64x64_meta.json --out reports/scroll23_evidence/candidate_003/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 004: `pred_18304_4128_4128_64x64`

- Location: Scroll 2 div_90 z=18304 y=4128 x=4128
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_004/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_004/predictions/pred_18304_4128_4128_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_004/predictions/pred_18304_4128_4128_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 4 --out-dir reports/scroll23_evidence/candidate_004 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_004/predictions/pred_18304_4128_4128_64x64_meta.json --out reports/scroll23_evidence/candidate_004/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 005: `pred_20224_4128_4128_64x64`

- Location: Scroll 2 div_100 z=20224 y=4128 x=4128
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_005/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_005/predictions/pred_20224_4128_4128_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_005/predictions/pred_20224_4128_4128_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 5 --out-dir reports/scroll23_evidence/candidate_005 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_005/predictions/pred_20224_4128_4128_64x64_meta.json --out reports/scroll23_evidence/candidate_005/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 006: `pred_20224_4128_4000_64x64`

- Location: Scroll 2 div_100 z=20224 y=4128 x=4000
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_006/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_006/predictions/pred_20224_4128_4000_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_006/predictions/pred_20224_4128_4000_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 6 --out-dir reports/scroll23_evidence/candidate_006 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_006/predictions/pred_20224_4128_4000_64x64_meta.json --out reports/scroll23_evidence/candidate_006/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 007: `pred_20224_4000_4128_64x64`

- Location: Scroll 2 div_100 z=20224 y=4000 x=4128
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_007/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_007/predictions/pred_20224_4000_4128_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_007/predictions/pred_20224_4000_4128_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 7 --out-dir reports/scroll23_evidence/candidate_007 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_007/predictions/pred_20224_4000_4128_64x64_meta.json --out reports/scroll23_evidence/candidate_007/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 008: `pred_20224_4000_4000_64x64`

- Location: Scroll 2 div_100 z=20224 y=4000 x=4000
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_008/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_008/predictions/pred_20224_4000_4000_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_008/predictions/pred_20224_4000_4000_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 8 --out-dir reports/scroll23_evidence/candidate_008 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_008/predictions/pred_20224_4000_4000_64x64_meta.json --out reports/scroll23_evidence/candidate_008/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 009: `pred_20096_4128_4128_64x64`

- Location: Scroll 2 div_100 z=20096 y=4128 x=4128
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_009/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_009/predictions/pred_20096_4128_4128_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_009/predictions/pred_20096_4128_4128_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 9 --out-dir reports/scroll23_evidence/candidate_009 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_009/predictions/pred_20096_4128_4128_64x64_meta.json --out reports/scroll23_evidence/candidate_009/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 010: `pred_29568_7712_7712_64x64`

- Location: Scroll 3 div_90 z=29568 y=7712 x=7712
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_010/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_010/predictions/pred_29568_7712_7712_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_010/predictions/pred_29568_7712_7712_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 10 --out-dir reports/scroll23_evidence/candidate_010 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_010/predictions/pred_29568_7712_7712_64x64_meta.json --out reports/scroll23_evidence/candidate_010/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`

### Candidate 011: `pred_29568_7712_7840_64x64`

- Location: Scroll 3 div_90 z=29568 y=7712 x=7840
- Review score: `2.350000`
- Preflight report: `reports/scroll23_evidence/candidate_011/preflight_report.json`
- Expected prediction image: `reports/scroll23_evidence/candidate_011/predictions/pred_29568_7712_7840_64x64.png`
- Expected prediction metadata: `reports/scroll23_evidence/candidate_011/predictions/pred_29568_7712_7840_64x64_meta.json`
- Evidence command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/run_villa_prize_evidence_chain.py --ranked reports/scroll23_ranked_candidates.tsv --candidate-index 11 --out-dir reports/scroll23_evidence/candidate_011 --execute --checkpoint best_model.pt`
- Validate command: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/validate_prize_artifact.py --metadata reports/scroll23_evidence/candidate_011/predictions/pred_29568_7712_7840_64x64_meta.json --out reports/scroll23_evidence/candidate_011/validation_report.json`
- Review commands: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_crackle_viewer.py; /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python scripts/launch_vc3d.py`
