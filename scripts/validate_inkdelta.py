"""Validate inkdelta on this project's corpus. Implements
`docs/preregistration/2026-09-27_inkdelta_validation.md`. **Written, with every case's expected
verdict, before inkdelta was run on any real run directory.**

Each case states what a correct checker MUST say. The script exits non-zero on any disagreement and
writes every case's full output to reports/inkdelta_validation.json either way.
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

INKDELTA_SRC = Path("/home/jon/openclaw-workspace/Neo-VM/projects/inkdelta/src")
sys.path.insert(0, str(INKDELTA_SRC))
from inkdelta.compare import compare  # noqa: E402
from inkdelta.runs import load_run  # noqa: E402

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
DETFIT_LOG = SO / "detfit_chain.log"
UP_LOG = SO / "upstream_fitter_chain.log"
RPATH_LOG = SO / "upstream_render_path_chain.log"
BASE = [f"detfit_s{i}" for i in range(4, 10)]
UP = ["detfit_up1", "detfit_up2", "detfit_up3"]

# name -> (A dirs, A log, B dirs, B log, kwargs, expected verdict, extra expectation)
CASES = {
    "1_stale_slices_invalid": (["detfit_up1"], UP_LOG, ["smp_pub"], SO / "smp_pub.render.log",
                               {}, "INVALID", "STALE_SLICES on B"),
    "2_reproduces_finding_62": (BASE, DETFIT_LOG, UP, UP_LOG, {"build_a": "edge", "build_b": "edge"},
                                "NOT RESOLVED", "interval == +4.82% [-7.51%, +17.15%]"),
    "3_declared_route_incomparable": (["detfit_s4"], DETFIT_LOG, ["step2_s4"], SO / "step2_s4.render.log",
                                      {"build_a": "edge-0513", "build_b": "post-1146"}, "INCOMPARABLE", ""),
    "4_undeclared_route_single_runs": (["detfit_s4"], DETFIT_LOG, ["step2_s4"], SO / "step2_s4.render.log",
                                       {"cv": 0.074}, "NOT RESOLVED", "SAMPLER_BUILD_UNDECLARED warning"),
    "5_deterministic_repeats_pass": (["rpath_up_a"], RPATH_LOG, ["rpath_up_b"], RPATH_LOG,
                                     {"build_a": "edge", "build_b": "edge", "cv": 0.074}, "NOT RESOLVED",
                                     "|rel| < 0.01%"),
    "6_deliberate_rescore_flagged": (["detfit_up1"], UP_LOG, ["tif_score_pr1905"],
                                     SO / "tif_score_pr1905.render.log", {}, "INVALID", "STALE_SLICES on B"),
}  # fmt: skip


def run_case(name, spec):
    a_dirs, a_log, b_dirs, b_log, kw, expect, extra = spec
    a = [load_run(SO / d, a_log) for d in a_dirs]
    b = [load_run(SO / d, b_log) for d in b_dirs]
    res = compare(a, b, **kw)
    codes = {f.code for f in res.findings}
    ok = res.verdict == expect
    iv = res.interval or {}
    if name == "2_reproduces_finding_62":
        ok &= (round(iv.get("rel", 9), 4), round(iv.get("lo", 9), 4), round(iv.get("hi", 9), 4)) == (
            0.0482, -0.0751, 0.1715)  # fmt: skip
    if name in ("1_stale_slices_invalid", "6_deliberate_rescore_flagged"):
        ok &= "STALE_SLICES" in codes
    if name == "4_undeclared_route_single_runs":
        ok &= "SAMPLER_BUILD_UNDECLARED" in codes
    if name == "5_deterministic_repeats_pass":
        ok &= abs(iv.get("rel", 1)) < 1e-4 and not any(
            f.level == "FAIL" for f in res.findings
        )
    return ok, {"expected": expect, "extra": extra, "pass": ok, **asdict(res)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    results, all_ok = {}, True
    for name, spec in CASES.items():
        ok, rec = run_case(name, spec)
        results[name] = rec
        all_ok &= ok
        iv = rec.get("interval") or {}
        rel = f" {iv['rel']:+.2%}" if "rel" in iv else ""
        print(f"{'PASS' if ok else 'FAIL'}  {name:34s} -> {rec['verdict']}{rel}")
    args.out.write_text(
        json.dumps({"all_pass": all_ok, "cases": results}, indent=2, default=str) + "\n"
    )
    print("ALL PASS" if all_ok else "VALIDATION FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
