# Repository audit and remaining decisions

Audited from parent commit `cc9dda42acdacaea39769ea56d0e8edd29d630b3`, with
Villa pinned to `ccb431818fa68059138f2c964ae299fc474ff116`.

This is a repository-wide inventory and automated scan, with focused manual
review of the training, inference, data, artifact-publication, developer and
proofreading workflows. It is not a claim that every line of research code,
every historical result or every possible defect has been independently verified.
No study data, model scores, frozen upstream sources or running research state
were changed. No new GPU experiment was run.

## Coverage

The starting tree contains 3,227 tracked files: 999 Python files (213,528 lines),
158 shell scripts, 444 JSON files and nine YAML files, plus documentation,
images, patches and other artifacts. All tracked Python files parsed, all shell
scripts passed `bash -n`, and all JSON/YAML files parsed with their respective
loaders. Bash syntax checking does not establish POSIX-sh compatibility or
shell runtime correctness. Python's JSON loader accepts nonstandard NaN tokens;
the separate finite-value scan found four historical files containing them.

Mypy initially reported `Success: no issues found in 943 source files`. Its
configuration disables several error categories and ignores missing third-party
imports; this is useful coverage, not proof of type safety. Ruff initially
reported 95 findings: 66 in byte-preserved Villa sources, 18 in the retained
GP-winner reproductions and 11 elsewhere. The preserved sources must not be
reformatted just to obtain a green global lint result.

The curated runner originally selected 197 of 449 test modules. The two new
regression modules are now registered. Historical report/data tests outside that
registry were also attempted; their missing inputs and checkout-history
requirements are recorded below. Verification results and exact commands are
in the final section.

## Fixed in this change

| Problem | Evidence and resulting behavior |
| --- | --- |
| Regional inference could destroy inputs or corrupt its own artifacts. | Four new regressions initially failed: both single and ensemble commands accepted a checkpoint or the ink NPY as `--metadata_out`, then replaced it with JSON. Shared planning now protects checkpoints, the CT group and selected array, and the complete output family. It rejects path/inode/ancestor aliases and unsafe existing entries before inference and rechecks before invalidating old metadata. |
| Unrecordable checkpoint settings failed only after outputs had been replaced. | A NaN or set in an otherwise usable checkpoint configuration now fails finite-JSON preflight. The new tests require no inference or filesystem changes in these cases. |
| The proofreader launcher did not match pinned Villa. | It supplied `[16, 64, 64]` where Villa expects one integer cubic patch edge, inherited Villa's z=2500 default, looked up Villa relative to the caller's directory, overwrote a fixed config file and swallowed child failures. It now uses an explicit scalar edge, z=0, checkout-relative launch, a temporary config and the child exit code. Metadata-only checks reject mismatched 3D shapes, floating-point labels, oversized patches, overlapping output paths and nonempty previous sessions. These checks do not prove physical registration. |
| Developer checks depended on undeclared tools. | The default locked dev group now declares pytest, Ruff and Mypy; the existing no-sync Mypy hook can use the project tool. The augmentation pipeline's missing `fft-conv-pytorch` dependency is now declared; Numba and jsonschema are explicit rather than only transitive. Existing runtime package versions were retained. A launcher test now uses the active Python instead of assuming a checkout-local `.venv`. `make validate` and `make test-all` make the distinction from the existing smoke alias visible. |
| An unused partial-loading helper and stale documentation contradicted current inference/training. | Removed the prediction module's uncalled `load_compatible_state_dict` and its helper-only test; real inference continues to require strict weights. Corrected the pseudo-label docstring that still claimed PNG 128 had residual BCE/Dice weight. Regional CLI help now accurately requests a local volume. |

Path checks are snapshots, not locks. Regional publication remains a sequence of
writes with metadata last; interruption can leave incomplete outputs without a
success sidecar. No multi-writer or power-loss guarantee is added.

## Items for owner review

The priority below is the suggested work order, not a claim that each item has
caused a measured scientific failure.

