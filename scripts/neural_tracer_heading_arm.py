"""villa's neural fiber volume tracer with one change: what it does with a seed dot whose CT axis misses the dot's
presence direction.

villa's tracing/volume.py (ccb431818) gives each seed dot the CT sheet's axis for its fiber family (`ct_seed_heading`:
an H fiber along the sheet's horizontal line, a V fiber up the sheet), signed along the dot's presence direction, and
skips the dot when that axis lies more than 35 degrees from the presence direction (`_seed_heading`). Finding 99
(reports/neural_tracer_heading_residual.md) found that skip behind every classified drop with the scan around the cube.
Training never applies it: villa's training seeds take the CT axis whatever the fiber's tangent (data/seeds.py,
data/targets.py), skipping only when the CT gives no axis.

`--arm` sets what happens to a dot whose CT axis lies more than 35 degrees from its presence direction:
* `villa`: skipped, as villa does (the launcher's identity smoke);
* `keep`: traced from villa's own CT axis, signed along the presence direction, as training seeds are;
* `sheet`: traced from the presence direction projected into the CT's sheet (the plane normal to villa's own
  `ct_normal`), which follows the sheet and points along the fiber the presence shows. Only a projection shorter than
  villa's own ambiguity floor (1e-3, `sheet_heading`) is skipped.
Every other dot, and every other step, is villa's: the same `ct_normal` and `sheet_heading` calls in the same worker
processes, the same order and chunking.

As a launcher, in villa's tracer environment (repro/fibers/setup_neural_tracer_env.sh):

    python scripts/neural_tracer_heading_arm.py --arm ARM <villa volume arguments>

runs villa's own main() with `seed_headings` replaced. villa's axis workers are spawned processes; they import this
module by name (its directory is on the path they inherit) and read villa's own `_WORKER_VOL`, which villa's
initializer sets. OUT/heading_arm.json records the arm and, at the end, how each offered dot was headed; a resume
with another arm is refused here, and by villa, whose run.json records the arm in its seed-heading policy.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ARMS = ("villa", "keep", "sheet")
# villa's `if abs(h @ direction) < np.cos(np.radians(35)): return None`
AGREE_COS = np.cos(np.radians(35))
# villa's sheet_heading: `if size < 1e-3: raise SeedHeadingError(...)`
DEGENERATE = 1e-3
FAR_OUT_OF_SHEET = 45.0  # degrees; counted, never acted on
POLICY_SUFFIX = {"keep": "+keep_ct_axis_v1", "sheet": "+presence_in_sheet_v1"}
KINDS = ("agree", "skipped", "rescued", "rescued_far", "degenerate", "error")


def choose(h, normal, direction, arm: str):
    """(heading or None, kind) for one dot: h is villa's CT axis for its family, normal the CT sheet normal it came
    from, direction the dot's presence direction. Where h agrees with the direction, villa's own signed heading."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    if abs(h @ direction) >= AGREE_COS:
        return (h if h @ direction > 0 else -h), "agree"
    if arm == "villa":
        return None, "skipped"
    if arm == "keep":
        return (h if h @ direction > 0 else -h), "rescued"
    d = np.asarray(direction, np.float64) / np.linalg.norm(direction)
    p = d - (d @ normal) * normal
    size = float(np.linalg.norm(p))
    if size < DEGENERATE:
        return None, "degenerate"
    far = size < np.cos(np.radians(FAR_OUT_OF_SHEET))
    return p / size, ("rescued_far" if far else "rescued")


def arm_heading(task):
    """villa's `_seed_heading`, in its axis worker, with the arm's rule for a disagreeing dot."""
    from vesuvius.neural_tracing.tracers.fibers.frames.ct import (
        ct_normal,
        sheet_heading,
    )
    from vesuvius.neural_tracing.tracers.fibers.tracing import volume
    from vesuvius.neural_tracing.tracers.shared.ct_structure import SeedHeadingError

    xyz, family, direction, arm = task
    try:
        # villa's ct_seed_heading(vol, pos, family) is sheet_heading(ct_normal(vol, pos), family)
        normal = ct_normal(volume._WORKER_VOL, xyz)
        h = sheet_heading(normal, family)
    except SeedHeadingError:
        return None, "error"
    return choose(h, normal, direction, arm)


def patched_seed_headings(arm: str, tally: Counter, fn=None):
    """villa's `seed_headings`, line for line, mapping the arm's heading over villa's own pool."""
    fn = arm_heading if fn is None else fn

    def seed_headings(vol, dots, pool):
        tasks = [
            (x, f, d, arm)
            for x, f, d in zip(
                dots["xyz"], dots["family"], dots["direction"], strict=False
            )
        ]
        results = list(pool.map(fn, tasks, chunksize=max(1, len(tasks) // 32)))
        tally.update(kind for _, kind in results)
        heads = [h for h, _ in results]
        keep = np.array([h is not None for h in heads], bool)
        out = {k: v[keep] for k, v in dots.items()}
        out["heading"] = np.asarray([h for h in heads if h is not None]).reshape(-1, 3)
        return out, keep

    return seed_headings


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
    """OUT/heading_arm.json, beside villa's run.json; a resume must use the same arm."""
    rec = {
        "arm": arm,
        "agree_degrees": 35.0,
        "degenerate": DEGENERATE,
        "launcher": "scripts/neural_tracer_heading_arm.py",
    }
    path = Path(out) / "heading_arm.json"
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


def main(argv: list[str] | None = None) -> int:
    arm, rest = split_argv(sys.argv[1:] if argv is None else argv)
    # By its module name, so the function the axis workers unpickle is this module's, not __main__'s.
    import neural_tracer_heading_arm as arms
    from vesuvius.neural_tracing.tracers.fibers.tracing import volume as vol

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--out", required=True)
    out = Path(ap.parse_known_args(rest)[0].out)
    rec = arms.record_arm(out, arm)
    tally: Counter = Counter()
    saved = vol.seed_headings, vol.SEED_HEADING_POLICY
    vol.seed_headings = arms.patched_seed_headings(arm, tally)
    vol.SEED_HEADING_POLICY = saved[1] + POLICY_SUFFIX.get(arm, "")
    try:
        rc = vol.main(rest) or 0
    finally:
        vol.seed_headings, vol.SEED_HEADING_POLICY = saved
    rec["offered"] = {k: tally[k] for k in KINDS}
    (out / "heading_arm.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
