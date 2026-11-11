# Repository audit and remaining decisions

The first pass started at `cc9dda42acdacaea39769ea56d0e8edd29d630b3`. The
follow-up includes main `f00cfc45` (the accepted November strategy and canvas
registration work). Villa remains pinned to
`ccb431818fa68059138f2c964ae299fc474ff116`.

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
| Developer checks depended on undeclared tools. | The default locked dev group now declares pytest, Ruff and Mypy; the existing no-sync Mypy hook can use the project tool. The augmentation pipeline's missing `fft-conv-pytorch` dependency is now declared; Numba and jsonschema are explicit rather than only transitive. These declarations retained existing runtime versions; the separate Lightning patch is recorded below. A launcher test now uses the active Python instead of assuming a checkout-local `.venv`. `make validate` and `make test-all` make the distinction from the existing smoke alias visible. |
| An unused partial-loading helper and stale documentation contradicted current inference/training. | Removed the prediction module's uncalled `load_compatible_state_dict` and its helper-only test; real inference continues to require strict weights. Corrected the pseudo-label docstring that still claimed PNG 128 had residual BCE/Dice weight. Regional CLI help now accurately requests a local volume. |

Path checks are snapshots, not locks. Regional publication remains a sequence of
writes with metadata last; interruption can leave incomplete outputs without a
success sidecar. No multi-writer or power-loss guarantee is added.

## Follow-up fixes against current main

- **Canvas publication:** the new correction CLI could replace either input,
  follow output links, leave a partial previous result after a write failure,
  or write `corrected.NPY.npy` when asked for `corrected.NPY`. Four input-alias
  cases, a failed-write case and the uppercase-filename case reproduced these
  defects. It now validates input/output separation before measurement and
  publication and stages encoded output before replacing an existing result.
  It preserves replacement permissions and returns the documented error status
  on encoding/storage failures. Direct and module launches use this checkout's
  helper modules when another editable checkout is on the import path.
- **Canvas value integrity:** nearest-neighbor warp and resize converted 64-bit
  categorical IDs through float64, changing IDs above 2^53. Linear interpolation
  could also wrap a saturated int64/uint64 value to the opposite endpoint.
  Categorical gathering now retains the original integer dtype and linear
  conversion assigns saturated endpoints before casting. Geometry is compared
  with OpenCV, including fractional offsets and zero-filled boundaries. Complex
  and nonnumeric input planes are rejected rather than cast to real intensities.
- **Tile planning:** regional inference now returns a sized lazy sequence,
  preserving row-major order, interleaved shards, indexing and slicing. The
  61,009-tile fixture allocated 5,489,925 traced bytes before this fix; a fresh
  measurement with the correct checkout allocated 1,012 bytes afterward.
  Production dry-run and regional planning share the same axis-count formula.
  These figures concern Python tile planning, not model or GPU peak memory.
- **Dependency patch:** PyTorch Lightning 2.6.1 was updated to 2.6.6, removing
  advisory `PYSEC-2026-3967` from the root lock's PyPI lookup. The other existing
  package versions were retained. The [dependency audit](../reports/dependency_audit.json)
  records the remaining versions, advisory IDs, aliases and known fixes; counts
  are advisory records and can include duplicates, not distinct exploitable bugs.
