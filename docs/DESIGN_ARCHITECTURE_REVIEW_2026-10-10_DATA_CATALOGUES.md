# Design and architecture review: local data catalogues

Reviewed baseline c4c53a5e after the merged experiment-report review and tracer
report updates. This pass covers local-file inventory and the label atlas:
bounded input discovery, interpretation, image/mask validation, source identity,
publication, CLI failures and visual layout.

## What changed

Publish a bounded metadata inventory and a bounded binary-label overview into
new, verified bundles, with explicit inspection scope, source fingerprints,
exact image counts and clear mask status.

## Why

The old inventory inferred readiness and coverage from names and apparent size,
followed symlink loops, and overwrote reports. The atlas crashed for one
fragment, accepted ambiguous labels, claimed mask validity from file presence,
disabled image-size protection, and independently overwrote PNG/SVG assets.

## Findings and repairs

| Priority | Verified problem | Repair |
|---|---|---|
| P1 | A sparse file in a directory ending in the expected suffix earns a readiness status. Total size and division coverage are hardcoded or inferred from names; small/root entries are omitted. | Report complete bounded path metadata and apparent bytes without readiness, identity or coverage inference; qualify the committed old manifest as historical and unverified while preserving its rows. |
| P1 | The atlas accepts RGB/arbitrary grayscale labels and treats any existing mask path as valid. | Reuse the binary PNG contract, normalize 0/1 and 0/255, reject invalid selected sources, and check optional mask encoding, YX shape and positive support. State that CT registration and label truth are unassessed. |
| P1 | Recursive directory-size calculation follows symlink targets, including loops and external files; image safety is disabled and the entire atlas is unbounded. | Use iterative lstat-based discovery, close scan/read handles, exclude symlink targets and special-file contents, and enforce entry, depth, selected-fragment, PNG-byte and pixel budgets before decoding. Retain Pillow protection. |
| P2 | A single-fragment grid wraps the axes array incorrectly and crashes. Zero/one labels render nearly black. | Flatten a guaranteed 2D axes grid and render normalized binary thumbnails with fixed grayscale bounds. |
| P2 | Missing inventory roots and empty atlases exit successfully; invalid label reads are silently skipped. | Explicit roots, limits and new destinations, with nonzero errors and no partial publication. An empty metadata inventory remains a valid explicit zero observation. |
| P2 | Fixed output names overwrite prior reports; independent PNG/SVG writes can leave inconsistent artifacts and provide no input provenance. | Stage and verify the complete bundle, record output hashes and source metadata, embed identical selected-source hashes in PNG/SVG, and check stable inputs before using the existing immutable publisher. |
| P2 | Full long names produce captions that overlap the tall image in the previous row; automatic aspect positioning moves headers within a row. | Align headers at the top, reserve two caption lines, truncate long names with a visible marker and JSON flag, and retain full names in JSON. Use explicit text/background colors and canvas bounds without changing caller plotting state. |

Initial regression command:

~~~bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_data_catalogue_contracts.py -q --no-header --tb=short
~~~

Captured: **9 failed in 3.00s**. Tiny temporary sources reproduce the single-grid
crash, RGB acceptance, unchecked mask shape, symlink cycle/external counting,
sparse-file readiness, overwrite, and missing/empty false success. No real
datasets or historical output assets were changed.

The visual layout defect was independently reproduced before its repair:

~~~bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_data_catalogue_contracts.py -k long_caption -q --no-header --tb=short
~~~

Captured: **1 failed, 127 deselected in 1.77s**. The renderer's measured long-title
bounds intersect the tall preceding panel. Two final regressions cover long
underscored names and spaced names; bounds no longer intersect.

## Architecture decisions

Keep bounded listing, stat signatures, byte capture, PNG validation, fingerprints,
name escaping and JSON readback in the shared data-catalogue helper. Inventory
and atlas retain separate semantics: inventory reads metadata only; atlas reads
and hashes only the selected binary PNGs, retaining small thumbnails rather
than all full-size arrays. Exact counts precede resampling.

Reuse the existing binary decoder, source/output separation, finite JSON writer
and new-directory publisher. No new dependency, training invocation or dataset
producer is introduced. CLI/output migration, budgets and source-stability
assumptions are documented in [Local data catalogues](DATA_CATALOGUES.md).
The root itself is excluded from the entry count; hardlinks count once per
pathname and sparse files contribute apparent bytes.

Both workflows require stable local sources and serialized writers. Rescanning
detects changed metadata; selected-image rehashes detect content changes even
when stat metadata is preserved. Inventory metadata hashes are explicitly not
content hashes. These checks do not claim an adversarial filesystem snapshot,
CT registration, ground-truth lineage, independence or eligibility.

## Verification

Focused final regressions:

~~~bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_data_catalogue_contracts.py -q --no-header --tb=short
~~~

Captured: **129 passed in 15.24s**. The suite checks actual PNG/SVG generation and
metadata, binary encodings, mask shape/support and exact counts, safe traversal,
limits, source hashes, immutable destinations, failure rollback, source changes,
CLI execution outside the checkout, caller plotting state and caption geometry.
These regressions are included in standard validation.

