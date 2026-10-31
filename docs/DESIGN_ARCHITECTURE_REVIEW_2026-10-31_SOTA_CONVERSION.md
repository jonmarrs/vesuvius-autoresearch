# Design and architecture review: SOTA fragment conversion

Reviewed main `59c2419e` in an isolated checkout on October 31, 2026 (UTC).
Scope: the raw TIFF converter, qualitative depth extraction, shared fragment
publisher and downloader selection handoff.

## Findings and fixes

1. **Depth planes used different intensity scales.** In a synthetic float32
   volume, `0.5` at the same spatial position became 127 in one output plane and
   0 in another because only the second plane contained a value above 1. Both
   the raw converter and qualitative writer chose scaling per plane. The shared
   publisher now resolves `auto` once across the selected volume, with explicit
   `unit` and `byte` alternatives that validate their declared ranges. Integer
   mappings and the single-image teacher helper remain compatible.
2. **Centering rules disagreed and explicit requests were clipped.** With 40
   available planes and 25 requested, qualitative extraction began at 8 while
   raw conversion and download began at 7. A far-out explicit center silently
   returned a boundary window. One dependency-free helper now owns the default
   floor rule and refuses explicit windows that cannot fit.
3. **Conversion eagerly decoded unbounded inputs.** A header preflight checks
   scalar TIFF layout, common shape/dtype, a selected-volume voxel budget and
   per-file encoded size before pixel decoding. A new CLI exposes the plan and
   explicit encoding. RGB/palette/transparency, multiframe or uint16 supervision
   is refused rather than silently coerced. Existing origin-preserving two-pixel
   label/mask fitting and exclusion of padded label pixels are preserved.
4. **The download-to-conversion handoff was unverified.** Conversion now hashes
   and decodes the same captured bytes, validates a present download completion
   record, and checks consumed payload identities. Legacy raw inputs without
   that record remain explicitly unverified against a downloader record.
   Source selection, headers and consumed hashes are rechecked before publication.
   Review also reproduced a deleted downloaded mask being replaced by an
   all-valid mask. Recorded supervision selection must now match too, so a
   missing mask fails before decoding.
5. **Successful image writes were accepted without readback.** Shared output
   publication now decodes TIFF/PNG files and compares intended pixels, records
   output hashes and encoding in `fragment.json`, reads metadata back and checks
   hashes after all staged writes. Corrupt-but-successful writes and later output
   rewrites fail without publishing a final fragment. Existing destinations are
   still refused, and qualitative outputs still have no invented ink labels.

`convert.py` retains the Python entry point and lazy `to_uint8` compatibility
export, and provides standard-library-only CLI help. `conversion_artifacts.py`
owns local planning, captured input decoding and source verification. The shared
publisher owns encoding and complete output publication, and `depth_window.py`
keeps selection consistent without importing image/S3/ML libraries. Downloader
source captures now include that shared helper. See [usage and migration](SOTA_SEGMENT_CONVERSION.md).

## Verification and limits

The selected curated suite passed **331 tests in 25.91s, no skips**, including
55 new conversion contract cases. Twelve of 164 curated modules were selected:
all `*sota*` modules, surface-render contracts, the surface renderer and validation
runner/coverage checks. Actual downloader SDK tests use service stubs; input
images and mutation/failure fixtures are synthetic. Three existing TIFF RGB
storage deprecation warnings remain in registration fixtures.

The required smoke check passed **8/11, 3 skipped, 0 failed in 14.7s**. Skips were
two unavailable local training datasets and the missing BGv2 augmentation entry
point. Ruff check/format passed for eight changed Python files; Mypy passed for
seven conversion/download/test files with explicit package bases. Test evidence
includes the actual detector loader, raw download-to-conversion roundtrip,
consistent odd selection, explicit center refusal, integer byte parity,
big-endian uint16, transparent/mixed-dtype rejection, no-decode/no-write plans,
source mutation, corrupt writes and metadata-stage output mutation.

These are isolated CPU engineering checks. No live research checkout or study
measurements were used; no GPU jobs, dataset rewrites or checkpoint promotion
occurred. The smoke check uses the tracked isolated model. No full-repository,
large-volume, speed or peak-memory benchmark, concurrent-writer or power-loss
guarantee is claimed. Limits constrain accepted inputs, not every allocation
inside third-party decoders. Array-based callers retain responsibility for
acquisition limits. `auto` remains a heuristic and cannot establish physical
units. Hashes do not establish scientific release authenticity or CT alignment;
label quality and training readiness remain false.
