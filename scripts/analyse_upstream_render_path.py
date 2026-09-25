"""Does villa's updated Python render stage change the ink score of FIXED meshes?

Implements `docs/preregistration/2026-09-25_upstream_render_path.md`. **Written, with
its tests, before any arm was rendered.**

One fit (`upfit_s1`, scored windings w120-w129) rendered three more times:

* `rpath_up_a`, `rpath_up_b` -- Python stage from villa `75c79ac5f` (lasagna flatten,
  tifxyz I/O, get_ink_metrics); same render image, same venv, deterministic flatten;
* `rpath_pin_a` -- the pinned `be09a8503` stage again, today.

Reference: `detfit_up1`, the same meshes on the pinned stage (09-24/25).

The meshes are identical in every arm, and the flatten is meant to be deterministic, so
the floor is near zero -- IF determinism holds on the new code. The shim uses
warn_only=True, so an op without a deterministic kernel would run stochastically without
failing. That is why the upstream stage is rendered twice.
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

SPIRAL_OUT = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
PIN = "be09a85035059fd83471b1632b5898c62f2c65b1"
UP = "75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3"
REF = "detfit_up1"
ARMS = {"rpath_up_a": UP, "rpath_up_b": UP, "rpath_pin_a": PIN, REF: PIN}
INK = "total_fg_pixels"
REPRO_TOL = 1e-4  # 0.01%: pinned deterministic re-renders agree to 0.0014%
INERT = 0.005  # |effect| below 0.5% is called inert (fit-only floor is ~7%)


def read_arm(work: Path) -> dict:
    ink = json.loads((work / "ink_metric" / "metrics.json").read_text())["summary"][INK]
    img = dict(
        line.split("=", 1)
        for line in (work / "RENDER_IMAGE").read_text().split()
        if "=" in line
    )
    return {
        "ink": float(ink),
        "villa_sha": (work / "VILLA_SHA").read_text().strip(),
        "image_id": img.get("image_id"),
        "flatten_deterministic": img.get("flatten_deterministic"),
    }


def rel(a: float, b: float) -> float:
    return a / b - 1.0


def decide(arms: dict[str, dict]) -> dict:
    missing = [a for a in ARMS if a not in arms]
    if missing:
        raise ValueError(f"partial sample refused: missing {missing}")
    fails = []
    for a, sha in ARMS.items():
        if arms[a]["villa_sha"] != sha:
            fails.append(f"{a}: tree {arms[a]['villa_sha']} != {sha}")
        if arms[a]["flatten_deterministic"] != "1":
            fails.append(f"{a}: flatten not deterministic")
    if len({r["image_id"] for r in arms.values()}) != 1:
        fails.append("render images differ across arms")
    if fails:
        return {"verdict": "INVALID", "failed_gates": fails}

    pin_repro = rel(arms["rpath_pin_a"]["ink"], arms[REF]["ink"])
    up_repro = rel(arms["rpath_up_b"]["ink"], arms["rpath_up_a"]["ink"])
    out = {"pin_reproducibility": pin_repro, "upstream_reproducibility": up_repro}
    if abs(pin_repro) > REPRO_TOL:
        return {
            **out,
            "verdict": "INVALID",
            "failed_gates": [
                f"pinned stage no longer reproduces detfit_up1 ({pin_repro:+.4%}): "
                "the environment drifted, so no comparison is attributable"
            ],
        }
    up = st.mean([arms["rpath_up_a"]["ink"], arms["rpath_up_b"]["ink"]])
    pin = st.mean([arms["rpath_pin_a"]["ink"], arms[REF]["ink"]])
    effect = rel(up, pin)
    floor = abs(up_repro)
    out.update({"effect": effect, "upstream_mean": up, "pinned_mean": pin})
    if floor > REPRO_TOL:
        # the new stage is stochastic: the effect must clear 3x its own repeat spread
        out["upstream_deterministic"] = False
        if abs(effect) > max(INERT, 3 * floor):
            out["verdict"] = "RENDER PATH CHANGES INK (upstream stage nondeterministic)"
        else:
            out["verdict"] = "NOT RESOLVED (upstream stage nondeterministic)"
        return out
    out["upstream_deterministic"] = True
    out["verdict"] = (
        "RENDER PATH INERT (within 0.5%)"
        if abs(effect) < INERT
        else "RENDER PATH CHANGES INK"
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spiral-out", type=Path, default=SPIRAL_OUT)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    arms = {a: read_arm(args.spiral_out / a) for a in ARMS}
    res = decide(arms)
    res["per_arm"] = {a: arms[a]["ink"] for a in ARMS}
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    print(res["verdict"])
    for k in ("effect", "pin_reproducibility", "upstream_reproducibility"):
        if k in res:
            print(f"  {k}: {res[k]:+.4%}")
    for f in res.get("failed_gates", []):
        print("  GATE FAILED:", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