Design inspection:

~~~bash
.venv/bin/python scripts/generate_manifest.py --root /tmp/vesuvius-data-catalogue-review-igp_45k8/local_data --out /tmp/vesuvius-data-catalogue-review-igp_45k8/inventory
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/generate_training_atlas.py --root /tmp/vesuvius-data-catalogue-review-igp_45k8/local_data --out /tmp/vesuvius-data-catalogue-review-igp_45k8/atlas_final_layout --limit 7
~~~

Captured: both commands publish successfully. The inventory records **13 regular
files, 3,911 apparent bytes**, and an ignored directory symlink. Seven synthetic
label sources exercise equivalent 0/1 and 0/255 encodings, zero ink, absent masks,
tall/wide aspect ratios, outside-mask ink and a long name. The final **2250 by
1950** PNG was visually inspected: all seven headers are aligned and legible,
unused panels are blank, and the long caption no longer overlaps another image.
The exact counts/full name remain in JSON. The inventory Markdown and final
PNG/SVG byte counts and SHA-256 values were independently checked from the
generated JSON. This is rendering evidence, not new experimental evidence.

Standard validation:

~~~bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py
~~~

Captured: **1469 passed, 3 skipped, 1 xfailed, 9 warnings in 184.47s (0:03:04)**.
All standard workflow checks pass, including the final 129 catalogue
regressions. Existing optional skips and the expected upstream failure retain
their conditions; warnings concern CPU data-loader pinning. The complete suite
was rerun after the visual layout repair.

Required smoke:

~~~bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py
~~~

Captured: **8/11 passed, 3 skipped, 0 failed in 21.6s**. Imports, architectures,
auxiliary heads, best-checkpoint compatibility, augmentations and bandit
templates pass. Two missing local-data fixtures and the unavailable optional
batch-generators transform account for skips.

Documentation, claims, filing numbers and upstream parity:

~~~bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_filing_2026_10_numbers.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_soft_count_report_numbers.py tests/test_tracer_rescore_numbers.py tests/test_tracer_frozen_numbers.py -q --no-header --tb=short
~~~

Captured: **110 passed, 16 skipped in 30.04s**. Available checks pass, including
the tracer-report additions on main. Skips require a missing sibling ScrollGT
checkout or external render artifacts. Historical experiments were not rerun.

Final reference and claim check after completing the review:

~~~bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py -q --no-header --tb=short
~~~

Captured: **16 passed in 3.54s**. Completed operator and review documentation
passes the reference and claim guards.

Typing:

~~~bash
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python
~~~

Captured: **Found 16 errors in 13 files (checked 632 source files)**. Existing
repository typing failures concern missing YAML/requests stubs, OpenCV overloads,
augmentation slices, loader tensor-list annotations and training tensor-list
mean/variance calls. None are in changed files; typing remains a failing
repository check.

Lint, format and whitespace:

~~~bash
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff check scripts/data_catalogue.py scripts/generate_manifest.py scripts/generate_training_atlas.py tests/test_data_catalogue_contracts.py scripts/run_validation_tests.py
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff format --check scripts/data_catalogue.py scripts/generate_manifest.py scripts/generate_training_atlas.py tests/test_data_catalogue_contracts.py scripts/run_validation_tests.py
git diff --check
~~~

Captured: **All checks passed!**, **5 files already formatted**, and no
whitespace diagnostics. Cached lint and typing tools ran offline; no dependency
changes were needed.

## Edge cases considered

Symlink loops, external targets, directory aliases, broken links, hardlinks,
sparse files, root files, empty roots, special files, inaccessible entries,
nested entry limits and depth boundaries; invalid/boolean/nonfinite/out-of-range
limits; label candidate selection and uninspected sources; RGB, RGBA, palette,
16-bit, corrupt and disguised JPEG inputs; binary encodings, mixed 1/255,
zero ink, absent/invalid/empty/wrong-shaped masks; byte/pixel and Pillow safety
limits; source changes during capture, appearing masks, changed listings,
same-metadata image content changes; existing/appearing destinations, second
image and JSON failures; single/multiple grids, tall/wide previews, long/spaced
names, literal math/control characters, Markdown escaping, explicit canvas
bounds, preserved plotting state and outside-checkout CLI invocation.

## What was NOT tested

Full local-data scans, full-scroll decoding, GPU/training execution, historical
experiment recomputation, independent CT/label registration, ground-truth
lineage, held-out eligibility, scientific quality or performance on production
datasets. Visual inspection uses synthetic binary arrays. Images above the
documented hard bounds require explicit smaller inputs. Metadata inventory
does not detect content changes that preserve stat metadata. Source bytes are
hashed but not copied into the bundle; future independent verification needs
retained sources. The publisher assumes stable sources and serialized writers.

## Reviewer focus

Check the distinction between metadata inventory and selected-image validation,
the explicit absence of readiness/registration claims, and verified paired
publication with source-stability checks.
