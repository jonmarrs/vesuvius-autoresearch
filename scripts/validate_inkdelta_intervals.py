"""Second inkdelta validation: reproduce every registered replicated interval. Implements
`docs/preregistration/2026-09-27_inkdelta_registered_intervals.md`. **Written, with every case's
expected values, before inkdelta was run on any of these arms.**

Exits non-zero on any disagreement and writes every case's full output to
reports/inkdelta_registered_intervals.json either way.
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
BASE6 = ["baseline01", "seed02", "seed03", "seed04", "seed05", "seed06"]
CURBASE = ["curbase_s1", "curbase_s2", "curbase_s3"]
BOOT = ["boot090s1", "boot090s2", "boot090s3"]

# name -> (A tags, B tags, required verdict, (rel, lo, hi) to 4 d.p., df to 2 d.p.)
CASES = {
    "1_gap_expander": (BASE6, ["gap133"] + [f"gap133s{i}" for i in range(2, 7)],
                       "RESOLVED (-)", (-0.1035, -0.1568, -0.0503), 8.89),
    "2_patch_bootstrap": (["rand090s1", "rand090s2", "rand090s3"], BOOT,
                          "NOT RESOLVED", (-0.0083, -0.1835, 0.1669), 3.11),
    "3_stripmatch": (BOOT, ["strip090s1", "strip090s2", "strip090s3"],
                     "NOT RESOLVED", (-0.0380, -0.2073, 0.1314), 3.56),
    "4_samewinding_pinned": (BASE6, ["nosame_s1", "nosame_s2", "nosame_s3"],
                             "NOT RESOLVED", (-0.0174, -0.1027, 0.0679), 4.41),
    "5_samewinding_current": (CURBASE, ["nosamecur_s1", "nosamecur_s2", "nosamecur_s3"],
                              "NOT RESOLVED", (0.0028, -0.0256, 0.0313), 4.00),
    "6_anchor_ablation": (CURBASE, ["anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3"],
                          "NOT RESOLVED", (-0.0086, -0.1021, 0.0850), 2.35),
}  # fmt: skip


def run(tag):
    d = SO / f"outer_{tag}"
    log = next(
        (
            p
            for p in (SO / f"{d.name}.render.log", SO / f"{d.name}_render.log")
            if p.is_file()
        ),
        None,
    )
    return load_run(d, log)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/inkdelta_registered_intervals.json")
    args = ap.parse_args()
    rows, n_fail = [], 0
    for name, (a_tags, b_tags, expect, want, want_df) in CASES.items():
        a, b = [run(t) for t in a_tags], [run(t) for t in b_tags]
        res = compare(a, b, build_a="edge", build_b="edge")
        iv = res.interval or {}
        got = tuple(round(iv.get(k, 9.0), 4) for k in ("rel", "lo", "hi"))
        got_df = round(iv.get("df", -1.0), 2)
        fails = [f.code for f in res.findings if f.level == "FAIL"]
        ok = res.verdict == expect and got == want and got_df == want_df and not fails
        n_fail += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {res.verdict} {got} df={got_df}"
              f"  (required {expect} {want} df={want_df})"
              + (f"  findings={sorted({f.code for f in res.findings})}" if res.findings else ""))  # fmt: skip
        rows.append({"case": name, "pass": ok, "required": {"verdict": expect, "interval": want, "df": want_df},
                     "a": a_tags, "b": b_tags, "result": asdict(res)})  # fmt: skip
    json.dump(
        {"inkdelta_src": str(INKDELTA_SRC), "cases": rows},
        open(args.out, "w"),
        indent=1,
        default=str,
    )
    print(f"\n{len(CASES) - n_fail}/{len(CASES)} cases pass")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
