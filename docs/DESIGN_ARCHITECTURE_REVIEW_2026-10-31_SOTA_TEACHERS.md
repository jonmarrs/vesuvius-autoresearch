# Design and architecture review: teacher ingestion and pseudolabels

Reviewed main `dc7de981` in an isolated checkout on October 31, 2026 (UTC).
Scope: distillation teacher downloads, cache reuse, teacher decoding/cropping and
single-/cross-scroll pseudolabel preparation.

## Findings and fixes

1. **An interrupted download became a reusable teacher.** A synthetic transport
   wrote `partial TIFF`, raised an error, and the next `fetch_teacher` call returned
   that file immediately with no source record. New downloads stage a directory
   containing the image and a completion record, verify it and publish once.
   Reuse checks the completion schema, exact layout, source identity, image header
   and observed bytes. Legacy unverified files are refused with migration guidance;
   no old cache is deleted or silently adopted.
2. **The first prediction by filename was silently chosen.** That order does not
   identify the desired teacher. Multiple candidates now require an explicit
   basename. A new CLI provides metadata-only plans and byte budgets, records the
   chosen source and candidates and uses the existing downloader's conditional
   range reader. No second S3 transfer implementation was introduced.
3. **Teacher pixels and reported source were unbound.** An old sidecar could claim
   a remote file for different local pixels. `read_teacher` hashes and decodes the
   same captured bytes, verifies a bundle's recorded identity and returns pixels
   and provenance together. Direct legacy inspection claims no remote identity.
   The compatibility provenance helper refuses mismatching supplied pixels.
4. **Crops could change a float teacher's units.** A full teacher containing 2.0
   uses byte units under the existing heuristic; a crop containing only 0.75 was
   independently treated as unit-scaled and became 191, crossing the ink threshold.
   Both orchestration paths now carry the full teacher's resolved mode into crops.
   Explicit unit/byte modes remain available for callers with known release units.
5. **Invalid arrays and thresholds silently produced labels.** RGB input selected
   its first channel; a NaN threshold generated all-background labels. Both were
   reproduced together before the fix. Preparation now requires scalar nonempty
   teachers, 3D layers and integer thresholds in [0,255]. Crop boxes must fit the
   declared level, with no negative slicing, clipping or fractional truncation.
   A baseline negative crop `(-2,0,10,10)` returned the last two rows; it now fails.
6. **A fragment did not identify its supervision as a model prediction.** The
   shared publisher now receives per-fragment `TEACHER_PSEUDOLABEL` provenance,
   including threshold, shape, dtype, encoding and the teacher input identity when
   supplied. Ground truth, registration, label quality and readiness are not
   inferred from a successful preparation step.

`teacher_cache.py` owns standard-library-only CLI help. `teacher_artifacts.py`
owns selection, immutable cache publication/reuse and captured-byte image loading,
reusing the internal `download_artifacts` transport. `distill_prep.py` validates
geometry/thresholds and prepares labels; the existing shared fragment publisher
owns output readback, hashes and directory publication. Orchestrators load each
teacher once together with its provenance and carry its mode into every crop.
Historical report calculations, checkpoints and the Villa pin are unchanged.
See [usage and migration](SOTA_TEACHER_CACHE.md).

## Verification and limits

The curated selection passed **376 tests in 30.36s, no skips**, including **45 new
teacher contract cases**. Scope: 13/165 curated modules selected by `*sota*`,
surface-render contracts, the surface renderer and validation runner/coverage
checks. Focused teacher and existing distillation tests passed **61 in 8.42s**.
Three existing tifffile RGB storage deprecations remain in registration fixtures.

Tests cover interrupted transfers followed by retries; ambiguous and explicit
selection; fresh and cached metadata-only plans; budgets before transfer/decode;
cache corruption, missing metadata, extra files and symlinks; observed input
hashes; actual single-/cross-scroll preparation; invalid teachers, thresholds
and crop boxes; and CLI behavior. Actual s3fs/aiobotocore stub tests cover the
whole teacher-publication path, fragmented response bodies, explicit Range and
IfMatch parameters, and a 412 precondition failure. These use service stubs and
synthetic images, not live full prediction downloads.

The required smoke check passed **8/11, 3 skipped, 0 failed in 11.2s**. Skips were
two absent local training datasets and the unavailable BGv2 augmentation entry
point. Host font-cache warnings did not fail checks. Ruff lint passed for eight
changed Python files, formatting for six fully formatted files, and Mypy for six
teacher/preparation/test files. Changed sections in the two legacy orchestrators
were formatted without rewriting their unrelated reporting code.

No live research measurements or files were used; no GPU jobs, model promotion,
training, cache migration or dataset rewrite occurred. The smoke check uses the
tracked model in the isolated checkout. The full repository suite, real large
teacher exports, peak memory, throughput, GPU/scientific quality, CT alignment,
concurrent writers and power-loss durability were not tested. Encoded captures
and decoded images coexist; accepted byte/pixel caps do not bound every decoder
allocation. SDK metadata buffers and retry traffic are outside input budgets.
An immutable local cache pins observed bytes and does not discover remote updates
or authenticate the scientific release. `auto` intensity scaling remains a range
heuristic, and all downstream metrics on these labels measure teacher agreement.
