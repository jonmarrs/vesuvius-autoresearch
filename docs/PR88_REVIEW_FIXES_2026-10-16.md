# PR #88 — review fixes

Date: 2026-10-16. Reviewed head:
`2b59459f6985459bca7a395938f44e004d947c68`.
This report covers the two follow-up review comments on inference metadata
publication and coherence scoring.

## What changed

Invalidate both canonical and explicitly requested prediction sidecars before
replacing shared outputs, and compute coherence with reflected filter context
cropped back to the original field.

## Why

A custom metadata path left the default sidecar authorizing stale fiber files,
and Villa's internal zero padding made flat fields and intensity offsets create
artificial coherence.

## Repairs

| Comment | Repair | Regression coverage |
| --- | --- | --- |
| Default sidecar survives a custom-metadata rerun | Share `invalidate_prediction_metadata` between single and ensemble prediction. Invalidate both known sidecars before any array or weight write, then publish only the requested sidecar after the outputs complete. | Both entry points, successful and interrupted headless reruns, stale custom and default sidecars, and downstream candidate ranking. |
| Coherence includes artificial boundaries | Subtract the constant intensity mean in float64 for numerical stability, reflect sufficient context for Gaussian smoothing, the pinned nine-sample derivative kernels and component integration, then crop the components to the original field before eigendecomposition. | Constant fields, offset invariance and input preservation in 2-D, 3-D and singleton-depth inputs; invalid filter scales are refused. |

At the default scales the halo is 16 voxels: 3 for gradient smoothing, 4 for
the largest derivative radius and 9 for component smoothing. The chosen upper
bound also covers noninteger scales. The input is not modified. Fractional
anisotropy retains its existing dimension-dependent definition and is clamped
to its physical range to absorb floating-point roundoff.

These changes do not remove retained fiber arrays. Without an authoritative
canonical sidecar the ranker refuses them. They do not promise coordination
between concurrent writers or discovery of every arbitrary historical custom
metadata path.

## Verification

The restored runtime has no project `.venv`. Tests use the already cached
Python 3.10 interpreter and package archives without installing or syncing
packages. Only the structure-tensor source from the unchanged Villa pin
`9afddaf0fdc12efe088bab7b82534c4f9a79e536` is supplied through an external
namespace path; the full Villa checkout, native binaries and scroll data are
absent. The tracked incumbent checkpoint is present and loads in the smoke
test. Baseline and final standard-suite runs use the same inputs.

Runtime: Python 3.10.21, Torch 2.9.1+cu128 (CPU execution), NumPy 2.2.6,
pytest 9.0.3 and Zarr 2.18.3.

### Runtime bootstrap

The commands below ran from the fix worktree, except the explicitly labelled
baseline runs from a detached worktree at the reviewed head. No packages were
installed. `/tmp/pr88-run-python.py` adds the existing cached package archives
and the worktree's own source directories before invoking Python modules:

```python
import os
import runpy
import site
import sys
from pathlib import Path

root = Path.cwd()
archives = sorted(Path('/workspace/.cache/uv/archive-v0').iterdir())
for archive in archives:
    site.addsitedir(str(archive))
source_paths = [str(root), str(root / 'src')]
if os.environ.get('VESUVIUS_REVIEW_VILLA_SOURCE'):
    source_paths.append(os.environ['VESUVIUS_REVIEW_VILLA_SOURCE'])
sys.path[:0] = source_paths
os.environ['PYTHONPATH'] = os.pathsep.join(source_paths + [str(path) for path in archives])
if sys.argv[1] == '-m':
    module = sys.argv[2]
    sys.argv = [module, *sys.argv[3:]]
    runpy.run_module(module, run_name='__main__')
else:
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name='__main__')
```

### Regression cases and affected modules

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py -m pytest -q tests/test_volume_inference_contracts.py -k 'custom_metadata_rerun or coherence_constant or coherence_rejects' --no-header --tb=short
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py -m pytest -q tests/test_volume_inference_contracts.py tests/test_submission_contracts.py tests/test_production_predict.py tests/test_prize_readiness.py --no-header --tb=short
```

Captured summaries:

```text
New regression cases before the fixes:
15 failed, 111 deselected in 3.85s
New regression cases after the fixes:
15 passed, 111 deselected in 4.67s
Affected modules after the fixes:
227 passed in 15.57s
```

Interpretation: all 15 new cases reproduce failures on the reviewed code and
pass after the repairs. The affected modules pass together.

### Smoke

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py scripts/smoke_test.py
```

```text
PASS: imports
PASS: build_resenc_unet
PASS: build_gated_unet
PASS: multi_task_heads_dummy_default
PASS: multi_task_heads_real_outputs
  Loaded 288/288 compatible tensors from best_model.pt (skipped missing=0, shape=0).
PASS: best_model_loads
SKIP: dataloader_3tuple_sobel — training URI / inklabels not present
SKIP: dataloader_frangi_target — training URI / inklabels not present
PASS: augmentations_albumentations
SKIP: augmentations_bg2 — create_training_transforms not available
PASS: bandit_templates
--- 8/11 passed, 3 skipped, 0 failed in 5.3s ---
```

