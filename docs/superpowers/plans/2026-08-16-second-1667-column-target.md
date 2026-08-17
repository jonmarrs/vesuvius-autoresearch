# Second 1667 Column Target Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a second ScrollGT column target carrying the same PHerc 1667 reading on a different flattening, so the family can test whether a column-level score survives a change of geometry.

**Architecture:** Both flattenings are surfaces over the same 3D scan, so column boxes transfer by a nearest-neighbour tifxyz bridge rather than by re-registering figure strips or reading ink. A derivation script in `vesuvius-autoresearch` produces the mapped columns and a gate report; the target then ships to `../scrollgt` in the existing 4-file column-target format.

**Tech Stack:** Python 3.10, numpy, scipy `cKDTree`, tifffile, Pillow, s3fs, pytest, `uv`. Two repos.

## Global Constraints

- **Interpreter:** always `uv run python ...`. Tests: `uv run python -m pytest -q <paths>`.
- **Run long work in the FOREGROUND.** No background jobs, monitors, or waiting tools — three implementers were lost to unresolved waits on the previous plan.
- **Commit trailer:** exactly `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`. **No `Claude-Session:` line** — the harness template adds one; this project forbids it.
- **`../scrollgt` is public: commit locally, NEVER push.** The user reviews before publication.
- **Never stage `villa`** (vendored upstream checkout).
- **No AI-authorship markers** in prose or metadata.
- Match surrounding prose style; ScrollGT uses em-dashes.
- Do not cite line numbers inside a file your own edit shifts; quote text instead.

**Measured facts, to be used verbatim:**
- Existing target: `../scrollgt/data/pherc1667_merged_columns/`, grid `2061 x 30097`, 22 columns, `line_pitch_range` `[85, 160]`.
- `columns.json` shape: `{"columns": [{col, gx0, gx1, cross_strip, text_band, transcription, measured_line_pitch}, ...], ...}`.
- Column target dir format: `meta.json`, `columns.json`, `valid_mask.png`, `README.md`.
- Loader: `load_column_target(target_dir) -> (meta, columns, valid)`; scorer: `score_columns(pred_path, target_dir, origin=(0,0))`; reads `meta["line_pitch_range"]` (default `[60, 220]`) and `meta["geometry"]["grid_shape"]`.
- Source flattening (existing): `PHerc1667/segments/20260612121456-w011_20260108140509268_merged_v4_flatboi_straightened_v4`, tifxyz `20260612121456-on-20251217075048-2.399um.tifxyz`.
- **Target flattening (new): `PHerc1667/segments/20260108140509-w011_20260108140509268_flatboi`, tifxyz `20260108140509-on-20251217075048-2.399um.tifxyz`** — same scan, same resolution.
- Columns 9 and 16 are flagged `cross_strip` in the merged target.
- **Pre-registered stop condition: fewer than 5 columns passing both gates → do not ship; write up the finding and leave the family at n=1.**

---

### Task 1: Column transfer by tifxyz bridge

**Files:**
- Create: `scripts/transfer_columns_to_flattening.py`
- Test: `tests/test_transfer_columns.py`

**Interfaces:**
- Produces:
  - `transfer_columns(src_xyz, dst_xyz, columns, max_residual=None) -> (list[dict], dict)` — mapped columns plus a stats dict. Each mapped column is `{col, gx0, gx1, text_band, cross_strip, n_mapped, median_residual, fully_inside}`.
  - `bridge_points(src_xyz, dst_xyz, pts_yx) -> (np.ndarray, np.ndarray)` returning destination `(row, col)` integer coordinates and per-point residuals.
- Task 2 consumes both.

- [ ] **Step 1: Write the failing test**

Create `tests/test_transfer_columns.py`:

