"""Finding 111: what the recipe's render and four ink models show on PHerc. 0841's published surfaces.

Usage:
    surface_control.py instrument OUT.json PUBLISHED_DIR SEGMENT [SEGMENT ...]
    surface_control.py sweep OUT.json --segment NAME MESH MAPS RENDER LABELS --depths LO HI
    surface_control.py confirm OUT.json --choice SWEEP.json --gate DIR \
        --segment NAME MESH MAPS RENDER LABELS [--segment ...]

The team's ink labels are drawn on the same surface, meshed on the 2.4 um scan. Its grid is the 9.366 um
mesh's grid 3.9 times finer, pixel centre on pixel centre (`instrument` measures that), so the labels are
carried onto our render by a plain resize. Everything is then compared on the lattice of 4 x 4 render
pixels that finding 110 used, over the cells the team marked as supervised, where every one of the 66
render layers has CT, and whose label is unambiguous.

The score of a map is the area under the ROC curve of the four-model ensemble (mean of per-model z-scores,
broad background taken off) against the label. `sweep` scores every depth and both sides on the
development segment and picks the best; `confirm` scores the held-out segments at that one depth and side,
with the map slid by 512 render pixels as the floor, and applies the registered table.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pherc343" / "mesh_step"))

import mesh_step_analysis as analysis  # noqa: E402
import transfer_maps  # noqa: E402

LABEL_LEVEL = "2"  # 9.612 um a pixel, the level nearest the render's 9.366 um
SUPERVISED_MIN = 0.99  # share of a cell's label pixels inside the supervision mask
INK_MIN = 0.5  # a cell is ink at or above this labelled share ...
BARE_MAX = 0.0  # ... bare at or below this one, and left out in between
SLIDE_CELLS = 128  # 512 render pixels: the floor
MIN_CELLS = 1000  # of each class, for a segment to be scored
P1_AUC = 0.60
P1_MARGIN = 0.05  # above the slid floor
P2_AUC = 0.75
INSTRUMENT_NORMAL_MAX = 1.0  # voxels: the two meshes are one surface
INSTRUMENT_LATERAL_MAX = (
    2.0  # voxels (half a lattice cell): the resize lines the labels up
)


def auc(score: np.ndarray, positive: np.ndarray) -> float | None:
    """Area under the ROC curve (the Mann-Whitney statistic, ties given their mean rank)."""
    from scipy.stats import rankdata

    n1 = int(positive.sum())
    n0 = int(positive.size - n1)
    if n1 == 0 or n0 == 0:
        return None
    ranks = rankdata(score)
    return float((ranks[positive].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def labels_on_lattice(
    labels: Path, canvas_hw: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray]:
    """(labelled-ink share, supervised share) of every lattice cell of a render of `canvas_hw` pixels."""
    import cv2
    import zarr

    out = []
    for name in ("inklabels", "supervision"):
        level = zarr.open_group(str(labels / f"{name}.zarr"), mode="r")[LABEL_LEVEL]
        binary = (np.asarray(level[:]) > 0).astype(np.float32)
        resized = cv2.resize(
            binary, (canvas_hw[1], canvas_hw[0]), interpolation=cv2.INTER_LINEAR
        )
        out.append(analysis.block_mean(resized))
    return out[0], out[1]


def cell_classes(
    ink_share: np.ndarray, supervised_share: np.ndarray, render_ok: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """(cells that are scored, which of them are ink)."""
    supervised = supervised_share >= SUPERVISED_MIN
    ink = ink_share >= INK_MIN
    bare = ink_share <= BARE_MAX
    return render_ok & supervised & (ink | bare), ink


def ensemble(maps: dict[str, np.ndarray], render_ok: np.ndarray) -> np.ndarray:
    return analysis.highpass(analysis.zscore_ensemble(maps, render_ok), render_ok)


def slid_floor(
    score: np.ndarray, render_ok: np.ndarray, scored: np.ndarray, ink: np.ndarray
) -> dict:
    """AUC of the map slid by SLIDE_CELLS in each direction, over the scored cells its slid copy covers."""
    out: dict = {}
    for label, (dr, dc) in {
        "down": (SLIDE_CELLS, 0),
        "up": (-SLIDE_CELLS, 0),
        "right": (0, SLIDE_CELLS),
        "left": (0, -SLIDE_CELLS),
    }.items():
        slid = np.roll(score, (dr, dc), axis=(0, 1))
        covered = np.roll(render_ok, (dr, dc), axis=(0, 1))
        if dr > 0:
            covered[:dr] = False
        elif dr < 0:
            covered[dr:] = False
        if dc > 0:
            covered[:, :dc] = False
        elif dc < 0:
            covered[:, dc:] = False
        both = scored & covered
        enough = min(int(ink[both].sum()), int((~ink[both]).sum())) >= MIN_CELLS
        out[label] = auc(slid[both], ink[both]) if enough else None
    values = [v for v in out.values() if v is not None]
    out["largest"] = max(values) if values else None
    return out


class Segment:
    def __init__(self, name: str, mesh: Path, maps: Path, render: Path, labels: Path):
        self.name, self.maps, self.render = name, maps, render
        xyz, valid = analysis.load_tifxyz(mesh)
        _, corners = analysis.lattice_points(xyz, valid)
        self.canvas = (
            xyz.shape[0] * analysis.PX_PER_NODE,
            xyz.shape[1] * analysis.PX_PER_NODE,
        )
        self.render_ok = corners & transfer_maps.render_valid(render, corners.shape)
        ink_share, supervised_share = labels_on_lattice(labels, self.canvas)
        self.scored, self.ink = cell_classes(
            ink_share, supervised_share, self.render_ok
        )
        self.supervised_cells = int((supervised_share >= SUPERVISED_MIN).sum())

    def counts(self) -> dict:
        return {
            "lattice": list(self.render_ok.shape),
            "render_cells": int(self.render_ok.sum()),
            "supervised_cells": self.supervised_cells,
            "scored_cells": int(self.scored.sum()),
            "ink_cells": int(self.ink[self.scored].sum()),
            "bare_cells": int((~self.ink[self.scored]).sum()),
        }

    def scorable(self) -> bool:
        c = self.counts()
        return min(c["ink_cells"], c["bare_cells"]) >= MIN_CELLS

    def score_map(self, depth: int, reading_side: bool) -> np.ndarray:
        name = self.render.name.removesuffix(".zarr")
        maps = {
            model: transfer_maps.read_map(
                transfer_maps.map_file(self.maps, name, model, reading_side, depth),
                model,
                self.canvas,
            )
            for model in analysis.MODELS
        }
        return ensemble(maps, self.render_ok)

    def auc(self, depth: int, reading_side: bool) -> float | None:
        score = self.score_map(depth, reading_side)
        return auc(score[self.scored], self.ink[self.scored])


def choose(table: list[dict]) -> dict | None:
    """The depth and side with the highest AUC; ties go to the depth nearest zero, then the `_reverse` side."""
    rows = [row for row in table if row["auc"] is not None]
    if not rows:
        return None
    best = max(rows, key=lambda r: (r["auc"], -abs(r["depth"]), r["side"] == "reverse"))
    return {"depth": best["depth"], "side": best["side"], "auc": best["auc"]}


def held_out_reading(segment: Segment, depth: int, side: str) -> dict:
    reading = side == "reverse"
    score = segment.score_map(depth, reading)
    value = auc(score[segment.scored], segment.ink[segment.scored])
    floor = slid_floor(score, segment.render_ok, segment.scored, segment.ink)
    other = segment.auc(depth, not reading)
    out = {
        **segment.counts(),
        "auc": _r(value),
        "slid_floor": {k: _r(v) for k, v in floor.items()},
        "other_side_auc": _r(other),
    }
    out["p1"] = p1_holds(out)
    out["p2"] = p2_holds(out)
    return out


def p1_holds(reading: dict) -> bool:
    value, floor = reading["auc"], reading["slid_floor"]["largest"]
    if value is None or floor is None:
        return False
    return value >= P1_AUC and value >= floor + P1_MARGIN


def p2_holds(reading: dict) -> bool:
    return reading["auc"] is not None and reading["auc"] >= P2_AUC


def verdict(gate: dict, readings: dict[str, dict] | None) -> dict:
    """The registered table. A step that failed or never ran decides first."""
    failed = sorted(name for name, step in gate.items() if step.get("exit") != 0)
    if failed or not gate or not readings:
        return {"verdict": "DOES_NOT_RUN", "failed_steps": failed}
    p1 = {name: bool(r["p1"]) for name, r in readings.items()}
    p2 = {name: bool(r["p2"]) for name, r in readings.items()}
    if all(p1.values()) and all(p2.values()):
        name = "LETTER_LEVEL_SIGNAL"
    elif all(p1.values()):
        name = "BLOB_LEVEL_SIGNAL"
    else:
        name = "NO_SIGNAL"
    return {"verdict": name, "p1": p1, "p2": p2}


def read_gate(directory: Path, names: list[str]) -> dict:
    """The exit record of the render and the ink step of every segment; a missing record is a failure."""
    out = {}
    for name in names:
        for step in ("render", "ink"):
            path = directory / f"{step}_{name}.json"
            out[f"{step}_{name}"] = (
                json.loads(path.read_text()) if path.is_file() else {"exit": None}
            )
    return out


def instrument(published: Path, segments: list[str]) -> dict:
    """Are the 9.366 um mesh and the labelled 2.4 um mesh the same surface, node centre on node centre?

    The 2.4 um mesh is carried into the 9.366 um scan with the published transform and read at
    (i + 0.5) * f - 0.5, the pixel-centre rule of a resize by f. The difference from the 9.366 um node is
    split along that node's normal and across it.
    """
    matrix = np.array(
        json.loads((published / "transform" / "transform.json").read_text())[
            "transformation_matrix"
        ]
    )
    out = {}
    for name in segments:
        stamp = name.split("-")[0]
        low, low_ok = analysis.load_tifxyz(
            published / name / "mesh" / f"{stamp}-on-20250821151531-9.366um.tifxyz"
        )
        high, high_ok = analysis.load_tifxyz(
            published / name / "mesh" / f"{stamp}-on-20260319124803-2.403um.tifxyz"
        )
        carried = high @ matrix[:, :3].T + matrix[:, 3]
        out[name] = mesh_agreement(low, low_ok, carried, high_ok)
        out[name]["grids"] = [list(low.shape[:2]), list(high.shape[:2])]
    out["ok"] = all(
        abs(v["normal_median"]) <= INSTRUMENT_NORMAL_MAX
        and v["lateral_median"] <= INSTRUMENT_LATERAL_MAX
        for k, v in out.items()
        if k != "ok"
    )
    return out


def mesh_agreement(
    low: np.ndarray, low_ok: np.ndarray, carried: np.ndarray, high_ok: np.ndarray
) -> dict:
    rows, cols = low.shape[:2]
    fy, fx = carried.shape[0] / rows, carried.shape[1] / cols
    gy = (np.arange(rows) + 0.5) * fy - 0.5
    gx = (np.arange(cols) + 0.5) * fx - 0.5
    y0 = np.clip(np.floor(gy).astype(int), 0, carried.shape[0] - 2)
    x0 = np.clip(np.floor(gx).astype(int), 0, carried.shape[1] - 2)
    wy = (gy - y0)[:, None, None]
    wx = (gx - x0)[None, :, None]
    at = (
        carried[y0][:, x0] * (1 - wy) * (1 - wx)
        + carried[y0 + 1][:, x0] * wy * (1 - wx)
        + carried[y0][:, x0 + 1] * (1 - wy) * wx
        + carried[y0 + 1][:, x0 + 1] * wy * wx
    )
    corners = (
        high_ok[y0][:, x0]
        & high_ok[y0 + 1][:, x0]
        & high_ok[y0][:, x0 + 1]
        & high_ok[y0 + 1][:, x0 + 1]
    )
    normals, normal_ok = analysis.grid_normals(low, low_ok)
    use = low_ok & normal_ok & corners
    diff = (at - low)[use]
    along = (diff * normals[use]).sum(axis=1)
    lateral = np.sqrt(np.maximum((diff**2).sum(axis=1) - along**2, 0.0))
    return {
        "nodes": int(use.sum()),
        "normal_median": _r(float(np.median(along))),
        "normal_p95_abs": _r(float(np.percentile(np.abs(along), 95))),
        "lateral_median": _r(float(np.median(lateral))),
        "lateral_p95": _r(float(np.percentile(lateral, 95))),
    }


def _r(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _segment(values: list[str]) -> Segment:
    name, mesh, maps, render, labels = values
    return Segment(name, Path(mesh), Path(maps), Path(render), Path(labels))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("instrument")
    p.add_argument("out")
    p.add_argument("published", type=Path)
    p.add_argument("segments", nargs="+")
    p = sub.add_parser("sweep")
    p.add_argument("out")
    p.add_argument("--segment", nargs=5, required=True)
    p.add_argument("--depths", nargs=2, type=int, required=True)
    p = sub.add_parser("confirm")
    p.add_argument("out")
    p.add_argument("--choice", required=True, type=Path)
    p.add_argument("--gate", required=True, type=Path)
    p.add_argument("--segment", nargs=5, action="append", required=True)
    args = parser.parse_args(argv)
    if Path(args.out).exists():
        raise SystemExit(f"{args.out} exists: this is measured once")

    if args.command == "instrument":
        result = instrument(args.published, args.segments)
    elif args.command == "sweep":
        segment = _segment(args.segment)
        if not segment.scorable():
            raise SystemExit(f"too few scored cells: {segment.counts()}")
        table = [
            {
                "depth": depth,
                "side": side,
                "auc": _r(segment.auc(depth, side == "reverse")),
            }
            for depth in range(args.depths[0], args.depths[1] + 1)
            for side in ("reverse", "forward")
        ]
        for row in table:
            print(row["depth"], row["side"], row["auc"])
        result = {
            "segment": segment.name,
            **segment.counts(),
            "table": table,
            "chosen": choose(table),
        }
    else:
        chosen = json.loads(args.choice.read_text())["chosen"]
        segments = [_segment(values) for values in args.segment]
        gate = read_gate(
            args.gate,
            [segment.render.name.removesuffix("_66.zarr") for segment in segments],
        )
        ran = all(step.get("exit") == 0 for step in gate.values())
        readings = None
        if ran and chosen:
            readings = {
                segment.name: held_out_reading(segment, chosen["depth"], chosen["side"])
                for segment in segments
            }
        result = {
            "chosen": chosen,
            "gate": gate,
            "held_out": readings,
            **verdict(gate, readings),
        }
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "table"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
