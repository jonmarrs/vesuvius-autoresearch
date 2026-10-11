# Design and architecture review — local volume reads and benchmark

Date: 2026-10-11. Baseline: c4cdbfee160d740aed849b487ef86501b288b4e4.
Scope: local Volume Cartographer-compatible Python reads, comparable timing
evidence, CLI publication, training/readiness integration, and current
contribution-history attribution.

## What changed

Validate local volume metadata and chunk/voxel requests, benchmark two Python
Zarr access paths on one checked region, and record the attributed September
Progress Prize while scoping older closure statements to their historical period.

## Why

Invalid coordinates were truncated or turned into empty/wrapped reads, benchmark
paths could read different data, and unscoped historical wording obscured later
merged contributions and the supplied award announcement.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | bool/fractional origins and sizes were converted with int(); negatives and outside origins could yield unrelated or empty reads. | Require nonnegative integral origins and positive integral explicit sizes before payload access; reject origins outside any dimension. |
| P2 | Non-3D/empty arrays and unsupported voxel types were accepted until later code failed. | Require a nonempty 3D real-numeric/boolean array or explicit array 0 during construction. |
| P2 | file URI paths were not decoded, and a foreign file authority was silently ignored. | Decode local URI paths, accept only empty/localhost authority with absolute paths, and refuse remote/query/fragment forms. |
| P2 | Chunk separator detection depended on JSON whitespace. | Parse actual metadata rather than matching a formatted substring. |
| P2 | Benchmark direct slices assumed 64x256x256 blocks while wrapper reads used actual storage chunk dimensions. | Require one explicit fully in-bounds voxel region for both access paths and check shape/dtype/payload equality on every read. |
| P2 | Timings included initialization, always placed one path second, and used wall-clock time. | Record opening separately, time reads with perf_counter_ns, warm up explicitly, alternate first reader and use an even measured repeat count. |
| P2 | Missing benchmark data was skipped with success, and a zero time could produce an infinite ratio. | Fail explicit missing/invalid workloads and nonpositive durations; publish only completed finite results. |
| P2 | The old script offered no workload-bound, repeat-level evidence or backend scope for its ratio. | Bound decoded requested bytes before reads, record all samples and selected payload identity, and declare the actual Python Zarr/cache scope. |
| P2 | The archived strategy claimed “C-speed performance” for an adapter implemented with Python Zarr. | Correct the implementation/performance scope and link the validated local benchmark contract. |
| P2 | The archived strategy's “all our villa PRs” wording could be read as current despite subsequent merges and the September prize. | Scope the May reset and pre-SOP closure history, add an attributed award record, and link the current contribution outcome. |

The initial read-contract regressions all failed on the baseline. A controlled
synthetic volume with shape (4,31,42) and chunks (2,3,4) demonstrated the old
benchmark's mismatch: direct reads returned (4,0,0), while wrapper chunk reads
returned (2,1,2). It still printed a timing ratio. That ratio does not compare
the same workload.

## Architecture and compatibility decisions

[The local adapter](../volume_cartographer_wrapper/volume.py) keeps its existing
grid-index and six-argument voxel API, source dtype, and volume-cartographer-zarr
backend. Python/NumPy integral values are accepted, excluding bool. A valid
origin with a positive requested size still clips at the high boundary;
partial edge chunks remain supported. Wholly outside origins are invalid,
rather than successful empty chunks. No padding, intensity normalization or
physical-coordinate inference is added.

Construction selects a bare array or the explicit 0 child, records the declared
source root and selected array separately, and checks dimensionality/dtype
before decoding. The metadata and read validation belong in the adapter so
training, readiness and future consumers share the same behavior. The
[training loader](../src/vesuvius_autoresearch/core/vesuvius_loader.py) and
[readiness probe](../scripts/build_volume_cartographer_readiness.py) retain
their valid read behavior without edits.