| Priority | Finding and source | Recommended decision / next check |
| --- | --- | --- |
| High | **GitHub reports an untriaged dependency-security backlog.** The push notification reported 149 alerts on the default branch: 6 critical, 57 high, 59 moderate and 27 low ([Dependabot dashboard](https://github.com/jonmarrs/vesuvius-autoresearch/security/dependabot)). The available GitHub integration returned HTTP 403 when listing the alerts. | Review individual advisories, affected manifests, reachable workflows and available fixes with an account that can read security alerts. Prioritize confirmed applicable critical/high findings. The notification counts do not establish which pinned runtime packages need upgrades; no blanket dependency update was applied. |
| High | **The human-feedback loop is incomplete.** Regional uncertainty is a one-plane window diagnostic with a source offset; the proofreader expects aligned volumetric categorical labels, and approved TIFF patches are not automatically consumed by ink training. See [checkpoint/labeling workflow](CHECKPOINT_ANALYSIS.md), [launcher](../scripts/launch_proofreader.py) and [training inputs](../scripts/training/input_paths.py). | Choose whether this should review 2D ink windows or 3D segmentation labels. Then specify coordinate transforms, label semantics and a reviewed-patch ingestion contract. Do not broadcast a window mask through CT depth or interpret entropy as an ink label. Existing-session resume also needs a source-bound progress manifest before this wrapper can support it safely. |
| High | **The alternate v3 trainer has drifted from the maintained training contract.** [trainer](../v3_training/trainer.py) uses `from train import apply_augmentations`, mixes a labeled dataset returning three elements with an unlabeled dataset returning two, and its custom loops have their own teacher/loss/checkpoint behavior. The maintained implementation is [training/train.py](../scripts/training/train.py). | Retire the v3 entry point, or fund a dedicated port with actual training tests. Fixing tuple unpacking alone would not validate its SSL/UA-MT method, so this audit does not present it as repaired. Its prior sprint board is already marked archived. |
| High | **Training-data onboarding is incomplete.** The [quick start](../README.md) expects fragment CT Zarrs and aligned labels, but explicitly states that no maintained command builds those directories. Archived downloaders fetch different inputs. | Choose a supported source/format and add a pinned download/conversion manifest plus one small verified example. Do not revive placeholder-producing archival downloaders as though they prepared the training recipe. |
| High | **A clean checkout cannot run every research test successfully.** Some probe tests require the original private spiral corpus; render-equivalence and preserved-source tests require old Villa commit objects absent from a shallow pinned checkout. See [real-patch tests](../tests/test_probe_real_patch_scatter.py), [render-equivalence tests](../tests/test_check_render_equivalence.py) and [preserved-source tests](../tests/test_villa_preserved.py). | Decide which tests are portable unit tests and which are corpus/history integration checks. Add explicit fixtures/markers and a documented provision step without weakening their scientific assertions. Missing real data is not evidence that the underlying claims pass. |
| Medium | **Regional memory scales with the whole region.** [single](../scripts/inference/predict.py) and [ensemble](../scripts/inference/ensemble_predict.py) allocate full-region GPU accumulators; [region_tiles](../src/vesuvius_autoresearch/core/inference.py) materializes the tile list, and ensemble members are all resident together. Skipping uncertainty also skips that export's size budget. | Select a RAM/VRAM planning contract or tile-streaming design, then profile on the 4090. The existing [production path](../scripts/production_predict.py) is a useful batched alternative, but no full-scroll peak-memory or throughput result was measured here. |
| Medium | **The installed package relies on checkout-only modules.** Package discovery includes `src/`, while model construction imports root `vesuvius_model`, volume access uses `volume_cartographer_wrapper`, and several public commands live under `scripts/`. See [package configuration](../pyproject.toml) and [model factory](../src/vesuvius_autoresearch/core/model_wrappers.py). | Decide whether the supported product is an editable research checkout or a standalone wheel. If wheel support is wanted, package those dependencies and add a clean-directory installation test. Do not assume that an editable-import pass validates a wheel. |
| Medium | **Four historical JSON artifacts contain 30 nonfinite tokens.** [old queue](../reports/active_learning_queue.json) has 20 NaN uncertainty scores; [old detector card](../reports/detector/PHercParis2Fr143_scorecard.json), [interpolation result](../reports/interp_vs_labels.json) and [tracking-gap result](../reports/scorer_tracking_gap_descriptive.json) contain the others. | Keep these as historical evidence with explicit status, or regenerate into new versioned artifacts from retained inputs. Do not turn missing/undefined measurements into zeros or rewrite the old scores to make JSON valid. The old queue is not a usable ranking. |
| Medium | **Fresh scientific validation is still needed after earlier correctness changes.** The [surface-renderer guide](SURFACE_RENDERER.md) and [confidence-analysis guide](CONFIDENCE_REPRODUCIBILITY.md) describe changed contracts and historical limits. Unit tests do not rerun those real-data comparisons. | Prioritize one source-pinned rerun before using a historical number to justify a new research direction. Preserve the original artifacts and publish the new contract/version separately. |
| Medium | **The research plan mixes a dated snapshot with later progress.** [strategy](RESEARCH_STRATEGY.md) still ranks feedback on #2141/#2259 as pending in its October 28 snapshot; the [second filed response](PRIZE_FILING_2026-10_SECOND_SUBMITTED.md) records their October 30 merges. Later research updates do not rewrite that ranked table. | Refresh current action items and upstream states as one owner-facing plan while preserving filed text and historical observations. This audit does not claim current upstream adoption from internal PR counts. |
| Lower | **Dependency and archive maintenance need a scope decision.** The default environment includes CUDA, notebook and broad research dependencies; several declared packages have no obvious first-party import, but retained upstream workflows may need them. Ruff also reports the reproduction/style backlog counted above. | Inventory actual supported commands before splitting CPU/GPU/research extras or removing dependencies. Keep byte-preserved sources and measured reproduction scripts distinct from maintained code. Do not bulk-delete reports, `sprint_logs/`, `scripts/archive/` or reproductions solely because they are not imported. |
| Lower | **No checked-in CI workflow enforces the checks.** `.github/` contains review/report templates but no workflow. | Choose a bounded CPU CI job and a separate opt-in data/GPU integration job. Set runtime/storage budgets before enabling broad historical tests on every push. |

## Verification record

Validation uses Python 3.10.21 and Torch 2.9.1 CPU in the isolated review
environment. Scientific training inputs and a GPU were unavailable. The local
review environment initially lacked some locked dependencies, and its AWS SDK
versions differed from the lock; those were corrected before the curated rerun.
Socket-based checks needed network-capable sandbox execution even though the
SDK tests stub the service and no live S3 test was opted into.

The complete 199-module curated run finished with
`6 failed, 5307 passed, 41 skipped, 1 xfailed` in 665.71 seconds. Four failures
were missing review-environment jsonschema/imagecodecs, one exposed the missing
augmentation dependency chain, and one exposed a test hardcoding
`.venv/bin/python`. That interpreter assumption and the undeclared FFT package
were fixed; the failing modules were rerun after installing their locked
requirements. The final recheck results are recorded below.

The 252 outside-registry modules were attempted separately, with an interrupted
run reporting `37 failed, 2098 passed, 104 skipped`. The failures require missing
local measurements or old Git revisions. The remaining research modules ran as
`1 failed, 271 passed, 5 skipped` (the additional failure was the absent
preserved-source commit), and the registration selection passed `33 passed`.
These are partial/split runs and must not be described as one passing full
research suite.

The changed-workflow selection passed `368 passed` in 100.59 seconds across
nine curated modules. Mypy passed on 948 source files. The documentation guards
passed `138 passed, 1 skipped` (the skip needs the original spiral corpus).
Ruff passed on the changed Python files. The final failed-module recheck passed
`209 passed` in 39.40 seconds; smoke passed `9/11 passed, 2 skipped, 0 failed`
in 19.4 seconds. Its two skips need local training CT/ink labels. All six failures
from the completed curated run are resolved, but the whole suite was not repeated
after these fixes. No GPU, GUI interaction, full-scroll throughput, standalone
wheel installation or missing-corpus/historical-commit integration was verified.

Commands used for the completed curated run and final workflow checks (the
absolute interpreter/cache paths identify the review environment):

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py -- --tb=short -o faulthandler_timeout=90

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py --match '*regional_artifact_plan*' --match '*proofreader_launcher*' --match '*volume_inference_contracts*' --match '*uncertainty_handoff*' --match '*predict_checkpoint_loading*' --match '*production_artifact_plan*' --match '*candidate_ranking_contracts*' --match '*ranked_inference_planning*' --match '*validation_runner*' -- --tb=short

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_geometry_handoff_contracts.py tests/test_interpolation_drivers.py tests/test_autoresearch_measurement.py -q --tb=short

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/smoke_test.py

/workspace/.vesuvius-review-env/bin/python -m mypy . --explicit-package-bases --namespace-packages --python-executable /workspace/.vesuvius-review-env/bin/python

env UV_CACHE_DIR=/workspace/.vesuvius-review-cache/uv uv lock --check --offline --python /workspace/.vesuvius-review-env/bin/python
```

Interpretation: path/metadata preservation and launcher behavior have regression
coverage; resolved integration/dependency failures were rerun; smoke exercised
both augmentation backends and loaded all 288 checkpoint tensors. The lock check
passed, with no pre-existing package version/source changes. These checks do not
supply the missing real-data evidence identified in the review table.