- **Operational messages and cleanup:** a forced exclusivity-guard override
  now reports that Villa jobs are still running. Removed the unreferenced
  [legacy augmentation wrapper](https://github.com/jonmarrs/vesuvius-autoresearch/blob/6320a32f818caa61dd1d67ecd07c617b09c73c13/scripts/training/vesuvius_augmentations.py), which could silently
  substitute an identity transform. The maintained augmentation path remains in
  `scripts/training/train.py`. Fixed eleven non-preserved Ruff findings; the
  remaining 84 are in preserved Villa or retained GP-winner reproductions. The
  native-retry record guard still verifies the same source URL and supports
  both dictionary spellings instead of depending on formatting.
- **Lifecycle regression stability:** the repeated-stop test used a two-second
  child write deadline, so suite scheduling delays could let the child write
  before either stop. It now gates the write on actual loop settlement and
  still requires the process to be dead at settlement. Supervisor behavior
  was unchanged.

Main's accepted November strategy resolves the previous audit's stale-strategy
item. This is an upstream change included in the follow-up, not a newly measured
research result. Historical scientific artifacts and frozen Villa files were
kept unchanged.

## Labeling and registration follow-up

This pass continues from `41f55bf7`, on the same audit branch.

- **Prediction-to-label handoff:** inference writes `REGION_meta.json` beside
  `REGION_ink.zarr`, but the label generator looked only for
  `REGION_ink_meta.json`. Real producer fixtures reproduced acceptance of partial
  prediction records and failure to record complete ones. The generator now
  checks the canonical and legacy sidecars plus any explicitly selected record.
  Contradictory or broken sidecars fail; recognized producer outputs require a
  run sidecar, including after interrupted publication. Bare external map names
  retain their documented caller-declared contract. Valid local file URIs are
  normalized for source comparison, and all checked records are retained in label
  provenance. These checks do not attest pixel contents or physical registration.
- **Prediction input preflight:** incorrect shape or unsupported dtype could be
  discovered after loading CT and the prediction. Metadata-only fixtures with
  100,000-by-100,000 prediction planes now reject before either payload is read.
  The labeling algorithm and intensity gates for supported inputs are unchanged.
- **Skeleton work outside the cube:** edges wholly outside any cube axis are
  skipped before recursive interpolation. Crossing and boundary-touching fixtures
  retain the existing voxelization. One synthetic 1,000-pixel disjoint edge on a
  3-by-4-by-5 cube allocated 2,571,721 traced Python bytes before culling and 4,073
  afterward, both producing no labeled voxels. This is not a real-data throughput
  or GPU measurement. A later pass below adds a budget for crossing edges.
- **Placement gates:** the standalone tool could return zero offset with a NaN
  score when every evaluation crop lacked foreground, and could report a reduced
  search boundary as an interior peak. Both implementations now reject nonfinite
  inputs and peaks pinned to requested/refinement bounds. The standalone tool
  also enforces coarse/crop checks already present in the registration gate, and
  uses the gate's nearest-neighbor resize lattice for odd dimensions. The gate's
  existing OpenCV sampling is retained. Unsupported search geometry is named;
  the standalone CLI returns status 2 without a score when placement is unknown.
  The gate's deliberate `strict=False` diagnostic boundary behavior remains.
  Existing historical placements were not remeasured.
- **Portable regression coverage:** the retirement inverse test now uses a
  sentinel fetch instead of slow live requests for a nonexistent segment. The
  handoff, standalone placement, implementation-parity and synthetic registration
  modules are included in the curated registry. With the later frame checks
  below it contained 207 modules; the CLI retirement checks bring the current
  registry to 208.

## Numeric diagnostics and skeleton resource limits

This pass continues from `5a6870a8` and resolves two entries from the review list.

- **Frame diagnostics:** oversized voxel-size strings could parse as infinity,
  optional bbox metadata could retain NaN/Infinity, and an oversized optional
  scale could raise instead of being omitted. Bbox squaring also overflowed for
  large but representable diagonals. Parsed voxel sizes now require finite
  positive values; optional invalid values are omitted, and `math.hypot` avoids
  intermediate square overflow. Output uses strict JSON. Unrepresentable derived
  ratios return an error status without a partial report, in both output modes.
  Ten regressions failed before these changes; all 47 frame-tool tests pass.
- **Crossing skeleton edges:** the previous disjoint-edge culling did not bound
  a long edge passing through the cube. Each edge now has an explicit
  `max_edge_samples` limit, default 65,537. A geometric preflight rejects clearly
  over-budget edges with ordinary pixel precision before recursive sampling,
  while an exact interval counter handles shallow recursion limits, coarse
  floating-point spacing and norm underflow. Exceeding the
  limit fails the whole run before label publication. No edge is silently
  omitted or sampled at a different spacing. Plans and label metadata record
  the limit; the CLI passes it through the process pool.
- **Compatibility:** 32 sample sequences and 32 voxel grids matched the parent
  commit exactly on synthetic edges within the default budget. Golden dyadic
  samples, recursion-limit boundaries and a real-SDK CLI refusal also have
  regression coverage. These checks do not establish real-data annotation
  quality or a total worker/volume memory bound.

## Archived launchers and portable CI

This pass continues from `c45acbec` and resolves two more review-list entries.

- **Retired v3 CLI:** both `v3_training/run_v3.py` and
  `v3_training/trainer.py` now explain the maintained training command and refuse
  execution with status 2 before importing ML packages or reading configuration.
  Direct and module launches, including `--help`, are checked from another
  working directory with import traps and an unchanged dummy configuration.
  The archived class implementation and YAML files remain for reference;
  retiring the CLI does not repair or validate its historical training methods.
  See the [archive contract](../v3_training/README.md).
- **Bounded CPU CI:** the [root workflow](../.github/workflows/cpu.yml) checks
  maintained-source lint and a nine-module portable profile, selected by the
  existing validation runner. The default remains the full curated registry.
  Profile-scoped globs fail if unmatched and cannot silently expand to research
  tests. A fresh Linux/Python 3.10 environment uses a small hashed dependency
  lock, pinned Actions, read-only repository permissions, no submodule checkout
  and explicit installation/test/job time limits. Frozen Villa and GP-winner
  sources retain their lint exclusions. Required-status branch protection and
  opt-in data/GPU jobs remain owner decisions; adding a workflow does not make
  its status a merge requirement.
- **CI dependency scope:** the [CI advisory snapshot](../reports/ci_dependency_audit.json)
  binds the requirements hash and records zero public PyPI advisory records
  across its ten pinned dependencies, with no skipped packages. This does not
  cover bootstrap tools, Actions, OS packages or the GPU research environment.
  The root-lock advisory migrations below remain unresolved.

## Items for owner review

The nine remaining items below are in suggested work order, not a claim that
each has caused a measured scientific failure.

| Priority | Finding and source | Recommended decision / next check |
| --- | --- | --- |
| High | **Dependency advisories still need migrations and applicability review.** GitHub reported 149 alerts on the default branch (6 critical), but its advisory API returned HTTP 403. The public [root-lock audit](../reports/dependency_audit.json) now identifies 197 raw advisory records across eight remaining packages. A separate lookup for upstream Torch 2.9.1 found five candidate records; the CUDA-suffixed wheel was not directly audited. | Prioritize applicable advisories by the recorded IDs. aiohttp/dotenv updates require a WEBKNOSSOS/cluster-tools major upgrade; the scratch resolution was discarded. Windows additionally has a tensorstore constraint conflict. Review those migrations, the remaining major library updates, and advisories without a known fix using appropriate CPU/GPU/native validation. Public advisory matching does not establish reachability or replace GitHub alert access. |
| High | **The human-feedback loop is incomplete.** Regional uncertainty is a one-plane window diagnostic with a source offset; the proofreader expects aligned volumetric categorical labels, and approved TIFF patches are not automatically consumed by ink training. See [checkpoint/labeling workflow](CHECKPOINT_ANALYSIS.md), [launcher](../scripts/launch_proofreader.py) and [training inputs](../scripts/training/input_paths.py). | Choose whether this should review 2D ink windows or 3D segmentation labels. Then specify coordinate transforms, label semantics and a reviewed-patch ingestion contract. Do not broadcast a window mask through CT depth or interpret entropy as an ink label. Existing-session resume also needs a source-bound progress manifest before this wrapper can support it safely. |
| High | **Training-data onboarding is incomplete.** The [quick start](../README.md) expects fragment CT Zarrs and aligned labels, but explicitly states that no maintained command builds those directories. Archived downloaders fetch different inputs. | Choose a supported source/format and add a pinned download/conversion manifest plus one small verified example. Do not revive placeholder-producing archival downloaders as though they prepared the training recipe. |
| High | **A clean checkout cannot run every research test successfully.** Some probe tests require the original private spiral corpus; render-equivalence and preserved-source tests require old Villa commit objects absent from a shallow pinned checkout. See [real-patch tests](../tests/test_probe_real_patch_scatter.py), [render-equivalence tests](../tests/test_check_render_equivalence.py) and [preserved-source tests](../tests/test_villa_preserved.py). | Decide which tests are portable unit tests and which are corpus/history integration checks. Add explicit fixtures/markers and a documented provision step without weakening their scientific assertions. Missing real data is not evidence that the underlying claims pass. |
| Medium | **Regional GPU memory still scales with the whole region.** [Single](../scripts/inference/predict.py) and [ensemble](../scripts/inference/ensemble_predict.py) allocate full-region GPU accumulators and keep ensemble members resident together. CPU tile enumeration is now lazy, but skipping uncertainty still skips that export's size budget. | Select a RAM/VRAM planning contract or accumulator-streaming design, then profile on the 4090. The [production path](../scripts/production_predict.py) is a batched alternative; no full-scroll peak-memory or throughput result was measured here. |
| Medium | **The installed package relies on checkout-only modules.** Package discovery includes `src/`, while model construction imports root `vesuvius_model`, volume access uses `volume_cartographer_wrapper`, and several public commands live under `scripts/`. See [package configuration](../pyproject.toml) and [model factory](../src/vesuvius_autoresearch/core/model_wrappers.py). | Decide whether the supported product is an editable research checkout or a standalone wheel. If wheel support is wanted, package those dependencies and add a clean-directory installation test. Do not assume that an editable-import pass validates a wheel. |
| Medium | **Four historical JSON artifacts contain 30 nonfinite tokens.** [old queue](../reports/active_learning_queue.json) has 20 NaN uncertainty scores; [old detector card](../reports/detector/PHercParis2Fr143_scorecard.json), [interpolation result](../reports/interp_vs_labels.json) and [tracking-gap result](../reports/scorer_tracking_gap_descriptive.json) contain the others. | Keep these as historical evidence with explicit status, or regenerate into new versioned artifacts from retained inputs. Do not turn missing/undefined measurements into zeros or rewrite the old scores to make JSON valid. The old queue is not a usable ranking. |
| Medium | **Fresh scientific validation is still needed after earlier correctness changes.** The [surface-renderer guide](SURFACE_RENDERER.md) and [confidence-analysis guide](CONFIDENCE_REPRODUCIBILITY.md) describe changed contracts and historical limits. Placement gates now decline additional boundary-limited results. Unit tests do not rerun those real-data comparisons. | Prioritize one source-pinned rerun before using a historical number or placement record to justify a new research direction. Preserve the original artifacts and publish the new contract/version separately. |
| Lower | **Dependency and archive maintenance need a scope decision.** The default environment includes CUDA, notebook and broad research dependencies. The maintained Ruff findings are fixed; preserved/upstream reproductions retain their historical lint backlog. The root demo/evidence generators still use direct GPU imports and fixed output locations. | Inventory supported commands before splitting CPU/GPU/research extras. Decide whether to retain, port or archive the two root generators. Review upstream synchronization/releases for the placement-check and scroll-frames subtree fixes, required-status branch protection for the new CPU job, and opt-in data/GPU CI provisioning. Keep byte-preserved sources and measured reproduction scripts distinct from maintained code; do not bulk-delete reports, logs or reproductions solely because they are not imported. |

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

## Follow-up validation

The earlier verification section describes the first pass. Against current
main, the full **202-module curated suite** completed with
`2 failed, 5402 passed, 41 skipped, 1 xfailed` in 847.32 seconds. One failure
was the wall-clock lifecycle assertion described above. The other was the
temporary-file mode guard reading the deleted wrapper from `git ls-files`
before its deletion was staged; the final index resolves that mismatch.

The final six-module recheck passed `126 passed` in 33.43 seconds, covering
both failed modules, canvas publication/value contracts, lazy tiles, the
exclusive guard message and the retry record guard. After the lifecycle
assertion was changed, its entire module also passed `38 passed` in 20.23 seconds,
and the repeated-stop case passed ten separate isolated runs.
All failures from the completed curated run are resolved; the whole suite
was not repeated after these final changes. A separate six-module workflow
selection passed `269 passed` in 39.95 seconds. Results from overlapping runs
are not additive.

Smoke passed `9/11 passed, 2 skipped, 0 failed` in 17.3 seconds and loaded all
288 checkpoint tensors; the skips still require local CT/ink labels. The
documentation guard selection passed `138 passed, 1 skipped` in 74.58 seconds.
The skipped guard needs the original spiral corpus.

Configured Mypy passed on 952 source files. Ruff check and format passed on all
27 changed Python files. The whole-repository Ruff scan has 84 findings, all in
the preserved Villa and retained GP-winner reproductions. The offline lock
consistency check passed (255 packages); Lightning is the only pre-existing
package whose version changed. The advisory report's lock hash and record
totals were checked against the final lock and report contents.

Exact commands for the full run and final failed-module/workflow recheck:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py -- --tb=short -o faulthandler_timeout=90

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_loop_lifecycle.py tests/test_file_modes.py tests/test_canvas_artifact_contracts.py tests/test_region_tile_iteration.py tests/test_guard_heavy_analysis.py tests/test_check_retry_cycle.py -q --tb=short

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_loop_lifecycle.py -q --tb=short
```

The [advisory report](../reports/dependency_audit.json) is a dated public PyPI
lookup of the exported non-dev root lock on Linux/Python 3.10. The before/after
raw advisory record counts were 198 and 197 after the Lightning patch. Neither
those counts nor the supplementary Torch lookup establish exploitability.
The lookup used `pip-audit 2.10.1`; export and audit commands were:

```sh
env UV_CACHE_DIR=/workspace/.vesuvius-review-cache/uv UV_PYTHON_INSTALL_DIR=/workspace/.vesuvius-review-python uv export --python /workspace/.vesuvius-review-env/bin/python --locked --no-dev --no-hashes --no-emit-project --format requirements-txt --output-file /tmp/vesuvius-audit-runtime-requirements-after.txt

env UV_CACHE_DIR=/workspace/.vesuvius-review-cache/uv UV_PYTHON_INSTALL_DIR=/workspace/.vesuvius-review-python UV_TOOL_DIR=/workspace/.vesuvius-review-cache/tools uv tool run --python /workspace/.vesuvius-review-env/bin/python --from pip-audit pip-audit --cache-dir /workspace/.vesuvius-review-cache/pip-audit -r /tmp/vesuvius-audit-runtime-requirements-after.txt --no-deps --disable-pip --progress-spinner off --timeout 15 --format json --output /tmp/vesuvius-pip-audit-after.json
```

The audit command returned status 1 because advisory records remain; this is
not a passing security check.
The GPU, missing data/history, GUI, wheel and real-data limitations above
still apply.

## Labeling and registration verification

The final curated selection covers ten of the 206 registered modules and passed
`320 passed, 10 skipped` in 19.12 seconds. The skips are the optional WebKnossos
checks in the base review environment. A separate SDK run using WebKnossos 3.4.1
and lock-constrained dependencies passed the entire fiber-label module:
`67 passed` in 11.67 seconds, including those ten checks. An additional isolated
retirement regression run passed `4 passed` in 0.91 seconds. These overlapping
counts are not additive.

The SDK dependencies were installed in a separate temporary directory. Combining
that directory with the base review environment's newer Pydantic caused an
import-time typing-extensions conflict, so the base and SDK checks were run
separately. This does not constitute validation of a complete GPU lock install.

Configured Mypy passed on 953 source files; Ruff check and format passed on all
ten Python files changed in this pass. Smoke passed
`9/11 passed, 2 skipped, 0 failed` in 13.0 seconds. Its skips still require local
CT/ink labels. The full curated suite was not repeated for this pass. GPU,
real-data placement remeasurement and standalone upstream publication remain
outside the verified scope.

The final documentation guards passed `138 passed, 1 skipped` in 30.80 seconds
(the skip requires the original spiral corpus). File-mode guards passed
`11 passed` in 3.45 seconds. Ruff check and format also passed across all 36
Python files in the cumulative PR.

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py --match '*volumetric_label_contracts*' --match '*pseudo_label_prediction_handoff*' --match '*fiber_label_generation*' --match '*label_edit_proposals*' --match '*placement*' --match '*sota_register.py' --match '*sota_registration_gates*' --match '*sota_gt_register*' --match '*validation_runner*' -- --tb=short -o faulthandler_timeout=90

env PYTHONPATH=src:/tmp/vesuvius-review-sdk OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_fiber_label_generation.py -q -rs --tb=short

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /workspace/.vesuvius-review-env/bin/python -m pytest tools/placement_check/test_placement_check.py tests/test_placement_impl_parity.py tests/test_sota_register.py tests/test_sota_registration_gates.py tests/test_sota_gt_register.py tests/test_retirement_shared.py -q --tb=short
```

The last command passed `92 passed` in 18.81 seconds. All scientific fixtures in
these new regression checks are synthetic; no eligible scroll imagery or
research measurement was produced or published.

## Numeric and resource-limit verification

The final six-module curated selection passed `292 passed, 11 skipped` in 8.10 seconds.
The eleven optional SDK checks in the base environment were covered separately:
the complete fiber-label module passed `81 passed` in 10.06 seconds using the
lock-constrained WebKnossos SDK directory. Counts overlap and are not additive.
The new frame suite passed all 47 tests, including ten cases that failed before
the numeric fixes. The sample-budget regressions initially reported ten failures
and one SDK-dependent skip before implementation.

Author review also reproduced three false rejections in the first geometric
preflight: adjacent large float64/float32 coordinates and a tiny custom-step
case whose legacy norm underflows. The fast estimate now applies only to
ordinary pixel precision and uses a conservative margin. All other cases use
the exact counter, preserving those within-budget legacy samples without
removing the hard limit. The final counts above include the three regressions.

Configured Mypy passed on 953 source files, and Ruff check/format passed on all
38 Python files in the cumulative PR. Smoke passed
`9/11 passed, 2 skipped, 0 failed` in 10.3 seconds; the skipped dataloader checks
need local CT/ink labels. The full 207-module curated registry was not rerun.
GPU, Windows process pools, real-data label quality and independent upstream
releases remain unverified.

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py --match '*scroll_frames*' --match '*fiber_label_generation*' --match '*label_edit_proposals*' --match '*volumetric_label_contracts*' --match '*pseudo_label_prediction_handoff*' --match '*validation_runner*' -- --tb=short -o faulthandler_timeout=90

env PYTHONPATH=src:/tmp/vesuvius-review-sdk OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_fiber_label_generation.py -q -rs --tb=short

/workspace/.vesuvius-review-env/bin/python -m pytest tools/scroll_frames/test_scroll_frames.py -q --tb=short
```

The differential check compiled only `_interpolate_adaptive` and
`_fill_volume_for_tree` from parent `5a6870a8`, with NumPy in their namespace. For
32 endpoint pairs from `default_rng(17).uniform(-3, 8, (2, 3))`, both the sample
sequences and 3-by-4-by-5 voxel grids matched the current implementation exactly.
This check uses synthetic geometry and does not replace a corpus measurement.

The final documentation guard selection passed `138 passed, 1 skipped` in 33.03
seconds (the skip needs the original spiral corpus). File-mode guards passed
`11 passed` in 3.90 seconds, and `git diff --check` passed.

## Portable CI and retirement verification

The new launcher/profile regression selection passed `44 passed` in 2.00
seconds, after initially reproducing eleven failures. A separate source
snapshot, without Villa's checkout or research data, installed only the ten
hashed CI dependencies into a new Python 3.10 environment. The portable profile
passed `234 passed` in 24.06 seconds with plugin autoload disabled and no skips.
Torch, CuPy, SciPy, Zarr and the Villa package were absent. Maintained-source
lint also passed there. This local run exercises the workflow commands; it is
not evidence of a completed hosted GitHub run.

`actionlint 1.7.12` accepted the workflow. Configured Mypy passed on 955 source
files. Inventory/coverage checks passed `19 passed` in 35.41 seconds, file-mode
guards passed `11 passed` in 29.95 seconds, and smoke passed
`9/11 passed, 2 skipped, 0 failed` in 15.1 seconds. The smoke skips still require
local CT/ink labels. The full 208-module curated registry was not repeated.
No training, GPU, corpus or historical-method claim follows from these checks.
The documentation guard selection passed `138 passed, 1 skipped` in 30.53
seconds; that skip still requires the original spiral corpus. Ruff format
accepted all 42 Python files in the cumulative PR, and `git diff --check` passed.

Reproduction commands for the isolated snapshot and the profile regressions:

```sh
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/vesuvius-portable-ci-env/bin/python scripts/run_validation_tests.py --profile portable -- --tb=short --maxfail=1 -o faulthandler_timeout=60

/tmp/vesuvius-portable-ci-env/bin/ruff check . --extend-exclude repro/villa_preserved,repro/gp_winner

/workspace/.vesuvius-review-env/bin/python -m pytest tests/test_v3_retirement.py tests/test_validation_runner.py -q --tb=short

/tmp/vesuvius-actionlint/actionlint .github/workflows/cpu.yml
```

The snapshot commands run from `/tmp/vesuvius-portable-ci-checkout`; the others
run from the audit checkout. The CI advisory lookup used the same `pip-audit`
options documented above, with `requirements/ci-cpu.txt` as the input and a
separate report. It returned status 0; the root-lock audit still returns 1.
