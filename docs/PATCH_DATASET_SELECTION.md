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
  --bootstrap /path/to/new_bootstrap --out /path/to/new_stripmatch --seed 0
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
  --random /path/to/new_random --threshold 0.90
uv run python scripts/check_patch_spatial_balance.py \
  --reference /path/to/reference.json --bootstrap /path/to/new_bootstrap \
  --random /path/to/new_stripmatch --full /path/to/full_dataset
```

The spatial checker reports diagnostics; follow the study's registered criteria
instead of inventing new acceptance thresholds from observed outcomes.

## Inspect seeded draws without publishing

```sh
uv run python scripts/build_stripmatch_dataset.py \
  --full /path/to/full_dataset --reference /path/to/reference.json \
  --bootstrap /path/to/new_bootstrap --out /path/to/unused_output \
  --stability 10
```

Stability mode accepts 2–1,000 draws and writes no dataset. It reports observed
share, satisfaction and overlap diagnostics, without asserting that distinct
seeds necessarily produce different subsets. A single draw is rejected because
there is no between-draw comparison.
