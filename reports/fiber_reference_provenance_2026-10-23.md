# Fiber reference provenance audit — 2026-10-23 UTC

The published fiber references contain substantial tracer-generated geometry
between annotator control points. That supports a small clarification in
Villa's evaluation documentation; it does **not** establish that the reference
favors a particular tracer or that a scoring change improves evaluation.

This is a descriptive follow-up to [Villa #2264](https://github.com/ScrollPrize/villa/issues/2264),
not a registered experiment. All 620 PHerc0139 and 233 PHerc0332 JSON files
listed by the public annotation folders were downloaded and audited locally.
The 318,241,559 original bytes stay outside the repository. Per-file SHA-256,
size, captured listing hashes, source URLs and completion times are preserved:

- [PHerc0139 audit](evidence/fiber_reference_pherc0139_2026-10-23.json)
- [PHerc0332 audit](evidence/fiber_reference_pherc0332_2026-10-23.json)
- [Snapshot and script bindings](evidence/fiber_reference_snapshots_2026-10-23.json)

Source data: Vesuvius Challenge open data, CC BY-NC 4.0. The annotations remain
credited to their recorded annotators; this report does not alter those files.

## What the data establishes

| Folder | Files | Control points | Saved line points | `trace` spans | `cspline` spans | `lasagna` spans |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| PHerc0139 | 620 | 18,076 | 2,307,098 | 13,862 | 3,034 | 560 |
| PHerc0332 | 233 | 16,160 | 682,279 | 2,422 | 13,464 | 41 |

The PHerc0139 span counts exactly match #2264. Every recorded `trace` span
in both folders has the same saved configuration: beam width 8, lookahead 2
and cone angle 25 degrees, among the other fields retained in the audit.
Those three values match `FiberTraceConfig` on Villa main `e2254ebe`.
This is not a claim that the annotations record every current configuration
field or that reproducing those three values recreates each saved line.

The length calculation here is **the Euclidean chord between consecutive
control points**, grouped by the starting control point's
`segment_to_next.interp_mode`. It does not measure the interpolated line's
arc length. #2264's exact length calculation was not reproduced, so the
percentages below should not be substituted for its 98.1% / 87.0%.

| Recorded coordinate frame | Files | `trace` share of control-chord length |
| --- | ---: | ---: |
| `PHerc0139/20260102150214@L0` | 619 | 97.9813% |
| PHerc0139 frame field absent | 1 | 100.0000% |
| `PHerc0332/20251211183505@L0` | 5 | 99.8836% |
| PHerc0332 frame field absent | 228 | 84.8983% |

The 1 and 228 files also omit `vc_open_data_source_original_resolution`.
Missing metadata is not evidence of incorrect coordinates: the evaluator
requires callers to supply base XYZ and does not transform from these fields.
The audit keeps missing-frame files in an unknown group and does not pool
lengths across frames or convert them to physical units.

`fiber_manifest` provenance is retained verbatim. Some values are local paths
rather than public URLs (912 PHerc0139 trace spans; 1,181 PHerc0332 trace
spans). A local path alone does not identify immutable prediction bytes, and
the audit does not guess a public replacement from a matching filename.

## Prepared Villa contribution

The [eight-line patch](../docs/villa_pr_fiber_reference_provenance.patch) adds
one paragraph to `volume-cartographer/docs/fiber_evaluation.md` explaining:

- `trace` spans remain eligible when Lasagna spans are excluded.
- Scores measure agreement with saved geometry, including interpolation.
- Annotation provenance matters when comparing tracers; scoring only clicks
  would be a separate protocol.

The existing documentation and Python `reference_cases()` wrapper were checked
at `e2254ebe`. The selector's documented policy is
`cp-bounded-no-lasagna-v1`; the documentation already explains that controls
must match the dense line. No scorer, selection rule, model or tracing default
is changed by the patch. No native evaluation run was needed or performed.

The Villa commit is `1edad72d6668fca85b19dac11c9b53c4292505be`, on
`jonmarrs/villa:docs/fiber-reference-provenance`, pushed from
`/workspace/villa-fiber-reference-docs`.
[The public comparison](https://github.com/ScrollPrize/villa/compare/main...jonmarrs:docs/fiber-reference-provenance?expand=1)
and [PR draft](../docs/VILLA_DRAFT_fiber_reference_provenance.md) preserve the
reviewed change. [Autoresearch #197](https://github.com/jonmarrs/vesuvius-autoresearch/pull/197)
publishes the audit and evidence.

The publication review corrected the upstream draft's relative evidence link
to an immutable Autoresearch permalink. It regenerated both audits from all
853 saved files: the complete outputs, download manifests, input hashes and
snapshot/script bindings match. Nine audit tests pass again (0.08 s), and the
smoke reports 8 passed, 3 skipped, 0 failed (6.7 s). The same review reran the
prepared native retry tests (13 passed, 40 deselected), fractional seeding
tests (20 passed) and SQLite tests (5 passed), with the compatibility import
limitations disclosed in their individual reports.

Villa PR creation for the native retry fix and normal merge of #2141 were
again denied by GitHub with HTTP 403, “Resource not accessible by integration”.
The account's repository permissions remain read-only. The second new PR
was not retried through the same blocked route. No authentication settings
were changed. All available GitHub Actions runs on #2141, #2258 and #2259
have completed successfully; their Vercel preview status is a separate
authorization failure. These observations are preserved in the
[review record](evidence/villa_pr_review_2026-10-23.json).

Searches for `2264`, `"reference provenance"` and
`"fiber_evaluation.md" "trace"` found no matching documentation patch.
[PR #2265](https://github.com/ScrollPrize/villa/pull/2265) proposes an optional
sheet-plane penalty and reports click-only results; it does not change this
documentation. [PR #2248](https://github.com/ScrollPrize/villa/pull/2248)
adds geometry/load QA, a separate purpose from this local provenance audit.

## Reproduction and checks

The downloader captures a listing once, refuses an existing destination, and
writes a success manifest only after every listed JSON has been downloaded.
No packages need installing for the downloader or audit (Python standard
library only). The real audit ran with Python 3.12.14.

```sh
python3 repro/fibers/fetch_reference_annotations.py \
  https://dl.ash2txt.org/other/annotators/0139_fibers/ \
  /workspace/villa-fiber-reference-evidence/pherc0139
# Downloaded all 620 listed JSON files (235298374 bytes)
python3 repro/fibers/fetch_reference_annotations.py \
  https://dl.ash2txt.org/other/annotators/0332_fibers/ \
  /workspace/villa-fiber-reference-evidence/pherc0332
# Downloaded all 233 listed JSON files (82943185 bytes)

python3 scripts/audit_fiber_reference_provenance.py \
  /workspace/villa-fiber-reference-evidence/pherc0139/annotations \
  --out reports/evidence/fiber_reference_pherc0139_2026-10-23.json
python3 scripts/audit_fiber_reference_provenance.py \
  /workspace/villa-fiber-reference-evidence/pherc0332/annotations \
  --out reports/evidence/fiber_reference_pherc0332_2026-10-23.json
```

All 853 saved files were rehashed and their manifest entries compared to the
audit's input entries. The final downloader's listing parser was also replayed
on both captured index files: its accepted names exactly match the manifests.
The snapshot record binds the final scripts and audit outputs by SHA-256.
Remote data can change; a future download is a new snapshot until hashes match.

```sh
VILLA_REVIEW_ROOT=/workspace/villa-native-retry AGENTS_AGENT_MODE=1 \
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
/workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 \
  /workspace/villa-review-evidence/run_python.py -m pytest -q \
  tests/test_audit_fiber_reference_provenance.py
# 9 passed in 0.09s

VILLA_REVIEW_ROOT=/workspace/villa-native-retry AGENTS_AGENT_MODE=1 \
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
/workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 \
  /workspace/villa-review-evidence/run_python.py scripts/smoke_test.py
# 8/11 passed, 3 skipped, 0 failed in 6.8s

python3 -m py_compile scripts/audit_fiber_reference_provenance.py \
  repro/fibers/fetch_reference_annotations.py
git diff --check
```

Tests cover span direction, chord versus dense-line measurement, byte hashes,
unknown metadata, invalid coordinates, separate coordinate frames, an empty
folder, a download/audit round trip and failure without a success manifest.
The smoke skips are the absent training URI/labels and unavailable bg2
augmentation entry point. Matplotlib/fontconfig also warned about the host's
read-only cache; the smoke checks completed successfully.

## Limits and next work

This does not reproduce #2264's click-only scores, CT review or model ranking.
It does not show whether the beam tracer made mistakes in these references.
The folders are a dated public snapshot, not an independent evaluation cohort.
The script counts metadata and does not validate VC3D loading or geometry;
#2248 is the existing upstream work for those checks.

Our Findings 91–95 use Dataset004/ScrollGT NML references and separate masks,
not these public JSON folders. This audit makes no new provenance claim about
those NMLs and does not invalidate, rerun or alter their registered results.
A true tracing-context follow-up to Finding 95 still needs GPU runs on the
24 octants; this environment has no GPU. No production Villa pin or loop state
changed. Existing fixes #2141, #2258, #2259 and the prepared #1482 retry fix
remain higher priority than adding another evaluation metric.
