# Villa PR Closure Recovery Matrix - 2026-05-26

This records the full `ScrollPrize/villa` PR reset for `jonmarrs` and keeps the recovery path narrow. Do not argue on closed PRs. Preserve useful local work, rebuild only the strongest slices from current `ScrollPrize/villa:main`, and reopen only when the evidence is stronger than the original submission.

## Verified State

GitHub check on 2026-05-26: every `ScrollPrize/villa` PR authored by `jonmarrs` is closed, none are open, and none are merged.

| PR | Closed | Topic | Recovery decision |
| --- | --- | --- | --- |
| #899 | 2026-05-26 00:02 PT | Primus optimized-inference loader | Fresh Sprint 037 replacement only after real Docker container execution works and the Primus Docker smoke passes end to end. |
| #901 | 2026-05-26 00:02 PT | Vesuvius Autoresearch community listing | Fresh Sprint 038 listing only after Sprint 037 has credible evidence; do not cite closed PRs. |
| #910 | 2026-05-26 00:02 PT | `vesuvius-c` Python bindings community listing | Do not replace as `vesuvius-c`; fold into Sprint 034 / Volume Cartographer-aligned data-access evidence. |
| #913 | 2026-05-26 00:02 PT | `SpatialTransform` CUDA/CPU device mismatch | Keep local if useful; fresh upstream PR only if current `main` still reproduces the issue with a clean human-written repro/test. |
| #914 | 2026-05-23 06:53 PT | `vesuvius-c` `file://` download fix | Obsolete with `vesuvius-c`; convert the requirement into local/offline Volume Cartographer-backed access tests. |
| #915 | 2026-05-23 06:50 PT | Fibers CuPy acceleration | Highest technical recovery candidate, but only after tiled/halo production-scale evidence and focused clean tests. |
| #916 | 2026-05-23 06:53 PT | `vesuvius-c` Python ctypes bindings | Obsolete with `vesuvius-c`; do not revive. |
| #922 | 2026-05-19 13:04 PT | CT fiber pseudo-label generation | Useful sketch; needs production-scale tiled execution, real-scroll contact sheets, and calibration before replacement. |
| #923 | 2026-05-19 13:03 PT | CT 3D ink pseudo-label generation | Useful sketch; needs real-data calibration and failure-case review before replacement. |

## Recovery Order

1. **Unblock Docker for Sprint 037.** This is still host-level, not Villa code. The current VM can pull images but cannot execute containers: `runc` fails mounting `devpts` with `gid=5`, and `newuidmap/newgidmap` are missing. Use `ink-detection/optimized_inference/PR899_DOCKER_HOST_FIX.md`, then rerun the Primus Docker smoke.
2. **Rebuild #899 as a fresh current-main PR.** Carry over only the minimal Primus loader/dependency/test pieces, remove generated-content footers, write the PR body in human review language, and include the passing Docker smoke evidence.
3. **Recover #915 separately.** The best non-Docker technical candidate is the fibers work, but the replacement has to lead with the old cuSolver failure, closed-form eigensolver evidence, tiled `384^3+` behavior, and focused tests.
4. **Fold `vesuvius-c` work into Volume Cartographer.** Do not submit new `vesuvius-c` PRs or listings. Prove equivalent local/offline access through `volume_cartographer_wrapper` and VC3D-compatible outputs.
5. **Treat #922/#923 as research prototypes.** Keep the ideas, but do not reopen until thresholds are calibrated against real labels or maintainer-provided ground truth.

## Do Not Do

- Do not comment on the closed PRs unless there is a fresh replacement PR or concrete evidence artifact to link.
- Do not reopen or repost #901/#910 listings.
- Do not present #913/#914 as shipped upstream work in prize docs or community posts.
- Do not rerun the full CUDA Docker smoke on this VM until `docker run hello-world` succeeds.
