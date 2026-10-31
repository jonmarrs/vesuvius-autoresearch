# Inspect and prepare a teacher prediction

Distillation uses released **model predictions**, not annotated ground truth.
Choose the intended prediction before creating training labels. Inspect the
metadata plan with a new local cache path:

```bash
python -m repro.sota_data.teacher_cache \
  --prefix "PHercParis4/segments/<segment>/ink-detection" \
  --out "local_data/sota_distill_teachers/scroll1_<segment>.teacher" \
  --dry-run
```

With exactly one direct, non-hidden `.tif`, the plan selects it. With multiple
predictions, the command reports the candidate basenames and requires
`--source exact_prediction_name.tif`. It previously chose the first name
lexicographically, which did not establish that it was the intended model.
Remove `--dry-run` to fetch the chosen prediction. Public bucket-relative prefixes
and `s3://vesuvius-challenge-open-data/...` are accepted; other buckets and unsafe
paths are refused. Missing `.tif` layouts are not guessed from PNG or Zarr stores.

Fresh-cache plans are `METADATA_PLAN_ONLY`: direct remote metadata is read, with
no object-body reads or output writes. Existing-cache plans are
`CACHED_METADATA_ONLY`: local metadata, TIFF headers and file sizes are checked,
with `payload_hash_checked: false`. They do not rehash image bytes or contact S3.
Neither plan assesses pixel values, annotation quality or registration. Help
imports only Python's standard library; normal commands need image libraries and
new downloads need s3fs. No Torch, training or GPU work is performed.

## Cache completion and reuse

The cache is a complete directory containing `teacher.tif` and `teacher.json`.
The latter records the chosen source URI, candidate URIs, observed object
identity, payload byte count/SHA-256 and scalar TIFF header. Each S3 range request
uses the existing downloader's explicit ETag condition and bounded body checks.
Selected metadata is relisted afterward. Payload hashes, exact local layout and
completion JSON are rechecked before the staged directory is renamed into place.
A failed transfer never becomes the final cache. A killed process may leave a
hidden staging directory; it is not reusable as a completed cache.

Ordinary reuse is local and rehashes the file. It refuses missing/changed files,
bad or missing completion metadata, unexpected entries, symlinks, source-prefix
or explicit-prediction mismatches. An existing cache pins its recorded prediction;
it does not discover newer remote models automatically. Choose a fresh cache path
for a different prediction. Serialize writers and keep artifacts immutable.

`distill_run.fetch_teacher(segment, scroll_key=...)` now returns the bundle's
`teacher.tif` path, preserving the file-path API. Its default bundle is
`local_data/sota_distill_teachers/<scroll_key>_<segment>.teacher`.

**Legacy cache migration:** the old `<scroll_key>_<segment>.tif` and Scroll-1
`<segment>.tif` files have no verifiable completion boundary. An interrupted
download used to leave a partial file that the next call immediately reused.
Those files and their old `.source.json` sidecars are not automatically trusted,
adopted or deleted. Fetch a new bundle with the command above at the expected
`.teacher` path; once complete, the preparation runner uses it and leaves the old
file alone. A directory left incomplete by external edits also needs a fresh path
or deliberate operator cleanup; there is no automatic repair/resume.

## Budgets and decoding

The download budget defaults to **2 GiB**, with an explicit `--max-bytes` maximum
of **8 GiB**. A declared larger object fails before transfer. Direct listings
accept at most 4096 entries; a completion record is at most 64 KiB, with candidate
metadata checked before payload transfer. SDK listing buffers, HTTP/retry traffic
and disk reservation are outside these limits.

Before publication, the TIFF header must describe one nonempty scalar 2D image,
at most **536,870,912 pixels**, with uint8, uint16 or float16/32/64 samples. Color,
stacks and signed/unsupported types fail. This is a header check; downloading does
not certify finite or meaningful model probabilities.

`read_teacher(path)` checks a present bundle record, captures at most 8 GiB of
encoded bytes, checks the same captured bytes against the recorded SHA-256, then
decodes from that buffer after checking the header. It validates float values and
returns `(pixels, provenance)` with the input identity. Direct explicitly supplied
legacy files may be read for inspection, but claim no remote source identity; old
unbound sidecars are ignored. A bundle payload whose metadata is missing cannot
silently downgrade to that path. The compatibility `teacher_provenance(path,
pixels)` helper additionally refuses supplied pixels that differ from the decoded
source.

These are accepted input caps, **not a process peak-memory guarantee**. The encoded
capture, decoded teacher, validation and crop buffers coexist; float64 alone uses
eight bytes per pixel. Full-size exports may require substantial CPU RAM. Large
downloads, peak memory and throughput were not benchmarked. The ordinary
preparation runner uses the default 2 GiB download/reuse budget; a larger workflow
must explicitly call the Python fetch API with `max_bytes=...` before reading and
preparing its regions.

## Pseudolabel preparation

Both single-scroll and cross-scroll preparation now load teacher pixels and
provenance together. A float teacher's `auto` encoding is resolved over the full
teacher: [0,1] if its maximum is <=1, otherwise [0,255]. That mode is carried into
each crop, so a crop's range cannot silently change its units. This heuristic does
not infer physical units; explicit callers can use
`read_teacher(path, float_encoding="byte" or "unit")` and pass the recorded mode
to `prep_distill_fragment(..., teacher_encoding=...)`.

Crop boxes must contain integer coordinates and fit entirely inside the declared
level. Negative indices, clipping, reversed/empty boxes, fractional indices and
crops that disappear at a coarser teacher level fail. Existing power-of-two
pyramid-scale checks and nearest-neighbor label resampling remain in effect;
shape compatibility alone does not prove CT alignment.

`prep_distill_fragment` requires nonempty `(depth,height,width)` layers and a
scalar 2D teacher. RGB inputs must be explicitly converted upstream; the first
channel is no longer silently selected. Thresholds must be integer byte values
in [0,255], default 128. NaN, infinity, booleans and fractional thresholds fail
before writing. Labels use `>= threshold` after uint8 conversion as before.

Each completed fragment carries `TEACHER_PSEUDOLABEL` provenance, threshold,
teacher shape/dtype/encoding and the full teacher source identity when supplied.
`ground_truth`, `alignment_verified`, `label_quality_verified` and
`training_ready` remain false. These changes do not revise historical reports or
measurements, adopt checkpoints, or establish better ink detection. Hashes and
ETags record observed bytes/objects and do not authenticate a scientific release.

The cache CLI exits 0 for a completed plan/download/reuse, 1 for input or I/O
failure, and 2 for usage errors. See the [design review](DESIGN_ARCHITECTURE_REVIEW_2026-10-31_SOTA_TEACHERS.md)
for the regression scope and validation limits.