```python
"""Column boxes must transfer by 3D correspondence, not by re-reading ink.

The column metric asks whether a prediction carries more signal inside text columns than in
gutters. If the boxes were derived from an ink-detection output, the target would measure
agreement with that output -- the agreement-with-teacher circularity this project already
corrected. So columns move between flattenings through the shared 3D scan, and their
identities stay anchored to the papyrological reading.
"""

import pathlib
import sys

import numpy as np
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from transfer_columns_to_flattening import bridge_points, transfer_columns  # noqa: E402


def _grid(h, w, x0=0.0, y0=0.0):
    """A synthetic flattening: grid cell (r, c) holds a known 3D point."""
    rr, cc = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    xs = (cc + x0).astype(np.float32)
    ys = (rr + y0).astype(np.float32)
    zs = np.zeros_like(xs)
    return np.stack([xs, ys, zs], axis=-1)


def test_identity_flattening_maps_every_point_to_itself():
    src = _grid(20, 30)
    pts = np.array([[3, 4], [10, 25], [19, 0]])
    dst_yx, resid = bridge_points(src, src, pts)
    assert np.array_equal(dst_yx, pts)
    assert np.allclose(resid, 0.0)


def test_a_shifted_flattening_recovers_the_shift():
    """The destination grid holds the same 3D points offset by 5 columns."""
    src = _grid(20, 30)
    dst = _grid(20, 30, x0=-5.0)
    pts = np.array([[3, 10], [7, 20]])
    dst_yx, resid = bridge_points(src, dst, pts)
    assert np.array_equal(dst_yx[:, 1], pts[:, 1] + 5)
    assert np.allclose(resid, 0.0)


def test_transfer_reports_columns_that_fall_outside_the_destination():
    """A destination covering only part of the source must not silently clip a column."""
    src = _grid(40, 100)
    dst = _grid(40, 50)  # covers source x in [0, 50) only
    columns = [
        {"col": 1, "gx0": 5, "gx1": 20, "text_band": [5, 35], "cross_strip": False},
        {"col": 2, "gx0": 70, "gx1": 90, "text_band": [5, 35], "cross_strip": False},
    ]
    mapped, stats = transfer_columns(src, dst, columns)
    inside = {m["col"]: m["fully_inside"] for m in mapped}
    assert inside[1] is True
    assert inside[2] is False
    assert stats["n_fully_inside"] == 1


def test_cross_strip_flag_is_carried_not_dropped():
    src = _grid(40, 100)
    columns = [
        {"col": 9, "gx0": 5, "gx1": 20, "text_band": [5, 35], "cross_strip": True},
    ]
    mapped, _ = transfer_columns(src, src, columns)
    assert mapped[0]["cross_strip"] is True


def test_invalid_source_cells_are_excluded_rather_than_bridged():
    """tifxyz marks invalid cells; bridging them would invent correspondence."""
    src = _grid(20, 30)
    src[5:10, :, :] = -1.0  # the released invalid marker
    columns = [{"col": 1, "gx0": 2, "gx1": 25, "text_band": [0, 19], "cross_strip": False}]
    mapped, _ = transfer_columns(src, src, columns)
    assert mapped[0]["n_mapped"] > 0
    assert mapped[0]["n_mapped"] < 20 * 24  # the invalid band did not contribute


def test_a_column_with_no_valid_cells_is_reported_not_crashed():
    src = _grid(20, 30)
    src[:, :, :] = -1.0
    columns = [{"col": 1, "gx0": 2, "gx1": 25, "text_band": [0, 19], "cross_strip": False}]
    mapped, stats = transfer_columns(src, src, columns)
    assert mapped[0]["n_mapped"] == 0
    assert mapped[0]["fully_inside"] is False
    assert stats["n_fully_inside"] == 0
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run python -m pytest -q tests/test_transfer_columns.py`
Expected: FAIL at collection — `ModuleNotFoundError: No module named 'transfer_columns_to_flattening'`

- [ ] **Step 3: Write the script**

Create `scripts/transfer_columns_to_flattening.py`:

