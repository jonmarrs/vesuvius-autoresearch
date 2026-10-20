"""Exploratory, after finding 92's registered result: where the pitch-matched run lost its fibers.

villa's volume tracer appends one line of counters per finished tile to OUT/tiles.jsonl (seed dots, dots skipped for
having no CT heading or lying on a written fiber, traces, traced and kept grid voxels, stop reasons). Summed per cube
for finding 91's native run and finding 92's 9.6 um run, they show at which step the fibers go. A pitch-run grid voxel
is r = 9.6 / 7.91 times longer, so voxel counts are compared in physical length. Writes
reports/neural_tracer_pitch_funnel.json.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_pitch_analysis as pa  # noqa: E402

COUNTERS = (
    "dots",
    "owned_dots",
    "no_heading",
    "traced",
    "traced_vox",
    "kept_vox",
    "fibers",
    "stop_confidence",
    "stop_owned_or_live",
    "stop_bounds",
)


def tile_totals(run: Path) -> dict[str, int]:
    """Each counter summed over the run's tiles, a tile finished twice counting by its last line."""
    last = {}
    for line in (run / "tiles.jsonl").read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            last[d["tile"]] = d
    return {k: sum(d.get(k, 0) for d in last.values()) for k in COUNTERS}


def funnel(native: dict, pitch: dict, r: float = pa.R) -> dict:
    """Pitch-run over native for each step; (native, pitch) pairs for the shares."""

    def pair(num, den):
        return (native[num] / native[den], pitch[num] / pitch[den])

    return {
        "dots": pitch["dots"] / native["dots"],
        "no_heading_share": pair("no_heading", "dots"),
        "owned_share": pair("owned_dots", "dots"),
        "traces": pitch["traced"] / native["traced"],
        "grid_vox_per_trace": pair("traced_vox", "traced"),
        "physical_traced": r * pitch["traced_vox"] / native["traced_vox"],
        "kept_share": pair("kept_vox", "traced_vox"),
        "physical_kept": r * pitch["kept_vox"] / native["kept_vox"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--native",
        type=Path,
        required=True,
        help="finding 91's work dir (one subdir per cube)",
    )
    ap.add_argument("--pitch", type=Path, required=True, help="finding 92's work dir")
    ap.add_argument(
        "--rows", type=Path, default=Path("reports/neural_tracer_pitch.json")
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_pitch_funnel.json")
    )
    args = ap.parse_args()
    d = json.loads(args.rows.read_text())
    cubes = {}
    for c in f91.ALL:
        nat, pit = tile_totals(args.native / c), tile_totals(args.pitch / c)
        f = funnel(nat, pit)
        pen = d["pitch_rows"][c][pa.PEN] / d["native_rows"][c][pa.PEN]
        cov = d["pitch_rows"][c][pa.COV] / d["native_rows"][c][pa.COV]
        cubes[c] = {
            "native": nat,
            "pitch": pit,
            "funnel": f,
            "pen_ratio": pen,
            "coverage_ratio": cov,
        }
    med = statistics.median
    summary = {
        k: med(v["funnel"][k] for v in cubes.values())
        for k in ("dots", "traces", "physical_traced", "physical_kept")
    }
    for k in ("no_heading_share", "owned_share", "grid_vox_per_trace", "kept_share"):
        summary[k] = [med(v["funnel"][k][i] for v in cubes.values()) for i in (0, 1)]
    out = {
        "status": "exploratory, after the registered result",
        "ratio": pa.R,
        # work dirs as finding 92 names them (spiral_out/neural_tracer/...), not machine paths
        "sources": {
            "native": "/".join(args.native.resolve().parts[-3:]),
            "pitch": "/".join(args.pitch.resolve().parts[-3:]),
            "rows": str(args.rows),
        },  # fmt: skip
        "cubes": cubes,
        "summary": summary,
        "groups": {
            "in_sample": f91.IN_SAMPLE,
            "s3": f91.S3,
            "s5_held_out": f91.S5_HELDOUT,
        },
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
