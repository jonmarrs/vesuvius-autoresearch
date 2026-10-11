"""Snapshot the in-sample rows finding 83 compares against: ScrollGT's 11 fiber targets on the current annotations.

Reads each target's meta.json from a ScrollGT checkout (0.5.0 or later) and records the commit it came from.

Usage: .venv/bin/python scripts/fiber_heldout_in_sample_rows.py [--scrollgt DIR] [--out reports/fiber_heldout_in_sample_rows.json]
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

CC, TRACER = "floor_connected_components", "tracer_strict_relink"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--scrollgt",
        type=Path,
        default=Path("/home/jon/openclaw-workspace/Neo-VM/projects/scrollgt"),
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/fiber_heldout_in_sample_rows.json")
    )
    args = ap.parse_args()
    commit = subprocess.run(["git", "-C", str(args.scrollgt), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()  # fmt: skip
    cubes = {}
    for d in sorted((args.scrollgt / "data").glob("fibers_*")):
        m = json.loads((d / "meta.json").read_text())
        nml = m["ground_truth"].get("nml", {})
        if not nml.get("dataset", "").startswith("Dataset004"):
            raise SystemExit(
                f"{d.name}: no Dataset004 provenance; needs ScrollGT 0.5.0"
            )
        cubes[m["cube"]] = {
            "scroll": m["scroll"],
            "size_class": m["size_class"],
            "n_fibers_scored": m["ground_truth"]["n_fibers_scored"],
            "mask_density": m["mask"]["density"],
            "mask_enrichment": m["convention_check"]["landing_enrichment_vs_chance"],
            "rows": {
                "oracle": m["floors"]["oracle"],
                CC: m["floors"][CC],
                "tracer": m["floors"][TRACER],
            },
        }
    out = {"scrollgt_commit": commit, "cubes": cubes}
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(cubes)} targets from ScrollGT {commit[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
