# Faster fragment linking with the same geometry

The conservative tracer's existing fragment linker now uses a spatial index to
find nearby endpoints. The original Euclidean gap, tangent, angle, cost and
greedy cycle checks still decide every link, including equal-cost ties. The
index queries a cube containing the accepted distance sphere; it does not
approximate the acceptance test. Dense endpoint clusters can still require
quadratic work. SciPy was already a project dependency.

The existing benchmark command uses this path automatically:

```sh
python -m vesuvius_autoresearch.fibers.bench_cli trace \
  --cube s1_00497_01497_03997_256 --model /path/to/fiber_hz_vt
```

This command requires its normal data and model inputs. `--no-relink` still
disables linking. No tracing thresholds or frozen studies were changed.

Two correctness fixes accompany the search:

- Joined endpoint stop reasons follow the output point order when either
  fragment is reversed. Previously they could describe the internal join.
- Nonfinite/negative settings, invalid angles, a nonpositive gap-fill step,
  a noninteger endpoint window, and nonfinite geometry or fragments with fewer
  than two points fail explicitly.
  In particular, NaN previously bypassed the maximum-gap comparison.

`stop_counts` continues to count the input walks, including joined endpoints;
the two stop fields on each output fiber describe its surviving outer ends.
Confidence aggregation and interpolated gap geometry retain their prior rules.

## CPU replay

The hypothesis was that rejecting distant endpoint pairs through an index
would reduce CPU time while retaining the exact linked point arrays. This is
an engineering hypothesis, not a claim of more accurate fiber tracing.

The replay uses the released ScrollGT skeletons at
[`1605fadb12ba0f8c4afff31f8d160332e6656d0b`](https://github.com/jonmarrs/scrollgt/tree/1605fadb12ba0f8c4afff31f8d160332e6656d0b/data).
Download these two files, retaining the indicated names, into a separate input
directory. They are public annotation data under ScrollGT's documented
CC BY-NC 4.0 data license; the replay does not load their object-array names.

- `data/fibers_s1_00497_01497_03997_256/skeleton.npz` → `s1_00497_01497_03997_256.npz`
- `data/fibers_s5_03997_01497_03997_256/skeleton.npz` → `s5_03997_01497_03997_256.npz`

The harness walks annotated edges at 0.5-voxel spacing, keeps in-bounds
stretches, and retains 48 samples out of each 64. These deliberately imposed
breaks make an annotation-derived workload; they are not observed tracer errors.
Both implementations receive the same fragment arrays, default weights, gap
10, link angle 30 and tangent angle 35. After one warm-up each, three trials
alternate execution order. Input, source, harness and output geometry hashes
are retained, and input/source drift fails the run. No GPU, inference, fitting,
native object-store export or independent quality evaluation is performed.

```sh
CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python repro/fibers/benchmark_relink.py \
  --baseline-ref cd3bf6da217cb0300d3a05b35d291acc2c7e9477 \
  --skeleton /path/to/inputs/s1_00497_01497_03997_256.npz \
  --skeleton /path/to/inputs/s5_03997_01497_03997_256.npz \
  --repeats 3 --out /path/to/new-result.json
```

The retained [measurement](../reports/evidence/fiber_relink_cpu_2026-11-05.json)
contains every timing, environment version and exact input/output hash.

| Input geometry | Fragments | Baseline median | Indexed median | Factor |
| --- | ---: | ---: | ---: | ---: |
| Scroll 1 cube above | 722 | 2.825 s | 0.046 s | 61.2× |
| Scroll 5 cube above | 540 | 1.630 s | 0.041 s | 39.7× |

This is a replay of public geometry, not an end-to-end speedup or a connectivity
gain on unseen traces. No expected prize amount or community adoption follows
from this measurement.
