# Manual-review queue design and architecture review — 2026-10-28

## Scope

Reviewed the setup inspector, catalogue helpers, geometry worklist builder and
active-learning workflow against remote main
`63ba17fa09818aa41622584154c3a098f12aaa95` (PR #275). The fixes focus on the
active-learning queue's numerical scoring, patch identity, publication and
operator controls. This is not a certification of the entire research system.
All execution used synthetic inputs in an isolated checkout, with CUDA hidden.
No live study measurements or research-host runtime files were used.

## Findings and fixes

| Finding | Result |
| --- | --- |
| Entropy added `1e-8` before logarithms. In float16 this underflowed to zero, producing NaN at valid probabilities 0 and 1. Float64 endpoints were slightly negative. | Use `xlogy`'s defined zero term and promote low-precision probabilities to float32. Entropy is finite and nonnegative at endpoints, with maximum ln(2) nats. |
| Queue JSON opened the requested destination with mode `w` after inference. It could overwrite a checkpoint, labels, patch catalog or previous queue, or write into the input Zarr. Serialization failure could leave a partial queue. | Require a new source-disjoint output before loading the model. Use the existing staged new-file publisher and check the destination again before publication. Default output filenames carry a UTC timestamp. |
| Sequential sampler checks accepted subclasses with reordered iteration. A custom collator or unordered worker delivery could also reorder patches while the sampler still associated scores with sequential coordinates. | Require standard sequential sampling/batching, default collation and ordered delivery. Validate and capture coordinates, check emitted counts and reject catalog mutation during scoring. Duck-typed loaders remain responsible for their stated ordering contract. |
| Equal scores were reversed through an unstable sort, without a documented tie rule. | Sort descending stably and keep evaluated catalog order on ties. Seeded subsamples are restored to source order before evaluation. |
| Label discovery duplicated training/validation precedence and mishandled trailing volume slashes. | Reuse the standard-library label-path helper, including refined/filled/original precedence; preserve the existing local-data fallback. |

Before implementation, the endpoint/output regression subset reported
**10 failed, 1 passed**. Separate ordering probes reported **3 failed**, covering
reversing collation, a reversing sequential-sampler subclass and unordered delivery.
These probes use synthetic inputs, including fake checkpoint bytes for overwrite
checks, so they do not endanger a real model.

## Features and operator experience

`--min-distance` optionally requests a wider spread of annotation suggestions.
The sampler visits candidates by decreasing entropy and accepts a patch only
when its center is at least the requested Euclidean y/x distance from previously
selected patches. A zero distance preserves score-only selection. Patch sizes
are constant, so distances between centers equal distances between top-left
coordinates. This heuristic can return fewer than the requested count, and does
not guarantee nonoverlap, an optimal spread or accuracy gains.

`--max-eval-patches` exposes the existing inference budget, from 1 to 5000.
Larger catalogs use the existing seed-42 sample without replacement. The cap
limits model evaluations; it does not bound discovery/loading costs or model
VRAM. The queue records the selection policy, distance, budget, seed and actual
counts. Scores remain prediction ambiguity, not calibrated confidence or error
measurements. No automatic label acceptance or SAM2 integration is added.

The CLI accepts hyphenated sample-count/catalog aliases, returns concise errors,
prints requested versus returned counts and chooses a fresh default destination.
Explicit destinations no longer overwrite prior files. Existing JSON entry keys
remain, with additive selection metadata and an offset-qualified UTC timestamp.
Input path references are not content fingerprints or immutable source evidence.

## Architecture decisions

- Keep numerical scoring and deterministic selection in the existing sampler;
  avoid introducing a second ranking implementation for the CLI.
- Reuse the shared label-path and immutable-file publication helpers. Do not add
  another output writer or subtly different label-priority rules.
- Validate cheap arguments and output separation before checkpoint/model loading.
  Validate the full supplied catalog before subsampling; out-of-bounds coordinates
  must not be hidden by a small inference budget.
- Retain strict checkpoint reconstruction, complete weight loading, checkpoint
  depth/ridge settings, strict data reads and non-jittered coordinates.
- Treat custom reordering as unsupported rather than guessing patch identities.
  Supporting arbitrary collators would require explicitly carrying row identities
  through the data loader in a separately designed interface.

## Verification

Commands run from `/workspace/vesuvius-workflow-review` with existing cached
dependencies, without installing packages or changing credentials:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python -m pytest -q -rs tests/test_active_learning_queue_contracts.py tests/test_active_learning.py tests/test_checkpoint_tool_contracts.py tests/test_volume_inference_contracts.py tests/test_production_predict.py tests/test_predict_checkpoint_loading.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
/tmp/vesuvius-pr256-lint/bin/ruff check scripts/active_learning_sampler.py scripts/run_validation_tests.py tests/test_active_learning_queue_contracts.py
/tmp/vesuvius-pr256-lint/bin/ruff format --check scripts/active_learning_sampler.py scripts/run_validation_tests.py tests/test_active_learning_queue_contracts.py
PYTHONPATH=/tmp/vesuvius-pr256-types python3 -m mypy --follow-imports=skip --explicit-package-bases --namespace-packages --cache-dir /tmp/vesuvius-queue-mypy scripts/active_learning_sampler.py scripts/run_validation_tests.py tests/test_active_learning_queue_contracts.py
PYTHONPATH=src CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python -m scripts.active_learning_sampler --help
git diff --check
```

The native CPU integration case builds a gated UNet, saves complete weights,
reconstructs them through the real checkpoint helper, reads a real synthetic
Zarr and explicit patch catalog, and writes a queue through the real publisher.
It checks finite scores, spacing, actual evaluated/returned counts, score order,
and preservation of checkpoint and CT contents. Other tests cover aliases,
invalid requests, ties, catalog mutation, ordering violations, source/output
aliases, partial-write cleanup, a destination appearing during inference,
fresh default outputs and concise subprocess CLI failures. The new module is
included in the lightweight validation runner.

Final results: **246 passed, 17 skipped in 44.76 seconds**. The 17 skips all
concern optional fiber-coherence imports without `nrrd`; they are not covered by
this run. Smoke: **8 passed, 3 skipped, 0 failed in 19.6 seconds**. Two smoke
data-loader checks lack local training data; the optional bg2 augmentation entry
point is unavailable. Fontconfig emitted an unwritable-cache warning without a
failure. Ruff and formatting passed for three files; targeted mypy reported no
issues in three files with imported implementations skipped. The CLI help and
diff whitespace check passed. There are 35 new regression/integration cases.

Review also checked local volume spellings: the path guard protects local
`file://` URIs and existing local names containing a colon, instead of treating
every URI-shaped string as a remote resource. Explicit nonlocal file authorities
are rejected. Both supported local spelling cases have preflight regression tests.

## Limits

No native GPU performance, human annotation benefit, model accuracy, prize
eligibility or live deployment was tested. The 4090-relevant value is an optional
smaller evaluation budget and less spatially redundant human-review suggestions;
there is no measured quality or prize claim. Inputs must remain stable and
writers serialized; publication is not a concurrent-writer API. External callers
using custom collators/sampler subclasses must adopt the supported loader or
design explicit patch identities before using the sampler.
