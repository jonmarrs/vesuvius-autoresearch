"""villa's neural fiber volume tracer with one change: a decision that would stop on confidence first retries once,
with its crop refit to its own prediction (villa's `TraceParams.refit_retry`).

villa's tracer (#2045; `tracing/trace.py` at ccb431818) has that retry, off by default: "a decision that would stop on
confidence first retries once at the same head with its crop refit to its own prediction (frames.learned.predicted_axis
over the gate horizon); only a second stop then ends the trace". The retry is reset after every advance
(`retried[i] = False`), so each stop along a trace gets one. villa's single-seed CLI exposes it
(`tracing/inference.py --refit-retry`). Its volume tracer (`tracing/volume.py`), which findings 91-102 ran, does not:
`build_tracer` builds `TraceParams.from_policy(...)` without it.

`--arm` sets it:
* `villa`: off, as villa runs (the launcher's identity smoke, and the floor arm);
* `refit`: on.
Every other setting is villa's.

As a launcher, in villa's tracer environment (repro/fibers/setup_neural_tracer_env.sh):

    python scripts/neural_tracer_refit_arm.py --arm ARM <villa volume arguments>

runs villa's own main() with `build_tracer` wrapped: the tracer it builds gets `refit_retry` set by the arm. OUT/
refit_arm.json records the arm and, at the end, the value the tracer held. villa's run.json does not record the
setting, so a resume with another arm is refused here.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

ARMS = ("villa", "refit")
LAUNCHER = "scripts/neural_tracer_refit_arm.py"


def split_argv(argv: list[str]) -> tuple[str, list[str]]:
    """(arm, villa's arguments). --arm once, spelled out: no villa option starts with --ar."""
    if sum(a.split("=", 1)[0].startswith("--ar") for a in argv) != 1 or not any(
        a == "--arm" or a.startswith("--arm=") for a in argv
    ):
        raise SystemExit("give --arm once, spelled out")
    ap = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    ap.add_argument("--arm", required=True, choices=ARMS)
    ns, rest = ap.parse_known_args(argv)
    return ns.arm, rest


def record_arm(out: Path, arm: str) -> dict:
    """OUT/refit_arm.json, beside villa's run.json; a resume must use the same arm."""
    rec = {"arm": arm, "refit_retry": arm == "refit", "launcher": LAUNCHER}
    path = Path(out) / "refit_arm.json"
    if not path.exists() and (Path(out) / "run.json").exists():
        raise SystemExit(f"{out} holds a run started without this launcher")
    if path.exists():
        old = json.loads(path.read_text())
        if {k: old.get(k) for k in rec} != rec:
            raise SystemExit(f"{path} records another arm: {old}, not {rec}")
        return old
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def wrapped_build_tracer(arm: str, fn, seen: dict):
    """villa's build_tracer, its tracer's rollout parameters then given the arm's refit_retry; `seen` records it."""

    def build_tracer(args):
        tracer, vol, spec, policy = fn(args)
        tracer.p = dataclasses.replace(tracer.p, refit_retry=arm == "refit")
        seen["refit_retry"] = bool(tracer.p.refit_retry)
        return tracer, vol, spec, policy

    return build_tracer


def main(argv: list[str] | None = None) -> int:
    arm, rest = split_argv(sys.argv[1:] if argv is None else argv)
    from vesuvius.neural_tracing.tracers.fibers.tracing import volume as vol

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--out", required=True)
    out = Path(ap.parse_known_args(rest)[0].out)
    rec = record_arm(out, arm)
    seen: dict = {}
    saved = vol.build_tracer
    vol.build_tracer = wrapped_build_tracer(arm, saved, seen)
    try:
        rc = vol.main(rest) or 0
    finally:
        vol.build_tracer = saved
    rec["in_effect"] = seen.get("refit_retry")
    (out / "refit_arm.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
