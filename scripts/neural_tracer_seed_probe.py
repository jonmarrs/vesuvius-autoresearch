"""Exploratory, after finding 92: how many seed dots villa's volume tracer finds with its seeding set per micrometre.

villa's tile_dots (tracing/volume.py at ccb431818) seeds a tile from its presence: dots in planes (--plane-spacing,
--dot-radius) and fill-in 3D maxima (--fill-spacing), after smoothing the presence at sigma 1 grid voxel, each dot's
direction from a Hessian at sigma 1.5. The two sigmas are fixed in code, and a 9.6 um grid voxel is r = 9.6 / 7.91 times
longer than a native one. This calls tile_dots itself (CPU only: no CT, no network) on each cube's presence:

  A: finding 92's 9.6 um presence, seeded per micrometre as natively (each scale / r);
  B: finding 91's native presence, seeded per micrometre as at 9.6 um (each scale * r);

first at the run's own settings, which must reproduce the `dots` its tiles.jsonl recorded, then with the two spacing
flags scaled, then the smoothing too, then the Hessian too (scripts/neural_tracer_seeding.py). Each cube is one tile.
--dot-radius stays at 2: the window is a whole number of voxels. Runs in villa's tracer environment
(repro/fibers/setup_neural_tracer_env.sh). Writes reports/neural_tracer_seed_probe.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_seeding as sd  # noqa: E402

T = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer")
R = 9.6 / 7.91  # resample_cube_pitch: TO_UM / FROM_UM, as finding 92


def variants(arm: str, run: dict, r: float = R) -> dict[str, dict]:
    """Seeding settings to count, in order: the run's own, then each scale moved by r (arm A divides, B multiplies)."""
    f = 1 / r if arm == "A" else r
    own = {"plane_spacing": run["plane_spacing"], "fill_spacing": run["fill_spacing"], "smoothing": sd.VILLA_SMOOTHING,
           "hessian": None}  # fmt: skip
    flags = {
        **own,
        "plane_spacing": own["plane_spacing"] * f,
        "fill_spacing": own["fill_spacing"] * f,
    }
    return {
        "run": own,
        "flags": flags,
        "flags_smooth": {**flags, "smoothing": sd.VILLA_SMOOTHING * f},
        "flags_smooth_hessian": {
            **flags,
            "smoothing": sd.VILLA_SMOOTHING * f,
            "hessian": sd.VILLA_HESSIAN * f,
        },
    }


def recorded_dots(run: Path) -> int:
    """Seed dots the run recorded, a tile finished twice counting by its last line."""
    last = {}
    for line in (run / "tiles.jsonl").read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            last[d["tile"]] = d
    return sum(d["dots"] for d in last.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--native", type=Path, default=T / "run", help="finding 91's work dir"
    )
    ap.add_argument(
        "--pitch", type=Path, default=T / "pitch_run", help="finding 92's work dir"
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_seed_probe.json")
    )
    args = ap.parse_args()
    import numpy as np
    import zarr
    from vesuvius.neural_tracing.tracers.fibers.tracing import volume as vol

    cubes = {}
    for c in sorted(
        p.name for p in args.native.iterdir() if (p / "tiles.jsonl").exists()
    ):
        row = {
            "native_dots": recorded_dots(args.native / c),
            "pitch_dots": recorded_dots(args.pitch / c),
        }
        for arm, run in (("A", args.pitch / c), ("B", args.native / c)):
            rec = json.loads((run / "run.json").read_text())
            lo, hi = np.array(rec["box"]["lo"]), np.array(rec["box"]["hi"])
            assert np.all(hi - lo <= rec["tile"]), f"{c}: more than one tile"
            presence = zarr.open(rec["presence"], mode="r")
            row[arm] = {}
            for name, v in variants(arm, rec).items():
                ns = argparse.Namespace(threshold=rec["threshold"], dot_radius=rec["dot_radius"],
                                        plane_spacing=v["plane_spacing"], fill_spacing=v["fill_spacing"])  # fmt: skip
                with sd.seeding_scaled(vol, v["smoothing"], v["hessian"]):
                    d = vol.tile_dots(presence, lo, hi, ns)
                n = 0 if d is None else len(d["xyz"])
                fill = 0 if d is None else int((d["plane"] == "fill").sum())
                row[arm][name] = {**v, "dots": n, "fill_dots": fill}
        cubes[c] = row
        print(c, row["native_dots"], row["pitch_dots"],
              {a: {k: v["dots"] for k, v in row[a].items()} for a in "AB"}, flush=True)  # fmt: skip
    out = {
        "status": "exploratory, after finding 92's registered result",
        "ratio": R,
        "villa": "ccb431818",
        "sources": {
            "native": "/".join(args.native.resolve().parts[-3:]),
            "pitch": "/".join(args.pitch.resolve().parts[-3:]),
        },  # fmt: skip
        "cubes": cubes,
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
