"""Finding 110: do the windings fitted here trace the sheets of the published PHerc. 343 windings, and does the
ink on them agree with the ink on the published ones?

Registered in docs/preregistration/2026-11-10_first_letters_343_mesh_step.md. Five subcommands:

    mesh_step_analysis.py distance A.tifxyz B.tifxyz [OUT.json]
    mesh_step_analysis.py select OUT.json --published NAME=DIR [NAME=DIR ...] --candidates DIR [DIR ...]
    mesh_step_analysis.py gate OUT.json --dir GATE_DIR --fit-config recipe|reduced --windings [W ...]
    mesh_step_analysis.py orientation FINAL.json WINDING
    mesh_step_analysis.py verdict GATE.json FINAL.json AGREEMENT.json OUT.json

`distance` is the measurement behind the control (published w047 against published w048) and behind P1.
`select` scores every candidate winding against each published winding and picks one per published winding
by geometry alone. `gate` gathers the exit codes the run scripts wrote, one file per step and winding,
into the record `verdict` reads. `orientation` prints whether a final winding's normals point with (+) or
against (-) the published ones, which decides whether its render is flipped. `verdict` applies the registered decision table. The ink comparison (P3) is built from
the functions below by transfer_maps.py, which holds the file reading.

A tifxyz surface is a folder of x.tif, y.tif, z.tif: a grid of scroll positions in voxels, one node every
20 voxels, with -1 marking nodes that do not exist.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

LATERAL_MAX = (
    30.0  # voxels; a node whose nearest partner is further off sideways is uncovered
)
WITHIN = 2.0  # voxels along the normal that count as the same sheet
P1_FRACTION = 0.50  # share of the published nodes that must be within WITHIN
P1_MEDIAN = 3.0  # voxels
ELIGIBLE_COVERAGE = (
    0.50  # a candidate covering less of the published winding cannot be chosen
)
PX_PER_NODE = 20  # render pixels per grid node (tifxyz scale 0.05)
LATTICE = 4  # render pixels per lattice cell of the ink comparison
ACCEPT = 4.0  # voxels between a published lattice point and the point of ours it takes its ink from
SHIFT_CELLS = 16  # 64 render pixels: the slid control
HIGHPASS_CELLS = (
    16.0  # sigma of the background taken off each ensemble before it is compared
)
P3_R = 0.50
P3_RATIO = 2.0  # r must be at least this many times each control
P3_COVERAGE = (
    0.50  # share of the letter-box cells that must have received ink from our windings
)
GATE_STEPS = ("distance_field", "fit", "snap", "flatten", "render", "ink")
FIT_CONFIGS = ("recipe", "reduced")
MODELS = ("dnative", "hecate", "hybrid_3d2d-seed42", "hybrid_3d2d-seed43")


def load_tifxyz(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Nodes as (rows, columns, 3) in x, y, z order and the mask of nodes that exist."""
    import tifffile

    xyz = np.stack(
        [tifffile.imread(f"{path}/{c}.tif").astype(np.float64) for c in "xyz"], -1
    )
    return xyz, np.asarray(np.isfinite(xyz).all(-1) & (xyz > -0.5).all(-1))


