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
  below it contained 207 modules; CLI retirement brought it to 208. The later
  regional resource checks bring the current registry to 210.

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

## Regional resources and historical artifact disposition

This pass continues from `e38d2d6f`.

- **Independent accumulator limit:** both regional predictors now require
  `width * height * 12` bytes for three explicitly float32 blend planes to fit
  `--max_accumulator_bytes`, default 512 MiB. Preflight runs before model
  construction or CT reads, including default-z inference, skipped uncertainty
  export and tile shards. Checkpoints deserialize on CPU and the saved state
  is released after loading each model. Successful metadata records the byte
  plan. This caps persistent blend planes, not peak RAM/VRAM; model residency,
  activations, normalization, decoding and export temporaries are additional.
  The 4090 profiling/streaming decision remains open below. The
  [inference guide](VOLUME_INFERENCE.md#regional-output-planning) records the
  arithmetic, override and limitations.
- **Historical invalid fields:** the four identified JSON artifacts are retained
  unchanged as historical evidence, with explicit status in the
  [catalogue](../reports/HISTORICAL_ARTIFACTS.md) and its strict-JSON
  [digest/pointer record](../reports/historical_artifact_status.json).
  It identifies all 30 nonfinite fields. The old queue is unusable as a ranking;
  the other artifacts contain partial historical metrics with undefined fields.
  No value was filled with zero or regenerated. Unaffected finite fields keep
  their original scope and were not newly validated. New measurements need
  separate versioned outputs and retained source inputs. This resolves the
  review-list choice about retaining versus regenerating these four files.
- **Portable coverage:** the allocation-free byte arithmetic is included in the
  portable profile, which now has ten modules. The new predictor preflight
  regressions require the separate research review environment. Default full
  selection remains the 210-module curated registry.

## Research-test prerequisites and recovery checks

This pass continues from `1d1465fb` and resolves the classification/provisioning
decision for the missing-input failures identified above.

- **Explicit prerequisites:** corpus-dependent tests in fifteen probe modules
  now name `spiral_patches` or `spiral_rays`. Historical render and preserved
  source comparisons name their immutable Villa commits. Missing declared inputs
  skip by default with the missing paths/refs; `--require-research-inputs` makes
  them fail for selected checks. It does not require inputs for deselected tests
  or change unrelated legacy skip policies. All numerical test-function bodies
  in those probe modules are unchanged. Three source-inspection guards no longer
  depend on the patch corpus and now execute without it.
- **Strict history checks:** prerequisites require Villa's own repository, so a
  hash resolving in the parent cannot satisfy the gate. Read-only probes prohibit
  transport and have timeouts; marked tests disable implicit lazy fetch. After
  commit preflight, a missing preserved-source blob fails instead of skipping
  the remaining byte comparisons. Temporary-repository tests cover these failure
  modes without presenting synthetic history as original-study evidence.
  Git probes and temporary-repository operations ignore inherited repository/index
  selectors from hooks while retaining authentication and guard configuration.
- **Portable recovery precheck:** ref acceptance now uses a temporary Git
  repository, and absence uses a temporary missing path rather than a developer's
  home directory. Every precheck test forces an unattainable capacity threshold,
  preventing an accidental render on a large host. The validation registry now
  includes 212 modules; its portable profile includes twelve.
- **Provisioning and scope:** the [research-test guide](RESEARCH_TESTS.md) lists
  the original corpus paths, historical commit requirements, explicit history
  provisioning and strict/selective commands. Skips are unavailable coverage,
  not scientific passes. These declarations do not certify payload provenance,
  provide missing originals, migrate all legacy skips or establish that every
  research test is portable. Data onboarding and new scientific runs remain
  separate review items below.

## Items for owner review

The eight remaining items below are in suggested work order, not a claim that
each has caused a measured scientific failure.

| Priority | Finding and source | Recommended decision / next check |
| --- | --- | --- |
| High | **Dependency advisories still need migrations and applicability review.** GitHub's latest observed push banner reported 151 alerts on the default branch (6 critical); its advisory API previously returned HTTP 403. The public [root-lock audit](../reports/dependency_audit.json) now identifies 197 raw advisory records across eight remaining packages. A separate lookup for upstream Torch 2.9.1 found five candidate records; the CUDA-suffixed wheel was not directly audited. | Prioritize applicable advisories by the recorded IDs. aiohttp/dotenv updates require a WEBKNOSSOS/cluster-tools major upgrade; the scratch resolution was discarded. Windows additionally has a tensorstore constraint conflict. Review those migrations, the remaining major library updates, and advisories without a known fix using appropriate CPU/GPU/native validation. Public advisory matching does not establish reachability or replace GitHub alert access. |
| High | **The human-feedback loop is incomplete.** Regional uncertainty is a one-plane window diagnostic with a source offset; the proofreader expects aligned volumetric categorical labels, and approved TIFF patches are not automatically consumed by ink training. See [checkpoint/labeling workflow](CHECKPOINT_ANALYSIS.md), [launcher](../scripts/launch_proofreader.py) and [training inputs](../scripts/training/input_paths.py). | Choose whether this should review 2D ink windows or 3D segmentation labels. Then specify coordinate transforms, label semantics and a reviewed-patch ingestion contract. Do not broadcast a window mask through CT depth or interpret entropy as an ink label. Existing-session resume also needs a source-bound progress manifest before this wrapper can support it safely. |
| High | **Training-data source onboarding still needs a real example.** A maintained [local TIFF/PNG importer](TRAINING_DATA_IMPORT.md) now pins captures, preserves uint16 CT and publishes a new loader-compatible directory. Synthetic CPU tests verify conversion and failure handling, but no original fragment inputs or official download provenance were available here. | Select a supported official source, add a pinned download manifest and verify one small real-fragment example end to end. Confirm label registration and output-relative depth settings before training. Archived downloaders remain unsupported; local conversion does not establish scientific validity or source provenance. |
| Medium | **Regional peak memory and ensemble residency still need profiling.** [Single](../scripts/inference/predict.py) and [ensemble](../scripts/inference/ensemble_predict.py) now cap three persistent float32 blend planes independently of uncertainty export/sharding and load saved state on CPU. They still allocate whole-region arrays, normalization/export temporaries and all ensemble members together. | Profile on the 4090 with representative source/model settings before choosing streaming accumulators or sequential member residency. The 512 MiB default is an input acceptance policy, not a measured fit guarantee or total RAM/VRAM estimate. The [production path](../scripts/production_predict.py) is batched but also retains dense output accumulation; no full-scroll peak-memory or throughput result was measured here. |
| Medium | **The installed package relies on checkout-only modules.** Package discovery includes `src/`, while model construction imports root `vesuvius_model`, volume access uses `volume_cartographer_wrapper`, and several public commands live under `scripts/`. See [package configuration](../pyproject.toml) and [model factory](../src/vesuvius_autoresearch/core/model_wrappers.py). | Decide whether the supported product is an editable research checkout or a standalone wheel. If wheel support is wanted, package those dependencies and add a clean-directory installation test. Do not assume that an editable-import pass validates a wheel. |
| Medium | **Fresh scientific validation is still needed after earlier correctness changes.** The [surface-renderer guide](SURFACE_RENDERER.md) and [confidence-analysis guide](CONFIDENCE_REPRODUCIBILITY.md) describe changed contracts and historical limits. Placement gates now decline additional boundary-limited results. Unit tests do not rerun those real-data comparisons. | Prioritize one source-pinned rerun before using a historical number or placement record to justify a new research direction. Preserve the original artifacts and publish the new contract/version separately. |
| Medium | **Training read-failure defaults and recovery still need a decision.** The trainer now supports `strict_training_reads: true` for both labeled and active UA-MT inputs; strict labeled reads propagate into the underlying CT reader. Checkpoints, run results and diagnostics record the selected policy. The default still retains counted legacy fallbacks, and validation remains strict. | Decide whether to adopt strict training by default after a source-pinned real-data run, or add bounded retries/skips with an explicit failure budget. No real-data failure rate was measured here. Path-separation preflight cannot establish independence of copied/overlapping crops or different remote URLs; source-pinned split review remains required. |
| Lower | **Dependency and archive maintenance need a scope decision.** The default environment includes CUDA, notebook and broad research dependencies. The maintained Ruff findings are fixed; preserved/upstream reproductions retain their historical lint backlog. The two root demo/evidence generators now refuse execution before scientific imports or writes; their [original source](../scripts/archive/legacy_figures/README.md) is retained byte for byte. | Inventory supported commands before splitting CPU/GPU/research extras. Review upstream synchronization/releases for the placement-check and scroll-frames subtree fixes, required-status branch protection for the CPU job, and opt-in data/GPU CI provisioning. Keep byte-preserved sources and measured reproduction scripts distinct from maintained code; do not bulk-delete reports, logs or reproductions solely because they are not imported. |

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

## Regional resource and historical-status verification

The nine-module inference/production/runner selection passed `329 passed` in
155.42 seconds. After adding two more fixtures for checkpoint-derived default
dimensions, the complete ten-case preflight module and registry/file-mode
guards passed `28 passed` in 66.83 seconds. These overlapping counts are not
additive. The refusal fixtures use synthetic checkpoint/volume inputs and
traps for CT reads and model construction; they do not allocate the requested
oversized arrays or reproduce a physical GPU OOM.

The ten-module portable profile passed `254 passed` with no skips in 53.71
seconds in a separate source snapshot and the existing minimal hashed CI
environment. Its twenty resource-planning tests need no ML dependencies.
Maintained-source lint passed there too. Configured Mypy passed on 958 source
files. Smoke passed `9/11 passed, 2 skipped, 0 failed` in 45.9 seconds; the two
skips still need local CT/ink labels. Documentation guards passed
`138 passed, 1 skipped` in 91.51 seconds; that skip needs the original spiral
corpus. The full 210-module curated registry was not repeated.

The four original historical files were compared byte for byte with `e38d2d6f`,
and their hashes and all 30 catalogue pointers were checked against those
bytes. The new catalogue parsed as strict JSON. This verifies its disposition
record, not scientific validity or strict interchange of the original files.
No GPU measurement, full-scroll memory/throughput claim or regenerated metric
was produced.

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py --match '*regional_*' --match '*volume_inference_contracts*' --match '*uncertainty_handoff*' --match '*predict_checkpoint_loading*' --match '*production_predict*' --match '*production_artifact_plan*' --match '*validation_runner*' -- --tb=short -o faulthandler_timeout=90

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_regional_resource_preflight.py tests/test_validation_suite_covers_the_loop.py tests/test_file_modes.py -q --tb=short

env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/vesuvius-portable-ci-env/bin/python scripts/run_validation_tests.py --profile portable -- --tb=short --maxfail=1 -o faulthandler_timeout=60
```

The last command ran from `/tmp/vesuvius-portable-budget-checkout`; the others
ran from the audit checkout. This local portable run is separate from hosted
GitHub verification recorded on the PR.

## Research prerequisite verification

The nineteen-module affected selection passed `95 passed, 65 skipped` in 21.15
seconds. The skips explicitly name unavailable original study files or historical
Villa commits; they are not passing scientific comparisons. After adding the
late-blob regression, the complete prerequisite-policy module passed
`15 passed` in 4.84 seconds. Recovery, runner, registry and file-mode controls
passed `58 passed` in 10.90 seconds. These selections overlap.

Strict mode was exercised on the real patch-presence and preserved-source
tests: both missing prerequisites correctly produced setup errors and status 1,
with neither claim counted as passing. A temporary repository also reproduced
the parent commit's late skip when a source blob was missing after valid commit
preflight. The new regression requires failure instead. AST comparison against
`1d1465fb` confirms identical numerical test-function bodies across all fifteen
changed probe modules.

The twelve-module portable profile passed `274 passed`, with no skips, in
43.74 seconds from a separate source snapshot and the unchanged minimal hashed
CI environment. No Villa checkout, research corpus or ML dependency was needed.
Maintained-source lint passed there. Configured Mypy passed on 960 source files;
Ruff check and format passed on all 66 cumulative Python files. The offline lock
consistency check passed (255 packages); no runtime dependency version changed.

Smoke passed `9/11 passed, 2 skipped, 0 failed` in 23.8 seconds; the skips still
need local CT/ink labels. Documentation guards passed `138 passed, 1 skipped`
in 45.35 seconds; that separate legacy skip needs the original spiral corpus.
The full 212-module curated registry and full research tree were not repeated.
No original-corpus measurement, historical render equivalence or GPU result
was established in this pass.

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_probe_best_case_dr.py tests/test_probe_correlated_scatter.py tests/test_probe_cross_estimator_consistency.py tests/test_probe_exceedance_denominator.py tests/test_probe_is_corrected_scatter_physical.py tests/test_probe_nonparametric_surrogate.py tests/test_probe_onset_at_matched_correlation.py tests/test_probe_radial_span_mismatch.py tests/test_probe_real_patch_satisfaction.py tests/test_probe_real_patch_scatter.py tests/test_probe_real_residual_exceedance.py tests/test_probe_scatter_estimator_calibration.py tests/test_probe_self_consistent_exceedance.py tests/test_probe_spiral_satisfaction_empirical_transform.py tests/test_probe_spiral_satisfaction_onset.py tests/test_research_prerequisites.py tests/test_check_render_equivalence.py tests/test_villa_preserved.py tests/test_recover_arm_precheck.py -q -rs --tb=short -o faulthandler_timeout=90

/workspace/.vesuvius-review-env/bin/python -m pytest tests/test_research_prerequisites.py -q --tb=short

env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/vesuvius-portable-ci-env/bin/python scripts/run_validation_tests.py --profile portable -- --tb=short --maxfail=1 -o faulthandler_timeout=60
```

The last command ran from `/tmp/vesuvius-prerequisites-ci-checkout`; the others
ran from the audit checkout. The first command documents the affected selection;
its recorded count preceded the final late-blob test, which was covered by the
complete policy-module recheck.

Author review additionally covered inherited Git hook selectors: they must not
redirect a temporary test repository's commands into another index or object
store. After adding that regression, the final twelve-module portable run passed
`275 passed` with no skips in 33.35 seconds. It includes all sixteen policy tests
and the five recovery prechecks. Configured Mypy again passed on 960 files.

## Pre-merge review corrections

Review against main `f00cfc45` confirmed that commit `47ff96ec` on the existing
data-loss follow-up branch contained two fixes not yet incorporated here. Both
defects were reproduced against `538bb067`: its focused regressions reported
`25 failed, 8 passed` before the fixes. The commit was incorporated as `282f62fe`.

- **Actual image destination:** Matplotlib could append a default extension to
  a filename the artifact planner had validated, overwriting a checkpoint or
  sibling preview outside that plan. Planning now resolves the appended suffix
  and trailing-dot behavior, protects that actual path and supplies the planned
  format explicitly to both regional writers. Tests exercise the real savefig
  statement, aliases, case/default-format changes and both entrypoints.
- **Proofreader label IDs:** integer dtype alone did not prevent pinned Villa
  from truncating existing negative or greater-than-255 IDs when saving uint8.
  Wide/signed input labels now receive a complete bounded-block range scan;
  bool/uint8 inputs remain metadata-only. Valid wide labels are not rewritten.
  This does not restrict later human edits or establish physical registration.
  Both affected modules passed `70 passed` in 7.76 seconds after incorporation.
- **Zero-agreement placement:** a 136-by-135 synthetic fixture with a five-pixel
  displacement could produce a coarse four-pixel peak with zero full-resolution
  agreement when `refine=0`. The standalone tool returned it as located while
  the registration gate already refused. It now also requires positive final
  agreement. Two regressions failed before that guard; the 68-check standalone,
  parity and registration-gate selection passes, including a positive control
  that locates the true displacement with sufficient refinement.

The earlier and intermediate full-suite attempts were intentionally interrupted
when these fixes became necessary. They are not passing full-suite evidence.
The completed-run and follow-up verification are recorded below.

## Final review verification

The completed 212-module curated run reported
`1 failed, 5652 passed, 42 skipped, 1 xfailed` in 857.22 seconds. The failure
was `test_supervisor_reaps_term_resistant_descendants[True]`: its three-second
deadline expired while the leader waited for its worker's startup file. That
successful-exit test now allows fifteen seconds for interpreter/worker startup.
Its timeout-path case, descendant-liveness assertions and cleanup deadlines are
unchanged. The full lifecycle module passes in the final recheck.

Review also reproduced an immutable-ref gap in the new test prerequisites: a
hexadecimal branch named `deadbeef` could satisfy the gate while resolving to a
different commit. The fixture now requires the resolved hash to start with the
declared commit prefix. Both default and strict-mode regressions failed before
the fix and pass afterward.

The complete lifecycle and prerequisite modules passed `56 passed` in 25.13
seconds after those final changes. All failures from the completed curated run
are resolved; the whole registry was not repeated after the startup-test and
commit-prefix corrections. Counts from overlapping selections are not additive.
The separate lock-constrained WebKnossos SDK run passed all `81` fiber-label
tests in 68.19 seconds, including the optional SDK coverage absent from the
base environment. This is not a complete CUDA-lock or original-corpus run.

Configured Mypy passed on 960 source files. Maintained-source lint and the
cumulative 66-file format checks passed. Smoke passed
`9/11 passed, 2 skipped, 0 failed` in 16.5 seconds; skips need local CT/ink
labels. The documentation guards passed `138 passed, 1 skipped`; the skip needs
the original spiral corpus. Offline lock consistency passed (255 packages),
and dependency-report bindings plus the retained historical-artifact hashes
were verified. No historical artifact bytes changed relative to main.

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py -- --tb=short -o faulthandler_timeout=90

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_research_prerequisites.py tests/test_loop_lifecycle.py -q --tb=short

env PYTHONPATH=src:/tmp/vesuvius-review-sdk OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_fiber_label_generation.py -q -rs --tb=short
```

The seven remaining owner-review items, GPU/data/history limitations, and
non-transactional publication limits above still apply. The final hosted CPU
check and reviewed head are linked in the PR before merging.

## Local training-data import and figure retirement

This follow-up starts from merged main `90a1f029`. The new
[CPU local importer](TRAINING_DATA_IMPORT.md) accepts consecutive uint16 TIFF
planes and explicitly aligned binary PNG labels/masks. Planning captures and
decodes every source; building verifies those hashes again, writes and reads
back one CT plane at a time, and publishes a new directory only after success.
The parsed plan and its hash use the same captured bytes. Source/manifest changes,
shape/type mismatches, insufficient budgets and write failures refuse publication.
Build limits cannot be raised through the manifest. Planning also enforces the
reader's manifest-size limit before publishing a plan.

Output preserves uint16 values and original label PNG bytes. It records source
Z origin, but training coordinates remain output-relative. Geometry/chunk-storage
caps are acceptance limits rather than measured peak-memory or free-space
guarantees. Inputs must remain stable and writers serialized; the shared staged
publisher is not a crash-durable or concurrent-writer transaction. No data source
was downloaded, and no checkpoint/configuration or historical scientific result
was updated. A source-pinned download and verified real-fragment example remain
open in the onboarding item above.

The two unused root figure generators now refuse execution before scientific
imports or writes and direct callers to the maintained fiber workflow. Copies
under [legacy figures](../scripts/archive/legacy_figures/README.md) were compared
byte for byte with the originals at `90a1f029`; both SHA256 comparisons match.
Existing figures, measurements and reports are unchanged. Retaining historical
source does not validate its evidence.

Verification in the same isolated Python 3.10.21 CPU environment:

- Importer, retired entrypoints, existing converter and validation-runner tests:
  **140 passed** in 20.35 seconds. Synthetic fixtures cover direct command-line
  plan/build, the real volume reader and training dataset, uint16 extrema and
  endianness, binary-label rules, budgets, changed captures, aliases and cleanup.
- Loader, file-mode, validation-coverage and Villa component guards:
  **33 passed, 3 skipped** in 19.51 seconds. The skips need original local CT.
- The dependency-minimal portable profile: **283 passed** in 32.42 seconds.
  It now selects thirteen modules; the full curated registry selects 214.
  Importer tests require the full CPU scientific dependencies and are outside
  that portable profile. These selections are not a full curated rerun.
- Configured Mypy: **967 files**, no issues. Maintained-source Ruff and changed
  source formatting pass; the archived copies already match formatting without
  being rewritten. Offline lock consistency passes; dependencies are unchanged.
- Required nine-module documentation guards: **138 passed, 1 skipped** in 33.42
  seconds; the skip needs the original spiral corpus. Five additional/overlapping
  documentation and snapshot modules passed **60 tests** in 18.94 seconds.
  After staging all new files and completing this record, the documentation
  guards plus file-mode checks passed **149 passed, 1 skipped** in 33.88 seconds.
- Smoke: **9/11 passed, 2 skipped, 0 failed** in 13.2 seconds. Both skips need
  original CT/labels. No GPU, training, real-fragment conversion or new scientific
  measurement was performed.

Representative exact commands (all from the audit checkout):

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_surface_volume_import.py tests/test_legacy_figure_retirement.py tests/test_detector_conversion_contracts.py tests/test_convert_fragment.py tests/test_validation_runner.py -q --tb=short

env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/vesuvius-portable-ci-env/bin/python scripts/run_validation_tests.py --profile portable -- --tb=short --maxfail=1 -o faulthandler_timeout=60

/workspace/.vesuvius-review-env/bin/python -m mypy . --explicit-package-bases --namespace-packages --python-executable /workspace/.vesuvius-review-env/bin/python

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/smoke_test.py
```

The seven owner-review items remain, with local conversion and root-generator
disposition resolved and the corresponding rows narrowed. Dependency migrations,
human-feedback semantics, original-source onboarding, GPU profiling, packaging,
fresh scientific validation and the remaining maintenance decisions are still open.

## PR 403 review corrections

Review reproduced an undeclared TIFF transform: Pillow automatically applies
EXIF orientation, and orientation 3 rotated an 8×10 uint16 plane by 180° while
preserving its shape. Dimension checks and CT readback could therefore pass
while CT no longer matched the declared label grid. The new importer now requires
absent or identity orientation metadata on both TIFF CT and PNG labels/masks,
after header/pixel-budget checks and before accepting the image. Both planning
and building enforce this, including when a
rotated input has an updated, matching hash. The shared decoder's existing
converter defaults remain unchanged; this does not rerun historical conversions.

The input guide also clarifies that the optional binary mask guides thresholded
patch selection. Selected patches can overlap zero-mask pixels, ink-based
selection or patch catalogues can override the mask, and it is not a per-pixel
loss exclusion map.

The five-module affected selection above passed **150 tests** in 25.41 seconds,
including ten orientation regressions for CT, labels and masks, explicit
identity metadata and a re-hashed rotated build input. Configured Mypy passed
on **967 files**, and maintained Ruff passed. Final publication checks and
hosted CPU results are recorded on the PR. Missing original data and GPU
validation remain as stated above.

## Repeated whole-tree audit after PR 403

This pass starts from main `b1b9c365`. The tracked baseline contains **3,261
files**, including **1,021 Python**, **158 shell**, **447 JSON** and **10 YAML**
files. Every tracked Python file parsed, every shell file passed `bash -n`, and
JSON/YAML parsing found no syntax failures. The single script declaring POSIX
`sh` also passed `dash -n`; neither syntax check proves runtime correctness.
The same four historical JSON files still contain non-finite tokens; their
previous disposition and original artifact bytes remain unchanged.

The review combined those whole-tree scans with the full curated baseline and
manual checks of configuration, training/validation inputs, checkpoints, data
conversion, source imports, output publication and developer commands. An AST
reference scan followed by a project search found one unused private helper.
This is not a line-by-line certification of all historical experiments or the
pinned upstream repository, and no new GPU or real-fragment result was produced.

### Corrections

| Finding | Evidence and fix |
| --- | --- |
| Main training accepted its held-out volume as labeled input, and the UA-MT filter only compared literal strings. | A CPU probe of the real trainer reached validation construction with identical labeled/validation paths. A trailing-slash validation alias also survived the existing filter. A new stat-only split preflight refuses observable local aliases, ancestry and existing inode equality, plus matching remote resource identifiers. It runs before labels/GPU setup and is shared with workspace diagnostics. Disabled UA-MT inputs are not inspected. Copies, physically overlapping crops and different remote addresses remain unverified. |
| An experiment could replace the incumbent or other input while claiming the loop was untouched. | `save_cycle_checkpoints` accepted `best_model.pt` as `checkpoint_out`. New path checks protect loop weights/config/log/lock paths and named CT, label, mask, catalogue, pseudo-label, foundation and active-config inputs. The checks run before training and final saving; periodic CSV/step snapshots receive the active config path and are checked before evaluation/writing. Symlinks, hard links and special output files are refused. Ordinary experiment checkpoint replacement remains supported. These checks require serialized writers and are not filesystem locks. |
| The older uint16-to-uint8 detector converter still allowed Pillow's automatic TIFF orientation changes. | Source decoding now requires absent/identity orientation for CT and PNG labels/masks; failure preserves the preceding output generation. Readiness also rejects oriented converted images, even when manifest hashes match. New manifests record `source_orientation_policy`. Existing baked rotations cannot be inferred from output hashes; original-source review is still required. No old conversion or scientific score was rewritten. |
| The evidence-chain module retained an unused private numeric parser. | Removed `_as_float` after the AST scan and a project-wide reference search found only its definition. Existing evidence-chain and submission tests cover the maintained paths. No report or reproduction was deleted. |

The current owner table now lists **eight** items. It adds the explicit decision
about permissive training read/preprocessing failures. The other seven decisions
remain open, with dependency alert counts labeled as the latest observed banner
rather than a fresh applicability assessment.

### Verification

The complete, unchanged **214-module tracked baseline** passed **5,701 tests**,
with **42 skipped and one expected failure**, in 602.37 seconds. An initial
restricted-sandbox attempt was interrupted at an SDK fixture after
`1 failed, 2324 passed, 21 skipped, 1 xfailed`; its spawn/socket check also failed.
The successful rerun used socket-capable execution for SDK stubs, with no live
S3 test opted into. This was an environment requirement, not a product fix.

After corrections:

- Eleven affected modules passed **413 tests** in 58.40 seconds, including the
  real trainer's early refusal, checkpoint/periodic-save integration and
  read-only diagnostics. After the readiness follow-up, eight converter/evidence/
  submission/registry modules passed **309 tests** in 49.38 seconds. These
  selections overlap and are not a passing full-suite claim for the final tree.
- The minimal CPU profile passed **325 tests** in 31.47 seconds, with fifteen
  modules. The full registry now selects 216 modules. No CI dependency change
  was needed for the two new standard-library guard modules.
- Configured Mypy passed on **971 files**. Maintained Ruff, changed-file
  formatting and offline lock consistency pass; dependency versions are unchanged.
- Smoke passed **9/11, with 2 skipped and 0 failed**, in 12.7 seconds. Skips need
  the original local CT/labels. Final documentation/file-mode checks and hosted
  CI are recorded with the reviewable change before publication.

Final entrypoint review also propagated the active config path through the noise
probe and augmentation-ablation wrappers. Seven training/probe modules then
passed **311 tests** in 61.62 seconds, including actual ablation entrypoint refusal
before GPU setup. Mypy remained clean on 971 files. The documentation/file-mode
selection passed **149 tests with 1 missing-corpus skip** in 40.52 seconds.

Representative exact commands, from the audit checkout (the first and affected
training integration command used socket-capable sandbox execution):

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py -- --tb=short -o faulthandler_timeout=90

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_training_split.py tests/test_training_checkpoint_paths.py tests/test_training_data_sources.py tests/test_workspace_status.py tests/test_detector_conversion_contracts.py tests/test_convert_fragment.py tests/test_surface_volume_import.py tests/test_training_step_contracts.py tests/test_autoresearch_measurement.py tests/test_confidence_weighted_loss.py tests/test_validation_runner.py -q --tb=short

env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/vesuvius-portable-ci-env/bin/python scripts/run_validation_tests.py --profile portable -- --tb=short --maxfail=1 -o faulthandler_timeout=60

/workspace/.vesuvius-review-env/bin/python -m mypy . --explicit-package-bases --namespace-packages --python-executable /workspace/.vesuvius-review-env/bin/python
```

The baseline still leaves tests outside the curated registry, original study
inputs/history and GPU behavior with the previously documented coverage gaps.
Source-pinned scientific reruns, full-scroll performance and standalone-wheel
validation were not supplied by these CPU checks.

## Training read-policy follow-up

This follow-up continues PR 404 from `f549f4ac`. It narrows the training
read-failure review item without choosing a new default or recovery strategy.

Five synthetic regressions reproduced a strict-read propagation gap: the labeled
dataset was configured strict, but its underlying CT reader was permissive.
NaNs, float32 overflow, short depth/height and unsupported returned dtypes could
therefore pass the initial validation sample probe. All five tests failed before
the fix. Strict labeled datasets now pass the boolean policy to their volume
reader; normal strict reads still support CPU preprocessing. Worker serialization
retains the setting. This restores the intended validation preflight boundary;
it does not establish that a historical real-data run encountered these defects.

The optional `strict_training_reads` configuration field now selects strict
behavior for labeled and active UA-MT training readers. It defaults to `false`,
retaining legacy fallbacks; the new field is appended to preserve positional
configuration arguments. Invalid non-boolean values are rejected. Strict UA-MT
with unsupported Lasagna preprocessing is rejected before training begins.
Validation stays strict independently of the training setting.

Successful final and periodic checkpoints, run results and read-only workspace
diagnostics record `data_read_policy`; permissive-mode warning counts remain
available. Strict reads check returned chunks and requested preprocessing, not
physical registration, acquired-source completeness or holdout independence.
Aborting does not roll back earlier artifacts. The current configuration,
checkpoint, study reports and original evidence were not rewritten.

Verification in the existing CPU review environment:

- Nine affected loader/training/probe modules passed **391 tests, 4 skipped**
  in 123.12 seconds, including the five regression cases and worker serialization.
- Four compatibility modules passed **92 tests, 3 skipped** in 122.38 seconds,
  covering periodic checkpoint policy metadata, training steps and the importer.
- The dependency-minimal fifteen-module profile passed **331 tests** in 39.99
  seconds. An earlier concurrent run hit a 30-second subprocess startup timeout
  in an unchanged research-prerequisite fixture. The fresh rerun passed without
  modifying its timeout or prerequisite behavior.
- Mypy passed on **971 files**; maintained Ruff, changed-file formatting and
  offline lock consistency pass. No dependency versions changed.
- Documentation/file-mode guards passed **149 tests with 1 original-corpus
  skip** in 35.22 seconds.
- Smoke passed **9/11, 2 skipped, 0 failed** in 52.6 seconds. Original-data,
  optional GPU and original-corpus gaps remain; these selections are not a full
  final-tree curated rerun or a real-data failure-rate measurement.

Representative exact commands (the integration selection used socket-capable
sandbox execution for existing spawn/SDK tests):

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_preprocessing_contracts.py tests/test_volume_read_contracts.py tests/test_training_data_sources.py tests/test_workspace_status.py tests/test_autoresearch_measurement.py tests/test_noise_probe_contracts.py tests/test_noise_probe_pooled.py tests/test_loader_workers.py tests/test_vesuvius_loader.py -q --tb=short

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python -m pytest tests/test_confidence_weighted_loss.py tests/test_training_step_contracts.py tests/test_surface_volume_import.py tests/test_config_depth_band_fits_fragments.py -q --tb=short

env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/vesuvius-portable-ci-env/bin/python scripts/run_validation_tests.py --profile portable -- --tb=short --maxfail=1 -o faulthandler_timeout=60
```

The eight owner items remain, with strict training now an implemented option.
Adopting a different default, bounded retries/skips and real-data validation
remain decisions for a separate experiment; no GPU profiling was performed.
