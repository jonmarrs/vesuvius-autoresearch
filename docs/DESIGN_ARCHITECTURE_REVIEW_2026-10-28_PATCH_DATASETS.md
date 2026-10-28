# Patch dataset design and architecture review — 2026-10-28

Reviewed the filtered patch dataset and STRIPMATCH builders against main
`289f9ffb2dd755b666a84295c53860a94cee2eb4` (PR #280). The review covers selection
input interpretation, seeded aggregation, filesystem publication and operator
instructions. All executions used synthetic inputs in an isolated checkout.
No live study results/journals, historical dataset rebuilds, GPU jobs, research
deployment or prize filing were performed.

## Findings and fixes

- **Relative sources produced broken symlinks.** The filtered builder wrote a
  caller-relative source path into links interpreted relative to the destination.
  Both builders now plan canonical absolute targets, including external patch
  and auxiliary symlink targets.
  Both source and bootstrap patch containers are protected when the container
  itself is a symlink, so new outputs cannot pollute an external input directory.
- **STRIPMATCH merged selections on reuse.** Existing directories were accepted,
  and old patch links remained beside the newly drawn IDs. Both builders now
  require new, input-disjoint destinations and stage the complete selection and
  manifest before publication. A caught link/write/input-verification failure
  leaves no new completed output. Appearing destinations are preserved.
- **Malformed input could silently alter the population.** Duplicate reference
  IDs were overwritten, missing geometry was skipped, and unknown bootstrap IDs
  were intersected away. A shared bounded JSON reader rejects ambiguous records,
  unsafe IDs, invalid fractions/areas and empty populations. STRIPMATCH requires
  geometry for every scored patch and a valid, nonempty bootstrap set.
- **Sums depended on ID iteration order.** Under the required Python 3.10 runtime,
  area values `1e16, 1, 1` produce different totals in opposite iteration orders.
  Set ordering varies between processes. STRIPMATCH profiles now sort IDs before
  aggregation so targets and diagnostics use a stable order. The greedy draw,
  weighting formula and matching tolerances remain in place.
- **Selection had no durable build record.** Each new dataset includes
  `.autoresearch-selection.json` with selected IDs/hash, counts, achieved and
  target area, reference path/hash/size, settings and relevant strip/geometry
  provenance. Extra metadata cannot override core selection facts. Status is
  PREPARED, without a scientific-success claim.
- **Stability CLI accepted an unusable single draw.** It now requires 2–1,000
  draws (or 0 to build), verifies captured inputs, and reports observed overlap
  without asserting that different seeds necessarily produce different subsets.
  RANDOM's summary now correctly describes area matching rather than count
  matching.

The three original regressions all failed on the baseline: relative link
readability, existing STRIPMATCH preservation, and cleanup after an injected
link failure. Their captured result was **3 failed in 0.22s**. Additional tests
cover exact manifest/link membership, seeded RANDOM parity, source/output aliases,
bounded/strict JSON, missing geometry, input drift, appearing destinations,
stability behavior and actual CLI calls from a different working directory.

## Architecture decisions

`scripts/patch_dataset_artifacts.py` owns input captures, path plans, geometry
validation and new-directory publication. It reuses the existing stdlib
`Snapshot` for bounded UTF-8 captures; these builders still need no ML imports.
The selectors keep their existing scientific roles and pure selection APIs.
The shared publisher cannot replace existing outputs or let metadata replace
selection facts. Reference and geometry captures are checked again before
publication; geometry verification retains hashes rather than all metadata
payloads in memory. Source link mappings and bootstrap membership are rechecked.

The selection manifest binds the preparation inputs it records, not the full
linked dataset. Patch payloads and auxiliary file contents remain mutable source
dependencies. Writers must be serialized; publication is a same-filesystem
directory rename, not a concurrent-writer or crash-recovery protocol. A killed
process may leave hidden staging. Historical scientific measurements and
preregistrations have not been amended or reinterpreted.

[Patch dataset selection](PATCH_DATASET_SELECTION.md) documents the commands,
limits, matching semantics and required independent checks. Four related test
modules are now part of the curated validation registry.

## Verification

From `/tmp`, with cached dependencies:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python /workspace/vesuvius-patch-review/scripts/run_validation_tests.py --match '*patch_dataset_artifacts*' --match '*build_stripmatch_dataset*' --match '*check_patch_selection*' --match '*check_patch_spatial_balance*' --match '*validation_runner*' --match '*validation_suite_covers_the_loop*' -- -rs
```

Captured: **6/149 curated modules; CUDA hidden; 100 passed in 6.93s**. This covers
the new artifact contracts, existing scientific selector and checker regressions,
the validation CLI and its suite membership guard. Real subprocess cases use
small local patch directories with synthetic reference/geometry JSON, including
canonical links after publication from an unrelated caller directory.

From `/workspace/vesuvius-patch-review`:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
/tmp/vesuvius-pr256-lint/bin/ruff check scripts/patch_dataset_artifacts.py scripts/build_filtered_patch_dataset.py scripts/build_stripmatch_dataset.py scripts/run_validation_tests.py tests/test_patch_dataset_artifacts.py
/tmp/vesuvius-pr256-lint/bin/ruff format --check scripts/patch_dataset_artifacts.py scripts/build_filtered_patch_dataset.py scripts/build_stripmatch_dataset.py scripts/run_validation_tests.py tests/test_patch_dataset_artifacts.py
PYTHONPATH=/tmp/vesuvius-pr256-types python3 -m mypy --follow-imports=skip --explicit-package-bases --namespace-packages --cache-dir /tmp/vesuvius-patch-mypy scripts/patch_dataset_artifacts.py scripts/build_filtered_patch_dataset.py scripts/build_stripmatch_dataset.py scripts/run_validation_tests.py tests/test_patch_dataset_artifacts.py
git diff --check
```

Smoke: **8/11 passed, 3 skipped, 0 failed in 16.5s**. Two dataloader checks
lacked local training data; optional bg2 augmentation was unavailable.
Matplotlib/fontconfig emitted cache-directory warnings. Ruff check/format passed,
scoped mypy found no issues in five files, and whitespace checks passed.

## Limits

No full curated-suite run, production-size metadata/patch corpus, scientific
endpoint, GPU inference or research-host deployment was tested. Source/reference
identity is declared by the caller; metadata checks do not establish that a
reference fit or bootstrap directory came from the same immutable payloads.
The independent registered selection/spatial checks remain necessary before
future fits. RANDOM's greedy area draw can overshoot for coarse patches; the
manifest reports the achieved area rather than declaring an area-match pass.