```python
#!/usr/bin/env python3
"""Move column boxes from one flattening of a scroll to another, via the shared 3D scan.

Motivation (2026-08-16): ScrollGT's column family has one target. A genuinely independent
second reading does not exist in published artifacts -- PHerc 0172's reading image is
unannotated disconnected patches, and Scroll 1's would require deriving boxes from ink,
which would make a column-vs-gutter metric measure agreement with an ink-detection output.
What IS available is the same 1667 reading on a different flattening of the same winding,
which tests whether a column-level score survives a change of geometry.

Method: both flattenings store a 3D point per grid cell (tifxyz). For each source cell
inside a column, look up its 3D point, find the nearest point in the destination
flattening, and take that cell's coordinates. A column's destination extent is the envelope
of its mapped cells.

What this deliberately does NOT do:
  * it does not read ink, so column identities stay anchored to the papyrological reading;
  * it does not clip a column silently -- a column whose envelope leaves the destination
    grid is reported `fully_inside: False` and excluded upstream;
  * it does not bridge invalid cells. tifxyz marks them (-1, -1, -1); treating those as
    real points would invent correspondence where the surface has none.

Usage:
    uv run python scripts/transfer_columns_to_flattening.py --help
"""

import argparse
import json
import pathlib
import sys

import numpy as np
from scipy.spatial import cKDTree

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _valid_mask(xyz):
    """Cells with a real 3D point. tifxyz marks invalid as (-1,-1,-1); zeros are also unset."""
    a = np.asarray(xyz, np.float32)
    finite = np.isfinite(a).all(axis=-1)
    not_neg1 = ~(np.abs(a + 1.0) < 1e-6).all(axis=-1)
    not_zero = ~(np.abs(a) < 1e-9).all(axis=-1)
    return finite & not_neg1 & not_zero


def bridge_points(src_xyz, dst_xyz, pts_yx):
    """Map source grid cells to destination grid cells through 3D.

    Returns (dst_yx int array, residual float array). Points whose source cell is invalid
    must be filtered by the caller; this function assumes the given cells are valid.
    """
    src = np.asarray(src_xyz, np.float32)
    dst = np.asarray(dst_xyz, np.float32)
    pts_yx = np.asarray(pts_yx, int)

    dst_valid = _valid_mask(dst)
    dst_idx = np.argwhere(dst_valid)
    if len(dst_idx) == 0:
        raise ValueError("destination flattening has no valid cells")
    tree = cKDTree(dst[dst_valid])

    query = src[pts_yx[:, 0], pts_yx[:, 1]]
    resid, nn = tree.query(query, k=1)
    return dst_idx[nn], np.asarray(resid, float)


def transfer_columns(src_xyz, dst_xyz, columns, max_residual=None):
    """Map each column's box into the destination flattening.

    `max_residual` (in scan units) drops individual point correspondences that are outliers;
    None keeps all. Returns (mapped columns, stats).
    """
    src = np.asarray(src_xyz, np.float32)
    dst = np.asarray(dst_xyz, np.float32)
    src_valid = _valid_mask(src)
    dh, dw = dst.shape[:2]

    mapped = []
    for c in columns:
        y0, y1 = c["text_band"]
        x0, x1 = c["gx0"], c["gx1"]
        sub = np.zeros(src_valid.shape, bool)
        sub[max(0, y0) : y1 + 1, max(0, x0) : x1 + 1] = True
        cells = np.argwhere(sub & src_valid)

        entry = {
            "col": c["col"],
            "cross_strip": bool(c.get("cross_strip", False)),
            "n_mapped": 0,
            "median_residual": None,
            "fully_inside": False,
            "gx0": None,
            "gx1": None,
            "text_band": None,
        }
        if len(cells) == 0:
            mapped.append(entry)
            continue

        dst_yx, resid = bridge_points(src, dst, cells)
        if max_residual is not None:
            keep = resid <= max_residual
            dst_yx, resid = dst_yx[keep], resid[keep]
        if len(dst_yx) == 0:
            mapped.append(entry)
            continue

        entry["n_mapped"] = int(len(dst_yx))
        entry["median_residual"] = float(np.median(resid))
        entry["gx0"] = int(dst_yx[:, 1].min())
        entry["gx1"] = int(dst_yx[:, 1].max())
        entry["text_band"] = [int(dst_yx[:, 0].min()), int(dst_yx[:, 0].max())]
        entry["fully_inside"] = bool(
            entry["gx0"] >= 0 and entry["gx1"] < dw
            and entry["text_band"][0] >= 0 and entry["text_band"][1] < dh
            # A column pinned to the destination edge is a clipped column, not a mapped one.
            and entry["gx0"] > 0 and entry["gx1"] < dw - 1
        )
        mapped.append(entry)

    stats = {
        "n_columns": len(columns),
        "n_fully_inside": int(sum(1 for m in mapped if m["fully_inside"])),
        "dst_grid_shape": [int(dh), int(dw)],
    }
    return mapped, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src-tifxyz", required=True, help="source flattening tifxyz dir")
    ap.add_argument("--dst-tifxyz", required=True, help="destination flattening tifxyz dir")
    ap.add_argument("--columns-json", required=True, help="source columns.json")
    ap.add_argument("--out-json", required=True, help="where to write mapped columns")
    ap.add_argument("--max-residual", type=float, default=None)
    args = ap.parse_args()

    sys.path.insert(0, str(REPO_ROOT))
    from repro.sota_data.register import read_tifxyz

    src = read_tifxyz(args.src_tifxyz)
    dst = read_tifxyz(args.dst_tifxyz)
    with open(args.columns_json) as f:
        columns = json.load(f)["columns"]

    mapped, stats = transfer_columns(src, dst, columns, max_residual=args.max_residual)
    out = {"columns": mapped, "stats": stats}
    pathlib.Path(args.out_json).write_text(json.dumps(out, indent=2) + "\n")

    print(f"{'col':>4} {'n_mapped':>9} {'resid':>8} {'gx0':>7} {'gx1':>7} inside")
    for m in mapped:
        r = "-" if m["median_residual"] is None else f"{m['median_residual']:.2f}"
        print(f"{m['col']:>4} {m['n_mapped']:>9} {r:>8} {str(m['gx0']):>7} "
              f"{str(m['gx1']):>7} {m['fully_inside']}")
    print(f"\nfully inside: {stats['n_fully_inside']} / {stats['n_columns']}")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run python -m pytest -q tests/test_transfer_columns.py`
