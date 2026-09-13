"""Apply the per-arm winding-identity gate to every ablated arm, mechanically.

`docs/preregistration/2026-09-12_anchor_ablation.md` requires each ablated arm to
be checked against `curbase_s1`, and any arm whose winding numbering shifted to be
**excluded and reported as excluded**. Done by hand that is three commands whose
results have to be remembered, and the failure mode is not an error -- it is an
arm quietly analysed as if it had passed.

So this runs the check for all of them, decides pass/fail by the registered rule,
and prints the exact `analyse_anchor_ablation.py` invocation with `--excluded`
already populated. The exclusion cannot be forgotten because the command that
does the analysis is generated from the gate result.

Registered rule, not reinterpretable here:
  * every winding in the strip must match at offset 0;
  * the winner must beat the runner-up in at least 9 of 10 windings.
Anything else is a FAIL for that arm.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REF_ARM = "curbase_s1"
ABLATED = ("anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3")
STRIP = "120-129"
MIN_POSITIVE_MARGINS = 9


def mesh_root(spiral_out: Path, tag: str) -> Path | None:
    hits = sorted(spiral_out.glob(f"*patch_{tag}/meshes/fitted_{tag}"))
    return hits[0] if hits else None


def metrics_for(spiral_out: Path, tag: str) -> tuple[Path | None, Path | None]:
    m = spiral_out / f"outer_{tag}" / "ink_metric" / "metrics.json"
    s = spiral_out / f"outer_{tag}" / "satisfaction_metrics_fitted.json"
    if not s.is_file():
        cand = sorted(spiral_out.glob(f"*patch_{tag}/satisfaction_metrics_fitted.json"))
        s = cand[0] if cand else None
    return (m if m.is_file() else None), (s if s and s.is_file() else None)


def run_gate(repo: Path, spiral_out: Path, tag: str, ref_root: Path) -> dict:
    alt_root = mesh_root(spiral_out, tag)
    if alt_root is None:
        return {"arm": tag, "state": "NOT FITTED"}
    out = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts/measure_winding_identity.py"),
            "--ref-meshes",
            str(ref_root),
            "--ref-tag",
            REF_ARM,
            "--alt-meshes",
            str(alt_root),
            "--alt-tag",
            tag,
            "--strip",
            STRIP,
            "--json",
            "/dev/stdout",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return {"arm": tag, "state": "GATE ERROR", "stderr": out.stderr[-400:]}
    # the tool writes json to the path given; parse the object out of stdout
    start = out.stdout.find("{")
    data = (
        json.loads(out.stdout[start : out.stdout.rfind("}") + 1]) if start >= 0 else {}
    )
    rows = data.get("rows", [])
    offsets_ok = bool(rows) and all(r["offset"] == 0 for r in rows)
    positive = sum(1 for r in rows if (r["runner_up_dist"] - r["dist"]) > 0)
    passed = offsets_ok and positive >= MIN_POSITIVE_MARGINS
    return {
        "arm": tag,
        "state": "PASS" if passed else "FAIL",
        "n_windings": len(rows),
        "offsets_all_zero": offsets_ok,
        "positive_margins": positive,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    spiral_out = Path(args.spiral_out)
    ref_root = mesh_root(spiral_out, REF_ARM)
    if ref_root is None:
        raise SystemExit(f"reference arm {REF_ARM} has no meshes under {spiral_out}")

    results = [run_gate(repo, spiral_out, t, ref_root) for t in ABLATED]

    print(f"per-arm winding-identity gate, reference {REF_ARM}, strip {STRIP}")
    print(f"{'arm':<22}{'state':<12}{'offsets 0':>11}{'margins>0':>11}")
    for r in results:
        if r["state"] in ("PASS", "FAIL"):
            print(
                f"{r['arm']:<22}{r['state']:<12}"
                f"{str(r['offsets_all_zero']):>11}{r['positive_margins']:>8}/"
                f"{r['n_windings']}"
            )
        else:
            print(f"{r['arm']:<22}{r['state']:<12}")

    excluded = [r["arm"] for r in results if r["state"] == "FAIL"]
    unfitted = [r["arm"] for r in results if r["state"] == "NOT FITTED"]
    passed = [r["arm"] for r in results if r["state"] == "PASS"]

    if unfitted:
        print(
            f"\nnot yet fitted: {', '.join(unfitted)} -- gate incomplete, do not analyse"
        )
        return 0
    if excluded:
        print(f"\nEXCLUDED by the gate: {', '.join(excluded)}")
        print("  These arms compare different papyrus. They are reported, not dropped.")
    if len(passed) < 3:
        print(
            f"\nonly {len(passed)} of 3 ablated arms passed; the registered rule refuses a "
            "partial sample. The study does not report a verdict."
        )
    else:
        print("\nall three ablated arms passed. Analysis invocation:")
        parts = []
        for tag in passed + ["curbase_s1", "curbase_s2", "curbase_s3"]:
            m, s = metrics_for(spiral_out, tag)
            parts.append(
                f"{tag}={m or '<metrics.json MISSING>'},{s or '<satisfaction MISSING>'}"
            )
        ex = f" --excluded {' '.join(excluded)}" if excluded else ""
        print(
            "\n  python scripts/analyse_anchor_ablation.py \\\n    "
            + " \\\n    ".join(parts)
            + ex
            + " \\\n    --out reports/anchor_ablation_verdict.json"
        )

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "reference": REF_ARM,
                    "strip": STRIP,
                    "results": results,
                    "excluded": excluded,
                    "passed": passed,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
