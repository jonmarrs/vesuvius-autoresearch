"""docs/VILLA_DRAFT_volume_seed_heading.md, "Before posting" step 3: does villa's tracer at a later commit, with and
without the patch, give what the draft measured at ccb431818?

repro/fibers/run_villa_seed_heading_rerun.sh traces the two held-out Scroll-5 cubes with villa's own CLI at a later
villa commit: `before` unpatched, `after` with repro/fibers/villa_volume_seed_heading.patch. This compares each run
point for point with the draft's source run (`before` with finding 97's villa run, `after` with finding 100's `keep`
arm), adds the runs' seed counts, and scores every run with ScrollGT's fiber scorer (version 3, tolerance 2) as
findings 97 and 100 scored theirs, so a run that differs still has its numbers.

Each run's fibers are read from its finished tiles (tiles/*.npz): the points villa's exporters write, the .afv before
villa #2316 and its object store since, which the chain skips (a local CT crop has no open-data volume to bind). Where
a run has a fibers.afv, its tiles must give the same fibers. A run counts once the chain logged it DONE.

    nice -n 19 .venv/bin/python scripts/villa_seed_heading_rerun.py --work W [--out JSON]

The record is named by the villa commit its chain ran (reports/evidence/villa_volume_seed_heading_rerun_<commit>_
from_tiles.json) and is never replaced: the draft cites each commit's record, 322cb0899's among them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_ct_context as cc  # noqa: E402

CUBES = ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")
SOURCE = {
    "before": cc.T
    / "ct_context_run/neural",  # finding 97: villa ccb431818, the skip in place
    "after": cc.T / "steep_heading_run/keep",  # finding 100's keep arm at ccb431818
}
COUNTS = ("dots", "no_heading", "traced", "fibers")
ROW = ("coverage", "precision", "erl_merge_penalized")


def counts(run: Path) -> dict:
    """tiles.jsonl's seed counts, summed over each tile's last line."""
    lines = [json.loads(s) for s in (run / "tiles.jsonl").read_text().splitlines() if s.strip()]  # fmt: skip
    tiles = {t["tile"]: t for t in lines}
    return {k: int(sum(t.get(k, 0) for t in tiles.values())) for k in COUNTS}


def tile_fibers(run: Path) -> dict[int, np.ndarray]:
    """Fiber id -> (N, 3) float64 xyz in the traced CT's voxels: each finished tile's points times run.json's
    grid_scale, as villa's exporters write them. Interrupted tiles (*.partial.npz) are not finished."""
    scale = float(json.loads((run / "run.json").read_text())["grid_scale"])
    out: dict[int, np.ndarray] = {}
    for f in sorted((run / "tiles").glob("*.npz")):
        if f.name.endswith(".partial.npz"):
            continue
        with np.load(f, allow_pickle=False) as d:
            offsets, ids, points = d["offsets"], d["id"], d["points"]
            for k, (a, b) in enumerate(zip(offsets[:-1], offsets[1:], strict=True)):
                fid = int(ids[k])
                if fid in out:
                    raise ValueError(f"{run}: fiber {fid} in two tiles")
                out[fid] = points[a:b].astype(np.float64) * scale
    if not out:
        raise SystemExit(f"no finished tiles: {run}")
    return out


def same_fibers(a: dict, b: dict) -> bool:
    """The same fibers point for point, whatever their ids (finding 93's smoke comparison)."""

    def key(fibers):
        return sorted(np.ascontiguousarray(v, "<f8").tobytes() for v in fibers.values())

    return key(a) == key(b)


def run_fibers(run: Path) -> dict:
    """The run's tile fibers, and whether they are its fibers.afv's (None: no .afv)."""
    fibers = tile_fibers(run)
    match = None
    if (run / "fibers.afv").exists():
        afv = afv_to_labels.read_afv(run / "fibers.afv")
        match = sorted(afv) == sorted(fibers) and same_fibers(afv, fibers)
        if not match:
            raise SystemExit(f"{run}: fibers.afv differs from its tiles")
    return {"fibers": fibers, "tiles_match_afv": match}


def logged_done(work: Path, side: str, cube: str) -> bool:
    """The chain logged the run DONE (it traced and exited 0)."""
    return (
        re.search(rf"^DONE {side} {cube}\s", (work / "chain.log").read_text(), re.M)
        is not None
    )


def villa_commit(work: Path) -> str:
    m = re.findall(r"^CHAIN_START repo \S+ villa (\w+)", (work / "chain.log").read_text(), re.M)  # fmt: skip
    if len(set(m)) != 1:
        raise SystemExit(f"chain.log names no single villa commit: {m}")
    return m[0]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument(
        "--out", type=Path, help="default: named by the chain's villa commit"
    )
    a = ap.parse_args(argv)
    villa = villa_commit(a.work)
    if a.out is None:
        a.out = Path(f"reports/evidence/villa_volume_seed_heading_rerun_{villa}_from_tiles.json")  # fmt: skip
    if a.out.exists():
        raise SystemExit(
            f"{a.out} exists: each villa commit's record is kept; pass a new --out"
        )
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(f"the draft is scored with ScrollGT scoring version 3, found {SCORING_VERSION}")  # fmt: skip
    runs: dict = {}
    fibers: dict = {}
    for side, src in SOURCE.items():
        for c in CUBES:
            new = a.work / side / c
            if not logged_done(a.work, side, c):
                raise SystemExit(f"no run: {new}")
            got, source = run_fibers(new), run_fibers(src / c)
            fibers[side, c] = got["fibers"]
            skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
            size = int(c.rsplit("_", 1)[1])
            row = score_tracing(skel, cc.labels_of_fibers(got["fibers"], cc.MARGIN, size), tolerance=2.0).as_row()  # fmt: skip
            runs.setdefault(side, {})[c] = {
                "identical_to_source": same_fibers(got["fibers"], source["fibers"]),
                "tiles_match_afv": got["tiles_match_afv"],
                "source_tiles_match_afv": source["tiles_match_afv"],
                "counts": counts(new),
                "source_counts": counts(src / c),
                "row_tol2": {k: row[k] for k in ROW},
            }
    same = all(r["identical_to_source"] for s in runs.values() for r in s.values())
    # the comparison's control: the patch changes the traces, so before and after must differ
    control = {c: same_fibers(fibers["before", c], fibers["after", c]) for c in CUBES}
    out = {
        "status": "IDENTICAL" if same and not any(control.values()) else "DIFFERS",
        "before_identical_to_after": control,
        "villa": villa,
        "source_villa": "ccb431818",
        "sources": {k: str(v) for k, v in SOURCE.items()},
        "fibers_from": "tiles",
        "scoring_version": SCORING_VERSION,
        "tolerance": 2.0,
        "runs": runs,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