Expected: PASS (6 tests)

- [ ] **Step 5: Register the script with the path-discipline test**

`tests/test_probe_paths.py` enforces that scripts anchor paths to `REPO_ROOT` from `__file__` rather than the process cwd. Add the new script to its `PROBES` list, keeping the list alphabetical.

Run: `uv run python -m pytest -q tests/test_probe_paths.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/transfer_columns_to_flattening.py tests/test_transfer_columns.py tests/test_probe_paths.py
git commit -m "$(cat <<'EOF'
feat: transfer column boxes between flattenings via the shared 3D scan

ScrollGT's column family is n=1 and no independent second reading exists in
published artifacts. What does exist is the same 1667 reading on a different
flattening of the same winding, which answers a question the single target
cannot: does a column-level score survive a change of geometry.

Columns move through the 3D scan both flattenings are surfaces over, not by
re-registering figure strips and not by reading ink -- boxes derived from an
ink-detection output would make a column-vs-gutter metric measure agreement
with that output, which is the circularity this project already corrected.

Invalid tifxyz cells are excluded rather than bridged, and a column whose
envelope reaches the destination edge is reported not-fully-inside rather than
silently clipped.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Run the transfer and apply the gates

**Files:**
- Create: `scripts/build_w011_column_target.py`
- Create: `reports/detector/w011_column_transfer.md`
- Create: `reports/detector/w011_column_transfer.json`

**Interfaces:**
- Consumes: `transfer_columns`, `bridge_points` from Task 1.
- Produces: the gate report Task 3 reads to decide whether to ship.

**This task fetches data and may take several minutes. Run it in the FOREGROUND.**

- [ ] **Step 1: Fetch both tifxyz directories**

Both live in the open bucket under `vesuvius-challenge-open-data/PHerc1667/segments/`:

- source: `20260612121456-w011_20260108140509268_merged_v4_flatboi_straightened_v4/mesh/20260612121456-on-20251217075048-2.399um.tifxyz`
- destination: `20260108140509-w011_20260108140509268_flatboi/mesh/20260108140509-on-20251217075048-2.399um.tifxyz`

Cache them under `local_data/1667_flattenings/`. Reuse `repro.sota_data.distill_run._fs()` for the anonymous S3 filesystem rather than constructing a new client, and `fs.get(..., recursive=True)` since tifxyz is a directory of `x.tif`/`y.tif`/`z.tif` plus `meta.json`.

Report both grid shapes. **If the destination grid is larger than the source in both axes, stop and report** — that would mean the two are not the flattenings this plan assumes.

- [ ] **Step 2: Run the transfer**

```bash
uv run python scripts/transfer_columns_to_flattening.py \
  --src-tifxyz local_data/1667_flattenings/merged_v4.tifxyz \
  --dst-tifxyz local_data/1667_flattenings/w011_flatboi.tifxyz \
  --columns-json ../scrollgt/data/pherc1667_merged_columns/columns.json \
  --out-json reports/detector/w011_column_transfer.json