Interpretation: available smoke paths pass; three paths remain unverified.

### Standard-suite comparison

`/tmp/pr88-run-standard.py` invokes the unchanged standard target list:

```python
import sys
import pytest
from scripts.run_validation_tests import VALIDATION_TESTS

raise SystemExit(pytest.main([
    '-q', '--continue-on-collection-errors', '-rfE', '--tb=short',
    '--junitxml=' + sys.argv[1], *VALIDATION_TESTS,
]))
```

Commands, baseline first and fixes second:

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-run-standard.py /tmp/pr88-fixes-baseline.xml
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-run-standard.py /tmp/pr88-fixes-final.xml
python3 /tmp/pr88-compare-validation.py
```

```text
Baseline: 104 failed, 2149 passed, 18 skipped, 1 xfailed, 4 warnings, 1 error in 181.64s
Fixes:    104 failed, 2164 passed, 18 skipped, 1 xfailed, 3 warnings, 1 error in 168.08s
Baseline failure/error IDs: 105
Final failure/error IDs: 105
New failure/error IDs: []
Resolved failure/error IDs: []
Additional passing cases: 15
```

The comparison parses JUnit XML, compares `(classname, name)` for each failing
or erroring case, and asserts identical sets plus exactly 15 additional passing
cases. Interpretation: no additional failures in this environment. The full
suite remains red; this is not a clean integration certification. Examples
include unavailable Villa Tifxyz and sampling modules, label-curation scripts,
external artifacts, and missing `metrics` during collection of `test_dice.py`.

### Numerical reproduction

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-fix-metrics.py
```

The script uses float32 ones of shape (64, 64) and (8, 64, 64), then
`default_rng(0).standard_normal((64, 64)).astype('f4')` and that noise plus 100.

```text
constant slice: 0.0
constant block: 0.0
noise: 0.36128944158554077
offset noise: 0.36128947138786316
```

Interpretation: constants no longer create boundary coherence, and adding 100
to the same float32 noise changes the score by less than 0.00000003.

### Documentation and source checks

The nine documentation guards in `.pre-commit-config.yaml` were run with the
same runtime on both worktrees. `/tmp/pr88-fix-doc-tests.py` invokes:

```python
import sys
import pytest

tests = [
    'tests/test_audit_doc_references.py',
    'tests/test_audit_report_claims.py',
    'tests/test_withdrawn_claims_stay_withdrawn.py',
    'tests/test_arm_tiers.py',
    'tests/test_audit_arm_coverage.py',
    'tests/test_analyse_flat_displacement.py',
    'tests/test_quotations_match_source.py',
    'tests/test_analyse_pooled_fit_only_floor.py',
    'tests/test_analyse_ink_maximum_offset.py',
]
raise SystemExit(pytest.main(['-q', '--no-header', '--tb=short', '--junitxml=' + sys.argv[1], *tests]))
```

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-fix-doc-tests.py /tmp/pr88-fixes-baseline-docs.xml
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-fix-doc-tests.py /tmp/pr88-fixes-final-docs.xml
```

```text
Baseline: 1 failed, 90 passed, 2 skipped in 10.95s
Fixes:    1 failed, 90 passed, 2 skipped in 11.41s
FAILED tests/test_audit_doc_references.py::test_live_documents_stay_clean
```

Interpretation: the same reference guard fails on both worktrees, with an
identical missing-path diagnostic listing unavailable Villa files and external
detector weights. No new reference failure was introduced.

`git diff --check` and manual Python compilation, whitespace, final-newline and
2 MiB size checks pass. Protected config, incumbent checkpoint, scientific
controls, preregistrations, loop state and the Villa pin match the reviewed head.

## Edge cases considered

- Default and custom sidecars are absent before the first array write in both
  predictors, including when a later figure write fails.
- A retained fiber map from a previous model does not earn a ranking bonus after
  a headless rerun with a custom metadata path.
- Default-only runs and a custom path equal to the canonical path retain their
  existing behavior through the shared invalidation helper.
- Reflected context supports shallow and singleton dimensions; the original
  region, rather than its padded extension, contributes to the mean.
- Constant fields produce zero coherence; adding a constant intensity offset
  leaves the diagnostic unchanged within tolerance. Input arrays are preserved.
- Nonpositive/nonfinite scales, an overflowing combined scale, and empty or
  nonfinite inputs are rejected rather than producing a misleading score.

## What was NOT tested

- CUDA execution, real-scroll coherence, GPU performance, or the loop's live
  benchmark. Reflected context adds temporary memory; no memory budget was profiled.
- Full native Villa integration, unavailable scroll datasets or external detector checkpoints.
- Ruff and mypy: neither executable/module is available in this restored runtime.
  Python syntax, whitespace, EOF and file-size checks were used; no new packages
  were installed to make static checks available.
- Concurrent writers, power-loss durability, every old custom metadata alias,
  or atomic publication of the entire multi-file prediction.
- Training, promotion metric changes or scientific tolerance recalibration.

## Reviewer focus

Check that both entry points invalidate both known sidecars before writing any
shared outputs, and that the reflected halo covers the composed support of the
pinned Villa filters before cropping.