[The benchmark](../scripts/benchmark_volume_cartographer.py) compares the
selected array with the adapter's voxel API. Unlike the adapter's supported
partial edge reads, benchmark regions must fit completely so both paths
measure exactly the requested workload. Block/repeat limits are checked before
payload decoding. SHA-256 validation and summaries stay outside read timing;
every read must match the same selected payload, including across repeats.

Reports include source and selected-array paths, metadata, voxel region,
per-read bytes/hash, raw samples, summary statistics, opening durations, order,
warmup, backend and cache scope. The adapter still uses Python Zarr; the native
Volume Cartographer C++ API is not measured. Opening durations describe different
work (wrapper validation versus direct opening) and are kept separate.

JSON goes to stdout, with optional new-file publication using the existing
local artifact publisher. Outputs must be outside both the declared root and
selected array; choosing array 0 must not allow writing into its parent group.
Read/measurement/serialization/write failures cannot publish a successful
partial report or overwrite a previous report.

[The guide](LOCAL_VOLUME_READS.md) defines valid requests, clipping, URI behavior,
explicit benchmark use, timing interpretation, cache/memory limits and migration.
A per-read decoded bound does not cap total memory: storage chunk decoding,
copies and hashing can use more. Keep source data stable and serialize writers.

[The award record](PROGRESS_PRIZE_AWARDS.md) preserves the announcement supplied
and confirmed by Jonathan Marrs on 2026-10-11: $250 for “assorted useful merged
villa PRs.” It includes source limits and keeps the actual credit separate from
the September filing's individually documented contributions. The May closure
matrix and frozen filing/evidence artifacts retain their historical content.
No external post, filing or message is sent for this review.

No dependency, native Villa code, training/evaluation harness or scientific
result is changed. No training/research experiment is launched.

## Verification

Commands run from the repository root using the existing environment.
Process inspection found no active training, loop, fit or renderer.

### Reproduce read defects before repair

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_volume_read_benchmark_contracts.py -q --no-header --tb=short
~~~

~~~text
21 failed in 0.43s
~~~

Interpretation: initial cases reproduced invalid request acceptance, unsuitable
volume metadata, whitespace-dependent separators, undecoded local URIs and
ignored remote file authority.

### Controlled old-benchmark workload probe

The old script was run against a temporary synthetic Zarr via a recording
reader, with source lookup redirected to that fixture. The recorded excerpt is:

Command as run on the baseline before editing the benchmark:

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python - <<'PY'
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import zarr
from scripts import benchmark_volume_cartographer as legacy

with tempfile.TemporaryDirectory() as work:
    array = zarr.open(str(Path(work) / 'synthetic.zarr'), mode='w', shape=(4, 31, 42), chunks=(2, 3, 4), dtype='uint16')
    array[:] = 1
    shapes = []
    class RecordingArray:
        shape, chunks = array.shape, array.chunks
        def __getitem__(self, key):
            result = array[key]
            shapes.append(result.shape)
            return result
    with patch.object(legacy.os.path, 'exists', return_value=True), patch.object(legacy.zarr, 'open', return_value=RecordingArray()):
        legacy.benchmark()
    print('direct workload shape:', shapes[0])
    print('wrapper workload shape:', shapes[10])
    print('same workload:', shapes[0] == shapes[10])
PY
~~~

~~~text
direct workload shape: (4, 0, 0)
wrapper workload shape: (2, 1, 2)
same workload: False
~~~

Interpretation: even before considering cache/order or initialization, its two
timed workloads were different. This controlled reproduction is not a
production speedup measurement.

### Focused read/benchmark/integration checks

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_volume_read_benchmark_contracts.py tests/test_volume_cartographer.py tests/test_volume_cartographer_readiness.py -q --no-header --tb=short
~~~

~~~text
71 passed in 4.14s
~~~

Interpretation: validated request/URI/layout behavior, high-boundary clipping,
training/readiness use, matching workloads, balanced timing boundaries,
mutation/error detection, output preservation and real CLI behavior pass.