```

Record how many of the 22 columns come back `fully_inside`.

**`fully_inside` is necessary but NOT sufficient — apply a coverage floor too.** Task 1's
review established that `max_residual` filtering has no minimum-coverage floor: a column
whose correspondences are mostly outliers can end up with `n_mapped` as low as 1 and still
satisfy `fully_inside`, because a single well-placed point trivially clears the bounds test.
A one-point column is not a column.

For each column, compute `coverage = n_mapped / n_source_cells`, where `n_source_cells` is
the count of valid source cells in that column's `(gx0..gx1, text_band)` box — the same count
`transfer_columns` starts from. **Require `coverage >= 0.5` and `n_mapped >= 1000`** to
consider a column mapped at all. Both figures go in the report per column, so a column
excluded for thin coverage is visible rather than absent.

**Also distinguish edge-exclusion from clipping.** `fully_inside` is a strict-interior test
(`gx0 > 0`, `gx1 < dw-1`), which cannot tell a genuinely clipped column from a legitimate one
whose true nearest destination cell happens to be column 0 or `dw-1`. It fails safe — toward
excluding — but a wrongly excluded column reduces the count against the stop condition. Report
any column excluded *solely* because its envelope touches a grid edge under its own heading,
so that case is visible rather than folded into "clipped".

- [ ] **Step 3: Apply the teacher-free gate (line periodicity)**

For each fully-inside column, render or fetch the destination segment's surface and measure
line periodicity inside the mapped box using
`repro.sota_data.register.label_line_periodicity`, with the merged target's calibrated band
`[85, 160]`. A mapped column with no periodic line structure is misplaced whatever its
residual says — this is the gate, because it does not depend on any model.

Write the per-column periodicity into `reports/detector/w011_column_transfer.json`.

- [ ] **Step 4: Apply the supporting check (column-vs-gutter enrichment)**

The destination segment publishes its own `ink-detection` prediction. Compute, per mapped
column, the ratio of mean predicted-ink inside the column to the mean in the adjacent
gutters. Record it as a **supporting** figure and label it teacher-dependent in both the JSON
and the report: this project has twice mistaken a teacher-dependent diagnostic for a
teacher-free one, and a weak or absent prediction on this segment would make the number
uninformative rather than damning.

- [ ] **Step 5: Write the report**

Create `reports/detector/w011_column_transfer.md` covering: the method and why it is not
ink-derived; the two flattenings and the shared scan/resolution; per-column mapped extents,
residuals, periodicity and enrichment; how many columns passed; and — stated plainly — that
this pair tests robustness to flattening and **not** independence of reading.

- [ ] **Step 6: Evaluate the pre-registered stop condition**

A column counts toward the floor only if it clears **all** of: `fully_inside`,
`coverage >= 0.5`, `n_mapped >= 1000`, and the teacher-free periodicity gate. The
teacher-dependent enrichment figure is recorded but does not gate.

**If fewer than 5 columns pass, STOP.** Do not build a target. Finish the report
with the finding, commit it, and report BLOCKED to the coordinator — the family stays at
n=1 and that is a legitimate outcome, not a failure. The merged target records ~±0.08
statistical granularity at n=18 text columns vs 17 gutters, so a much smaller n publishes
noise.

- [ ] **Step 7: Commit the report**

```bash
git add scripts/build_w011_column_target.py reports/detector/w011_column_transfer.md reports/detector/w011_column_transfer.json
git commit -m "$(cat <<'EOF'
report: transfer the 1667 reading onto the raw w011 flattening

