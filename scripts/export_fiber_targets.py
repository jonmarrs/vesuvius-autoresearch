"""Export fiber-skeleton cubes as self-contained ScrollGT targets.

Reads the raw cubes in local_data/fiber_skeletons/ (NML traces, the shipped
semantic label, and the fiber_hz_vt probability volume) and writes, per cube,
a directory that ScrollGT can score with no GPU, no model, and no network.

The semantic label is used here for one purpose only: to measure the rate at
which in-bounds NML nodes land on fiber-positive voxels. That rate is the
empirical proof of the coordinate convention (NML x,y,z against volume z,y,x,
origin from the filename), and it is recorded into meta.json so the guarantee
survives into a repo that does not ship the raw cubes.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import tifffile

from vesuvius_autoresearch.fibers.skeleton_io import (
    origin_from_stem,
    parse_nml,
    size_from_stem,
)

SRC = pathlib.Path("local_data/fiber_skeletons")
VOXEL_UM = 7.91
THRESHOLD = 0.5


def split_for_stem(stem: str) -> str:
    """Reporting split, derived from the scroll rather than a hardcoded cube list.

    This was `"cross_scroll" if stem == CROSS_SCROLL_SPLIT else "primary"` -- a single
    stem, so every additional Scroll-5 cube would have been labelled "primary". An unknown
    scroll raises rather than defaulting, because defaulting is exactly how a cross-scroll
    cube gets silently reported as same-scroll.
    """
    prefix = stem.split("_", 1)[0]
    if prefix == "s1":
        return "primary"
    if prefix == "s5":
        return "cross_scroll"
    raise ValueError(f"unknown scroll prefix {prefix!r} in cube stem {stem!r}")


def size_class_for_stem(stem: str) -> int:
    """Cube edge in voxels. ERL is a length statistic and does not compare across these."""
    return size_from_stem(stem)


CUBES = [
    "s1_00497_01497_03997_256",
    "s1_00497_02497_02997_256",
    "s1_00997_02497_02997_256",
    "s1_08997_02997_02497_256",
    "s1_10997_02997_02997_256",
    "s5_03997_01497_03997_256",
]


def pack_skeleton(skel, shape) -> dict:
    """Flatten a Skeleton into fixed-key arrays with per-fiber offsets."""
    coords, edges, fiber_offsets, edge_offsets = [], [], [0], [0]
    fiber_ids, fiber_names = [], []
    for fib in skel.fibers:
        coords.append(np.asarray(fib.coords, dtype=np.float32))
        # rebase local edge indices onto the concatenated coords array
        edges.append(np.asarray(fib.edges, dtype=np.int32) + fiber_offsets[-1])
        fiber_offsets.append(fiber_offsets[-1] + len(fib.coords))
        edge_offsets.append(edge_offsets[-1] + len(fib.edges))
        fiber_ids.append(fib.id)
        fiber_names.append(fib.name)
    return {
        "coords": np.concatenate(coords) if coords else np.zeros((0, 3), np.float32),
        "edges": np.concatenate(edges) if edges else np.zeros((0, 2), np.int32),
        "fiber_offsets": np.asarray(fiber_offsets, dtype=np.int64),
        "edge_offsets": np.asarray(edge_offsets, dtype=np.int64),
        "fiber_ids": np.asarray(fiber_ids, dtype=np.int64),
        "fiber_names": np.asarray(fiber_names, dtype=object),
        "scale_um": np.asarray(skel.scale_um or (VOXEL_UM,) * 3, dtype=np.float64),
        "origin_zyx": np.asarray(skel.origin_zyx, dtype=np.int64),
        "shape": np.asarray(shape, dtype=np.int64),
    }


def landing_rate(skel, semantic) -> float:
    """Fraction of in-bounds NML nodes landing on a fiber-positive voxel."""
    hits = total = 0
    for fib in skel.fibers:
        ok = fib.in_bounds_mask(semantic.shape)
        if not ok.any():
            continue
        idx = np.rint(fib.coords[ok]).astype(int)
        idx = np.clip(idx, 0, np.asarray(semantic.shape) - 1)
        hits += int((semantic[idx[:, 0], idx[:, 1], idx[:, 2]] > 0).sum())
        total += int(ok.sum())
    return hits / total if total else 0.0


def export(stem: str, out_root: pathlib.Path, bench: dict) -> None:
    size = size_from_stem(stem)
    shape = (size, size, size)
    skel = parse_nml(SRC / f"{stem}.nml", origin_zyx=origin_from_stem(stem))
    prob = np.load(SRC / f"{stem}_fiberprob.npy")
    semantic = tifffile.imread(SRC / f"{stem}_semantic.tif")

    if prob.shape != shape or semantic.shape != shape:
        raise SystemExit(
            f"{stem}: expected {shape}, got prob={prob.shape} semantic={semantic.shape}"
        )

    rate = landing_rate(skel, semantic)
    if rate < 0.999:
        raise SystemExit(
            f"{stem}: node landing rate {rate:.4f} < 0.999 — the coordinate "
            f"convention does not hold for this cube; do not ship it"
        )

    mask = prob >= THRESHOLD
    n_in_bounds = sum(int(f.in_bounds_mask(shape).sum()) for f in skel.fibers)
    # Same filter the benchmark uses (bench_cli.py::_load_cube) to decide which
    # fibers are scoreable: a fiber needs at least two in-bounds nodes to
    # contribute a measurable run, so 0- and 1-node fibers are excluded.
    n_fibers_scored = sum(1 for f in skel.fibers if f.in_bounds_mask(shape).sum() > 1)
    n_gt_fibers = bench["cubes"][stem]["rows"]["oracle"]["n_gt_fibers"]
    if n_fibers_scored != n_gt_fibers:
        raise SystemExit(
            f"{stem}: n_fibers_scored={n_fibers_scored} != floors.oracle.n_gt_fibers="
            f"{n_gt_fibers} — the scoreable-fiber filter no longer matches the "
            f"benchmark; do not ship a meta.json with unreconciled fiber counts"
        )

    out = out_root / f"fibers_{stem}"
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "skeleton.npz", **pack_skeleton(skel, shape))
    np.savez_compressed(
        out / "mask.npz",
        packed=np.packbits(mask),
        shape=np.asarray(shape, dtype=np.int64),
    )

    meta = {
        "target_id": f"fibers_{stem}",
        "family": "fiber_connectivity",
        "cube": stem,
        "scroll": "Scroll 5" if stem.startswith("s5_") else "Scroll 1 (PHerc. Paris 4)",
        "split": split_for_stem(stem),
        "size_class": size_class_for_stem(stem),
        "split_note": (
            "'cross_scroll' is a labelled reporting convention, not held-out "
            "secrecy: the ground truth comes from a public villa dataset and "
            "cannot be hidden. This split exists to report transfer across "
            "scrolls, not to withhold labels from entrants."
        ),
        "shape": list(shape),
        "origin_zyx": list(origin_from_stem(stem)),
        "voxel_size_um": VOXEL_UM,
        "tolerance": bench["tolerance"],
        "ground_truth": {
            "origin": (
                "villa fiber-skeletons dataset, dl.ash2txt.org/datasets/fiber-skeletons/ — "
                "every papyrus fiber in the cube hand-traced in WEBKNOSSOS at 7.91 um"
            ),
            "source_file": f"nml/{stem}.nml",
            "n_fibers": len(skel.fibers),
            "n_fibers_scored": n_fibers_scored,
            "n_nodes_in_bounds": n_in_bounds,
            "note": (
                "n_fibers is every fiber in the raw NML trace. n_fibers_scored "
                "(and floors.*.n_gt_fibers) is smaller: it excludes fibers with 0 "
                "or 1 in-bounds nodes, since a fiber needs at least two in-bounds "
                "nodes to contribute a measurable run. Annotators traced beyond "
                "the cube boundary, so this gap reaches ~12% on the shipped cubes."
            ),
        },
        "convention_check": {
            "claim": (
                "NML nodes are x,y,z in absolute scroll space; volumes index z,y,x; "
                "the cube origin is encoded in the filename as <scroll>_<z>_<y>_<x>_<size>"
            ),
            "measured_node_landing_rate_on_semantic_label": round(rate, 6),
            "verified_against": f"labelsTr/{stem}.tif (shipped semantic label)",
        },
        "mask": {
            "model": "scrollprize/fiber_hz_vt (Apache-2.0)",
            "threshold": THRESHOLD,
            "density": round(float(mask.mean()), 6),
            "note": (
                "Every entrant is scored against this identical mask, so scorecard "
                "differences come from the instance labelling rather than from a "
                "better or worse segmentation."
            ),
        },
        "floors": bench["cubes"][stem]["rows"],
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    kb = (out / "mask.npz").stat().st_size / 1e3
    print(
        f"{stem}: {len(skel.fibers)} fibers ({n_fibers_scored} scored), "
        f"landing {rate:.4f}, mask {kb:.0f} KB"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-root", required=True, help="scrollgt data/ directory")
    ap.add_argument("--bench", default="reports/fiber_benchmark_all_cubes.json")
    args = ap.parse_args()

    bench = json.loads(pathlib.Path(args.bench).read_text())
    for stem in CUBES:
        export(stem, pathlib.Path(args.out_root), bench)


if __name__ == "__main__":
    main()
