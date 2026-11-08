"""Splice a villa neural volume-tracer run's pieces into polylines, by finding 105's rule.

villa's `tracing/volume.py` writes each fiber once, keeping `--overlap` points where a trace was cut beside a fiber
already written, and records the fibers each piece's ends touch (`links`). This reads a run's output directory as villa
writes it (`run.json` and `tiles/*.npz`), splices each piece to the linked fiber whose end it overlaps
(`neural_tracer_link_splice.splice_candidates` and `choose_splices`, the rule finding 105 registered), and writes one
polyline per chain of spliced pieces.

Distances are in base voxels (the tiles' trace-grid xyz times the run's `grid_scale`). A splice needs the piece's end
within `--overlap` trace-grid voxels of arclength of the linked fiber's nearer end: in findings 97 and 98's runs
(overlap 16, grid scale 2) that is finding 105's registered 32 voxels.

Along a chain, each next piece is turned to start at its spliced end, and its points up to the one nearest the
polyline's last point are dropped: they run beside the previous piece's kept overlap.

Usage: .venv/bin/python scripts/neural_tracer_splice.py OUT --write SPLICED.npz
  SPLICED.npz: points (base-voxel xyz, concatenated), offsets, id (each chain's smallest piece id), members and
  member_offsets (the chain's piece ids, in order); a JSON summary is printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import neural_tracer_link_splice as ls  # noqa: E402


def load_run(out: Path) -> tuple[dict, dict, dict]:
    """A volume-tracer OUT directory: piece id -> base-voxel xyz, piece id -> (stop reasons, links), run.json."""
    run = json.loads((out / "run.json").read_text())
    g = float(run["grid_scale"])
    pieces, meta = {}, {}
    tiles = sorted((out / "tiles").glob("*.npz"))
    if not tiles:
        raise SystemExit(f"{out}/tiles holds no finished tile")
    for f in tiles:
        z = np.load(f)
        o = z["offsets"]
        for k, i in enumerate(z["id"].tolist()):
            if i in pieces:
                raise SystemExit(f"{f}: piece {i} is written twice")
            pieces[i] = z["points"][o[k] : o[k + 1]].astype(np.float64) * g
            meta[i] = (
                tuple(z["reasons"][k].tolist()),
                tuple(int(v) for v in z["links"][k]),
            )
    return pieces, meta, run


def chains(ids, splices) -> list[list[tuple[int, bool]]]:
    """Every piece once, in chains [(id, reversed), ...], each read from a free end. splices: (a, a's end, b, b's
    end), each piece end at most once and no rings, as `choose_splices` gives them."""
    nbr: dict = {}
    for a, ea, b, eb in splices:
        if (a, ea) in nbr or (b, eb) in nbr:
            raise ValueError(f"a piece end is spliced twice: {(a, ea, b, eb)}")
        nbr[(a, ea)] = (b, eb)
        nbr[(b, eb)] = (a, ea)
    seen, out = set(), []
    for s in sorted(ids):
        if s in seen:
            continue
        free = [e for e in (0, 1) if (s, e) not in nbr]
        if not free:
            continue  # inside a chain, reached from one of its ends
        f = free[0]
        chain, cur, exit_end = [(s, f == 1)], s, 1 - f
        seen.add(s)
        while (cur, exit_end) in nbr:
            nxt, nxt_end = nbr[(cur, exit_end)]
            if nxt in seen:
                raise ValueError(f"a ring through {nxt}")
            chain.append((nxt, nxt_end == 1))
            seen.add(nxt)
            cur, exit_end = nxt, 1 - nxt_end
        out.append(chain)
    if len(seen) != len(set(ids)):
        raise ValueError("a ring: some pieces have no free end")
    return out


def join(pieces: dict, chain) -> tuple[np.ndarray, dict]:
    """One chain's polyline, and per joint the points dropped and the gap bridged."""
    first, rev = chain[0]
    out = pieces[first][::-1] if rev else pieces[first]
    dropped, gaps = [], []
    for pid, rev in chain[1:]:
        p = pieces[pid][::-1] if rev else pieces[pid]
        j = int(np.argmin(np.linalg.norm(p - out[-1], axis=1)))
        rest = p[j + 1 :]
        dropped.append(j + 1)
        gaps.append(float(np.linalg.norm(rest[0] - out[-1])) if len(rest) else 0.0)
        out = np.concatenate([out, rest])
    return out, {"dropped": dropped, "gaps": gaps}


def splice(pieces: dict, meta: dict, arc_limit: float) -> tuple[dict, dict, dict]:
    """Chain key -> polyline, chain key -> its piece ids, and a summary of the splices and joints."""
    candidates, missing = ls.splice_candidates(pieces, meta, arc_limit)
    splices = ls.choose_splices(candidates)
    problems = ls.chain_problems(splices, candidates)
    if problems:
        raise ValueError(f"the splices break the chain rules: {problems}")
    polys, members, dropped, gaps = {}, {}, [], []
    for chain in chains(list(pieces), splices):
        key = min(pid for pid, _ in chain)
        polys[key], info = join(pieces, chain)
        members[key] = [pid for pid, _ in chain]
        dropped += info["dropped"]
        gaps += info["gaps"]
    summary = {
        "pieces": len(pieces),
        "links": sum(v >= 0 for _, ls_ in meta.values() for v in ls_),
        "missing_targets": missing,
        "candidates": len(candidates),
        "splices": len(splices),
        "fibers": len(polys),
        "longest_chain": max((len(m) for m in members.values()), default=0),
        "dropped_points": int(sum(dropped)),
        "joint_gap_median": float(np.median(gaps)) if gaps else 0.0,
        "joint_gap_max": float(max(gaps)) if gaps else 0.0,
        "arc_limit": arc_limit,
    }
    return polys, members, summary


def write(path: Path, polys: dict, members: dict) -> None:
    keys = sorted(polys)
    pts = [polys[k] for k in keys]
    mem = [members[k] for k in keys]
    np.savez(
        path,
        points=np.concatenate(pts) if pts else np.zeros((0, 3)),
        offsets=np.cumsum([0] + [len(p) for p in pts]),
        id=np.array(keys, dtype=np.int64),
        members=np.array([m for ms in mem for m in ms], dtype=np.int64),
        member_offsets=np.cumsum([0] + [len(m) for m in mem]),
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "out", type=Path, help="a tracing.volume OUT directory (run.json, tiles/)"
    )
    ap.add_argument(
        "--write", type=Path, required=True, help="the spliced fibers (.npz)"
    )
    args = ap.parse_args(argv)
    if args.write.exists():
        raise SystemExit(f"{args.write} exists")
    # np.savez appends this case-sensitive suffix before opening its output.
    # Check that actual destination too, so a shorthand cannot overwrite it.
    if not str(args.write).endswith(".npz"):
        args.write = Path(f"{args.write}.npz")
        if args.write.exists():
            raise SystemExit(f"{args.write} exists")
    pieces, meta, run = load_run(args.out)
    polys, members, summary = splice(
        pieces, meta, float(run["overlap"]) * float(run["grid_scale"])
    )
    write(args.write, polys, members)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