Both flattenings are surfaces over the same scan at the same resolution
(20251217075048, 2.399um), so the pair isolates flattening exactly. Records
per-column mapped extents, bridge residuals, teacher-free line periodicity and
the teacher-dependent column-vs-gutter enrichment, kept explicitly separate.

States plainly that this measures robustness to flattening and not
independence of reading -- both targets rest on the same papyrological
consensus.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Ship the target to ScrollGT

**Files:**
- Create: `../scrollgt/data/pherc1667_w011_flatboi_columns/{meta.json,columns.json,valid_mask.png,README.md}`
- Create: `../scrollgt/tests/test_column_target_pair.py`

**Interfaces:**
- Consumes: `reports/detector/w011_column_transfer.json` from Task 2.

**Only run this task if Task 2 cleared the stop condition.**

- [ ] **Step 1: Write the failing test**

Create `../scrollgt/tests/test_column_target_pair.py`:

```python
"""The column family is now a pair, and the pair must not overclaim.

Both targets carry the same PHerc 1667 reading on different flattenings. That tests whether
a column-level score survives a change of geometry. It does NOT provide an independent
reading -- a model that mislocates columns for reasons intrinsic to the reading mislocates
them on both. An n=2 count implies independence unless the target says otherwise, so the
disclosure is pinned here rather than left to prose that a later edit can drop.
"""

import json
import pathlib

import pytest

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
MERGED = DATA / "pherc1667_merged_columns"
W011 = DATA / "pherc1667_w011_flatboi_columns"


def test_both_column_targets_exist():
    assert MERGED.is_dir() and W011.is_dir()


def test_the_pair_declares_it_is_not_an_independent_reading():
    meta = json.loads((W011 / "meta.json").read_text())
    text = json.dumps(meta).lower()
    assert "not an independent reading" in text
    assert meta["pair_with"] == "pherc1667_merged_columns"
    assert meta["shares_reading_with"] == "pherc1667_merged_columns"


def test_the_two_targets_share_a_scan_but_not_a_flattening():
    a = json.loads((MERGED / "meta.json").read_text())
    b = json.loads((W011 / "meta.json").read_text())
    assert a["geometry"]["tifxyz"] != b["geometry"]["tifxyz"]
    assert "20251217075048" in a["geometry"]["tifxyz"]
    assert "20251217075048" in b["geometry"]["tifxyz"]


def test_every_shipped_column_lies_inside_the_declared_grid():
    meta = json.loads((W011 / "meta.json").read_text())
    h, w = meta["geometry"]["grid_shape"]
    cols = json.loads((W011 / "columns.json").read_text())["columns"]
    assert cols, "a column target with no columns is not a target"
    for c in cols:
        assert 0 < c["gx0"] < c["gx1"] < w - 1, f"col {c['col']} touches the grid edge"
        y0, y1 = c["text_band"]
        assert 0 <= y0 < y1 < h


def test_excluded_columns_are_enumerated_with_reasons():
    meta = json.loads((W011 / "meta.json").read_text())
    excluded = meta["coverage"]["excluded_columns"]
    shipped = {c["col"] for c in json.loads((W011 / "columns.json").read_text())["columns"]}
    assert set(excluded) | shipped == set(range(1, 23)), "every source column is accounted for"
    for col, reason in excluded.items():
        assert reason.strip(), f"column {col} excluded without a reason"


def test_the_target_meets_the_preregistered_minimum():
    cols = json.loads((W011 / "columns.json").read_text())["columns"]
    assert len(cols) >= 5, "below the pre-registered floor; this target should not have shipped"


def test_it_scores_with_no_network_and_no_gpu():
    import numpy as np

    from scrollgt.columns import load_column_target

    meta, cols, valid = load_column_target(str(W011))
    assert valid is not None and valid.shape == tuple(meta["geometry"]["grid_shape"])
    assert len(cols) == len(json.loads((W011 / "columns.json").read_text())["columns"])
    assert np.asarray(valid).dtype == bool
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd ../scrollgt && uv run python -m pytest -q tests/test_column_target_pair.py`
Expected: FAIL — the target directory does not exist yet

