# Fiber probability cache: design and architecture review

Reviewed the benchmark cache-to-score boundary on main `9156eb38`. This follows
the scoring-input/publication review in PR #378; it does not rerun the published
fiber experiments or change their measurement definitions.

## Findings and fixes

- **The cache could load different bytes from those verified (P2).** The old
  path hashed the probability filename, then opened it again with `np.load`.
  Replacing that file between operations returned probability 0.125 under the
  digest of the original 0.75 field. The regression failed before repair.
  Probabilities now use the same bounded numeric NPY capture parser as instance
  labels. Parsing, value validation and SHA-256 refer to the same bytes.
- **Reports could identify a different inference from the one scored (P2).**
  Scoring accepted an array, then report construction reread the mutable cache
  manifest. Replacing it after floor scoring changed the reported digest to
  `ffff...` and inference to an unrelated record. This also failed before repair.
  `ProbabilityResult` carries probabilities, a captured inference record and
  cache diagnostics. All floor, score-with-floors and trace paths retain this
  result; measurement provenance is now a pure projection of its record.
- **Interrupted refresh could retain an old manifest (P2).** The old array was
  replaced before the manifest, leaving an old sidecar on manifest-write failure.
  Although a later digest check rejected mismatches, the pair was misleading.
  Publication now removes the old manifest immediately before array publication,
  then writes the new manifest last, preserving its prior permissions. A failed
  publication may leave an unattested array; it must be recomputed. Failures in
  inference or validation still preserve the prior pair.
- **Cache reuse was difficult to diagnose or deliberately bypass.** Model-backed
  commands now print HIT/REFRESHED and a reason, include `probability_cache` in
  JSON, and accept `--refresh-cache`. Score-only rejects that flag unless floors
  were requested, so it cannot silently ignore a requested refresh.

## Architecture and compatibility

The shared NPY reader verifies shape, scalar numeric dtype, exact payload length,
and bounded headers before exposing an immutable view. Probability files allow
float16/32/64, including byte order and Fortran layout, and require finite values
in [0, 1]. Capture is bounded to the actual cube's float64 payload plus 10,012
header bytes; metadata is bounded to 1 MiB. This limits file capture, not RSS or
GPU use. Invalid caches are recomputed with a recorded reason; model errors are
not hidden by a fallback. A model/image identity recheck now guards hits as well
as inference.

The old `_fiber_prob` array interface remains available to research scripts as
a writable float64 array. Commands use the explicit result interface and a
read-only array. Existing attested cache manifests remain compatible; inference
version 1, scoring version 5, numeric probabilities, metric formulas and tracer
defaults are unchanged. Cache outcomes/paths are deliberately outside scientific
provenance: refreshing identical probabilities still preserves an eligible prior
all-cube tracer row. Score without floors still needs no model or cache loading.
See [fiber tracing](FIBER_TRACING.md) for CLI and report details.

## Verification

Python 3.10.21, NumPy 2.2.6, Torch 2.9.1+cpu; Villa pinned at
`ccb431818fa68059138f2c964ae299fc474ff116`.

- Both original regressions failed before implementation: 2 failed in 3.96s.
- Final affected curated selection: **247 passed in 32.45s**, across 7/187
  modules. It covers cache file replacement, post-scoring manifest replacement,
  malformed/oversized manifests, invalid numeric payloads and advertised huge
  allocations, supported float layouts, model mutation during cache validation,
  explicit refresh, publication failures, permissions, score-only behavior,
  floor/trace report identity and all-cube tracer carryover. Existing instance
  capture, path-planning, NML, tracer recipe and file-mode tests also pass.
- Required smoke: **8/11 passed, 3 skipped, 0 failed in 12.0s**. Training data
  and the optional batchgenerators transform were unavailable. Available model,
  import and augmentation checks passed, including 288/288 checkpoint tensors.
- Ruff lint/format and scoped Mypy passed all seven changed Python files.
  Exact commands and captured output are in the PR.

Tests use temporary synthetic data, stub semantic inference for cache/report
tests, and real cache I/O, scoring and tracing. No full curated suite, published
semantic model on CUDA/RTX 4090, full-cube memory/runtime benchmark, new research
measurement or prize-filing update was performed. Read-only probability arrays
do not make the entire workflow immutable. CT, ground truth and model files are
not captured together; inputs/paths still need stability and serialized writers.
Rechecks are not locks, and publication remains per-file without rollback.
