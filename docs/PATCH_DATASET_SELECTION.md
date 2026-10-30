# Prepare patch-selection datasets

These commands prepare new local symlink datasets for the existing BOOTSTRAP,
RANDOM and STRIPMATCH recipes. They do not fit models, read study endpoints or
establish scientific improvement. Historical datasets and study results are not
updated by these code changes. Use the project interpreter (Python 3.10, as
required by `pyproject.toml`) for builds and checks; system Python versions can
use different floating-point summation behavior.

```sh
uv run python scripts/build_filtered_patch_dataset.py \
  --source /path/to/full_dataset --satisfied /path/to/reference.json \
  --out /path/to/new_bootstrap --mode bootstrap --threshold 0.90

uv run python scripts/build_filtered_patch_dataset.py \
  --source /path/to/full_dataset --satisfied /path/to/reference.json \
  --out /path/to/new_random --mode random --threshold 0.90 --seed 0

uv run python scripts/build_stripmatch_dataset.py \
  --full /path/to/full_dataset --reference /path/to/reference.json \
  --bootstrap /path/to/new_bootstrap --out /path/to/new_stripmatch --seed 0 \
  --require-manifests
```

Use the original full dataset as the source. Relative CLI inputs resolve from
the caller's directory; generated links use absolute, canonical targets and
remain valid after staged publication. The target must be a new, separate
directory. Existing paths, including dangling symlinks, are rejected. STRIPMATCH
no longer adds patches to an existing selection: choose a new output for each
build. Source data is linked, not copied.

The reference must contain a nonempty `patches` list with unique, safe basename
IDs, numeric finite fractions in [0,1], and nonnegative finite `total_area` values.
The total area must be positive. Duplicate JSON fields, nonfinite constants and
invalid/deep JSON fail. Limits are 100,000 reference patches, 64 MiB for the
reference JSON, 256 KiB per geometry JSON and 200,000 entries per enumerated
directory. Scored patch IDs must resolve to directories in `verified_patches/`.
Non-patch root entries are linked as auxiliary inputs. The reserved root name
`.autoresearch-selection.json` must not already exist in the source.

BOOTSTRAP retains IDs whose fraction reaches the threshold. RANDOM uses the
existing seeded shuffle and greedy total-area target; it does **not** match
patch count. A coarse patch can overshoot that target. The manifest reports the
achieved area; the independent selection checker remains necessary. Empty
selections are rejected.

STRIPMATCH requires a nonempty bootstrap selection containing only scored IDs,
plus valid finite 2×3 XYZ bounding boxes for **all** scored patches. Missing
geometry no longer silently reduces the draw population. Each box must have
ordered bounds. The established radial proxy, center and strip bounds, seeded
two-pool greedy draw, and 1% area / 0.005 strip-share tolerances are retained.
Aggregate ID order is now sorted to keep target sums stable across Python
processes. This is a deterministic input-preparation repair; prior studies were
not rerun or reinterpreted. The radial proxy does not establish physical winding
alignment or biological ground truth.

## Inspect a completed build

The new directory contains `verified_patches/`, auxiliary links and
`.autoresearch-selection.json`. The manifest records:

- the canonical source, exact selected IDs and their SHA-256, count and area;
- mode, seed, threshold where applicable, and reference JSON path/hash/size;
- the bootstrap area target and, for STRIPMATCH, bootstrap IDs, strip target and
  achieved share, radial settings and an aggregate geometry-source fingerprint.

`status: PREPARED` describes a finished selection artifact. It does not certify
study matching, payload integrity, scientific quality or prize eligibility.
Reference bytes and STRIPMATCH geometry bytes and bootstrap membership are
rechecked before publication. Link mappings are also rechecked. Payload files
and auxiliary file contents are not hashed; links still depend on their source
directories, so keep inputs stable and preserve them after building.

All links and the manifest are staged before a directory rename publishes the
result. Caught failures remove staging and leave no new completed output.
Writers must be serialized; this is not a concurrent-writer or crash-recovery
protocol. A killed process may leave a hidden staging directory. Builds do not
overwrite existing datasets or write through source symlinks.

Continue to run the registered checks before any fit, using explicit paths:

```sh
uv run python scripts/check_patch_selection.py \
  --reference /path/to/reference.json --bootstrap /path/to/new_bootstrap \
  --random /path/to/new_random --threshold 0.90 --require-manifests
uv run python scripts/check_patch_spatial_balance.py \
  --reference /path/to/reference.json --bootstrap /path/to/new_bootstrap \
  --random /path/to/new_stripmatch --full /path/to/full_dataset --require-manifests
```

