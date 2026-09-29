"""What villa's runners/run_single.py passes to fit_spiral.py, with and without --gpus.

Run with CUDA_VISIBLE_DEVICES, FIT_SPIRAL_RUN_TAG and FIT_SPIRAL_OUT_DIR set, as autoresearch.md
says to launch it. Result at villa 6e53201ac: without --gpus the fit is ONE process (no torchrun)
although four devices are visible; FIT_SPIRAL_OUT_DIR is overridden by --output; the tag passes.

Usage: python scripts/probe_villa_runner_gpus.py <extracted spiral-fitting/> <scratch out>
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

SF = Path(sys.argv[1])
OUT = Path(sys.argv[2])
sys.path[:0] = [str(SF / "runners"), str(SF)]
import run_single

seen = []


def fake_run(command, *, check, env):
    script = next(Path(p).name for p in command if str(p).endswith(".py"))
    if script == "fit_spiral.py":
        seen.append(
            {
                "cmd": command[:5],
                "CVD": env.get("CUDA_VISIBLE_DEVICES"),
                "TAG": env.get("FIT_SPIRAL_RUN_TAG"),
                "OUT": env.get("FIT_SPIRAL_OUT_DIR"),
            }
        )
        (Path(env["FIT_SPIRAL_OUT_DIR"]) / "d" / "meshes" / "fitted").mkdir(
            parents=True
        )
    elif script == "render_ink.py":
        (Path(command[2]) / "ink").mkdir()
        (Path(command[2]) / "ink" / "x.jpg").touch()
    else:
        m = Path(command[2]).parent / "ink_metric"
        m.mkdir()
        (m / "metrics.json").write_text(json.dumps({"summary": {"total_fg_pixels": 1}}))
    return SimpleNamespace(returncode=0)


run_single.subprocess.run = fake_run
for name, extra in (("no_gpus", []), ("gpus", ["--gpus", "0,1,2,3"])):
    (OUT / "ds").mkdir(parents=True, exist_ok=True)
    a = run_single.build_parser().parse_args(
        [
            "--dataset",
            str(OUT / "ds"),
            "--ink-volume",
            str(OUT / "ds"),
            "--output",
            str(OUT / name),
            "--no-wandb",
            *extra,
        ]
    )
    run_single.run(a)
    print(name, seen[-1])
