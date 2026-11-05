# Fiber filtering at singleton boundary tiles

The [October 30 review](../docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-30_OWNER_MERGES_292_295.md)
identified a mismatch between dense and tiled filtering at the accepted minimum
halo. A tile containing only the last voxel on an axis missed one source plane.
Two central derivatives need two smoothed voxels of context; composing two
second-order one-sided gradients at a physical face reaches three voxels inward.
The shared source-window helper now includes that context at physical faces.
Accepted halo values and the `block_size + 2 * halo` transfer bound are preserved.

## Public CT replay

This CPU check uses the `ct[:17, :17, :17]` subcrop of Villa's existing
[PHerc0139 fixture](https://github.com/ScrollPrize/villa/blob/9c343a16494cf61d72727cbc85dc5e12e8773677/vesuvius/tests/ink_detection/fixtures/ink_roi_case.npz).
Its [provenance](https://github.com/ScrollPrize/villa/blob/9c343a16494cf61d72727cbc85dc5e12e8773677/vesuvius/tests/ink_detection/fixtures/ink_roi_case.json)
records the public surface-volume chunks, depth indices and crop center.
The fixture SHA-256 is
`2bd2ef9bfbdd620f1250cda59cf83f2f679cb4a8be9feffefd3e3de32ee503ea`.
The [receipt](evidence/fiber_boundary_halo_2026-11-05.json) preserves the baseline
commit, source hashes, input hash, versions and parameters. Block size is 8,
halo 10, Gaussian sigma 2 and Hessian scale 6.

| Output | Baseline differences from dense | Baseline maximum absolute error | Corrected differences |
| --- | ---: | ---: | ---: |
| Ridges | 351 voxels | 0.00006804182104225287 | 0 |
| Vesselness | 200 voxels | 0.00003323510842988264 | 0 |
| Orientation | 2,424 vector components | Not summarized | 0 |

The corrected streamed float32 responses also equal dense responses cast to
float32, and validity masks agree exactly. Halo-16 ridge and vesselness outputs
are unchanged from the baseline on this crop. These are numerical correctness
checks, without model inference, tracing-quality, GPU or performance claims.

With the pinned fixture saved locally, run from this repository's root using
the project interpreter. This loads the retained baseline source for comparison;
it does not check out or modify the baseline.

```sh
export FIBER_HALO_FIXTURE=/path/to/ink_roi_case.npz
PYTHONPATH=src CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python - <<'PY'
import hashlib
import json
import os
import subprocess
import types
from pathlib import Path
import numpy as np
from vesuvius_autoresearch.fibers import detection as d, streaming

receipt = json.loads(Path('reports/evidence/fiber_boundary_halo_2026-11-05.json').read_text())
fixture = Path(os.environ['FIBER_HALO_FIXTURE'])
assert hashlib.sha256(fixture.read_bytes()).hexdigest() == receipt['fixture_sha256']
with np.load(fixture, allow_pickle=False) as data:
    ct = data['ct'][:17, :17, :17].copy()
assert hashlib.sha256(ct.tobytes()).hexdigest() == receipt['ct_c_order_bytes_sha256']
source = subprocess.check_output(['git', 'show', receipt['baseline_commit'] + ':src/vesuvius_autoresearch/fibers/detection.py'])
assert hashlib.sha256(source).hexdigest() == receipt['baseline_detection_sha256']
baseline = types.ModuleType('baseline_detection')
exec(compile(source, 'baseline_detection.py', 'exec'), baseline.__dict__)
for name in ('ridges', 'vesselness'):
    dense = getattr(d, 'detect_' + name)(ct)
    before = getattr(baseline, 'detect_' + name + '_tiled')(ct, block_size=8, halo=10)
    after = getattr(d, 'detect_' + name + '_tiled')(ct, block_size=8, halo=10)
    np.testing.assert_array_equal(after, dense)
    output = np.empty(ct.shape, np.float32)
    streaming.filter_into(ct, output, filter_name=name, block_size=8, halo=10)
    np.testing.assert_array_equal(output, dense.astype(np.float32))
    np.testing.assert_array_equal(
        getattr(d, 'detect_' + name + '_tiled')(ct, block_size=8, halo=16),
        getattr(baseline, 'detect_' + name + '_tiled')(ct, block_size=8, halo=16),
    )
    print(name, np.count_nonzero(before != dense), np.max(np.abs(before - dense)))
dense_d, dense_valid = d.fiber_direction(d.hessian(ct)[0])
tiled_d, tiled_valid = d.fiber_direction_tiled(ct, block_size=8, halo=10)
np.testing.assert_array_equal(tiled_d, dense_d)
np.testing.assert_array_equal(tiled_valid, dense_valid)
before_d, _ = baseline.fiber_direction_tiled(ct, block_size=8, halo=10)
print('orientation components', np.count_nonzero(before_d != dense_d))
PY
```

The synthetic regressions additionally cover singleton tails along every axis,
corner tiles, both float precisions, Gaussian sigma 0/1/2, one-voxel blocks at
both physical faces, and complete streamed CLI outputs. All 43 new cases failed
before the source-window correction and pass afterwards.
