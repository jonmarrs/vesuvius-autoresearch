# Design and architecture review: classical fiber-filter CLI

Baseline: `f2efeda9` (after PR #294). Scope: the classical ridge/vesselness CLI,
its memory ownership and file publication. Development used an isolated
worktree and synthetic CPU inputs, without reading active-study measurements.

## Findings and repairs

| Priority | Finding | Repair |
|---|---|---|
| P1 | `--tiled` transferred the entire CT to the backend and allocated a full backend result before saving. Halo processing alone therefore did not support volumes larger than device memory. | Read-only NPY input mapping, a staged float32 output mapping, and two passes that transfer only halo blocks and return only core responses. |
| P1 | Response/preview paths could overwrite the source CT, alias one another, or follow an output symlink. | Reuse shared path/inode collision checks before work and publication; reject nonregular outputs. |
| P1 | Writing directly to the final response could truncate a previous result on save failure. A failed preview could also leave artifacts from different runs. | Stage response and preview before publication. Invalidate the requested old preview before replacing the response; serialize complete files before renaming. |
| P2 | `np.save(path, ...)` silently appended `.npy`, while the success message named a different path. | Write NPY through a file handle or explicit memory-map path; both output names are exact. |
| P2 | Invalid halo settings reached backend allocation before failing. | Validate tiled geometry before device resolution or transfer. |

The initial baseline run had **12 failures and 7 passes**, including checks
for the newly added streaming interface. A separate execution of the baseline
CLI reproduced successful source overwrite, an appended output suffix, a full
volume passed to the tiled backend and loss of a previous output on save error.

## Architecture and compatibility

`streaming.py` owns iteration and transfer boundaries. It uses the existing
Gaussian normalization and ridge/vesselness implementations: the first pass
finds the global smoothed range, the second filters halo blocks and writes their
nonoverlapping cores. Only block-sized values are validated or transferred;
the complete input and result stay in host disk mappings. Device selection
happens once, and later allocation/filter failures do not trigger CPU retry.

The in-memory APIs in `detection.py` are unchanged, including their float64
filter output. CLI storage remains float32. CPU comparisons cover both filters,
uint16/float32/float64 CT, odd dimensions, short edge blocks, Fortran order and
constant fields. Transfer-boundary instrumentation rejects full-volume copies
and verifies both passes, but is not a native CUDA test.

`filter_artifacts.py` owns path checks, mappings, staging, disk-space checks,
permissions and publication. POSIX reservation is used when supported, allowing
disk/quota errors to fail before the first tile transfer. Unsupported
reservation falls back to the space check. Ordinary source changes are detected
through device/inode/size/mtime; there is no input content hash or writer lock.

The response is authoritative. Computation and serialization errors preserve
previous artifacts. During publication, the requested old preview is removed
before response replacement. A rename failure can leave a response without the
PNG, so the command fails and the PNG can be regenerated. Two file renames are
not a transaction; old unrequested images are not tracked. Temporary files can
remain after a process/OS crash. The guide documents these boundaries.

## Verification

Commands used `MPLCONFIGDIR=/tmp/vesuvius-filter-mpl`,
`XDG_CACHE_HOME=/tmp/vesuvius-filter-cache`, `OMP_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and `CUDA_VISIBLE_DEVICES=''`.

```sh
/tmp/vesuvius-chain-env/bin/python -m pytest -q -rs tests/test_fiber_streaming_cli.py tests/test_fiber_workflow_contracts.py tests/test_fibers_cli.py tests/test_fibers.py tests/test_fiber_direction_tiled.py tests/test_file_modes.py tests/test_validation_suite_covers_the_loop.py
```

**149 passed, 3 skipped in 31.55s.** The skips are two native GPU CLI
round-trips (dense and streaming) and GPU primitive parity, with CUDA masked.
CPU checks cover filtering parity, bounded transfer shapes, actual input/output
memory maps, alias rejection, source mutation, serialization/rename failures,
preview pixels, permissions, disk reservation failures, unsupported reservation,
GPU-allocation failure propagation and suite registration.

The final six parity cases additionally compare serialized NPY file bytes:

```sh
/tmp/vesuvius-chain-env/bin/python -m pytest -q tests/test_fiber_streaming_cli.py -k streaming_matches_existing
```

**6 passed, 31 deselected in 3.97s.** These compare both filters and all three tested dtypes against the existing
tiled API, quantized to the CLI's float32 contract. Counts overlap with the
integration run.

```sh
/tmp/vesuvius-chain-env/bin/python scripts/smoke_test.py
```

**8/11 passed, 3 skipped, 0 failed in 12.2s.** Two training URI/inklabel fixtures
and the batchgeneratorsv2 transform are unavailable. Ruff check/format and
targeted Mypy pass on all six changed Python files; `git diff --check` passes.

## Limits

No native CUDA execution, real-scan throughput/quality benchmark, peak RAM/VRAM
measurement, full repository suite, live-study inspection, deployment or prize
submission was performed. The June in-memory performance figures are labeled
historical and do not benchmark the new CLI. Allocators and OS page caching
are outside a hard memory bound; optional preview buffers scale with Y×X.
Inputs must remain stable and destination space available throughout the run.
The research loop, model weights, filter formulas, tracer, historical results
and registrations were not modified.
