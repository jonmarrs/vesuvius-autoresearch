"""docs/preregistration/2026-10-16_neural_fiber_tracer_entrant.md -- the smoke run that precedes any cube: villa's
tracer, with the registered flags, on a synthetic 256^3 volume (noise plus a few bright tubes), not on ScrollGT data.

It checks the plumbing only: the tracer reads a local CT group and a presence level made by make_tracer_presence.py,
finishes, exports an .afv through a template, and the analysis can read that .afv (geometry, stop reasons) and passes
its run.json through the identity check. Nothing about the tracer's accuracy is learned or recorded.

Usage: .venv/bin/python scripts/neural_tracer_smoke.py --tracer-python T/venv/bin/python --template X.afv --out DIR
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_to_labels  # noqa: E402
import make_tracer_presence  # noqa: E402
import neural_tracer_analysis  # noqa: E402

NAME, SIZE = "smoke_256", 256


def synthetic(size: int = SIZE, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """uint8 CT (Z, Y, X) with bright tubes along x, y and z, and their probability (1 inside a tube)."""
    rng = np.random.default_rng(seed)
    ct = rng.normal(100, 12, (size, size, size)).clip(1, 255)
    prob = np.zeros((size, size, size), dtype=np.float32)
    z, y, x = np.ogrid[:size, :size, :size]
    for axis, (a, b) in [
        (2, (96, 96)),
        (2, (160, 120)),
        (1, (128, 80)),
        (0, (100, 150)),
    ]:
        # A tube along `axis` through (a, b) in the other two axes, radius 4.
        u, v = [(z, y, x)[i] for i in range(3) if i != axis]
        inside = (u - a) ** 2 + (v - b) ** 2 <= 16
        prob[np.broadcast_to(inside, prob.shape)] = 1.0
    ct[prob > 0] = 200
    return ct.astype(np.uint8), prob


def write_ct(ct: np.ndarray, store: Path) -> None:
    import zarr

    level = zarr.open(
        str(store / "0"), mode="w-", shape=ct.shape, chunks=(128,) * 3, dtype="u1"
    )
    level[...] = ct


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracer-python", type=Path, required=True)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    args.out.mkdir(parents=True)
    ct, prob = synthetic()
    write_ct(ct, args.out / f"{NAME}.zarr")
    np.save(args.out / "prob.npy", prob)
    presence = make_tracer_presence.write_presence(
        args.out / "prob.npy", args.out / f"{NAME}_presence.zarr"
    )
    g = int(SIZE / neural_tracer_analysis.SETTINGS["grid_scale"])
    run = args.out / NAME
    command = [
        str(args.tracer_python), "-m", "vesuvius.neural_tracing.tracers.fibers.tracing.volume",
        "--checkpoint", neural_tracer_analysis.SETTINGS["checkpoint"],
        "--ct", str(args.out / f"{NAME}.zarr"), "--ct-level", "0", "--ct-grid-scale", "1", "--grid-scale", "2",
        "--presence", str(presence), "--box", f"0,0,0,{g},{g},{g}", "--base-um", "7.91",
        "--afv-template", str(args.template), "--out", str(run),
    ]  # fmt: skip
    started = time.time()
    with (args.out / "tracer.log").open("w") as log:
        rc = subprocess.run(
            command, stdout=log, stderr=subprocess.STDOUT, cwd=args.out,
            env=dict(os.environ, HF_HUB_OFFLINE="1"),
        ).returncode  # fmt: skip
    seconds = time.time() - started
    report: dict = {"returncode": rc, "seconds": round(seconds, 1)}
    afv = run / "fibers.afv"
    if rc == 0 and afv.exists():
        fibers = afv_to_labels.read_afv(afv)
        report["fibers"] = len(fibers)
        report["points"] = int(sum(len(v) for v in fibers.values()))
        report["stop_reasons"] = neural_tracer_analysis.stop_reasons(afv)
        record = json.loads((run / "run.json").read_text())
        report["identity_problems"] = neural_tracer_analysis.identity_problems(
            record, NAME
        )
        report["recorded_operating_policy"] = record.get("operating_policy")
    (args.out / "smoke.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    ok = rc == 0 and report.get("fibers", 0) > 0 and not report.get("identity_problems")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