The spatial checker reports diagnostics; follow the study's registered criteria
instead of inventing new acceptance thresholds from observed outcomes.

### Read machine-readable input checks

Selection manifests are now consumed by the builder and both checkers. A
present record must agree with the captured reference bytes (SHA-256 and size),
actual selected IDs/hash/count/area, source patch targets and expected role.
BOOTSTRAP must be the full threshold selection; a generated RANDOM arm whose
record is present cannot stand in for it. Checked BOOTSTRAP and control records
must use the same full source and, for RANDOM, the same threshold. STRIPMATCH
records also bind the bootstrap IDs and path; new builds preserve its manifest
snapshot as a dependency. Those inputs are rechecked before a successful report
or publication.

Use `--require-manifests` for newly prepared datasets, as above. It rejects an
arm whose record is missing; on the STRIPMATCH builder it requires the bootstrap
record. Without the flag, legacy inputs remain usable and are explicitly
reported as `absent` with unverified provenance. A present invalid record always
fails, including with the flag omitted. To use strict checks with an old
selection, rebuild a new dataset from preserved inputs. Identical reference
bytes copied to another file are accepted; changed bytes require a new build.

Both checkers reject the same physical patch container passed as both arms,
including aliases, and two arms that select exactly the same patches, such as a
copy of an arm's links. Different IDs cannot count the same physical patch
directory twice, in either a builder's scored population or a checked arm.
Legitimate patch overlap between distinct arm containers remains allowed.

JSON reports include `selection_manifests`, `manifests_required` and
`generation_replayed: false`. `checked` describes these manifest/input bindings;
it does not establish immutable payload identity, rerun the random draw, verify
all metadata claims or prove scientific validity. Payload contents can still
change behind the links. Legacy STRIPMATCH records without a bootstrap-manifest
snapshot retain only their recorded bootstrap path/IDs binding.

Append `--json` to either checker to print one JSON report. For example:

```sh
uv run python scripts/check_patch_selection.py \
  --reference /path/to/reference.json --bootstrap /path/to/new_bootstrap \
  --random /path/to/new_random --threshold 0.90 --require-manifests --json
uv run python scripts/check_patch_spatial_balance.py \
  --reference /path/to/reference.json --bootstrap /path/to/new_bootstrap \
  --random /path/to/new_stripmatch --full /path/to/full_dataset --require-manifests --json
```

Selection status is `PASS` or `FAIL`, scoped to nonempty positive-area patch
directories, reference membership, the bootstrap threshold and the existing
0.5 percentage-point area tolerance. Broken links, file entries, duplicate or
nonfinite reference records, and changed membership cannot pass. Empty sets
produce failure reports; undefined statistics are JSON `null` (text `n/a`).
Quartiles for fewer than three patches are undefined; larger sets retain the
existing exclusive quartile method. A passing input check does not establish
statistical power.

The spatial diagnostic returns `MEASURED` or `FAIL`. Successful measurement
leaves `balance_verdict: not_assessed` and winding calibration unverified; exit
0 means the input diagnostic completed. Missing or conflicting geometry fails
instead of silently reducing the population. With `--full`, every scored
reference patch must have matching geometry in that source. Unscored full-source
patches do not enter the reference-population comparison, nor its check that
different IDs name different directories.

The centre and cuts still derive from BOOTSTRAP | RANDOM, including when ALL is
shown. Global area gaps use the scored reference's total area; per-band shares
use each arm's own total area. The reported gap is computed from these inputs.
The outermost radial proxy band is not equated with particular scroll windings.
Repeated cuts in small or heavily weighted populations are preserved and
flagged, with zero-width bands, rather than inventing finer spatial resolution.
Point extents exactly on a cut retain the lower-band convention.

Both reports record the captured reference hash/size and hashes of arm IDs and
resolved link targets. Spatial reports add a geometry-source fingerprint. These
inputs are rechecked before returning a successful report. Patch payloads are
not read or hashed, and no immutable training/study lineage is established.
Keep inputs stable, and treat every nonzero exit as a failed command. Input
errors return `FAIL` and exit 1; CLI usage errors use exit 2. Text output remains
the default. Historical study measurements have not been rerun or restated.

## Inspect seeded draws without publishing

```sh
uv run python scripts/build_stripmatch_dataset.py \
  --full /path/to/full_dataset --reference /path/to/reference.json \
  --bootstrap /path/to/new_bootstrap --out /path/to/unused_output \
  --stability 10 --require-manifests
```

Stability mode accepts 2–1,000 draws and writes no dataset. It reports observed
share, satisfaction and overlap diagnostics, without asserting that distinct
seeds necessarily produce different subsets. A single draw is rejected because
there is no between-draw comparison.
