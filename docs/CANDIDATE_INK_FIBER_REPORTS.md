# Candidate ink/fiber co-occurrence reports

The historical `cross_scroll_validation.py` filename now denotes a descriptive
report over existing candidate arrays. It measures no accuracy or generalization.
A CT-derived fiber heuristic and an ink model can depend on the same CT, and ink
need not avoid fibers. A non-fiber/fiber probability ratio above or below one is
not evidence of correctness or independent validation.

## Inspect a candidate tree

```bash
uv run python scripts/cross_scroll_validation.py \
  --evidence-root /path/to/evidence --out /path/to/new_report \
  --top-n 12 --fiber-threshold 0.001
```

The output directory must be new and disjoint from the evidence root and input
artifacts, including resolved symlink targets. It contains `summary.json` and
`summary.md`, published together after validation. Failed rendering, a corrupt
JSON write, an appearing destination, or changed inspected inputs prevents
completed publication. Serialize writers and keep inputs stable.

Exit 0 means every selected candidate was mechanically inspected. Exit 2 means
a **PARTIAL** report was published with candidate-specific missing/invalid
records; those records do not enter group statistics. Exit 1 means an input,
catalog, or publication error prevented a completed report. CLI argument errors
use argparse's exit 2 without publishing. Stdout is finite JSON with status,
output, and inspected/failed counts; input errors go to stderr.

`--top-n` now limits the report itself: candidates are sorted by numeric directory
index, and the first N are selected. This is catalog selection, not a population
estimate. Requested, discovered, selected, inspected, and failed counts are
separate. Default N is 12; the maximum is 256. Discovery is bounded at 4,096
candidate entries. Entries must be real `candidate_<integer>` directories;
duplicate numeric indices, files, malformed names, and directory symlinks fail.

The old `--output-json`/`--output-md` flags are retired. Consume the paired files
inside `--out new_directory` instead. `--auto-generate-fiber-labels` is also
retired: this command reads existing artifacts and launches no label producer,
model, training run, or external process. The old auto command referenced an
absent script and did not pass the selected evidence root. Prepare and review
labels separately. Historical result files and dated studies were not rewritten.

## Accepted artifact contract

Each selected directory contains:

```text
candidate_000/
  candidate.json
  fiber_label.tif
  predictions/
    <artifact_stem>_ink.zarr/
    <artifact_stem>_meta.json          # checked when present
```

Candidate metadata must be a JSON object with a safe basename `artifact_stem`,
nonempty `scroll_id`, `short_id`, `division`, and `local_uri`, nonnegative integer
Z/Y/X origins, and positive integer width/height. TSV-style numeric strings are
accepted; booleans, fractions, nonfinite values, duplicate keys, and traversal
stems fail. A supplied review score must be finite. Missing review scores remain
unknown. Metadata files are limited to one MiB.

The completed summary JSON is checked against the same one-MiB limit; reduce
`--top-n` if a large selection or long source paths exceed it.

Ink predictions must be a nonempty `(H,W)` or `(1,H,W)` Zarr array, bare or under
explicit level `0`. Older exporter directories containing `/0` without a root
`.zgroup` remain readable. No multi-slice volume is reduced to its first slice.
Uint8 means probability divided by 255; floating values must be finite in [0,1].
Other encodings fail. The plane must match candidate height/width exactly.

Fiber TIFFs contain one scalar YX or ZYX series using binary 0/1 or 0/255 labels.
The encodings are normalized before projecting a depth volume by its binary
occupancy mean. Probability maps, mixed encodings, multiclass/orientation labels,
RGB images, extra series, malformed reads, and nonfinite labels fail. TIFF axes
YX, ZYX, QYX, and IYX are accepted; ambiguous color/channel axes are not depth.
The projected Y/X shape must exactly match the ink plane. There is no implicit
crop, resize, broadcasting, or registration.

The default ink-plane budget is 4,194,304 pixels (`--max-pixels`). The default
fiber budget is 2,097,152 voxels (`--max-voxels`). Headers are checked before
materializing Zarr data or decompressing TIFFs. The TIFF file byte budget is
`16 * max_voxels + 1 MiB`. Increase bounds explicitly for a deliberate larger
inspection. Arrays are handled one candidate at a time; no CT volume is read.

## Geometry and provenance

When prediction `<stem>_meta.json` or exporter Zarr `meta.json` is present, its
source URI, X/Y/Z origin, dimensions, and single-surface declaration must agree
with the candidate. Redundant scalar coordinates must agree too. Recorded
partial/sharded inference or incomplete coverage fails. Relative source paths
are interpreted from the repository root, matching the existing producer's
historical commands, so invocation from another working directory is stable.

Absent prediction metadata remains unknown. The record distinguishes
`prediction_geometry_checked` from `prediction_completeness_recorded`. Neither
proves a complete inference run: the report does not verify model weights,
blend-weight coverage, every stored Zarr chunk, or training lineage.

Fiber files do not carry a checked source origin in this workflow. Consequently
`alignment_verified`, `independent_validation`, and `accuracy_measured` remain
false even when array shapes and recorded prediction geometry agree. Supply
separate registration evidence before interpreting a relationship spatially.

Records contain candidate/fiber/present-prediction-metadata file SHA-256 values
and a digest of the decoded ink plane: JSON shape followed by contiguous
little-endian float64 normalized probabilities. Inputs are rechecked after
measurement and before publication; newly appearing prediction metadata also
fails. The digest is not a hash of the complete raw Zarr store or CT bytes.

## Metric interpretation

Fiber-region pixels have projected occupancy **strictly greater than** the
threshold. A threshold of 0.001 does not always mean any positive voxel: with
depth 1,001, one positive voxel has occupancy below 0.001.

`ink_anti_fiber_ratio` retains its historical field name and is the non-fiber
mean ink probability divided by the fiber mean probability. Absent fiber or
non-fiber regions, a zero fiber mean, or an overflowing ratio produces JSON
`null` with an explicit `ratio_status`. Zero-ink arrays remain measurable; no
epsilon or infinite ratio is manufactured.

Groups include scroll ID, short ID, and division. They report candidate counts,
defined-ratio counts, undefined-reason counts, and the equal-weight mean of
defined per-candidate ratios. This is not a pooled pixel ratio; no failed or
undefined candidate is silently assigned a replacement value. The report gives
mechanical and descriptive evidence only, not a ground-truth score or prize gate.
