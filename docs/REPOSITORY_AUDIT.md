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

The seven remaining items below are in suggested work order, not a claim that
each has caused a measured scientific failure.

| Priority | Finding and source | Recommended decision / next check |
| --- | --- | --- |
| High | **Dependency advisories still need migrations and applicability review.** The November 10 [root-lock snapshot](../reports/dependency_audit.json) recorded 197 raw advisory records across eight packages before the later migrations. The [November 14 review](../reports/dependency_migration_review_2026-11-14.json) records Pillow 12.1.1 → 12.3.0. The [November 15 review](../reports/dependency_migration_review_2026-11-15.json) records non-Windows WEBKNOSSOS 4.3.3, aiohttp 3.14.5, dotenv 1.2.4 and cryptography 50.0.2, with Python 3.10 workflow/native checks and unchanged Windows package selection. Fresh version-specific PyPI lookups report 89 → 0 raw records across the three latter packages. These dated, aliased counts are not a fresh whole-lock total or distinct reachable vulnerabilities. | Prioritize the remaining applicable IDs. Tornado 6.6, Pillow 13 and Filelock 4.2.1 require Python 3.11. Windows still selects the old SDK/aiohttp/dotenv chain because newer SDKs pin TensorStore below this project's minimum. Newer Virtualenv still conflicts with SDK typing-extensions constraints on Python 3.10. Decide Python/platform support before those migrations. GitHub's advisory API previously returned HTTP 403; public matching and CPU checks do not replace alert access, Windows execution or GPU validation. |
| High | **The human-feedback loop is incomplete.** Regional uncertainty describes a single plane with a source offset, and the proofreader expects aligned 3D categorical labels. Opt-in [session records and export checks](PROOFREADER_SESSION_RECORDS.md) bind input bytes, check each approved TIFF pair against the log and CT, and can verify agreement between approved label TIFFs and their edited Zarr crops. | Choose whether feedback will use 2D ink windows or 3D segmentation labels, then define coordinate transforms, label semantics and ingestion into the [training inputs](../scripts/training/input_paths.py). Resume needs a separate contract for Villa's grid snapping, pending entries and incomplete GUI-setting history. Physical alignment and label correctness require their own review. |
| Medium | **Regional peak memory and ensemble residency still need representative GPU measurements.** [Single](../scripts/inference/predict.py) and [ensemble](../scripts/inference/ensemble_predict.py) cap three persistent float32 blend planes and load saved state on CPU. The opt-in [regional profiler](VOLUME_INFERENCE.md#regional-memory-observations) now records process RSS, OS lifetime high-water RSS and selected-device PyTorch allocator peaks through the latest metadata observation. Synthetic CPU checks preserve output probabilities exactly; the CUDA path has only mocked API coverage. Whole-region arrays and all ensemble members remain resident. | Run `--profile_memory` on the 4090 with representative source/model/export settings before choosing streaming accumulators or sequential member residency. The 512 MiB cap remains an acceptance policy. CPU lifetime peaks include earlier process work; CUDA allocator peaks exclude other allocators/processes and device-context overhead, and are not independent phase peaks or fit guarantees. The [scratch CUDA probe](VRAM_PROBE.md) is a separate forward/backward path. [Production](../scripts/production_predict.py) remains outside the new regional profiling scope; no real GPU/full-scroll peak or throughput result was measured here. |
| Medium | **Broader scientific validation is still needed after earlier correctness changes.** The [registered renderer-v2 check](../reports/render_revalidation_review_2026-11-17.md) now supplies a new real-source compatibility measurement: one fixed PHerc1667 interior crop, center-plane NCC 0.78897, complete depth support, and a bitwise offline replay. This is not a repeat of the historical whole-segment/depth experiments. The [surface-renderer guide](SURFACE_RENDERER.md) and [confidence-analysis guide](CONFIDENCE_REPRODUCIBILITY.md) retain those limits. Placement gates now decline additional boundary-limited results. | Use the new reading only within its fixed-crop compatibility scope. Rerun the confidence analysis and any broader renderer/placement comparison before using its historical number to justify a research direction. Preserve original artifacts and register new methods separately. No accuracy, independent registration, depth-direction or whole-scroll claim follows from the crop check. |
| Medium | **Training read-failure defaults and recovery still need a decision.** The trainer supports `strict_training_reads: true` for labeled and active UA-MT inputs, and records the selected policy. Validation checks the bytes it parses for explicit catalogs and decodes for labels and masks. The [Frag1 failure exercise](#validation-image-identity-and-frag1-read-failures-2026-11-22-utc) shows that strict reads catch a short encoded chunk and that [prepared fragment verification](TRAINING_DATA_IMPORT.md#verify-a-prepared-fragment) also catches missing chunks. | Decide whether to adopt strict training by default after a source-pinned real-data run, or add bounded retries/skips with an explicit failure budget. The default uses counted legacy fallbacks for CT read failures. Review copied or overlapping crops and remote source identities separately when establishing split independence. |
| Medium | **The prepared precision contract needs adoption in a future registration.** The as-run [Finding 111 calculator](../repro/first_letters/pherc0841/surface_control.py) rounds AUC before its decision. The new [v2 calculator and contract](SURFACE_CONTROL_V2.md) retain full precision for sweep selection, stored metrics and P1/P2, with presentation-only rounding. Synthetic CPU checks reproduce and correct the boundary case without changing the published study. | Pin v2 and its helper sources in a new registration before a new measurement. Preserve the as-run code/records; historical rounded sweeps cannot be used as v2 inputs. The published held-out verdict is unchanged, and no original-data v2 run has been performed. |
| Lower | **Dependency and archive maintenance need a scope decision.** The default environment includes CUDA, notebook and broad research dependencies. The [command inventory](COMMANDS.md) records runtime, checkout/wheel, Villa and side-effect requirements for 28 reviewed entry points and modes. The maintained Ruff findings are fixed; preserved/upstream reproductions retain their historical lint backlog. The two root demo/evidence generators now refuse execution before scientific imports or writes; their [original source](../scripts/archive/legacy_figures/README.md) is retained byte for byte. | Use the inventory to design and test dependency closures, then decide Python/platform support before splitting CPU/GPU/research extras. Review upstream synchronization/releases for the placement-check and scroll-frames subtree fixes, required-status branch protection for the CPU job, and opt-in data/GPU CI provisioning. The [unimplemented registration/nnUNet launchers](UNSUPPORTED_LAUNCHERS.md) now refuse execution and retain their original source. Keep byte-preserved sources and measured reproduction scripts distinct from maintained code; do not bulk-delete reports, logs or reproductions solely because they are not imported. |

The new First Letters image, mesh and surface controls are recorded in the
[current strategy](RESEARCH_STRATEGY.md). They supply real-data evidence for
that campaign; they do not rerun the older surface-renderer/confidence studies
or validate the separate training-data importer. Broader remote-URI identity
normalization also remains a source-contract decision: the Python volume
wrapper currently supports local inputs, and version/query distinctions must
be considered before remote training is enabled.


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

## PR 404 review corrections

The pre-merge review reproduced eighteen failing cases across three remaining
path-guard gaps, then corrected them:

- Existing local volume names containing colons, including URI-like names, now
  take precedence over URL interpretation, matching `FastVesuviusVolume`.
  Observable split aliases and checkpoint destinations inside those CT trees
  are therefore checked as local resources. Workspace diagnostics use the same
  precedence.
- Checkpoint protection derives annotation paths from the configured volume
  spelling. A volume symlink no longer shifts label, mask or catalogue guards
  to the CT target's parent while training reads beside the visible URI.
  The shared collision validator still resolves the CT tree itself.
- Reserved loop paths now include journals, temporary/recovery files, log files
  and the `sprint_logs` directory. Experiment checkpoints cannot replace this
  state; ordinary experiment checkpoint replacement remains supported.

A follow-up relative-checkout probe exposed a base-directory duplication in
annotation protection. Normalizing the explicit checkpoint-check base to an
absolute path fixes it; a regression checks both refusal and an allowed output
without creating directories. An actual trainer regression also verifies that
visible symlink labels are protected before GPU setup.

Review validation in the existing Python 3.10.21 / CPU Torch 2.9.1 environment:

- The thirteen-module affected selection passed **563 tests, 1 skipped** in
  74.71 seconds. After the relative-base follow-up, the final split/checkpoint/
  workspace selection passed **96 tests** in 0.91 seconds.
- The complete 216-module curated CPU run passed **5802 tests, 42 skipped,
  1 xfailed** in 594.99 seconds, using the full-suite command recorded above.
  That run collected/imported its tests before the final relative-base
  correction; the 96-test final selection covers that correction separately.
- Documentation/file-mode guards passed **149 tests, 1 original-corpus skip**
  in 69.39 seconds.
- Mypy passed on **971 files**. Maintained Ruff, formatting of all seven changed
  Python files and offline lock consistency pass. No dependencies changed.
- Smoke passed **9/11, 2 skipped, 0 failed** in 11.7 seconds; the skips require
  original local CT/labels.

These checks do not supply original-data or GPU validation. The eight owner
items remain; the live research checkout, original study files and checkpoints
were not modified.

## Whole-tree follow-up, November 13, 2026

This pass starts at main `9fa747c5f96a77481fc75d88292742ba15930218`, including
the First Letters reproduction and the recent canvas/fiber boundary fixes.
The isolated audit checkout keeps the original research checkout unchanged.

### Coverage and reproduced defects

The starting tree has **3279 tracked regular files**, including **1031 Python
files (222455 lines), 162 shell scripts, 448 JSON files and 10 YAML files**.
All Python files parsed, shell scripts passed `bash -n`, and JSON/YAML parsed.
There were no duplicate top-level Python definitions or JSON object members.
The same four previously catalogued historical JSON files retain non-finite
tokens. Header/structure checks passed for 245 images and ten NPY payloads,
and both ZIP archives passed CRC checks. These scans read the tracked tree;
manual review focused on maintained training, inference, data loading,
publication, configuration, developer and newly merged reproduction workflows.
They do not establish every historical result or exhaustively verify every line.

Six defects were reproduced with **29 initially failing regressions**:

| Defect | Correction |
| --- | --- |
| Unknown training architectures silently selected Gated UNet while retaining another architecture name in the configuration. | Shared architecture choices now reject unsupported names during config construction and before training/model setup. The known training-only names remain explicit. |
| Unknown augmentation modes silently used Albumentations. | Supported mode names are checked at config and augmentation boundaries, including configs mutated after construction. |
| The batchgenerators pipeline cache used only patch geometry, retaining the previous run's four configured scroll-transform probabilities. | The cache key includes those probabilities. Stand-in pipelines verify their effect on actual output tensors and reuse for an identical configuration. |
| Four-dimensional backbone logits became a seven-dimensional projection input. | Planar logits receive one depth axis; scalar and volumetric paths retain their behavior. Projection tests check finite outputs and gradients for all three ranks. |
| The default unused skeleton-distance limit was Infinity, making newly trained checkpoint configurations unpublishable by either regional predictor's finite-JSON guard. | Its inactive default is `null`; loading the legacy positive-infinity sentinel normalizes it to `null` for new runs. Finite legacy values remain recorded. Existing checkpoint bytes are not rewritten. |
| Depth-band matching disagreed with split checks for existing URI-like local paths, encoded file paths and remote level-zero aliases with queries. | Both now share a standard-library volume-location classifier. Local resources cannot also match the remote spelling under an alternate checkout base. Copies, physically overlapping crops and different remote resources remain unverified. |

Removed the redundant augmentation-cache initialization and the noise probe's
now-obsolete special-case omission of the unused infinity default. The strategy
and proposed roadmap now distinguish September's confirmed award from unrecorded
July/August totals, and distinguish the passed image-chain kill test from the
unrun mesh stage. No roadmap decision was adopted and no scientific figure changed.

### Verification and remaining limits

The pre-fix 216-module curated CPU baseline passed **5817 tests, 42 skipped,
1 xfailed** in 727.92 seconds. Before the shared path follow-up, six affected
modules passed **313 tests, 1 skipped** in 66.25 seconds. The shared-path
selection then passed **271 tests** in 48.28 seconds. These overlapping subset
runs do not substitute for the final complete validation record.

Final validation:

- The complete 216-module curated CPU suite passed **5849 tests, 42 skipped,
  1 xfailed** in 597.03 seconds, including all 32 added regression/control cases.
- The other 250 `tests/` modules passed **2528 tests, 155 skipped** in 564.68
  seconds. Their selection began before the final shared-identity extraction;
  the final curated run above covers the affected paths. Missing original
  spiral inputs, historical Villa revisions, ScrollGT targets and external
  checkouts remain skipped coverage. One real TimeSformer inference emitted the
  90-second faulthandler diagnostic and subsequently passed; the diagnostic was
  not a test failure or an enforced time limit.
- A new dependency-minimal environment, installed from the hash-pinned CPU
  requirements, passed **360 portable tests** in 27.76 seconds. Torch and Zarr
  were absent; the profile still contains fifteen modules.
- Documentation/file-mode guards passed **149 tests, 1 original-corpus skip**
  in 32.96 seconds. Maintained Ruff, formatting of all eleven changed Python
  files and offline lock consistency pass.

Exact final curated and minimal-profile commands, from this checkout:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py -- --tb=short --junitxml=/tmp/vesuvius-nov13-curated-final.xml -o faulthandler_timeout=90

env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/vesuvius-nov13-portable/bin/python scripts/run_validation_tests.py --profile portable -- --tb=short --maxfail=1 -o faulthandler_timeout=60
```

The outside selection is every `tests/**/test_*.py` module absent from
`VALIDATION_TESTS`; it used the same CPU environment and `pytest -q`, with
`--tb=short --continue-on-collection-errors`, a JUnit report and the 90-second
faulthandler diagnostic. It recorded no collection errors or failing tests.

Mypy passed on **978 files**; maintained Ruff passed. Smoke passed **9/11,
2 skipped, 0 failed** in 12.3 seconds, with original-data skips. No new dependency
versions, running research state, measured artifacts or frozen sources changed.

At that stage there were nine owner-review items; the current table includes
later findings. This pass supplied no original-fragment/GPU runs,
full-scroll resource profiles, standalone-wheel support and historical-artifact
migrations were not supplied by this pass. In particular, old checkpoints whose
stored configs contain Infinity are retained unchanged; normalizing a new
training config is not a rewrite of an older artifact.

## Current-main integration and detector-loader follow-up

This pass integrated main `2a80588c` with the preceding audit fixes, yielding
review baseline `761e24c5`. Main adds the recorded PHerc. 343 mesh reproduction,
PHerc. 0841 surface control and further sampler/input tests. The roadmap now
identifies those completed controls and the next eligible-scroll detection
test. The strategy's older statement that the mesh stage's hardware capacity
was unmeasured now points to finding 110. Existing registrations, as-run
scripts, scientific records and the live research checkout were preserved.

### Inventory and confirmed corrections

The integrated starting tree contains **3328 tracked regular files**, including
**1043 Python files (226526 lines), 184 shell scripts, 450 JSON files, two
notebooks and ten YAML files**. Parsing, shell syntax, duplicate-definition and
duplicate-JSON-member checks found no new structural failures. The same four
catalogued historical JSON files retain NaN tokens. Structure/header checks
passed for 247 images, ten NPY payloads and both ZIP archives. This remains a
whole-tree inventory with focused manual workflow review, not independent
verification of every historical result or every line of upstream code.

Three defects were corrected:

- The detector padded an aligned axis by a whole extra tile. It now pads only
  to the next tile boundary. Original CT clipping, usable training tiles,
  label values, probability maps and coverage match the former recipe in the
  regression comparisons, including inputs aligned on one or both axes.
- The loader retained every padded CT plane while allocating a second stacked
  volume. It now fills one final zero-padded stack with per-plane temporaries.
  The full padded CT still resides in host RAM; this is not streaming inference.
- Coherence imports could select an already installed `vesuvius` module and
  depended on import order. The diagnostic now uses the shared private leaf
  loader for this checkout's Villa file. A missing pin raises ImportError for
  the optional diagnostic rather than falling back to another implementation.
  Ordinary imports preserve other callers' module/path state. Direct launches
  bootstrap this checkout, and the CLI adds explicit `--device cpu` support.

Seven new regression/feature cases failed before these changes; ten compatible-
output controls already passed. After correction, seven affected modules passed
**292 tests, 1 skipped** in 49.06 seconds. The detector-data module is now in the
curated registry, raising it to 217 modules; the portable profile stays at fifteen.

The [captured synthetic checks](../reports/repository_audit_2026-11-13_integrated.json)
bind the baseline/current loader source hashes and describe the input recipe:

| Input Y/X | Final CT array bytes, before → after | Traced peak bytes, before → after |
| --- | --- | --- |
| 256 × 256 | 6815744 → 1703936 | 13665025 → 1910991 |
| 264 × 264 | 6815744 → 6815744 | 13654475 → 7227323 |

The trace covers Python/NumPy allocations during loading. Package imports,
OpenCV/native allocations, whole-process RSS and GPU memory are outside its
scope. It is not a throughput measurement or a real-data GPU fit guarantee.

### Research-method observation retained for review

A valid synthetic rank-score field gives AUC **0.74996**. Finding 111's as-run
calculator records **0.75** before evaluating P2 and therefore reports
`LETTER_LEVEL_SIGNAL`; evaluating the threshold at raw precision gives
`BLOB_LEVEL_SIGNAL`. Its slid floor is 0.5083, so P1 holds in either case. The
published held-out AUCs, 0.7478 and 0.7194, remain below 0.75 and are unaffected
by this boundary example. The frozen method and its result were not rewritten.
The precision owner item calls for a versioned precision contract before a new
registered run uses this logic; the follow-up below prepares that successor.

### Verification

- All **217 curated modules** passed: **5933 tests, 42 skipped, 1 xfailed** in
  732.99 seconds.
- The other **253 test modules** passed: **2607 tests, 155 skipped** in 658.04
  seconds, with no collection errors. Original data, historical revisions and
  external checkouts remain unavailable coverage. These checks include the
  newly merged reproduction/analysis tests; they are not reruns of those studies.
- Mypy passed on **989 files**. Maintained Ruff, all five changed Python files'
  formatting and offline lock consistency pass. Dependency versions are unchanged.
- A fresh hash-pinned minimal environment passed **380 portable tests** in
  30.00 seconds, with Torch and Zarr absent. Smoke passed **9/11, 2 skipped,
  0 failed** in 15.8 seconds; skips require original local CT/labels.

The complete curated command used the existing CPU review interpreter:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib XDG_CACHE_HOME=/workspace/.vesuvius-review-cache /workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py -- --tb=short --junitxml=/tmp/vesuvius-integrated-curated.xml -o faulthandler_timeout=90
```

The outside selection used every `tests/**/test_*.py` absent from
`VALIDATION_TESTS`, with the same CPU/thread settings, `pytest -q --tb=short
--continue-on-collection-errors`, a JUnit report and the 90-second faulthandler
diagnostic. The ten current owner items above distinguish these software checks
and the newly merged campaign evidence from remaining real-data/GPU, interface,
dependency and future-method decisions.

## Review-item follow-up (2026-11-14 UTC)

This pass integrates main `bfbcae29`, including the owner's already measured
Finding 109 seam-confirmation record. That integration is separate from the
new engineering checks below. The live research checkout, historical
registrations, as-run calculators and measured scroll artifacts remain unchanged.

Two owner-review items advanced:

- **Precision:** the separate [v2 surface-control calculator](SURFACE_CONTROL_V2.md)
  compares full-precision AUCs for both sweep selection and P1/P2. JSON retains
  those floats; only sweep console rows round them. It rejects historical sweeps,
  recomputes the chosen row, binds the parsed choice bytes to their hash and
  recalculates verdict flags. Missing step records fail before data loading;
  invalid scores, undersized held-out classes and duplicate segment/gate names
  cannot produce a successful measurement. Exclusive output creation preserves
  an existing result even if it appears during calculation. Snapshot checks
  preserve historical geometry/constants and guard the original calculator's
  hash. This is a tested candidate for a new registration, not adoption or a
  remeasurement of Finding 111.
- **Dependencies:** the universal lock changes only Pillow **12.1.1 → 12.3.0**.
  The [migration review](../reports/dependency_migration_review_2026-11-14.json)
  binds both lock hashes and records a fresh, version-specific PyPI lookup:
  **93 → 58 raw Pillow advisory records**, with 35 removed IDs and no added IDs.
  Aliases can represent the same vulnerability. The November 10 whole-lock
  snapshot used an earlier advisory feed and must not be arithmetically combined
  with these counts. Remaining Pillow records include fixes requiring Python
  3.11. No new exploitability or full-lock advisory result is claimed.

The migration review also captures Python/platform blockers and the failed
Virtualenv 20.36.1 universal solve. Windows' selected WEBKNOSSOS/cluster-tools
requires typing-extensions below 4.13, while the candidate needs at least
4.13.2 on Python 3.10. Newer WEBKNOSSOS requires Windows tensorstore 0.1.76,
conflicting with this project's minimum 0.1.78. No markers, platform support or
SDK constraints were removed to force a resolution. A scratch cryptography
upgrade removed that package and downgraded its consumer instead of validating
the proposed major release; that scratch result was discarded.

### Verification

- Method, boundary, launcher and newly integrated Finding 109 tests passed
  **148 tests, 7 skipped** in 12.60 seconds. The missing study-input skips are
  unavailable coverage, not reruns of the scientific studies.
- Pillow 12.3.0 passed **486 workflow tests, 11 skipped** in 52.18 seconds and
  **133 importer/artifact tests** in 14.44 seconds. The skips need the optional
  WEBKNOSSOS SDK. Header/container checks passed for **247 tracked images**;
  they do not establish complete pixel decoding or scientific image validity.
- Mypy passed on **994 files**. Maintained Ruff and all three changed Python
  files' formatting pass. Offline universal lock consistency passes with only
  Pillow changed. The curated registry now has **218 modules**, with its
  portable profile unchanged at fifteen.
- The final v2, documentation/claim and file-mode guard selection passed
  **191 tests, 1 original-corpus skip** in 34.32 seconds. These selections
  overlap; their pass counts are not additive.
- Smoke passed **9/11, 2 skipped, 0 failed** in 10.8 seconds; skips require
  original CT/labels. The review interpreter uses Python 3.10.21, Torch 2.9.1
  CPU and Pillow 12.3.0. No GPU experiment, original-data v2 measurement, or
  Windows/macOS runtime validation was performed.

The new method and dependency changes use focused checks; the previous full
curated/outside-registry runs above remain the broader baseline. The ten owner
items now distinguish completed engineering preparation from adoption, migration,
physical registration, GPU profiling and new scientific measurements.

## Fresh audit after PR 422 (2026-11-14 UTC)

This pass starts at main `73c741a2`. It repeats the whole-tree structural
inventory and manually reviews data conversion/label preparation, detector
measurement/reporting, fiber tools, checkpoint cleanup, command launchers and
diagnostic scope. The [captured review](../reports/repository_audit_2026-11-14.json)
records the starting tree and reproducible defects. This is not a claim that
every line or historical scientific conclusion has been independently verified.

The initial tree contains **3341 tracked regular files**, including **1048
Python files (228725 lines), 185 shell scripts, 454 JSON files, two notebooks
and ten YAML files**. Python/shell/JSON/YAML structural checks passed, including
duplicate JSON members and duplicate top-level Python definitions. Header or
payload checks passed for **247 images, ten NPY files and two ZIP archives**.
Only the four already catalogued historical JSON files contain NaN constants;
they remain preserved. The scientific inputs and live research checkout were
not changed.

### Confirmed corrections

- **False registration success:** the cross-scan launcher imported an alignment
  function but never called it or wrote a transform. With importable dependencies
  it printed “Transform saved” and returned successfully; it also created the
  output directory before dependency checks. It now refuses execution with
  status 2 and directs users to the separate upstream manual-alignment workflow.
- **Unsafe, unintegrated nnUNet bridge:** the command only wrote a fixed temporary
  YAML. Evolving one parameter discarded unrelated template settings, and using
  that temporary path as input overwrote the input. Trainer generation and
  training existed only as comments; its default input was absent. It now
  refuses before reads/writes rather than presenting a working loop integration.
  Both launchers keep their flags, dependency-free help and
  [byte-preserved original source](../scripts/archive/legacy_launchers/README.md).
- **Invented CPU memory capacity and stale GPU peaks:** the memory search returned
  True without CUDA and printed batch 128/patch 384 as passing sizes. The
  [repaired probe](VRAM_PROBE.md) now requires CUDA, selects the requested device,
  resets each trial's peak, releases failed trial objects before cleanup, and
  distinguishes typed CUDA OOMs from other errors. Its scratch gated_unet
  forward/backward result excludes optimizer/data-pipeline costs and cannot
  establish production capacity or prize eligibility. No CUDA trial ran here.
- **Scope corrections:** the archived sprint board no longer repeats the obsolete
  global 64-pixel prize cap or treats the scratch probe as a production-capacity
  measurement. The archived nnUNet status now identifies the missing integration.
  Other historical results, registrations and measured artifacts are unchanged.

Fifteen regression/feature cases initially failed, including retirement/help
and preservation guards rather than fifteen distinct bugs. The focused
post-change selection passed **61 tests** in 5.08 seconds. It includes a real
small CPU model's forward/backward and controlled allocator/device/OOM tests;
the latter are software-lifecycle checks, not physical CUDA measurements.

### Verification and decisions still open

Mypy passes on **998 files**, and maintained Ruff passes. The validation
registry now has **220 curated modules** and **16 portable modules**; the new
launcher checks need only the minimal CPU test tools. Broader final checks are
recorded with the completion results below.

The ten owner items above still require their stated decisions or measurements.
This pass adds explicit scope for the unused random-feature volumetric ink
demo; it was not promoted into training or deleted merely because it has no
caller. The current limits remain original-data onboarding/reruns, human-label
semantics, Python/platform/SDK migrations, package scope and representative GPU
profiling. Fixing the scratch probe does not supply those measurements.

Completion results for this pass:

- All **220 curated modules** passed: **6001 tests, 42 skipped, 1 xfailed** in
  550.67 seconds. Skips remain unavailable coverage, including original inputs,
  history and optional dependencies.
- A fresh hash-pinned minimal environment passed **392 portable tests** in
  28.56 seconds, with Torch and Zarr verified absent. Maintained Ruff also passes
  with that environment's pinned 0.9.10 tool.
- Documentation, historical-claim and newly integrated research-source guards
  passed **98 tests** in 20.17 seconds. These do not rerun the scientific studies.
- Smoke passed **9/11, 2 skipped, 0 failed** in 11.7 seconds; skips need original
  local CT/labels. Mypy passes on **998 files**; changed Python formatting and
  offline lock consistency pass. No dependency version changed in this pass.
- The final staged-tree inventory covers **3349 regular files** and **1052 Python
  files (229188 lines)**, including the new tests and retained launcher sources.
  Python/shell/JSON/YAML/TOML/CFF/SVG parsing, duplicate checks, image headers,
  NPY payloads and ZIP CRC checks found no new failures. The same four historical
  JSON files retain their catalogued NaN values.

The curated command and captured source hashes are in the
[review record](../reports/repository_audit_2026-11-14.json). Selections overlap;
their counts are not additive. The other research modules retain the earlier
broader baseline; they were not all rerun in this pass. No GPU capacity result,
GUI registration, nnUNet training, original-data scientific rerun or production
training performance improvement is claimed.

### PR 424 review and current-main integration

The PR integrates main `04c36b46`, which adds the owner's Finding 112 band-fit
record and scripts. These are upstream research artifacts, not new measurements
performed by this software review. They remain unchanged in the PR diff.

Review found that the four retained legacy Python snapshots were still selected
by pre-commit auto-fix hooks and default Ruff discovery. They happen to match
the current formatter; no formatting drift was observed. The preservation rule
is now enforced by excluding the two frozen archive directories from default
Ruff discovery and their Python files from hooks. Active code, other archives
and the explanatory README files retain checks. Source bytes were preserved.

Five policy guards failed before the correction and ten coverage controls
already passed. The combined preservation, launcher, memory-probe and runner
selection then passed **81 tests** in 5.20 seconds. The curated registry now
contains **221 modules**, with **16 portable modules**. The review record retains
the initial audit hashes separately from the updated registry/configuration
hashes; the earlier full-run figures above retain their original scope.

The final integration selection passed **188 tests, 7 skipped** in 28.73
seconds, including Finding 112's source/report checks. Mypy passes on **1003
files**, maintained Ruff/format checks pass, and offline lock consistency
passes without changing dependency versions. These checks do not rerun
Finding 112 or measure GPU capacity.

## Dependency-review follow-up (2026-11-15 UTC)

This pass starts from main `bf6e9596`. The first owner-review item advances
without changing Python support, the TensorStore minimum or the live research
environment. The [migration record](../reports/dependency_migration_review_2026-11-15.json)
binds the before/after manifests and locks, platform export comparisons, public
metadata responses and validation commands.

The non-Windows WEBKNOSSOS floor is now 4.3.3. Its cluster-tools dependency
allows typing-extensions 4.15.0, unblocking the following selected versions:

| Package | Before | After (non-Windows) |
| --- | --- | --- |
| WEBKNOSSOS / cluster-tools | 3.4.1 | 4.3.3 |
| aiohttp | 3.10.11 | 3.14.5 |
| python-dotenv | 1.0.1 | 1.2.4 |
| cryptography | 45.0.7 | 50.0.2 |
| typing-extensions | 4.12.2 | 4.15.0 |
| yarl | 1.23.0 | 1.25.1 |

The SDK no longer brings in scm-pims on these platforms; slicerator is also
absent from their resolved export. No maintained project caller imports either
package. Torch, NumPy, TensorStore, Google Auth and the AWS SDK retain their
locked versions. A marker-evaluated Windows export has **no selected package
version changes**. This is a resolver comparison, not Windows execution.

An upgrade request alone was insufficient: scratch resolutions removed
cryptography and downgraded its consumer, or selected the old SDK everywhere.
Those results were discarded. The explicit non-Windows SDK floor keeps the
consumer chain present; Google Auth remains 2.49.2.

Today's version-specific PyPI lookup reports **89 → 0 raw advisory records**
across the compared aiohttp, dotenv and cryptography versions. The record keeps
their IDs and response hashes. These are service records that can include
aliases, not a count of distinct reachable vulnerabilities or a fresh whole-lock
audit. Windows retains its older aiohttp/dotenv versions. Do not combine these
figures arithmetically with the November 10 or November 14 snapshots.

### Verification and remaining work

- A clean Python 3.10.21 environment installed the SDK/auth/data dependencies
  constrained to the candidate lock. Its dependency check passed on **87
  packages**. Four maintained modules passed **291 tests with no skips** in
  9.55 seconds, including all **81 fiber-label tests** with the real SDK,
  nested NML round trips, CLI publication and stubbed AWS transport failures.
- A separate six-module selection passed **323 tests with no skips** in 43.52
  seconds, including surface rendering, model construction, training-step and
  volume-inference checks. This run appended the existing CPU ML environment
  after the isolated environment's packages; the new SDK/auth/typing packages
  remained selected, while Torch 2.9.1 CPU came from that read-only fallback.
  It is not a fully installed CUDA environment. Initial setup failures from
  missing OpenCV and ML imports are retained in the migration record.
- A local native compatibility probe passed PKCS8 RSA signing, X509 PEM
  round trips, Google Auth signature/JWT verification and tampered-message /
  wrong-audience rejection with cryptography 50.0.2 and OpenSSL 4.0.3. It used
  an ephemeral key, no real credentials and no service requests. The report
  retains the probe source for replay.
- Maintained Ruff and offline universal lock consistency pass. No GPU, original
  data, Windows/macOS runtime, live WEBKNOSSOS service or optional microscopy
  image reader was validated. The complete curated suite was not repeated.

The owner-review row remains open for applicability and the other migrations.
Windows' SDK/TensorStore conflict remains; Virtualenv's newer Python 3.10
typing-extensions requirement also exceeds the new cluster-tools pin. The
previously inspected full-fix Tornado, Pillow and Filelock candidates require
Python 3.11. No unsupported constraint overrides or platform removals were used.

## Installed-package follow-up (2026-11-15 UTC)

This pass continues from `aef38996`. It closes the package-boundary item with an
explicit [wheel/checkout contract](PACKAGING.md). The research loop and pinned
Villa integrations use an editable checkout; the wheel supplies the library
modules, model definitions, augmentation module and local-volume wrapper.

A wheel built from the previous configuration reproduced three failures from
an empty directory: the inference factory could not import `vesuvius_model`,
the volume wrapper was absent, and the TIFF/PNG importer could not import
checkout-only `scripts`. Package configuration now includes the missing runtime
sources. The importer uses shared publication helpers under `core`; script
callers retain their existing import names. The five moved helper functions'
ASTs match their prior implementations, preserving path checks, rollback,
publication permissions and the requirement to serialize writers.

The [installation regression](../tests/test_wheel_installation.py) builds an
sdist, builds its wheel, installs into a fresh environment and launches isolated
Python from an empty directory. It requires project modules to resolve inside
that installation and verifies that `scripts` is unavailable. Raw third-party
CPU dependency directories are appended without loading their editable-install
hooks. The wheel's payload includes all runtime Python sources and the license;
checkout scripts, reports, datasets, reproductions and Villa are excluded.

The five installed-wheel checks passed in **16.85 seconds**. They exercise a
small CPU model forward, strict uint16 CT reads, lossless TIFF/PNG import, the
fiber CPU CLI and detector CLI help. An earlier focused selection passed
**251 tests** in 17.40 seconds. These overlapping runs are not additive. Mypy
passes on **1005 files**. The curated registry now contains **222 modules**;
the portable profile remains at **16**.

The [packaging review record](../reports/packaging_review_2026-11-15.json)
retains artifact/source hashes, the old wheel's failures, validation scope and
the final curated result. No dependency version, model architecture, research
registration, original dataset or live research environment changed in this
packaging pass. GPU execution, real-data scientific validation and broader
CPU/GPU dependency extras remain separate work.

The complete 222-module run finished with **6031 passed, 31 skipped, 1 xfailed
and 1 failed** in 584.74 seconds. The failure was the source-preservation check
invoking Ruff through the scratch interpreter: its Python module was visible
through the CPU dependency fallback, but its executable was absent from that
environment. After provisioning the locked Ruff 0.9.10 there, the final policy,
wheel and publication-mode selection passed **31 tests** in 22.41 seconds.
No product code changed after the full run; the full suite was not repeated.
The skips and expected failure retain their original coverage limits.

An sdist built directly from the actual checkout also builds a wheel. Its
Python payload hashes match the installed-test wheel, and its 48 declared
runtime requirements match the project manifest. These build/installation
checks close the packaging defect within the documented library scope; the
nine owner-review decisions above remain open.

### PR 428 review and current-main integration

The PR integrates main `c0eeecca`, including the accepted canvas-shift estimator
fix from PR 426. The combined wheel/importer/publication, checkout-import and
canvas selection passed **215 tests** in 38.28 seconds. Maintained Ruff, Mypy
on **1005 files** and offline lock consistency pass.

A separate fresh editable installation also resolves the model, augmentation,
volume and core helpers from its source tree when launched outside that tree.
An explicitly selected sibling checkout's `src` still takes precedence. Review
found no additional code defects within this scope. The packaging guide now
calls separately supplied trained checkpoints by name. The report retains this
review separately from the earlier complete-run and wheel evidence.

## Regional-memory follow-up (2026-11-15 UTC)

This pass starts from merged main `3581fe40`. The regional resource item now
has an opt-in [measurement path](VOLUME_INFERENCE.md#regional-memory-observations)
for both single-model and ensemble commands. `--profile_memory` adds phased
observations to the existing protected metadata sidecar. Default runs do not
initialize the profiler or gain a memory-profile field. No allocation policy,
probability recipe, model residency or scientific registration changed.

The profiler starts after first-checkpoint configuration and accumulator-budget
preflight, before constructing a model. It records process RSS and the OS's
process-lifetime high-water RSS, keeping their distinct sources and units. On
CUDA it records the selected device's name/capacity and Torch build, resets that
device's PyTorch peak counters once, and synchronizes at phase observations.
Those allocator peaks are cumulative and include already-live allocations;
they exclude other allocators, device-context overhead and other processes.
Sampling ends before the latest metadata JSON serialization. This is an
observed-counter record, not a capacity estimate or fit guarantee.

The [review record](../reports/regional_memory_review_2026-11-15.json) retains
source/lock hashes, scope, commands and the raw synthetic CPU observations:

- The regional/artifact/queue/runner/wheel selection passed **371 tests** in
  77.62 seconds. The final memory-profile/production selection passed **60
  tests** in 10.87 seconds, including optional uncertainty/coherence and the
  production callers of the shared metadata writer. These selections overlap.
- Tests verify opt-in behavior, unchanged probability arrays, byte units,
  CPU lifetime-peak scope, null unavailable peaks, selected-device CUDA calls
  with a single reset, unchanged memory refusal and absence of success metadata
  after a primary measurement failure. CUDA behavior uses mocked APIs.
- Fresh CPU CLI processes ran a small single-model case and two-member ensemble
  with synthetic uint16 CT and random, untrained `gated_unet` checkpoints.
  Profiling on/off produced exactly equal ink/fiber probability arrays. The
  recorded RSS values validate the collection path, not representative capacity.
- Mypy passes on **1007 files**; maintained Ruff, changed Python formatting and
  offline lock consistency pass. Psutil is now a direct dependency; its locked
  version remains **6.0.0**, and all resolved package versions are unchanged.
  The curated registry now has **223 modules**, with **16 portable modules**.

The nine owner-review items remain open. Actual CUDA counters and representative
4090 source/model/export settings still need a GPU run before choosing streaming
accumulators, sequential member residency or different limits. No full curated
suite repeat, real-data accuracy measurement, production-path memory profile,
Windows/macOS runtime check or GPU throughput result is supplied by this pass.

## Experimental-interface follow-up (2026-11-15 UTC)

This pass continues from local memory-profile commit `cd4a085f`. The interface
scope decision is now explicit in [Experimental interfaces](EXPERIMENTAL_INTERFACES.md):
retain the optional scalar-field TTA adapter and untrained shape demo, keep
legacy names training-only, and keep the primary regional recipe unchanged.
This closes that owner-review item; eight remain in the current list above.

The [review record](../reports/experimental_interface_review_2026-11-15.json)
captures before/after reproductions and source hashes:

- **TTA geometry:** batched TTA accepted a `[B,1,1,4]` output for a `[B,1,2,2]`
  input because the element counts matched, silently restoring the wrong grid.
  Sequential TTA also turned two global-head values `[1.5, 5.5]` into `[3.5,
  3.5]` by flipping the batch dimension. The adapter now validates spatial rank
  and batch size before deaugmentation and the full grid for batched mirroring.
  Valid sequential/coarser fields and axis-transpose paths are preserved.
- **Task contract:** homogeneous scalar heads can still concatenate, with one
  unsplit tensor returned. Mixed ink/fiber/global-QC ranks fail clearly without
  broadcasting. Per-view shape records preserve upstream model/concatenator
  call order, including custom callbacks and typed OOM fallback. Directional
  vector/tensor reorientation remains outside this scalar-field contract.
- **Gaussian safety:** zero/nonfinite or negative sigma and noninteger/nonpositive
  patch edges now fail explicitly; unrepresentable float32 windows cannot cache
  zeros/NaNs. Implicit CUDA cache keys resolve the current index, fixing reuse of
  a previous GPU's tensor. The cache-routing check uses mocked device selection.
  Default window arithmetic and all eight synthetic regional probability-array
  files remain byte-identical; no speed or accuracy improvement is claimed.
- **Volumetric demo:** a head declaring three layers previously returned four
  when given that depth. It now validates channels/depth and retains its class,
  parameter names, valid convolution and gradients. The smaller CPU demo prints
  untrained logits shapes and no longer presents random outputs as an ink result.
  `resnet3d`/`i3d` remain training-only names with unchanged inference rejection.

The nine-module regression selection passed **437 tests, 1 skipped** in 70.88
seconds. The skip requires CUDA for Villa's existing uint8-warp check; it is
unavailable coverage. New cases compare valid scalar TTA exactly with the
unchanged pinned implementation. Mypy passes on **1008 files**; maintained
Ruff, changed Python formatting and offline lock consistency pass. The curated
registry now has **224 modules**, with **16 portable modules**.

The pinned Villa TTA file, model definitions, primary probability recipe,
architecture dispatch/trainer and lock remain unchanged. No full curated suite,
real CUDA execution, legacy-model training, original-data measurement or trained
volumetric detector was supplied by this pass.

## Proofreader-input record follow-up (2026-11-16 UTC)

This pass starts from main `72dcb445`, after the memory/interface PR and the
concurrent PHerc. 0826 research merges. It advances the human-feedback provenance
subtask without deciding between 2D ink review and 3D categorical-label feedback.
All eight owner-review items remain open.

The [session-record guide](PROOFREADER_SESSION_RECORDS.md) and
[review record](../reports/proofreader_session_review_2026-11-16.json) describe
the opt-in `--record-session` launch and read-only checker. New sessions can now
retain hashes of every encoded file in their selected CT/label directories,
initial settings and the pinned proofreader source. Recorded launches use
explicit progress and edited-label paths. Source/entry/file budgets are checked
before receipt publication or GUI launch; normal launches remain unchanged.
Receipts precede the child and do not attest that the GUI ran or work completed.

Executing the unchanged pinned `load_progress` in isolation reproduces its
acceptance of a log naming different CT. The new checker rejects that mismatch,
changed chunks/metadata/inventories, malformed records, invalid progress entries
and changed proofreader source. Receipt/progress digests bind the exact captured
bytes that are parsed. It reports logged pending/approval counts without
authenticating approvals or verifying the TIFFs/edited-label output.

Resume stays disabled. Pinned Villa snaps the last logged coordinate to a new
grid, and its progress metadata omits complete GUI-setting history. Source
fingerprints cannot establish a safe resume position or approved-patch contents.
No regional window mask is broadcast through CT depth or adopted as an ink label.

An eight-module integration selection passed **332 tests** in 75.10 seconds,
including installed-wheel and regional inference/uncertainty checks. After
adding exact JSON-capture hashes and two additional reproduction/snapshot tests,
the final focused selection passed **62 tests** in 1.24 seconds. The document
and claim guards gave **138 passed, 1 skipped** in 39.89 seconds; the skip needs
absent local arm artifacts. These selections overlap. A fresh checker subprocess
from outside the checkout exits zero without changing files on matching synthetic
inputs and exits one after a CT chunk changes. Mypy passes on **1014 files**,
maintained Ruff and changed-file formatting pass, and offline lock consistency
resolves **258 packages** without dependency changes. The curated registry now
contains **225 modules**, with **16 portable modules**.

After staging the new sources, the registry, file-mode and preserved-source
guards passed **33 tests** in 11.64 seconds. Extracted repository-path references
in all three changed Markdown documents exist, and all six final source hashes
in the review record match their captured files.

Validation used the existing separate Python 3.10 CPU environments. No full
curated-suite repeat, hosted CI, Napari/interactive edit, original annotation
data, GPU measurement or automatic training ingestion was supplied by this pass.

## Official-fragment onboarding follow-up (2026-11-16 UTC)

This pass starts from main `798a546d`. The bounded source/example onboarding
item is closed by a [pinned Frag1 recipe](OFFICIAL_FRAGMENT_EXAMPLE.md), its
[download manifest](../configs/data/fr47_two_layers.json) and a
[real-data review record](../reports/official_fragment_example_review_2026-11-16.json).
Seven owner-review items remain. Scientific validation, independent physical
registration and the training read-policy decision remain separate work.

Five original files from the public PHercParis2Fr47 surface export total
**207,294,186 bytes**: TIFF slices 16 and 17, labels, mask and metadata. HTTPS
response sizes/digests are pinned; these are retrieved-file hashes, not separately
published upstream checksums. The new acquisition command rejects partial,
changed, oversized or redirected responses and publishes a new directory only
after complete checks. It preserves all original file bytes.

The actual official labels and mask are **palette PNGs** with indices 0/1 for
black/white. The generic importer correctly refuses them. A separate explicit
adapter verifies used palette RGB colors and prepares grayscale 0/255 labels;
it refuses transparency, intermediate colors and invalid image contracts. Its
synthetic reversed-palette case confirms that colors define classes, not index
nonzeroness. The generic palette refusal remains unchanged.

The real files passed the maintained importer plan/build and strict CPU reader:

- Every CT value in the prepared **[2, 8181, 6330]** uint16 array equals its
  original big-endian TIFF value. The stored array is little endian; both source
  planes retain the full 0..65535 range. The decoded CT digest is in the record.
- Both canonical PNGs match the original palette colors at every pixel, and
  surface metadata and all image dimensions agree on the supplied export grid.
  This does not independently prove physical registration or annotation truth.
- A single explicitly label-conditioned 64×64 fixture patch passes the strict
  labeled dataset, returning CT **[1, 2, 64, 64]**, matching binary labels and the
  documented zero fiber placeholder. CT normalization agrees exactly with the
  strict reader on this patch. This is a compatibility check, not a performance
  estimate or independent scientific sample.
- Source TIFF indices **[16, 18)** map to output depth **[0, 2)**, with origin
  `[16, 0, 0]`. Passing the source indices as the output depth band is rejected.
  The existing loop configuration and full-depth research recipe were not changed.

The six-module synthetic integration selection passed **189 tests** in 44.72
seconds. The final focused set, including bundled-manifest preflight, passed
**95 tests** in 5.51 seconds. These overlapping counts are not additive. The live
HTTP fetch preceded the final additional staged-byte readback check; that final
helper was then verified on all five actual files, and the final acquisition
path is covered by synthetic publication/failure tests. No extra full download
was needed. The curated registry now contains **226 modules**, with **16 portable
modules**. No dataset images or Zarr stores are committed.

The source example has only two slices. It does not provide the default model's
depth/context and must not replace the live loop's dataset. Source/grid provenance
does not establish training/validation independence. No training, GPU run, accuracy
measurement, full curated-suite repeat or Windows/macOS runtime check was supplied.

The configured document/claim guards passed **138 tests, 1 skipped** in 38.98
seconds; the skip requires absent local arm artifacts. After staging, registry,
file-mode and preserved-source guards passed **33 tests** in 11.02 seconds.
Mypy passes on **1021 files**, maintained Ruff and all four changed Python files'
formatting pass, and the unchanged offline lock resolves **258 packages**.
The real-data checks used Python 3.10.21, NumPy 2.2.6, Pillow 12.3.0, Zarr 2.18.3
and Torch 2.9.1 CPU in the separate SDK/CPU dependency view. This is not a fully
installed CUDA environment. All nine final source bindings match; extracted
repository-path references in the four changed Markdown documents exist.

## Command/runtime inventory follow-up (2026-11-17 UTC)

This pass starts from main `ee38dc92`. The dependency-scope item now has a
[reviewed command inventory](COMMANDS.md) and a
[review record](../reports/command_inventory_review_2026-11-17.json). All seven
broader owner-review items remain open. No dependency extra, Python/platform
policy, live environment or scientific default changed.

The new stdlib-only discovery command lists 27 primary entrypoints/modes and
their declared stacks, checkout/wheel layout, Villa requirements, side effects
and usage guides. It validates a bounded JSON capture and reports the hash of
the same bytes it parsed. It does not import targets, execute commands or check
experiment readiness. A fresh `python -S` subprocess from another directory
confirms discovery works without site packages and without file writes.
Production prediction still requires Torch for dry-run imports; the live
scroll-frames list CLI needs s3fs. These distinctions are recorded explicitly.

The inventory review exposed unnecessary NumPy imports in repeatability
planning: protocol metadata came through the array-based promotion module, and
output-path validation came through the labeling wrapper. The planner now
imports a stdlib-only metadata module and the existing core path helper directly.
The moved protocol function is AST-identical to its original; all four constants
are unchanged, and promotion reexports the existing API. Planning binds the new
metadata source among its selected input hashes and refuses execution if it
changes. This is not a fingerprint of the entire dependency/source closure.
A fresh `python -S` subprocess now produces an actual dry-run plan without
NumPy, a GPU, training data or output publication.

The planning/promotion/inventory integration passed **251 tests** in 60.51 seconds.
The portable profile passed **408 tests** across **17 modules** in 28.82 seconds.
The configured document/claim guards gave **138 passed, 1 skipped** in 34.61
seconds; the skip needs absent local arm artifacts. These selections overlap.
The existing multiprocessing spawn check required local IPC permission in the
sandbox; its initial EPERM was resolved without changing or skipping the test.
CPU smoke from a new empty directory gave **8 passed, 3 skipped, 0 failed** in
10.9 seconds. Its skips require a checkpoint or training CT/ink labels; the
review checkout's checkpoint was not loaded.

After staging, registry, file-mode, preserved-source and document-reference
guards passed **46 tests** in 33.91 seconds. All ten recorded source hashes match,
and 161 extracted local links exist across the six changed Markdown documents.
Mypy passes on **1035 files**. Maintained Ruff, all eight changed Python files'
formatting and offline lock consistency pass; the unchanged lock resolves
**258 packages**. The curated
registry now contains **227 modules**, with **17 portable modules**. Dependency
closures, Windows/macOS execution, real-data scientific reruns, GPU capacity,
interactive GUI behavior and a full curated-suite repeat remain unverified by
this pass. Historical sources and scientific records were preserved.

## Renderer-v2 real-source follow-up (2026-11-17 UTC)

This pass starts from main `57a849d8`. It advances the scientific-validation
item with a [new registered compatibility check](preregistration/2026-11-17_renderer_v2_1667_compatibility.md),
[result](../reports/render_revalidation_review_2026-11-17.md) and
[complete receipt/review](../reports/render_revalidation_review_2026-11-17.json).
The seven broader owner-review items remain open; the separate confidence
analysis and historical whole-segment/depth renderer experiments were not rerun.

The old comparison scripts use geometry validity when scoring, while the
corrected sampler exposes full-depth support. They and their historical
reports remain byte-identical. The new runner compares the same full-depth
mask at every fixed reference depth, refuses insufficient/constant comparisons,
captures exact source objects through an optional chunk-reader transport and
publishes only after source and plan rechecks. Default renderer transport and
numerical behavior remain unchanged.

Registration, source pins and tested runtime were committed as `f5612360`
before geometry/CT/reference payload acquisition and scoring. The fixed
128 × 128 PHerc1667 crop achieved maximum NCC **0.7889665783396356** against the
released surface volume, above the registered **0.60** gate. All **16,384**
pixels have full-depth support. One live attempt captured **82 objects**,
**175,582,829 bytes**, inside the **192 MiB** source budget. The receipt records
all five depth correlations and exact source/array identities. An offline replay
with a transport that forbids network access reproduces the three arrays bit
for bit and the same sampling/comparison records; independent NumPy correlations
agree within **1e-14**. This is replay of the same data, not independent replication.

The crop lies inside a historically selected interior region. Its full support
means boundary exclusion is verified by the synthetic regression, not this real
crop. Agreement with a released render does not establish ink accuracy,
independent physical registration, depth direction/spacing, OBJ auto-scale,
whole-scroll coverage or a 4090 capacity measurement. No raw payload or array
is committed, and no live research configuration, checkpoint or process changed.

The final synthetic integration passed **121 tests** in 10.38 seconds, including
the **23 new revalidation tests** and all **80 surface-contract** and **18 renderer**
checks. Registry, mode, preservation and configured document/claim guards gave
**171 passed, 1 skipped** in 50.92 seconds; the skip requires absent local arm
artifacts. Mypy passes on **1037 files**, maintained Ruff and all four changed
Python files' formatting pass, and offline lock consistency still resolves
**258 packages**. CPU smoke from a separate empty working directory gave
**8 passed, 3 skipped, 0 failed** in 14.7 seconds; its skips need a checkpoint
or training CT/ink labels. These selections overlap. The curated registry now
contains **228 modules**, with **17 portable modules**.

After adding the actual receipt and report, configured document/claim guards
passed **138 tests, 1 skipped** in 38.66 seconds. All fifteen selected source,
historical and additional file hashes match; 68 extracted local links exist
across the four changed Markdown documents. The old scientific scripts and
reports were checked byte for byte against the main baseline.

## Approved proofreader export verification (2026-11-17 UTC)

The input checker could report an approved log entry even when the image or
label TIFF was missing or the image came from a different crop. The opt-in
`--verify-approved-patches` check links the log to the complete saved TIFF pairs
and verifies each image voxel and dtype against the recorded CT crop. The
label check enforces the cubic patch shape and categorical range `0..255`.
The report includes each pair's ZYX origin and hashes of the bytes it decoded.
Repeated approvals at one origin fail because Villa uses one pair of filenames
for that origin. The check also refuses unlisted files and incomplete TIFFs.
The command and limits are in the [session-record guide](PROOFREADER_SESSION_RECORDS.md).

The check runs after the GUI closes. It applies the existing receipt limits to
the combined export directories and bounds the decoded TIFF, CT patch and CT
chunk sizes. Source and export state checks detect ordinary changes during
verification. The pinned Villa writer and serializer produced the TIFFs and
progress JSON in the regression fixture. The fixture uses synthetic CT and an
edited categorical patch. Approval authenticity, the edited-label Zarr and
physical alignment remain outside this verification. Resume and reviewed-label
ingestion still need design work. All seven broader audit items remain open.

The CPU integration selection passed **193 tests** across proofreader sessions
and launches, command discovery, volume reading and patch dataset artifacts.
The portable profile passed **408 tests**. Registry, file-mode, preservation
and document/claim guards passed **171 tests**, with one skip for absent local
arm artifacts. CPU smoke passed **8 checks**, with three skips requiring a
checkpoint or training inputs. Ruff, formatting and Mypy passed, and the offline
lock resolved **258 packages**.

PR review found that a contiguous TIFF could decode despite an incorrect
strip byte count. The checker now requires declared bytes to match the stored
page dimensions, including row padding for packed boolean images. The revised
integration selection passed **194 tests**. A separate check decoded **24**
default-writer TIFFs across packed boolean and numeric dtypes.

## Training patch catalog validation (2026-11-17 UTC)

The labeled loader on `b4702312` accepted an explicit origin `(10000, -200)`
on an 8 × 32 × 32 synthetic volume. Even with strict reads enabled, jitter
clamped it to the edge and returned a full patch. Explicit catalogs now
require a nonempty list and integer YX origins that fit the full patch. The
checker also validates producer count and size fields when present and caps
input at 16 MiB. It reports the file and invalid entry before sampling.

The loader hashes the captured JSON bytes it parses. Validation checks this
digest against the catalog in its existing input fingerprint. A regression
rewrites the catalog during dataset construction and restores it before the
final disk check. The run stops because the dataset parsed the other bytes.
An unchanged valid catalog produces the same fingerprint and patch tensors
as the baseline on the synthetic comparison, including repeated origins and
both jitter settings. The [catalog guide](TRAINING_DATA_IMPORT.md#supply-an-explicit-patch-catalog)
documents the geometry, ordering and file limits.

This advances the input validation part of the training read review. All
seven owner items remain open. A wider CT read-policy change still needs
real-data evidence on failures and a decision about retry or skip behavior.

The integration selection passed **525 tests**, with one CuPy-dependent skip.
It covered the real validation builder, labeled readers, patch selection,
checkpoint tools and spawned training workers. Registry, file-mode, source
preservation and document guards passed **171 tests**, with one skip for absent
local arm artifacts. CPU smoke passed **8 checks**, with three skips requiring
a checkpoint or training inputs. Ruff, formatting and Mypy passed. The offline
lock check resolved **258 packages**.

## Prepared fragment verification (2026-11-22 UTC)

The importer checked CT as it wrote it, and stored a decoded digest in
`import.json`. The reader could still substitute zeros for a chunk missing
from a later copy. In the padded-grid fixture, removing one all-zero chunk
left the entire decoded Zarr array identical. The new verifier rejected the
copy and named the missing chunk. It also rejects short chunks, altered CT,
changed layout or origin, and differences in the original label and mask
files. A relocated fragment passed through the CLI with its original sources
and separate manifest absent. [Verification usage](TRAINING_DATA_IMPORT.md#verify-a-prepared-fragment)

A fresh download using the pinned Frag1 example was imported and then checked
through the verifier. The two planes have shape `[2, 8181, 6330]` with 6,400
physical chunks and 209,715,200 bytes of padded CT storage. The decoded CT hash
`81844e156f8360062e8ab462f4bcb91ae64baeb6e7382e9e60455681053b3f59`
and both PNG hashes match the November 16 reference. This is an integrity check
on a two-slice import. Training read policy and representative failure-rate
measurements remain open. [Reference receipt](../reports/official_fragment_example_review_2026-11-16.json)

The CPU integration selection passed **267 tests** across the importer, pinned
fragment acquisition, volume and labeled readers, and command inventory. The
acquisition tests use local socket permission for the existing HTTP fixture.
The portable profile passed **432 tests**. Registry, file-mode, source and
document guards passed **171 tests**, with one skip for missing arm artifacts.
CPU smoke passed **8 checks**, with three skips requiring a checkpoint or
training inputs. Ruff, formatting, Mypy and the offline lock check passed.

PR review reproduced a failure when a copied receipt used source paths from
another operating system. Verification now accepts absolute Windows and POSIX
paths as provenance. The build command still requires paths it can open on the
host. The regression passed with the full **268-test** integration selection.
The revised verifier also repeated the Frag1 check with the same 6,400 chunks
and hashes.

## Validation image identity and Frag1 read failures (2026-11-22 UTC)

This pass starts from `d170b3b6` and advances the training read review. Two
regressions temporarily replaced the selected validation label or mask PNG,
let the real dataset load the replacement, then restored the original. The
previous before-and-after disk checks accepted the original fingerprint with
changed targets or patch coordinates. The validation reader now checks and
decodes the same captured bytes for each selected image. A third regression
changes the file after capture and checks that the decoder still uses the
captured bytes. The existing fingerprint format and catalog check are retained.
See [validation image checks](TRAINING_DATA_IMPORT.md#choose-the-training-read-policy).

PR review found that the initial fingerprint could read an oversized image in
full before the loader refused it. Both checks now use the same 512 MiB encoded
file limit. Fingerprinting inspects the opened file's size and hashes in blocks.
The added regressions cover both image roles and file changes during hashing.

On a temporary copy of the [two-slice Frag1 import](OFFICIAL_FRAGMENT_EXAMPLE.md),
the selected labels and mask produced the same validation fingerprint as the
parent implementation and identical CT, label and fiber tensors. The explicit
catalog origin was YX `(424, 3541)`. With seed 42 and the existing jitter the
reader sampled YX `(443, 3523)` with CT shape `[1, 2, 64, 64]`.

- Removing chunk `0.3.27` changed **3,904 of 8,192** CT voxels to fill values
  even under strict reads. Prepared-fragment verification rejected the missing
  chunk.
- Shortening that chunk by one byte made the strict patch read fail. Permissive
  mode returned a zero patch and counted one `labeled_zero_patch` warning.
  Restoring the chunk restored the original tensors.

These controlled failures show when strict reads can help and when the separate
receipt check is needed. They leave the training default and all seven owner
items open. The exercise measured neither a natural failure rate nor model
performance.

The eleven-module CPU integration selection passed **531 tests**, with one
skip. It covered validation, checkpoint re-evaluation, training inputs,
spawned workers, volume reading and fragment import. The portable profile
passed **432 tests**. Maintained Ruff, changed-file formatting and Mypy
passed. Mypy checked 1,090 files.

## Edited proofreader labels (2026-11-22 UTC)

This pass starts from main `2d7463cd`. The pinned Villa writer saves the
approved TIFF pair before writing its edited-label Zarr crop, and catches Zarr
write exceptions. An injected write failure produced a valid progress log and
TIFFs, while the Zarr still returned zero for the approved crop of category 42.
The TIFF-only checker accepted that pair within its scope.

The opt-in `--verify-edited-labels` mode checks each approved TIFF against the
corresponding edited Zarr crop after the standard CT and TIFF checks. It
rejects the failed write at the recorded ZYX origin. A normal write and an
approved all-zero sparse crop pass without changing the session files. The
edited Zarr's layout and byte limits are checked before crop reads, and a
second inventory checks for ordinary changes during verification.
[Verification usage](PROOFREADER_SESSION_RECORDS.md#compare-approved-labels-with-the-edited-zarr)

PR review reproduced a traceback from zero-sized chunks, acceptance of
wrong-rank chunk geometry until crop decoding, and an uncaught error from
incomplete Zarr metadata. It also reproduced acceptance of a source-label
change during export checks. The preflight now checks chunk geometry and
reports unreadable metadata. Both input directories are rechecked before
reporting export verification success.

The fixtures execute Villa's pinned writer and progress serializer without
opening the GUI. The report compares approved crop values. The category
semantics, physical alignment, values outside those crops, resume behavior and
training ingestion still need their own review.

The checker also ran from a separate working directory against a fixture
approved at ZYX `(0, 8, 0)`. It passed after the pinned write and exited 1 when
one edited voxel was changed. Both invocations kept all session bytes intact.
The nine-module integration selection passed **250 tests**. The final
proofreader selection passed **87 tests**, and the portable CPU profile passed
**436 tests**. Ruff, formatting and Mypy passed.
With the PR review fixes, the nine-module selection passed **254 tests** and
the CLI returned status 1 for all three malformed metadata fixtures.

## Training and validation crop depth (2026-11-22 UTC)

This pass starts from main `bd85f8e9`. The readers can return fewer context
slices than a trainer requests when a volume is shallow. The trainer drew
offsets as if every read had the full context. In a 21-slice fixture, offset
7 yielded 14 layers for a 16-layer model. A separate fixture scored an
11-slice validation read as complete for an eight-layer model with a fixed
offset of four.

Training now bounds the shared offset to the available labeled and UA-MT
read depths. It rejects sources shallower than the model window and groups
whose differing buffered depths would prevent batch collation. Validation
checks for enough slices to keep its fixed offset. Short runtime reads count
as failed batches, and the periodic AUC path uses the same fixed-window check.
[Depth requirements](TRAINING_DATA_IMPORT.md#check-depth-for-training-and-validation)

PR review found that zero, negative, boolean and fractional `num_layers`
values could reach the crop code. Training configuration, direct reader
construction and validation scoring now use the shared positive-integer
check. Training configuration can still load without Torch.

On CPU, 128 full-context cases matched the parent crop tensors and the next
random draw exactly across 32 seeds, augmentation on and off, and with and
without an unlabeled batch. The 21-slice fixture now yields 16 layers. These
checks exercise crop geometry. A representative failure-rate measurement
and the strict-training policy decision remain open.

The twelve-module CPU integration selection passed **576 tests**. Two skips
require CuPy and the local PHercParis2Fr143 volume, respectively. The portable
profile passed **436 tests**, and repository guards passed **46 tests**.
Ruff, formatting and Mypy passed.

## Selected training images (2026-11-22 UTC)

This pass starts from main `ca063025`. The trainer selected each labeled
source's image before model setup. When the selected file disappeared before
dataset creation, the loader skipped it and returned zero targets. Losing a
selected mask similarly removed the patch-selection constraint. The real
trainer fixture reproduced both behaviors in strict and permissive CT modes,
including with a conventional label file still beside a source whose selected
refined or pseudo-label file disappeared.

Supervised training now requires the selected label and any selected mask to
open. A missing selected image fails during dataset construction with its
path. An explicit training patch catalog replaces mask-based discovery, so
the trainer skips the unused mask. A real trainer fixture with an unreadable
unused mask reached the loader using its catalog coordinates. Sixteen
synthetic patch tuples matched exactly with and without requiring selected
images, across both read policies and with or without a mask. This checks
readability during setup. Read-failure frequency on representative CT and the
default CT read policy remain open.
[Training input behavior](TRAINING_DATA_IMPORT.md#choose-the-training-read-policy)

PR review reproduced automatic patch discovery silently ignoring a dangling
`mask.png` symlink. The trainer now treats that directory entry as a selected
mask, so opening it reports the broken path. Explicit catalogs still reach
the loader with their saved coordinates when the unused mask is unreadable
or a dangling link.

The twelve-module integration selection passed **666 tests**. Two skips
require the local PHercParis2Fr143 volume and CuPy, respectively. The
portable profile passed **613 tests** and repository guards passed
**46 tests**. Ruff, formatting and Mypy passed.

## File URI training inputs (2026-11-24 UTC)

This pass starts from main `edf8fc37`. The CT reader accepted local file URIs,
but the trainer and validator searched for annotations beside the literal URI.
A path containing spaces and `#` reproduced missing labels and patch catalogs.
The checkpoint guard also missed a pseudo-label whose decoded segment name
matched the configured checkpoint output. The regression stops before model
setup and checks that the label bytes are intact.

Training, validation, checkpoint protection and workspace status now use the
decoded local path. Sidecar lookup keeps a volume symlink's visible parent.
The same held-out data supplied as a path or a `file://localhost` URI produced
identical validation fingerprints, coordinates and patch tensors with both
automatic and explicit patch selection. The real trainer fixture loaded a
pseudo-label and catalog beside a visible alias whose CT lives elsewhere.
Remote source identity and registration remain open review items.
[Local volume identifiers](TRAINING_DATA_IMPORT.md#local-volume-identifiers)

PR review found a second lookup of URI-shaped local paths using the process's
working directory. A literal matching path there made workspace setup status
unknown and let the checkpoint guard miss the decoded pseudo-label. Both
lookups now use the inspected checkout. The two regressions simulate another
caller directory and preserve the selected pseudo-label.

The twelve-module CPU integration selection passed **732 tests**. Two skips
require CuPy and the local PHercParis2Fr143 volume. The final focused URI
selection passed **10 tests**, including the URI form of the UA-MT band
fixture. The portable profile passed **623 tests** and repository guards
passed **46 tests**. Workspace status ran under `python -S` from a separate
working directory and preserved the fixture files. Ruff, formatting and
Mypy passed.

## Per-run training fallback counts (2026-11-24 UTC)

This pass starts from main `fe6c25ba`. Two calls to the trainer in one Python
process shared cumulative warnings and augmentation fallback counts. A CPU
fixture with one previous loader warning and one new CT read failure
reported two fallbacks for the new run.

`run_result.json` now records the difference from the counters at the start
of each run, plus warnings from the run's workers. Review reproduced a
training worker still running during final validation. The trainer now
releases the training loaders and workers before final validation, then
reports the counts after validation. Console throttling still uses the
process counters. The report includes validation and any worker prefetch.
A CT read-failure rate still requires an attempted-read count and a
representative workload.
[Training read policy](TRAINING_DATA_IMPORT.md#choose-the-training-read-policy)

## Finished training CT backend reads (2026-11-24 UTC)

This pass starts from main `9fbab54a`. The training result reported zero-patch
fallbacks without a read denominator. The same warning could come from the CT
backend, normalization, or downstream patch construction. The report now
counts returned and raised backend calls separately for labeled and UA-MT
training. Each spawned worker writes to its own counters, and the trainer
reads them after worker shutdown. The counts include finished prefetches.

The CPU trainer fixture truncates a stored CT chunk, restores it, and repeats
the run. It checks that labeled reads move from raised exceptions to returned
results, that the UA-MT read is counted separately, and that validation reads
are excluded. The incomplete-return fixture confirms that returned values
can still fail the strict CT checks. A representative real-data failure-rate
measurement and a default read policy decision remain open.
[Training read counts](TRAINING_DATA_IMPORT.md#choose-the-training-read-policy)

## Validation predictions and targets (2026-11-24 UTC)

This pass starts from main `cbbfd25a`. A CPU model fixture returned infinite
logits with the correct sign at every pixel. Sigmoid mapped them to 0 and 1,
so final validation accepted the sample and the promotion decision accepted
its F1 of 1.0. The same pattern produced a periodic AUC of 1.0. Malformed
probability tensors and targets could also reach the metrics.

The trainer now uses the checkpoint tools' ink-logit check before sigmoid.
Both final validation and periodic AUC check the shape and range of
probabilities and their targets before scoring. A failed final batch marks
the sample incomplete and blocks promotion. A failed periodic measurement
records a missing AUC and lets training continue.

PR review reproduced a negative validation batch size yielding an empty
sample marked complete. A negative periodic sample limit also read nearly
the full catalog and reported AUC. Both settings now require positive
integers at the evaluation boundary.

## Proofreader input stability during verification (2026-11-24 UTC)

This pass starts from main `9895bbed`. The default proofreader check hashed
each source and then parsed the progress log. In two CLI fixtures, a CT or
label voxel changed during the progress read and the command still reported
`input_record_matches: true`. Both export verification modes already checked
their input inventories again before reporting success.

The checker now repeats both input inventories in the default mode as well.
The fixtures report the changed source and exit 1. These inventory checks
detect ordinary file changes during verification. The broader decisions on
coordinate alignment, resuming sessions and training ingestion remain open.
[Proofreader session verification](PROOFREADER_SESSION_RECORDS.md#what-verification-establishes)

PR review reproduced late changes to the receipt in the default mode and to
the pinned proofreader source in both default and export verification. These
files are now rechecked before either mode reports success.

## Recorded proofreader launch input stability (2026-11-24 UTC)

This pass starts from main `f067c111`. One launcher fixture changed a CT
voxel while the label tree was being hashed. Another inserted category 300
after label preflight and before source capture. Both published receipts and
reached the GUI subprocess boundary.

The recorded launcher now checks geometry and categorical values between
source capture and a final inventory check. It also rechecks the pinned
proofreader file before publishing. Both fixtures refuse the launch before
creating a session directory or receipt. Physical alignment, resume and
training ingestion remain separate audit items.
[Recorded launch](PROOFREADER_SESSION_RECORDS.md#what-is-recorded)

PR review found that path selection still opened Zarr metadata ahead of the
recorded source file limit. It now resolves the selected local arrays without
opening their metadata. A fixture with over-budget metadata checks that the
launcher refuses it before either array opens. A two-level OME fixture still
selects level 0 and produces a verifiable receipt.

## Local Zarr metadata at volume open (2026-11-24 UTC)

This pass starts from main `4fd33125`. The shared local reader accepted
zero-sized and wrong-rank chunks. It silently truncated fractional sizes and
converted booleans to integers. It also accepted a chunk separator that did
not match either supported local Zarr v2 convention. Malformed metadata could
raise a parser exception through the proofreader launcher.

The reader now checks the opened array's three positive integer shape and
chunk dimensions and its resolved chunk separator. Metadata parse failures
report the selected array path. Both recorded and normal proofreader launches
refuse malformed metadata before opening the GUI or publishing a receipt.
This checks geometry and layout. A standard Zarr read can still substitute
fill values for absent chunks. Use the separate receipt check for prepared
training stores.
[Prepared fragment verification](TRAINING_DATA_IMPORT.md#verify-a-prepared-fragment)

PR review reproduced a separate path in the edited-label verifier. An invalid
separator made the reader return zero fill for stored nonzero edits, and the
comparison accepted two all-zero TIFFs. The edited-label verifier now uses the
same separator check before reading the approved crops.

## Volume benchmark report destinations (2026-11-24 UTC)

This pass starts from main `13f06abb`. The benchmark promised to publish its
optional JSON report outside both the declared source and the selected array.
Its CLI checked the declared root alone. A local file URI selecting a group
with a linked level 0 successfully wrote a report into the selected array.

The CLI resolves both paths before timing reads and refuses report destinations
in either directory. Path planning uses the same selector as the reader and
avoids opening the array an extra time before timing. The fixture now exits
with an overlap diagnostic and leaves the input directory intact.
[Volume-read benchmark](LOCAL_VOLUME_READS.md#comparable-repeated-read-timings)

PR review retargeted the level-0 link between planning and the benchmark
open. The first fix still wrote into the array actually read. The publisher
now also checks the resolved root and array recorded by the measurement.

## Linked Zarr arrays in training split checks (2026-11-24 UTC)

This pass starts from main `9c62e57e`. Two configured Zarr groups could point
their level-0 links at one array while passing the holdout split check. Real
trainer fixtures using a linked group as labeled or active UA-MT input reached
Torch setup even though the reader would use the holdout array.

The split check and volume wrapper now use the same stat-only array selection.
Setup compares both the configured roots and the resolved arrays before the
trainer opens labels or initializes the device. A bare array still takes
precedence over any unused level-0 link. Copied or physically overlapping crops
still require split review.
[Workspace split diagnostics](WORKSPACE_STATUS.md)

PR review reproduced the same path gap in checkpoint preflight. A checkpoint
destination could name a chunk in an external level-0 array while the guard
protected only the configured group. The guard now also protects the selected
array for training, validation and active UA-MT inputs. The real-trainer
fixture confirms refusal before Torch setup and preserves the chunk bytes.

## Depth bands for linked Zarr arrays (2026-11-24 UTC)

This pass starts from main `8fe5d55c`. The depth-band matcher inferred local
array identity by removing a trailing `0`. A linked level 0 could read the
same array while losing the recorded band. In a CPU prediction fixture the
linked view started at Z=2 instead of the band's Z=1. A UA-MT fixture read the
same CT over its whole depth. The old matcher also conflated separate bare
arrays when one was stored in a directory named `0` under the other.

The matcher now uses the same local array selector as the volume reader.
The inference and UA-MT fixtures recover the band, and distinct bare arrays
keep separate depth decisions. Remote version identity and the offline
spelling fallback remain supported. Copied volumes and physically overlapping
crops still need independent alignment and split review.
[Regional inference depth selection](VOLUME_INFERENCE.md)
