# Fiber label generation

`scripts/labeling/generate_fiber_labels.py` produces either CT vesselness
pseudo-labels or annotation-derived orientation labels. Both are heuristics that
need independent review before training or evaluation. The script uses the
repository's fiber filter; candidate mode needs neither a Villa checkout nor
WebKnossos. Install the project dependencies first.

## CT candidate windows

```bash
python scripts/labeling/generate_fiber_labels.py \
  --candidates /data/ranked_candidates.tsv \
  --evidence-root /data/fiber-run-001 --depth 16 --top-n 5 --dry-run

python scripts/labeling/generate_fiber_labels.py \
  --candidates /data/ranked_candidates.tsv \
  --evidence-root /data/fiber-run-001 --depth 16 --top-n 5
```

The output directory **must be new**, with no source/output ancestor, descendant,
or alias relationship. Previous versions appended into an existing evidence
tree. That behavior is retired: choose a fresh run directory and explicitly
verify candidate identity when adding other artifacts later. The new default is
`reports/fiber_labels_run`, rather than `reports/scroll23_evidence`.

The TSV has unique, nonempty headers and these required columns:

| Column | Meaning |
| --- | --- |
| `artifact_stem` | Safe prediction basename; no path separators |
| `local_uri` | Local CT Zarr path, resolved relative to the caller's working directory |
| `z`, `y`, `x` | Nonnegative source voxel origin |
| `height`, `width` | Requested Y/X extent, at least 3 each |

The first `--top-n` rows are selected in file order; the tool does not re-rank
them. `top-n` is between 1 and 256. The input TSV is a regular file of at most
16 MiB; its bytes are hashed again before publication, so a pipe or process
substitution is refused. A row repeating an earlier row's resolved `local_uri`,
origin and shape is rejected. The check compares paths, so a group and its
level-0 array (`ct.zarr` and `ct.zarr/0`) are not recognized as one source.
`review_score`, when supplied, must be finite; missing scores stay unknown.
Cohort identifiers `scroll_id`, `short_id`, and `division`, when supplied, must
be nonempty. Other columns are preserved in `candidate.json`. The
[candidate ink/fiber report](CANDIDATE_INK_FIBER_REPORTS.md)
requires those cohort identifiers and separately prepared ink predictions.

CT must be a real numeric 3D `(z, y, x)` Zarr array, or a group containing array
`0`. The exact requested window must fit entirely in it; bounds are never
clipped. Every axis is at least 3, and `depth * height * width` must fit
`--max-voxels` (default `128**3 = 2,097,152`). The source crop must remain finite
after float32 conversion. Uint8 intensities are divided by 255; other numeric
intensities retain their scale. This preserves the existing normalization.

CPU is the default. `--use-gpu` explicitly requires usable CuPy/CUDA. Missing
CUDA, allocation failures, and filter failures fail the run without a CPU retry.
The vesselness filter runs on the whole requested window. The voxel budget is
**not a hard RAM or VRAM limit**: filter temporaries, codec chunks, and GPU pools
need additional memory. Choose small regions and profile before increasing it.

`--threshold` is finite in `[0, 1]`, default `0.5`. Binary labels use
`response >= threshold`; threshold zero therefore includes zero responses.
`fiber_prob.tif` keeps its legacy filename, but contains an uncalibrated
vesselness response, not a measured probability of fiber material. Boundary
responses retain the existing filter's behavior; compare identically framed
regions and review edges independently.

Dry run parses and hashes the same TSV bytes, validates settings and output
separation, and prints a plan. It does **not** open CT, verify data bounds, probe
CUDA, or create output directories. A successful plan does not establish that
execution will succeed.

## Completed run artifacts

```text
fiber-run-001/
  fiber_labels_summary.json
  candidate_000/
    candidate.json
    fiber_prob.tif
    fiber_label.tif
    fiber_labels_meta.json
  candidate_001/...
```

The TIFFs are scalar ZYX volumes: float32 finite vesselness in `[0, 1]` and uint8
binary labels. Both are read back and compared before publication. Metadata
records source path, source shape/dtype and attributes, source-local
`evaluated_bbox_zyx` in **z0/z1/y0/y1/x0/x1** inclusive-exclusive order, decoded CT
content digest, filter source hash, threshold, backend, labeled fraction, and
the two serialized TIFF hashes. The summary binds the captured TSV hash, lists
final artifact paths, and is written last, after the rechecks below. Attribute
preservation does not validate the source's physical coordinate claims. These
TIFFs are not OME-Zarr exports.

All selected headers are checked before backend selection. The run is built in
a sibling staging directory, then published as one new directory after every
candidate succeeds. Before publication, the TSV, filter source, source metadata,
and every selected decoded CT region are checked again. A failure publishes no
final run; an existing output is preserved and rejected. A killed process
(SIGKILL, or the default SIGTERM) leaves its hidden staging directory,
`.<run name>-*` beside the output; remove it by hand. Exit status is 0 for
success or a plan, 1 for execution/input failures, and 2 for argparse errors.

Keep sources stable and serialize writers. Hash rechecks detect changes at the
checked points; they do not provide a filesystem snapshot or guard against a
source changing and reverting between reads. Publication uses rename and does
not promise concurrent-writer safety or durability across power loss.

The [co-occurrence report](CANDIDATE_INK_FIBER_REPORTS.md) checks this sidecar
when present; use its `--require-fiber-metadata` option to reject missing fiber
provenance. It compares recorded source geometry and the serialized label hash.
This does not prove physical ink/fiber registration or independently verify CT
bytes. Verify the actual CT window and prediction frame before associating
them; matching dimensions and a high descriptive ratio do not establish ink
accuracy.

## WebKnossos skeleton annotations

```bash
python scripts/labeling/generate_fiber_labels.py --mode skeleton \
  --nml-path /data/fibers_s5_00010z_00020y_00030x_64_v00.nml \
  --output-dir /data/skeleton-run-001 --n-workers 1 --radius 2 --dry-run
```

Remove `--dry-run` to execute with the optional `webknossos` package installed.
The filename must encode `_sN_Zz_Yy_Xx_SIZE_vREV.nml` (an optional `a` after the
scroll number is accepted). Coordinates in the annotation are interpreted as
XYZ voxel positions in that encoded source frame; this tool does not rescale
or register them. The cubic label volume is ZYX and must fit the same voxel
budget. The legacy 500-cube default needs an explicit larger budget; profile
memory before allowing it. One CPU worker is now the default because each
worker holds whole-cube temporaries. Submitted trees and retained results are
limited to one batch of at most that many workers, rather than every tree.

The existing edge interpolation, expansion, and principal-axis classification
remain heuristic: `0=background`, `1=horizontal`, `2=vertical`, `3=mixed`.
Bounds are checked in XYZ before integer conversion, so negative fractional
positions do not paint voxel zero. An empty skeleton mask stays empty through
expansion. The tool stages and verifies `labels.tif`, records the NML hash,
origin, shape, settings and TIFF hash in `labels_meta.json`, and rechecks the
NML before publishing the new directory. Dry run checks filename/settings only
and does not load the annotation or import its SDK.

Native WebKnossos parsing and processing SDK tree objects in subprocesses were
not exercised, and neither was real CUDA. Geometry and publication regressions
run on CPU; SDK publication tests use a stub. A real two-worker process pool was
tested with synthetic tree objects. The small public-CT check is operational
parity evidence,
not a label-quality result. See the
[design and architecture review](DESIGN_ARCHITECTURE_REVIEW_2026-10-30_FIBER_LABELS.md).