def grid_normals(xyz: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unit normal at each node from central differences: (step along columns) x (step along rows)."""
    p = xyz.copy()
    p[~valid] = np.nan
    du = np.full_like(p, np.nan)
    dv = np.full_like(p, np.nan)
    du[:, 1:-1] = p[:, 2:] - p[:, :-2]
    dv[1:-1, :] = p[2:, :] - p[:-2, :]
    n = np.cross(du, dv)
    with np.errstate(invalid="ignore", divide="ignore"):
        n = n / np.linalg.norm(n, axis=-1, keepdims=True)
    return n, np.isfinite(n).all(-1)


def surface_distance(
    a: np.ndarray, a_valid: np.ndarray, b: np.ndarray, b_valid: np.ndarray
) -> dict:
    """Distance from the nodes of A to the surface B, along B's normal.

    For each node of A: the nearest node of B, then the offset projected on B's normal there. The
    projection removes the sideways offset between two samplings of one sheet (up to half a grid step).
    A node of A whose nearest node of B is more than LATERAL_MAX away sideways is uncovered. Shares are
    of ALL nodes of A, so an uncovered node counts as not within; the quantiles are over covered nodes.
    """
    n, n_ok = grid_normals(b, b_valid)
    keep = b_valid & n_ok
    total = int(a_valid.sum())
    if total == 0:
        raise ValueError("surface A has no nodes")
    if int(keep.sum()) == 0:
        return {
            "a_nodes": total,
            "b_nodes": 0,
            "covered_fraction": 0.0,
            "median": None,
            "quantiles": None,
            "fraction_within": {str(t): 0.0 for t in (1, 2, 3, 5)},
            "signed_median": None,
            "normal_cosine_median": None,
        }
    points = a[a_valid]
    b_points, b_normals = b[keep], n[keep]
    _, index = cKDTree(b_points).query(points, k=1)
    offset = points - b_points[index]
    along = np.einsum("ij,ij->i", offset, b_normals[index])
    a_normals = grid_normals(a, a_valid)[0][a_valid]
    cosine = np.einsum("ij,ij->i", a_normals, b_normals[index])
    lateral = np.sqrt(np.maximum((offset**2).sum(1) - along**2, 0.0))
    covered = lateral <= LATERAL_MAX
    d = np.abs(along[covered])
    quantiles = (
        {
            k: round(float(v), 2)
            for k, v in zip(
                ("p5", "p25", "p50", "p75", "p95"),
                np.percentile(d, [5, 25, 50, 75, 95]),
                strict=True,
            )
        }
        if d.size
        else None
    )
    return {
        "a_nodes": total,
        "b_nodes": int(keep.sum()),
        "covered_fraction": round(float(covered.mean()), 4),
        "median": quantiles["p50"] if quantiles else None,
        "quantiles": quantiles,
        "fraction_within": {
            str(t): round(float((d <= t).sum()) / total, 4) for t in (1, 2, 3, 5)
        },
        "signed_median": round(float(np.median(along[covered])), 2) if d.size else None,
        "normal_cosine_median": _median_or_none(cosine[covered]),
    }


def _median_or_none(values: np.ndarray) -> float | None:
    values = values[np.isfinite(values)]
    return round(float(np.median(values)), 4) if values.size else None


def orientation(final: dict, winding: str) -> float:
    """Median cosine between the normals of final winding `winding` and of the published windings it lies
    along, from a `select` record. Raises unless every published winding it covers gives the same sign: a
    render is flipped as a whole or not at all."""
    values = [
        entry["scores"][winding]["normal_cosine_median"]
        for entry in final["published"].values()
        if winding in entry["scores"]
    ]
    values = [v for v in values if v is not None]
    if any(v == 0 for v in values) or len({v > 0 for v in values}) != 1:
        raise ValueError(f"no single orientation for {winding}: {values}")
    return min(values, key=abs)


def p1_holds(score: dict) -> bool:
    return (
        score["median"] is not None
        and score["fraction_within"][str(int(WITHIN))] >= P1_FRACTION
        and score["median"] <= P1_MEDIAN
    )


def winding_index(name: str) -> int | None:
    match = re.match(r"w(\d+)", Path(name).name)
    return int(match.group(1)) if match else None


def choose(scores: dict[str, dict]) -> str | None:
    """The candidate with the smallest median distance among those that cover enough of the published
    winding. Ties go to the larger share within WITHIN, then to the name, so the choice is reproducible."""
    eligible = [
        (score["median"], -score["fraction_within"][str(int(WITHIN))], name)
        for name, score in scores.items()
        if score["median"] is not None
        and score["covered_fraction"] >= ELIGIBLE_COVERAGE
    ]
    return min(eligible)[2] if eligible else None


def select(published: dict[str, str], candidates: list[str]) -> dict:
    """Score every candidate against every published winding (published nodes -> candidate surface)."""
    if len(published) != 2:
        raise ValueError("the registration compares exactly two published windings")
    loaded = {Path(c).name: load_tifxyz(c) for c in candidates}
    if len(loaded) != len(candidates):
        raise ValueError("candidate folder names are not unique")
    out: dict = {"candidates": sorted(loaded), "published": {}}
    for name, path in published.items():
        a, a_valid = load_tifxyz(path)
        scores = {
            cand: surface_distance(a, a_valid, b, b_valid)
            for cand, (b, b_valid) in loaded.items()
        }
        chosen = choose(scores)
        ranked = sorted(
            (s["median"], cand) for cand, s in scores.items() if s["median"] is not None
        )
        out["published"][name] = {
            "chosen": chosen,
            "chosen_score": scores[chosen] if chosen else None,
            "three_closest": [
                {"candidate": cand, **scores[cand]} for _, cand in ranked[:3]
            ],
            "scores": scores,
        }
    return out


def consecutive(chosen: dict[str, str | None]) -> bool | None:
    """P2: the two chosen windings are neighbours in the same order as the published pair."""
    names = sorted(chosen, key=lambda n: winding_index(n) or 0)
    picks = [winding_index(chosen[n]) if chosen[n] else None for n in names]
    if None in picks:
        return None
    return picks[1] - picks[0] == 1


# --- ink comparison (P3) -------------------------------------------------------------------------


def lattice_points(xyz: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Scroll position of the centre of every LATTICE x LATTICE block of render pixels.

    Render pixel p sits at grid coordinate p / PX_PER_NODE; the position is bilinear between the four
    surrounding nodes and exists only where all four do. Whether the renderer puts pixel centres half a
    pixel further is at most half a voxel here, an eighth of ACCEPT.
    """
    rows, cols = xyz.shape[:2]
    cells_r, cells_c = rows * PX_PER_NODE // LATTICE, cols * PX_PER_NODE // LATTICE
    gr = (np.arange(cells_r) * LATTICE + (LATTICE - 1) / 2) / PX_PER_NODE
    gc = (np.arange(cells_c) * LATTICE + (LATTICE - 1) / 2) / PX_PER_NODE
    r0 = np.clip(np.floor(gr).astype(int), 0, rows - 2)
    c0 = np.clip(np.floor(gc).astype(int), 0, cols - 2)
    fr = (gr - r0)[:, None, None]
    fc = (gc - c0)[None, :, None]
    inside = (gr <= rows - 1)[:, None] & (gc <= cols - 1)[None, :]
    corners_ok = (
        valid[r0][:, c0]
        & valid[r0 + 1][:, c0]
        & valid[r0][:, c0 + 1]
        & valid[r0 + 1][:, c0 + 1]
    )
    points = (
        xyz[r0][:, c0] * (1 - fr) * (1 - fc)
        + xyz[r0 + 1][:, c0] * fr * (1 - fc)
        + xyz[r0][:, c0 + 1] * (1 - fr) * fc
        + xyz[r0 + 1][:, c0 + 1] * fr * fc
    )
    return points, corners_ok & inside


def block_mean(image: np.ndarray) -> np.ndarray:
    """Mean over LATTICE x LATTICE blocks; rows and columns that do not fill a block are dropped."""
    h, w = image.shape[0] // LATTICE, image.shape[1] // LATTICE
    cut = image[: h * LATTICE, : w * LATTICE].astype(np.float64)
    return cut.reshape(h, LATTICE, w, LATTICE).mean(axis=(1, 3))


def transfer(
    target_points: np.ndarray,
    target_ok: np.ndarray,
    sources: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For every target lattice point: which source surface and which of its lattice cells is nearest.

    Returns (source number, flat cell index, distance), each shaped like the target lattice; source
    number is -1 where the target point does not exist or nothing lies within ACCEPT.
    """
    which = np.full(target_ok.shape, -1, dtype=np.int64)
    cell = np.zeros(target_ok.shape, dtype=np.int64)
    best = np.full(target_ok.shape, np.inf)
    query = target_points[target_ok]
    for number, (points, ok) in enumerate(sources):
        if not ok.any():
            continue
        flat = np.flatnonzero(ok)
        dist, index = cKDTree(points[ok]).query(query, k=1, distance_upper_bound=ACCEPT)
        hit = np.isfinite(dist)
        better = np.zeros(target_ok.shape, dtype=bool)
        better[target_ok] = hit & (dist < best[target_ok])
        take = better[target_ok]
        which[better] = number
        cell[better] = flat[index[take]]
        best[better] = dist[take]
    return which, cell, best


def normals_agree(
    target_points: np.ndarray,
    source_points: np.ndarray,
    which: np.ndarray,
    cell: np.ndarray,
    number: int,
) -> float | None:
    """Median cosine between the lattice normals of the target and of source `number` over the cells that
    take their ink from it. Positive: layer k of both renders lies on the same side of the sheet."""

    def lattice_normals(p: np.ndarray) -> np.ndarray:
        n = np.full_like(p, np.nan)
        n[1:-1, 1:-1] = np.cross(p[1:-1, 2:] - p[1:-1, :-2], p[2:, 1:-1] - p[:-2, 1:-1])
        with np.errstate(invalid="ignore", divide="ignore"):
            return n / np.linalg.norm(n, axis=-1, keepdims=True)

    mask = which == number
    if not mask.any():
        return None
    target_n = lattice_normals(target_points)[mask]
    source_n = lattice_normals(source_points).reshape(-1, 3)[cell[mask]]
    cosine = np.einsum("ij,ij->i", target_n, source_n)
    cosine = cosine[np.isfinite(cosine)]
    return round(float(np.median(cosine)), 4) if cosine.size else None


def zscore_ensemble(maps: dict[str, np.ndarray], mask: np.ndarray) -> np.ndarray:
    """Mean over the four models of each model's z-score, the mean and SD taken over `mask`."""
    if set(maps) != set(MODELS):
        raise ValueError(f"need exactly the four models, got {sorted(maps)}")
    if int(mask.sum()) < 2:
        raise ValueError("fewer than two cells to standardise over")
    total = np.zeros(mask.shape, dtype=np.float64)
    for model in MODELS:
        values = maps[model][mask]
        sd = float(values.std())
        if sd == 0:
            raise ValueError(f"{model} is constant over the compared cells")
        total += (maps[model] - float(values.mean())) / sd
    return total / len(MODELS)


def pearson(a: np.ndarray, b: np.ndarray) -> float | None:
    if a.size < 2 or a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def highpass(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """`image` minus its Gaussian-weighted local mean over the cells of `mask` (sigma HIGHPASS_CELLS).

    Ink maps carry a broad background that two maps share whether or not their letters line up: the
    published ensemble against itself slid by 64 pixels still scores r = 0.39 to 0.50. Taking the
    background off leaves the strokes (0.01 to 0.19 after the same slide).
    """
    weight = ndimage.gaussian_filter(mask.astype(np.float64), HIGHPASS_CELLS)
    local = ndimage.gaussian_filter(np.where(mask, image, 0.0), HIGHPASS_CELLS)
    with np.errstate(invalid="ignore", divide="ignore"):
        background = np.where(weight > 1e-6, local / weight, 0.0)
    return np.where(mask, image - background, 0.0)


def slid_control(
    target: np.ndarray,
    moved: np.ndarray,
    target_mask: np.ndarray,
    moved_mask: np.ndarray,
    cells: int = SHIFT_CELLS,
) -> dict:
    """Pearson r after sliding our transferred map by `cells` in each of the four directions, over the
    cells of `target_mask` whose slid partner is in `moved_mask`.

    The largest absolute value is the control: what two maps of the same sheet score when their ink does
    not line up.
    """
    out: dict = {}
    for label, (dr, dc) in {
        "down": (cells, 0),
        "up": (-cells, 0),
        "right": (0, cells),
        "left": (0, -cells),
    }.items():
        slid = np.roll(moved, (dr, dc), axis=(0, 1))
        slid_mask = np.roll(moved_mask, (dr, dc), axis=(0, 1))
        if dr > 0:
            slid_mask[:dr] = False
        elif dr < 0:
            slid_mask[dr:] = False
        if dc > 0:
            slid_mask[:, :dc] = False
        elif dc < 0:
            slid_mask[:, dc:] = False
        both = target_mask & slid_mask
        out[label] = pearson(target[both], slid[both])
    values = [abs(v) for v in out.values() if v is not None]
    out["largest_absolute"] = max(values) if values else None
    return out


def agreement(
    published_maps: dict[str, np.ndarray],
    published_blind_maps: dict[str, np.ndarray],
    transferred_maps: dict[str, np.ndarray],
    accepted: np.ndarray,
    letter_cells: np.ndarray,
) -> dict:
    """P3's numbers. All arrays are on the published lattice; `accepted` marks cells that received ink
    from our windings and are valid on both renders; `letter_cells` marks the published letter boxes.

    Each side is one ensemble with its background taken off. The deciding r is over the accepted cells
    inside the letter boxes. Two controls, both from this run: our reading-side ensemble against the
    published BLIND-side ensemble (the same sheet read from the wrong side), and our ensemble slid by
    64 pixels against the published one (the same sheet with the ink out of place).
    """
    in_letters = int(letter_cells.sum())
    if in_letters == 0:
        raise ValueError("no letter-box cells")
    compared = accepted & letter_cells
    coverage = float(compared.sum()) / in_letters
    result: dict = {
        "cells_accepted": int(accepted.sum()),
        "letter_box_cells": in_letters,
        "letter_box_cells_compared": int(compared.sum()),
        "letter_box_coverage": round(coverage, 4),
        "evaluable": coverage >= P3_COVERAGE,
    }
    if not result["evaluable"]:
        result.update(
            {"r": None, "control_wrong_side": None, "control_slid": None, "p3": None}
        )
        return result
    raw_ours = zscore_ensemble(transferred_maps, accepted)
    raw_theirs = zscore_ensemble(published_maps, accepted)
    ours = highpass(raw_ours, accepted)
    theirs = highpass(raw_theirs, accepted)
    blind = highpass(zscore_ensemble(published_blind_maps, accepted), accepted)
    r = pearson(theirs[compared], ours[compared])
    wrong_side = pearson(blind[compared], ours[compared])
    slid = slid_control(theirs, ours, compared, accepted)
    controls = [wrong_side, slid["largest_absolute"]]
    result.update(
        {
            "r": _rounded(r),
            "control_wrong_side": _rounded(wrong_side),
            "control_slid": {k: _rounded(v) for k, v in slid.items()},
            "control_slid_256px": {
                k: _rounded(v)
                for k, v in slid_control(
                    theirs, ours, compared, accepted, cells=4 * SHIFT_CELLS
                ).items()
            },
            "r_all_cells": _rounded(pearson(theirs[accepted], ours[accepted])),
            "r_all_cells_with_background": _rounded(
                pearson(raw_theirs[accepted], raw_ours[accepted])
            ),
            "per_model_r": {
                m: _rounded(
                    pearson(
                        highpass(published_maps[m], accepted)[compared],
                        highpass(transferred_maps[m], accepted)[compared],
                    )
                )
                for m in MODELS
            },
        }
    )
    result["p3"] = bool(
        r is not None
        and None not in controls
        and r >= P3_R
        and all(r >= P3_RATIO * abs(c) for c in controls)
    )
    return result


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


# --- gate and decision table ---------------------------------------------------------------------

PER_WINDING_STEPS = ("flatten", "render", "ink")


def assemble_gate(directory: Path, fit_config: str, windings: list[str]) -> dict:
    """The gate record from the files the run scripts wrote: distance_field.json, fit.json, snap.json and,
    for each chosen winding, flatten_W.json, render_W.json and ink_W.json.

    A file that is not there counts as a failed step (exit 1, "not_run"): a step that never started did
    not run. With no winding chosen, the steps after the fit had nothing to work on and are recorded as
    passed and "nothing_to_do"; the fit ran, and that no winding of it lies along a published one is a
    result for the decision table, not a failure to run.
    """
    if fit_config not in FIT_CONFIGS:
        raise ValueError(f"fit_config must be one of {FIT_CONFIGS}")

    def read(name: str) -> dict:
        path = directory / f"{name}.json"
        if not path.is_file():
            return {"exit": 1, "not_run": True}
        record = json.loads(path.read_text())
        if not isinstance(record.get("exit"), int):
            raise ValueError(f"{path} has no integer exit code")
        return record

    steps: dict = {"distance_field": read("distance_field"), "fit": read("fit")}
    if not windings:
        for step in ("snap", *PER_WINDING_STEPS):
            steps[step] = {"exit": 0, "nothing_to_do": True}
    else:
        steps["snap"] = read("snap")
        for step in PER_WINDING_STEPS:
            parts = {w: read(f"{step}_{w}") for w in windings}
            steps[step] = {
                "exit": max(abs(part["exit"]) for part in parts.values()),
                "windings": parts,
            }
    return {"steps": steps, "fit_config": fit_config, "windings": list(windings)}


def verdict(gate: dict, final: dict | None, ink: dict | None) -> dict:
    """The registered decision table.

    `gate` holds, for every step in GATE_STEPS, its exit code, plus fit_config ("recipe" or "reduced").
    `final` is the output of `select` run on the two chosen windings AFTER snap and flatten; `ink` is the
    output of `agreement`. A step that failed makes the verdict DOES_NOT_RUN and nothing else is read: a
    run that stopped half way has no say on the windings. A gate that passed needs both other records.
    """
    steps = gate.get("steps", {})
    missing = [s for s in GATE_STEPS if s not in steps]
    if missing:
        raise ValueError(f"gate record lacks steps: {missing}")
    if gate.get("fit_config") not in FIT_CONFIGS:
        raise ValueError(f"fit_config must be one of {FIT_CONFIGS}")
    failed = [s for s in GATE_STEPS if steps[s]["exit"] != 0]
    if failed:
        return {
            "verdict": "DOES_NOT_RUN",
            "failed_steps": failed,
            "fit_config": gate["fit_config"],
        }
    if final is None or ink is None:
        raise ValueError(
            "the gate passed: the distance and ink records are both required"
        )
    published = final["published"]
    if len(published) != 2:
        raise ValueError("need both published windings")
    p1 = {
        name: bool(entry["chosen"] and p1_holds(entry["chosen_score"]))
        for name, entry in published.items()
    }
    p2 = consecutive({name: entry["chosen"] for name, entry in published.items()})
    same_sheets = all(p1.values())
    if ink["evaluable"]:
        letters = bool(ink["p3"])
    else:
        letters = False
    if same_sheets and letters:
        name = "REPRODUCED"
    elif same_sheets:
        name = "SAME_SHEETS_NO_LETTERS"
    elif letters:
        name = "LETTERS_OFF_THE_PUBLISHED_WINDINGS"
    else:
        name = "NOT_REPRODUCED"
    if gate["fit_config"] == "reduced":
        name += "_WITH_REDUCED_FIT"
    return {
        "verdict": name,
        "fit_config": gate["fit_config"],
        "p1": p1,
        "p2_consecutive": p2,
        "p3": ink["p3"],
        "p3_evaluable": ink["evaluable"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("distance")
    d.add_argument("a")
    d.add_argument("b")
    d.add_argument("out", nargs="?")
    s = sub.add_parser("select")
    s.add_argument("out")
    s.add_argument("--published", nargs=2, required=True, metavar="NAME=DIR")
    s.add_argument("--candidates", nargs="+", required=True)
    g = sub.add_parser("gate")
    g.add_argument("out")
    g.add_argument("--dir", required=True, type=Path)
    g.add_argument("--fit-config", required=True, choices=FIT_CONFIGS)
    g.add_argument("--windings", nargs="*", required=True)
    o = sub.add_parser("orientation")
    o.add_argument("final")
    o.add_argument("winding")
    v = sub.add_parser("verdict")
    v.add_argument("gate")
    v.add_argument("final")
    v.add_argument("agreement")
    v.add_argument("out")
    args = parser.parse_args(argv)

    if args.command == "distance":
        a, a_valid = load_tifxyz(args.a.rstrip("/"))
        b, b_valid = load_tifxyz(args.b.rstrip("/"))
        result = {
            "a": args.a,
            "b": args.b,
            **surface_distance(a, a_valid, b, b_valid),
        }
        out = args.out
    elif args.command == "select":
        published = dict(item.split("=", 1) for item in args.published)
        result = select(published, [c.rstrip("/") for c in args.candidates])
        result["consecutive"] = consecutive(
            {name: entry["chosen"] for name, entry in result["published"].items()}
        )
        out = args.out
    elif args.command == "gate":
        result = assemble_gate(args.dir, args.fit_config, args.windings)
        out = args.out
    elif args.command == "orientation":
        print(orientation(json.loads(Path(args.final).read_text()), args.winding))
        return 0
    else:
        gate = json.loads(Path(args.gate).read_text())
        passed = all(
            gate.get("steps", {}).get(s, {}).get("exit") == 0 for s in GATE_STEPS
        )
        final = json.loads(Path(args.final).read_text()) if passed else None
        ink = json.loads(Path(args.agreement).read_text()) if passed else None
        result = verdict(gate, final, ink)
        out = args.out
    text = json.dumps(result, indent=1)
    if out:
        Path(out).write_text(text + "\n")
    if args.command == "select":
        for name, entry in result["published"].items():
            print(name, "->", entry["chosen"], entry["chosen_score"])
        print("consecutive:", result["consecutive"])
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
