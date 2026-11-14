"""Finding 113, step 6: numbered strips for a reader who does not know which side a strip shows.

A tile is TILE x TILE lattice cells (a cell is 4 render pixels). Each tile gives two strips, one a side; a strip
is the four-model ensemble at each depth, left to right, at render resolution, dark where the models see ink.
The grey scale is fixed per winding or segment over both sides. Strips are numbered in a shuffled order and the
key is written apart from them.

usage: blind_tiles.py OUT_DIR KEY.json --depths LO HI
           --target NAME MESH MAPS RENDER [--target ...]
           --anchor NAME MESH MAPS RENDER LABELS

The strips of a prize-eligible scroll are that scroll's ink maps: OUT_DIR and KEY.json stay on this machine.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))
sys.path.insert(0, str(HERE.parent / "pherc0841"))

import mesh_step_analysis as analysis  # noqa: E402
import transfer_maps  # noqa: E402

TILE = 96  # lattice cells: 384 render pixels, 3.6 mm
CT_MIN = 0.90  # share of a tile's cells with CT in all layers
TOP, RANDOM = 4, 4  # tiles a winding: highest score, and drawn from the rest
ANCHORS = 12
ANCHOR_SCORED_MIN = (
    0.50  # share of an anchor tile's cells that carry an unambiguous label
)
ANCHOR_INK_MIN = 0.10  # share of those cells that are ink
SEED = 113
GAP = 6  # white pixels between depths in a strip
SIDES = {"reading": True, "other": False}  # reading is the recipe's `_reverse`


def tile_origins(ok: np.ndarray, step: int = TILE) -> list[tuple[int, int]]:
    """Top-left cells of the tiles on a grid of `step` with CT in at least CT_MIN of their cells."""
    rows, cols = ok.shape
    return [
        (r, c)
        for r in range(0, rows - TILE + 1, step)
        for c in range(0, cols - TILE + 1, step)
        if ok[r : r + TILE, c : c + TILE].mean() >= CT_MIN
    ]


def pick(
    scores: dict[tuple[int, int], float], rng: np.random.Generator
) -> dict[tuple[int, int], str]:
    """The TOP highest-scoring tiles and RANDOM drawn from the rest, each with how it was picked."""
    ranked = sorted(scores, key=lambda origin: (-scores[origin], origin))
    out = {origin: "top" for origin in ranked[:TOP]}
    rest = ranked[TOP:]
    for i in rng.permutation(len(rest))[:RANDOM]:
        out[rest[int(i)]] = "random"
    return out


def anchor_origins(
    ok: np.ndarray, scored: np.ndarray, ink: np.ndarray, rng: np.random.Generator
) -> list[tuple[int, int]]:
    """ANCHORS tiles with labelled ink, drawn from a half-overlapping grid."""
    good = []
    for r, c in tile_origins(ok, TILE // 2):
        cells = scored[r : r + TILE, c : c + TILE]
        if (
            cells.mean() >= ANCHOR_SCORED_MIN
            and ink[r : r + TILE, c : c + TILE][cells].mean() >= ANCHOR_INK_MIN
        ):
            good.append((r, c))
    return [good[int(i)] for i in sorted(rng.permutation(len(good))[:ANCHORS])]


def contrast(lattice_map: np.ndarray, ok: np.ndarray, origin: tuple[int, int]) -> float:
    r, c = origin
    inside = ok[r : r + TILE, c : c + TILE]
    return float(lattice_map[r : r + TILE, c : c + TILE][inside].std())


def tile_scores(
    per_side: dict[str, list[np.ndarray]], ok: np.ndarray, origins: list
) -> dict:
    """Per tile: the larger of the two sides' contrast, each side's averaged over its depths."""
    return {
        origin: max(
            float(np.mean([contrast(m, ok, origin) for m in maps]))
            for maps in per_side.values()
        )
        for origin in origins
    }


def shuffled_numbers(count: int, rng: np.random.Generator) -> list[str]:
    return [f"{int(i) + 1:03d}" for i in rng.permutation(count)]


class Source:
    """One winding or segment: its lattice, and its maps at render resolution."""

    def __init__(self, name: str, mesh: Path, maps: Path, render: Path):
        self.name, self.maps, self.render = name, maps, render
        xyz, valid = analysis.load_tifxyz(mesh)
        _, corners = analysis.lattice_points(xyz, valid)
        self.canvas = (
            xyz.shape[0] * analysis.PX_PER_NODE,
            xyz.shape[1] * analysis.PX_PER_NODE,
        )
        self.ok = corners & transfer_maps.render_valid(render, corners.shape)
        self.stem = render.name.removesuffix(".zarr")

    def full(self, model: str, depth: int, reading: bool) -> np.ndarray:
        import cv2

        path = transfer_maps.map_file(self.maps, self.stem, model, reading, depth)
        raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if raw is None or raw.ndim != 2 or raw.dtype != np.uint8:
            raise SystemExit(f"cannot read {path} as an 8-bit grey map")
        if model == "hecate":
            values = raw.astype(np.float32) / 255.0
            if values.shape != self.canvas:
                values = cv2.resize(
                    values,
                    (self.canvas[1], self.canvas[0]),
                    interpolation=cv2.INTER_LINEAR,
                )
            return values
        if raw.shape != self.canvas:
            raise SystemExit(f"{path} is {raw.shape}, the render is {self.canvas}")
        return np.clip((raw.astype(np.float32) - 64.0) / 128.0, 0.0, 1.0)

    def ensemble(self, depth: int, reading: bool) -> np.ndarray:
        """Mean of the four models' z-scores at render resolution, standardised over the pixels with CT."""
        lattice = analysis.LATTICE
        mask = np.zeros(self.canvas, bool)
        rows, cols = self.ok.shape
        mask[: rows * lattice, : cols * lattice] = np.kron(
            self.ok, np.ones((lattice, lattice), bool)
        )
        total = np.zeros(self.canvas, np.float32)
        for model in analysis.MODELS:
            values = self.full(model, depth, reading)
            inside = values[mask]
            total += (values - inside.mean()) / max(float(inside.std()), 1e-6)
        return total / len(analysis.MODELS)

    def hecate_lattice(self, depth: int, reading: bool) -> np.ndarray:
        values = analysis.block_mean(self.full("hecate", depth, reading))
        return analysis.highpass(values.astype(np.float64), self.ok)