### Standard validation

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py
~~~

~~~text
1808 passed, 4 skipped, 1 xfailed, 9 warnings in 193.53s (0:03:13)
~~~

Interpretation: standard validation passes with 65 new read/benchmark cases;
existing optional/CUDA skips and the expected failure remain. Warnings concern
pinned-memory requests in CPU-only checkpoint checks.

### Smoke checks

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py
~~~

~~~text
--- 8/11 passed, 3 skipped, 0 failed in 7.6s ---
~~~

Interpretation: available smoke paths pass, including 288/288 checkpoint keys;
optional local training data and unavailable bg2 augmentation checks skip.

### Documentation and frozen-evidence guards

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_filing_numbers_match_sources.py tests/test_filing_2026_10_numbers.py tests/test_fiber_heldout_split_numbers.py -q --no-header --tb=short
~~~

~~~text
133 passed, 3 skipped in 31.43s
~~~

Interpretation: reference/claim guards, the historical September/current October
filing numbers and current held-out fiber evidence remain consistent.

Final document-reference/report-claim check:

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py -q --no-header --tb=short
~~~

~~~text
16 passed
~~~

Interpretation: the final operator guide, award record and review report pass
reference and frozen-report claim checks.

### Static checks

~~~sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff check volume_cartographer_wrapper/volume.py scripts/benchmark_volume_cartographer.py scripts/run_validation_tests.py tests/test_volume_read_benchmark_contracts.py
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff format --check volume_cartographer_wrapper/volume.py scripts/benchmark_volume_cartographer.py scripts/run_validation_tests.py tests/test_volume_read_benchmark_contracts.py
git diff --check
~~~

~~~text
All checks passed!
4 files already formatted
~~~

Interpretation: changed Python files pass Ruff and whitespace checks have no diagnostics.

~~~sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python
~~~

~~~text
Found 16 errors in 13 files (checked 649 source files)
~~~

Interpretation: the established errors remain in unchanged files (YAML/requests
stubs, OpenCV overloads, augmentation indices, optional loader tensors and
training list/tensor operations); no review file has a diagnostic.

## Edge cases considered

- Grid versus voxel coordinates, NumPy integers, bool/fraction/string/nonfinite/
  negative/outside values, incomplete sizes, oversized positive sizes and edge clipping.
- Nonempty 3D array/explicit level 0, empty or wrong-child groups, invalid shape/
  voxel type, compact slash-separated metadata and local paths with spaces.
- Local file URIs with localhost, remote/relative URIs, missing inputs and group/
  selected-array distinction during publication.
- Whole-region and decoded-byte bounds, invalid/even repeat counts and warmup,
  positive monotonic durations, initialization/verification outside read samples.
- Wrong shape/dtype/values, read errors and payload mutation across rounds;
  identical region independent of chunk layout and explicit backend/cache scope.
- Real subprocess execution outside the checkout, stdout/file agreement,
  prior reports, broken symlinks, source overlap, write cleanup and help.
- Supplied award source/credit versus historical PR closure and frozen filing data.

## What was NOT tested

- Native C++ Volume Cartographer, remote S3/HTTP reads, GPU behavior, Zarr v3,
  or representative whole-scroll throughput.
- Cold-cache execution or OS/storage/codec cache isolation, representative
  production performance, statistical significance or a general speedup.
- Whole-process memory, adversarial decoder internals, crash/power-loss durability,
  concurrent report writers or an atomic multi-file source snapshot.
- Physical registration, prediction quality, prize eligibility of these fixes,
  or scientific experiment re-execution.
- Independent retrieval of the Discord announcement or an
  itemized award-linked PR list; the attribution is the supplied announcement.
- Training/evaluation changes or unrelated established mypy failures.

## Reviewer focus

Check the stricter read contract with retained edge clipping, URI/metadata
interpretation, identical benchmark payload and timing boundaries, backend/
cache scope and immutable report publication, and the attribution/date scope
of the contribution-history correction.