- [ ] **Step 3: Build the target directory**

Write the four files from `reports/detector/w011_column_transfer.json`:

- `columns.json` — `{"columns": [...], "coordinate_frame": ..., "derivation": ..., "uncertainty": ..., "transcription_provenance": ..., "line_pitch_note": ...}`, mirroring the merged target's structure. Only fully-inside, gate-passing columns. Carry `cross_strip` through.
- `valid_mask.png` — the destination flattening's valid mask, same convention as the merged target (grayscale, >127 is valid).
- `meta.json` — mirroring the merged target's fields, plus:
  - `pair_with` and `shares_reading_with`: `"pherc1667_merged_columns"`
  - `coverage.excluded_columns`: `{column number: reason}` for every source column not shipped
  - an honesty note containing the exact phrase **`not an independent reading`**, explaining that both targets rest on the same eight-papyrologist consensus and that the pair measures robustness to flattening
  - `line_pitch_range` measured on this flattening, not copied from the merged target — a different flattening can have a different pitch, and copying it would be an unchecked assumption
  - the same CC BY-NC licence note the merged target carries, since the column coordinates derive from the same publication
- `README.md` — what the target is, how it was derived, and the same non-independence statement.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ../scrollgt && uv run python -m pytest -q tests/test_column_target_pair.py`
Expected: PASS

- [ ] **Step 5: Run the full ScrollGT suite in the foreground**

Run: `cd ../scrollgt && uv run python -m pytest -q`
Expected: PASS. Takes several minutes; wait for it. A failure here means an existing test asserts something about the column family that the new target breaks — read it before adjusting anything.

- [ ] **Step 6: Commit (do not push)**

```bash
cd ../scrollgt
git add data/pherc1667_w011_flatboi_columns tests/test_column_target_pair.py
git commit -m "$(cat <<'EOF'
data(columns): the 1667 reading on a second flattening

The column family was n=1. No independent second reading exists in published
artifacts, so this ships the same reading on the raw w011 flatboi flattening
instead of the merged and straightened one -- same scan, same resolution, so
the pair isolates flattening exactly and answers whether a column-level score
survives a change of geometry.

