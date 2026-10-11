# Local volume reads and benchmarking

## Local read contract

FastLocalVolume and VolumeCartographerVolume are Python Zarr adapters. The
recorded backend is volume-cartographer-zarr; prefer_native is retained as a
compatibility argument and does not select a C++ implementation.

~~~python
from volume_cartographer_wrapper.volume import FastLocalVolume

volume = FastLocalVolume("/data/ct.zarr")
chunk = volume.get_chunk(1, 2, 3)             # chunk-grid indices in z/y/x
patch = volume.get_chunk(1, 2, 3, 16, 64, 64) # voxel origin and depth/height/width
~~~

A source must be a nonempty 3D real-numeric or boolean Zarr array, or a local
directory with array 0. Other group children are not guessed. The existing
environment uses Zarr v2. Complex, text, object and structured voxel types are
refused before decoding. Values remain in their source dtype and units; this
adapter does not normalize intensity or infer a physical coordinate frame.

Local filesystem paths and absolute local file URIs are supported.
Percent-encoded file paths are decoded, including spaces. URI authority must
be empty or localhost; query/fragment components and remote URI schemes are
refused. Paths are resolved against the caller's current directory.
source_path records the declared local source root; path records the selected
array. For a group these can differ by the explicit 0 child.

Origins must be nonnegative Python/NumPy integers, excluding booleans and
fractional/string/nonfinite values. A grid origin is multiplied by the actual
chunk dimensions; a voxel origin uses its values directly. The resulting
origin must be strictly inside every source dimension.

Explicit depth/height/width must all be supplied together and be positive
integers. Only the high boundary is clipped: partial edge chunks and partial
voxel blocks remain supported. No negative indexing, low-edge wrapping, implicit
padding or wholly outside/empty read is accepted. Consumers needing a full block
must first check origin + shape <= volume.shape; a positive request alone does
not promise the complete requested size.

shape, chunks, dtype and sep describe the selected array. Separator parsing uses
actual JSON metadata, including compact metadata with a slash separator.
Read/codec errors propagate; the adapter does not turn them into zeros or
successful empty patches. This keeps valid training and readiness calls intact
while exposing invalid requests.

## Comparable repeated-read timings

~~~bash
.venv/bin/python scripts/benchmark_volume_cartographer.py \
  --input /data/ct.zarr --origin-zyx 0 2560 2560 \
  --shape-zyx 64 256 256 --iterations 10 --warmup 2 \
  --output /data/reports/read_timings.json
~~~

Choose an explicit local input and voxel shape. The whole benchmark region
must fit the source; it is never clipped. Both readers use that same selected
array, voxel origin and shape, regardless of its storage chunk dimensions.

Iterations must be even and between 2 and 1,000, so measured rounds balance
which path reads first. Warmup is 0..1,000 reads per path, default two. The
benchmark alternates first-reader order across rounds, keeps source objects
open, and uses monotonic perf_counter_ns for the read calls only. Opening the
two access paths is recorded separately; their initialization work differs
because the wrapper validates its source. Layout/content validation and hashing
are outside read timing.

Every warmup and measured read must return the expected shape and dtype and
the same payload SHA-256. A changed or incompatible result fails the benchmark.
This checks the selected bytes; it is not an atomic snapshot of all source files.
Keep sources stable and use the raw repeated samples when assessing variability.

The report records absolute source/root paths, source/chunk shape, dtype,
separator, selected region, bytes per read, payload hash, iteration/warmup
counts, initialization durations, individual read durations and min/median/max.
Its ratio is:

~~~text
direct_over_wrapper_median_ratio = direct read median / wrapper read median
~~~

A value above one means the wrapper was faster for this recorded run. Both
paths use Python Zarr. This does not measure native C++ Volume Cartographer,
GPU acceleration, full-scroll throughput, or a general implementation speedup.

This is a configured repeated-read comparison. It does not flush or isolate
OS/storage/codec caches; even warmup zero cannot establish cold-cache conditions.
Source order, contention, codec behavior and machine state can affect timings.
The report states that scope rather than labeling the ratio a native speedup.

The default per-read decoded payload budget is 67,108,864 bytes (64 MiB),
checked before either path decodes a block. Adjust --max-read-bytes explicitly
for a suitable machine. Whole compressed chunks, returned arrays, hashes and
decoder storage may require more memory; this is not a total-memory limit.

JSON is printed to stdout. Optional --output publishes a new .json file by an
adjacent temporary-file rename after all measurements and serialization succeed.
Destinations must be new and outside both the declared source root and selected
array. Existing reports, broken symlinks and source overlaps are refused.
Ordinary benchmark/read/write failures exit nonzero and publish no partial
report. Help exits zero. Serialize report writers.

The previous no-argument script hardcoded one source and voxel slice, then
compared it with chunk indices whose meaning depended on storage dimensions.
It also mixed initialization into read totals and skipped missing data with a
successful exit. Use the explicit workload above; missing data and invalid
workloads now fail with a diagnostic.

See [Volume inference](VOLUME_INFERENCE.md) for regional predictions and
[Geometry handoffs](GEOMETRY_HANDOFF.md) for coordinate declarations. Read
correctness and comparable timing do not certify prediction or registration
quality.

See the [design and architecture review](DESIGN_ARCHITECTURE_REVIEW_2026-10-11_VOLUME_READ_BENCHMARK.md)
for regression and integration evidence.
