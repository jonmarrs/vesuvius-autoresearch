# Fiber benchmark artifacts: design and architecture review

Reviewed the benchmark's scoring-input and artifact-publication boundary. Initial
reproductions used base `1e7315c2`; the branch was then updated to
`3c738a103f801db88165fc485821cdde8d94cd8e` before final validation.
All reproduction inputs were temporary synthetic NPYs/ground truth. No study
data, published benchmark numbers or prize filings were changed.

## Findings and repairs

- **Reports could replace inputs or each other (P1).** `score --json-out`
  pointing at `--instances` loaded/scored the NPY, then replaced it with JSON.
  Trace report/instance destinations were not checked for collisions before
  data work. A shared `BenchmarkArtifactPlan` now reserves the report, requested
  instance output and probability-cache outputs against each other and the
  declared cube/model/instance sources. All-cube floors plan every cube before
  processing the first. Resolved paths, ancestors and inode identities are
  compared, and symlink/special/directory destinations refused. Plans are
  rechecked before publication; cache writes also check their own boundary.
- **Score provenance could identify unscored bytes (P2).** The old path loaded
  an array, scored it and later hashed its filename. A fixture replacing that
  file during scoring bound the new file's digest to the original scores.
  `read_instances` now parses and hashes one captured regular file. Its array
  is an immutable view of the same bytes, preserving integer IDs, byte order
  and C/Fortran layout without a second full array copy.
- **Interrupted trace publication could retain a stale report (P2).** Saving
  instances and then failing to write JSON left the previous report in place.
  The selected report is now invalidated before instance replacement and written
  last. Its previous mode is retained through an explicit permissions argument
  to the existing atomic-file helper. Trace reports identify the saved NPY's
  actual staged bytes with path, digest, size, shape and dtype, or null when
  no instance file was requested.

The three initial regressions failed before repair: source overwrite was not
refused, a reported digest differed from the scored bytes, and data loading
preceded detection of aliased trace outputs. Existing reports and metrics were
not regenerated; the scoring version, formulas and tracer recipe remain intact.

## Architecture and user workflow

Artifact planning is separated from instance decoding and CLI orchestration.
It does not require data/model loading or create output directories. Normal
safe report refreshes remain supported, including all-cube floor row carryover.
Guarded destinations cover the requested cube families and model files; this is
not a recursive audit of every unrelated artifact in the data directory.

The regular-file capture implementation moved unchanged to
`core/file_capture.py`, so installed package code does not depend on repository
scripts. `scripts.text_snapshot` reexports it for existing callers and retains
UTF-8/BOM and snapshot verification behavior. Its local source bootstrap keeps
the helper usable under Python `-S` without an editable install or site packages.

`score --max-instance-bytes` defaults to 2 GiB, including the header. NPY header
parsing is limited to 10,000 bytes and uses a small prefix buffer. Shape, dtype
and exact payload length are verified before exposing an array, including a
regression for a tiny file declaring a trillion-element allocation. Plain integer
NPY versions 1–3 are supported; object/structured arrays, NPZ, negative IDs,
truncated/trailing payloads and malformed dimensions are refused. The limit is
not an RSS or GPU-capacity estimate; other benchmark stages have separate costs.

Score provenance retains `instances_sha256` and adds source path, byte count
and dtype. The digest describes the loaded capture even if the path is later
replaced. CLI data/path errors get a concise diagnostic and exit 1; invalid
usage exits 2. Programmatic `main` retains exceptions for these input failures.
See [fiber tracing](FIBER_TRACING.md) for the complete invocation and report fields.

## Verification

Python 3.10.21 / Torch 2.9.1+cpu / NumPy 2.2.6, with Villa pinned at
`ccb431818fa68059138f2c964ae299fc474ff116`.

- After updating to current main, the affected selection passed **370 tests in
  48.37s**, across 12/186 curated modules. It covers benchmark workflows, NML
  imports, capture/snapshot consumers, production inference, workspace/report
  inspection, file modes, checkout isolation and test registration.
- Final benchmark follow-up after protecting model paths in score-only mode:
  **49 passed in 3.72s**. Includes capture identity despite path replacement,
  NPY versions/layouts/byte orders/large uint64 IDs, malformed/oversized/special
  inputs, aliases/late changes, whole-list preflight, cache aliases, interrupted
  trace publication, preserved permissions, trace output hashes, CLI diagnostics
  and stdlib-only capture imports.
- Required smoke: **8/11 passed, 3 skipped, 0 failed in 9.1s**. Local training
  data and the optional batchgenerators transform were unavailable. Available
  model/import/augmentation checks passed, including 288/288 checkpoint tensors.
- Ruff lint/format and scoped Mypy passed all eight changed Python files.
  Exact commands and captured output are recorded in the PR.

The tracing/scoring tests use synthetic geometry and stub semantic inference;
their artifact handling is real. No full curated suite, CUDA/RTX 4090 semantic
model run, full-cube memory/runtime benchmark or new scientific measurement was
performed. CT, NML, model and probability-cache contents are not captured
together. Inputs/paths must remain stable and writers serialized; path rechecks
are not locks. Publication remains per-file, with no cross-file transaction or
rollback: a failed trace can leave instances without its selected report.