def strip(panels: list[np.ndarray], low: float, high: float) -> np.ndarray:
    """Depths left to right as 8-bit grey, dark where the ensemble is high."""
    height = panels[0].shape[0]
    gap = np.full((height, GAP), 255, np.uint8)
    parts: list[np.ndarray] = []
    for panel in panels:
        scaled = 1.0 - np.clip((panel - low) / max(high - low, 1e-6), 0.0, 1.0)
        parts += [(scaled * 255).astype(np.uint8), gap]
    return np.concatenate(parts[:-1], axis=1)


def main(argv: list[str] | None = None) -> int:
    import cv2

    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("key")
    ap.add_argument("--depths", nargs=2, type=int, required=True)
    ap.add_argument("--target", nargs=4, action="append", required=True)
    ap.add_argument("--anchor", nargs=5, required=True)
    args = ap.parse_args(argv)
    out, key_file = Path(args.out), Path(args.key)
    if out.exists() or key_file.exists():
        print(f"{out} or {key_file} exists: the strips are made once", file=sys.stderr)
        return 2
    depths = list(range(args.depths[0], args.depths[1] + 1))
    rng = np.random.default_rng(SEED)
    px = analysis.LATTICE
    pending: list[tuple[dict, np.ndarray]] = []

    def add(source: Source, kind: str, tiles: dict[tuple[int, int], str]) -> None:
        stacks = {
            side: [source.ensemble(d, flag) for d in depths]
            for side, flag in SIDES.items()
        }
        sample = np.concatenate(
            [e[::8, ::8].ravel() for maps in stacks.values() for e in maps]
        )
        low, high = np.percentile(sample, [2, 98])
        for (r, c), picked in tiles.items():
            window = (slice(r * px, (r + TILE) * px), slice(c * px, (c + TILE) * px))
            for side, maps in stacks.items():
                entry = {
                    "source": kind,
                    "unit": source.name,
                    "side": side,
                    "picked": picked,
                    "origin": [r, c],
                }
                pending.append((entry, strip([m[window] for m in maps], low, high)))

    for name, mesh, maps, render in args.target:
        source = Source(name, Path(mesh), Path(maps), Path(render))
        lattice = {
            s: [source.hecate_lattice(d, flag) for d in depths]
            for s, flag in SIDES.items()
        }
        origins = tile_origins(source.ok)
        add(source, "target", pick(tile_scores(lattice, source.ok, origins), rng))
    import surface_control as sc

    name, mesh, maps, render, labels = args.anchor
    segment = sc.Segment(name, Path(mesh), Path(maps), Path(render), Path(labels))
    source = Source(name, Path(mesh), Path(maps), Path(render))
    anchors = anchor_origins(source.ok, segment.scored, segment.ink, rng)
    add(source, "anchor", {origin: "anchor" for origin in anchors})

    out.mkdir(parents=True)
    numbers = shuffled_numbers(len(pending), rng)
    key = {}
    for number, (entry, image) in zip(numbers, pending, strict=True):
        cv2.imwrite(str(out / f"{number}.png"), image)
        key[number] = entry
    (out / "marks.csv").write_text(
        "strip,mark\n" + "".join(f"{n},\n" for n in sorted(key))
    )
    rows = "".join(
        f'<p>{n}<br><img src="{n}.png" style="max-width:100%"></p>\n'
        for n in sorted(key)
    )
    (out / "sheet.html").write_text(
        "<!doctype html><meta charset=utf-8><title>strips</title>"
        f"<p>Depths {depths[0]} to {depths[-1]}, left to right. Dark is ink-like. A strip may be mirrored or "
        "rotated. Mark each strip in marks.csv: 0 nothing, 1 strokes, 2 letter shapes.</p>\n"
        + rows
    )
    key_file.write_text(
        json.dumps({"depths": depths, "tile_cells": TILE, "strips": key}, indent=1)
        + "\n"
    )
    print(f"{len(key)} strips in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
