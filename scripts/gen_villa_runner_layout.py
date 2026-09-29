"""Drive villa's own spiral-fitting/runners/run_single.py with its fit/render/score subprocesses
stubbed, so the output layout inkdelta must read comes from villa's code, not from a reading of it.

Usage: git -C villa archive <ref> spiral-fitting/runners spiral-fitting/config.py | tar -x -C X
       python scripts/gen_villa_runner_layout.py X/spiral-fitting OUT
Writes OUT/single (no --seeds), OUT/base (--seeds 1,2,3) and OUT/change (--seeds 11,12,13)."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

SF = Path(sys.argv[1])  # extracted spiral-fitting/
OUT = Path(sys.argv[2])
sys.path.insert(0, str(SF / "runners"))
sys.path.insert(0, str(SF))
import run_single  # noqa: E402

FG = {
    None: 3_279_498,
    1: 3_300_000,
    2: 3_100_000,
    3: 3_450_000,
    11: 3_500_000,
    12: 3_650_000,
    13: 3_600_000,
}


def fake_run(command, *, check, env):
    script = next(Path(p).name for p in command if str(p).endswith(".py"))
    if script == "fit_spiral.py":
        out = Path(env["FIT_SPIRAL_OUT_DIR"])
        (
            out / "2026-09-29_PHercParis4_slice-0-100_10-patch" / "meshes" / "fitted"
        ).mkdir(parents=True)
        hist = env.get("FIT_SPIRAL_METRICS_HISTORY")
        if hist:
            Path(hist).write_text(
                json.dumps({"iteration": 0, "metrics": {"loss": 1.0}}) + "\n"
            )
    elif script == "render_ink.py":
        ink = Path(command[2]) / "ink"
        ink.mkdir()
        (ink / "w001-002_flat.000.jpg").touch()
    elif script == "get_ink_metrics.py":
        fitted = Path(command[2]).parent
        seed = CURRENT["seed"]
        (fitted / "ink_metric").mkdir()
        summary = {
            "model": "nnunet",
            "model_dir": "/hf/snapshots/abc123",
            "checkpoint": "final",
            "folds": [0, 1, 2, 3, 4],
            "fg_threshold": 0.5,
            "total_fg_pixels": FG[seed],
        }
        (fitted / "ink_metric" / "metrics.json").write_text(
            json.dumps({"summary": summary})
        )
    return SimpleNamespace(returncode=0)


CURRENT = {"seed": None}
orig_pipeline = run_single.run_pipeline


def tracking_pipeline(args, *, output, **kw):
    name = output.name
    CURRENT["seed"] = int(name.split("-", 1)[1]) if name.startswith("seed-") else None
    return orig_pipeline(args, output=output, **kw)


run_single.subprocess.run = fake_run
run_single.run_pipeline = tracking_pipeline

for sub, extra in (
    ("single", []),
    ("base", ["--seeds", "1,2,3"]),
    ("change", ["--seeds", "11,12,13"]),
):
    argv = [
        "--dataset",
        str(OUT / "ds"),
        "--ink-volume",
        str(OUT / "vol"),
        "--output",
        str(OUT / sub),
        "--no-wandb",
        *extra,
    ]
    (OUT / "ds").mkdir(parents=True, exist_ok=True)
    (OUT / "vol").mkdir(parents=True, exist_ok=True)
    args = run_single.build_parser().parse_args(argv)
    run_single.run(args)
print("ok")
