# Villa Component Coverage

This report maps official `ScrollPrize/villa` components to local Autoresearch hooks.

## Summary

- Total components: `8`
- Covered: `6`
- Partial: `2`
- Blocked by missing required hook: `0`
- Unwired: `0`
- Missing official component: `0`

## Components

| Component | Status | Priority | Prize use | Local hooks | Next action |
| --- | --- | --- | --- | --- | --- |
| vesuvius | `partial` | `high` | Official Python CT/Zarr data access and normalization. | `vesuvius_loader.py` ok, `v3_training/trainer.py` ok, `check_loader.py` missing | Keep loader smoke tests aligned with the pinned Villa data API. |
| ink-detection | `covered` | `high` | Official Grand Prize ink model recipes and optimized inference contracts. | `train.py` ok, `predict.py` ok, `scripts/smoke_test_villa_optimized_inference.py` ok | Keep optimized-inference smoke checks in the post-sprint gate before packaging evidence. |
| crackle-viewer | `covered` | `high` | Human review and labeling of virtually unwrapped ink predictions. | `scripts/launch_crackle_viewer.py` ok, `reports/villa_review_manifest.md` ok | Open GPU-ready candidates from the review manifest for human text-legibility review. |
| volume-cartographer | `covered` | `high` | Maintained Villa path for volume/chunk access, VC3D surface tracing, segmentation, and overlay review. | `volume_cartographer_wrapper` ok, `scripts/build_volume_cartographer_readiness.py` ok, `scripts/launch_vc3d.py` ok, `scripts/validate_prize_artifact.py` ok, `reports/villa_review_manifest.md` ok | Keep Python loading and VC3D overlay validation aligned with Volume Cartographer; do not add new vesuvius-c hooks. |
| lasagna | `covered` | `high` | Surface fitting, tifxyz conversion, and geometry-aware preprocessing. | `scripts/build_lasagna_fiber_worklist.py` ok, `reports/lasagna_fiber_worklist.tsv` ok | Route occupied Scroll 2/3 candidates through Lasagna/fiber preprocessing before more ink inference. |
| segmentation | `partial` | `medium` | Official segmentation models and topology-oriented evaluation metrics. | `test_import.py` missing, `submission_package_dry_run/HALLUCINATION_MITIGATION.md` ok | Keep topology metrics available as hallucination mitigation evidence. |
| foundation | `covered` | `medium` | Dataset management and fiber-label assets. | `scripts/generate_fiber_labels.py` ok | Use fiber assets to expand supervision for hard geometry candidates. |
| thaumato-anakalyptor | `covered` | `medium` | Alternative semi-automatic unwrapping and surface extraction pipeline. | `scripts/launch_thaumato.py` ok, `scripts/autoresearch_thaumato_solver.py` ok | Use as a fallback review route when VC3D/Lasagna surfaces are poor. |
