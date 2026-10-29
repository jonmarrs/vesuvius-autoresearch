# Design and architecture review: patch-selection input bindings

Baseline: `337dd1be` (main after PR #290). Scope: BOOTSTRAP/RANDOM/STRIPMATCH
preparation, selection manifests and pre-fit input checks. No study endpoints
were read and no historical datasets, results or registrations were changed.

## Findings and fixes

### Selection records were written but ignored

The builders publish `.autoresearch-selection.json`, but neither checker nor
the STRIPMATCH builder read it. A changed reference, retargeted patch link or
generated RANDOM dataset passed as BOOTSTRAP could therefore be processed as
though it were the prepared input.

The shared, standard-library `patch_selection_manifest.py` now checks present
records against the captured reference hash/size, actual selected IDs/hash/count,
scored population count, selected area, declared source paths, roles and
thresholds. BOOTSTRAP must include the complete threshold selection. Checked
arm records must agree on the full source and, for RANDOM, the threshold.
The spatial checker also binds a supplied FULL path to the recorded source.

STRIPMATCH validates its bootstrap record before drawing, captures its resolved
membership/targets and records the manifest binding as a dependency. Its output
is checked against the supplied bootstrap IDs/path and, when recorded, the
bootstrap manifest snapshot. Dependency identity uses stable status/path/hash/size
fields, so additions to derived report fields do not invalidate it. Records and
mappings are rechecked before returning
a successful check or publishing a dataset. Identical reference bytes at another
path remain usable; a content change requires a new preparation.

Present invalid manifests always fail. `--require-manifests` additionally
rejects absent records in both checkers and the STRIPMATCH builder. The default
continues to support legacy inputs, explicitly reporting their records as
`absent` and provenance unverified. The preparation guide recommends strict
mode for new builds. JSON reports expose the requirement and per-arm bindings.

### Directory aliases could masquerade as separate evidence

The selection checker accepted one directory as both arms, and two different
IDs could resolve to the same physical patch directory while counting its area
twice. The baseline reproduced both defects with a passing report.

Both checkers now reject the same physical patch container as BOOTSTRAP and
control, including root/container symlink aliases. A shared device/inode check
also rejects duplicate patch targets in the source population and checked arms.
Overlap of patch IDs between distinct arm containers is still allowed: this
does not impose a new disjointness or statistical-independence requirement.
Looping source links fail with the builders' normal refusal messages rather
than an uncaught traceback.

## Architecture and limits

The existing bounded JSON capture and reference validation remain the source of
truth; parsed fields and recorded hashes come from the same captured bytes.
The builders and checkers share binding validation instead of independently
interpreting the manifest. The established random draw, geometry proxy, area
tolerances and historical measurements remain unchanged.

`checked` means the specified manifest/input bindings hold at inspection. It
does not authenticate the author, replay generation or verify every metadata
claim. Reports explicitly retain `generation_replayed: false`,
`payload_contents_hashed: false` and `scientific_validity_verified: false`.
Payloads can still change behind live links. These are mechanical checks, not
an immutable training lineage, validation of reference quality or proof of
statistical power. Inputs must remain stable; no writer locking is added.

## Verification

```sh
MPLCONFIGDIR=/tmp/vesuvius-lineage-mpl XDG_CACHE_HOME=/tmp/vesuvius-lineage-cache \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-chain-env/bin/python -m pytest -q -rs \
  tests/test_patch_selection_lineage.py tests/test_patch_dataset_artifacts.py \
  tests/test_patch_input_checks.py tests/test_build_stripmatch_dataset.py \
  tests/test_check_patch_selection.py tests/test_check_patch_spatial_balance.py \
  tests/test_validation_suite_covers_the_loop.py
```

Result: **151 passed in 6.77s**, no skips. Tests exercise the real builders and
JSON CLIs, read-only behavior, strict/legacy modes, changed/forged records,
reference copies, source/target mismatches, aliasing, duplicate physical patches,
bootstrap dependencies, mutation during checking and looping links. The new
module is registered in the curated suite. Thirteen selected cases fail when
the baseline checkers/builder run against the same synthetic fixture inputs.

CPU smoke passed 8 checks, skipped 3 and failed 0 in 10.0 seconds. The two data
checks lack their training URI/inklabels; batchgeneratorsv2's transform is
unavailable. Ruff check/format, targeted mypy on all nine changed Python files
and `git diff --check` pass. Verification uses the frozen Python 3.10 dependency
environment.

The full repository suite, real 51 GB patch payloads, native Villa integration,
network-filesystem inode semantics, model fits and generation replay were not
tested. No GPU jobs, deployment, live-study measurements or prize submission
were performed. The prepared filing answer texts remain unchanged.