It is NOT an independent reading, and says so in its own metadata: both
targets rest on the same eight-papyrologist consensus. A test pins that
disclosure so a later edit cannot drop it and leave an n=2 count implying
something false.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git status -sb | head -1
```

---

### Task 4: Document the pair and the capped axis

**Files:**
- Modify: `../scrollgt/README.md`
- Modify: `../scrollgt/baselines/BASELINES.md`

- [ ] **Step 1: Update the column-family disclosure in README**

The README currently discloses that the column family has exactly one target. Replace that
with the accurate picture: two targets, same reading, different flattenings — what the pair
measures and what it does not. Keep the existing tone: a limitation stated plainly, not a
complaint about upstream data.

State the capped axis too, since this investigation established it: an independent second
reading is not available in published artifacts, because PHerc 0172's reading image is
unannotated disconnected patches and Scroll 1's would require deriving boxes from ink, which
would make a column-vs-gutter metric measure agreement with an ink-detection output.

- [ ] **Step 2: Add the new target to BASELINES**

Give the new target its own section mirroring the merged target's: geometry, registration
method, how many columns shipped and which were excluded and why, the floors, and the
non-independence statement. Do not present the two targets' scores as independent
corroboration anywhere.

- [ ] **Step 3: Verify the docs against the shipped data**

```bash
cd ../scrollgt && uv run python -c "
import json, pathlib
for d in sorted(pathlib.Path('data').glob('*columns*')):
    m = json.loads((d/'meta.json').read_text())
    c = json.loads((d/'columns.json').read_text())['columns']
    print(f\"{d.name:38s} cols={len(c):3d} grid={m['geometry']['grid_shape']}\")
"
grep -c "exactly one column target\|only column target" README.md
```

Expected: two targets listed with their column counts; `0` for the now-stale single-target
phrasing.

- [ ] **Step 4: Run the suite in the foreground**

Run: `cd ../scrollgt && uv run python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit (do not push)**

```bash
cd ../scrollgt
git add README.md baselines/BASELINES.md
git commit -m "$(cat <<'EOF'
docs(columns): the family is a pair, and the independent axis is capped

Replaces the single-target disclosure with what the family actually is: two
targets carrying one reading on two flattenings, measuring robustness to
geometry rather than independence.

Also records why the independent axis is capped rather than merely unfinished.
PHerc 0172's published reading image is five disconnected unannotated patches,
and Scroll 1's is unannotated too, so boxes could only come from ink -- which
would make a column-vs-gutter metric measure agreement with an ink-detection
output. Checked, not assumed.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage:**

| Spec item | Task |
|---|---|
| Column transfer by tifxyz bridge, not figure strips or ink | Task 1 |
| Invalid cells excluded rather than bridged | Task 1, Step 3 + test |
| Columns not silently clipped; `fully_inside` reported | Task 1 + tests |
| `cross_strip` flags carried through | Task 1 test; Task 3 Step 3 |
| Teacher-free gate: line periodicity | Task 2, Step 3 |
| Supporting check: column-vs-gutter enrichment, labelled teacher-dependent | Task 2, Step 4 |
| Pre-registered stop condition (<5 columns) | Task 2, Step 6; pinned by a test in Task 3 |
| Excluded columns enumerated with reasons | Task 3, Step 3 + test |
| Non-independence stated in meta and pinned by a test | Task 3, Steps 1 and 3 |
| `line_pitch_range` measured, not copied | Task 3, Step 3 |
| Visual inspection before shipping | Task 2, Step 5 (report includes per-column extents); Task 3 Step 3 builds `valid_mask.png` |
| Scores with no network/GPU | Task 3, Step 1 test + Step 5 |
| Docs state what the pair does and does not buy | Task 4 |
| Capped independent axis recorded | Task 4, Step 1 |
| Non-goal: no new metric | No task touches `score_columns` |
| Non-goal: merged target not re-registered | No task writes to `pherc1667_merged_columns` |

**Placeholder scan:** none. Task 2's steps describe measurements against real fetched data rather than pasting expected numbers, because the numbers are the deliverable and pre-writing them would invite fitting the report to the plan.

**Type consistency:** `transfer_columns` and `bridge_points` signatures match between Task 1's tests, the script, and Task 2's invocation. Mapped-column keys (`col`, `gx0`, `gx1`, `text_band`, `cross_strip`, `n_mapped`, `median_residual`, `fully_inside`) are identical across Task 1's implementation, Task 2's report and Task 3's target build. `meta["geometry"]["grid_shape"]` and `meta["line_pitch_range"]` match what `scrollgt.columns.score_columns` reads.

**One risk carried deliberately:** Task 2 can legitimately end in BLOCKED via the stop condition, leaving Tasks 3 and 4 unrun. That is a designed outcome, not a failure — Task 1 is still independently valuable, since the transfer tool and its tests stand on their own.
