"""docs/VILLA_DRAFT_volume_seed_heading.md, "Before posting" step 3: does villa's tracer at a later commit, with and
without the patch, give what the draft measured at ccb431818?

repro/fibers/run_villa_seed_heading_rerun.sh traces the two held-out Scroll-5 cubes with villa's own CLI at a later
villa commit: `before` unpatched, `after` with repro/fibers/villa_volume_seed_heading.patch. This compares each run
point for point with the draft's source run (`before` with finding 97's villa run, `after` with finding 100's `keep`
arm), adds the runs' seed counts, and scores every run with ScrollGT's fiber scorer (version 3, tolerance 2) as
findings 97 and 100 scored theirs, so a run that differs still has its numbers.

    nice -n 19 .venv/bin/python scripts/villa_seed_heading_rerun.py --work W [--out JSON]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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


def villa_commit(work: Path) -> str:
    m = re.findall(r"^CHAIN_START repo \S+ villa (\w+)", (work / "chain.log").read_text(), re.M)  # fmt: skip
    if len(set(m)) != 1:
        raise SystemExit(f"chain.log names no single villa commit: {m}")
    return m[0]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/evidence/villa_volume_seed_heading_rerun.json"),
    )
    a = ap.parse_args(argv)
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(f"the draft is scored with ScrollGT scoring version 3, found {SCORING_VERSION}")  # fmt: skip
    runs: dict = {}
    for side, src in SOURCE.items():
        for c in CUBES:
            new = a.work / side / c
            if not (new / "fibers.afv").exists():
                raise SystemExit(f"no run: {new}")
            skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
            size = int(c.rsplit("_", 1)[1])
            row = score_tracing(skel, cc.labels_in_cube(new / "fibers.afv", cc.MARGIN, size), tolerance=2.0).as_row()  # fmt: skip
            runs.setdefault(side, {})[c] = {
                "identical_to_source": cc.f96_afv_identical(
                    new / "fibers.afv", src / c / "fibers.afv"
                ),
                "counts": counts(new),
                "source_counts": counts(src / c),
                "row_tol2": {k: row[k] for k in ROW},
            }
    same = all(r["identical_to_source"] for s in runs.values() for r in s.values())
    # the comparison's control: the patch changes the traces, so before and after must differ
    control = {
        c: cc.f96_afv_identical(
            a.work / "before" / c / "fibers.afv", a.work / "after" / c / "fibers.afv"
        )
        for c in CUBES
    }
    out = {
        "status": "IDENTICAL" if same and not any(control.values()) else "DIFFERS",
        "before_identical_to_after": control,
        "villa": villa_commit(a.work),
        "source_villa": "ccb431818",
        "sources": {k: str(v) for k, v in SOURCE.items()},
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
