"""Same-winding ablation, extended to six seeds. Implements
`docs/preregistration/2026-09-28_samewinding_extension.md`. **Written, with its decision rule, before
any of the three new fits was started.**

Refuses rather than guesses: every new arm must pass the validity gates, and the primary comparison
needs exactly six arms per side.
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkdelta/src")
from inkdelta.compare import compare  # noqa: E402
from inkdelta.runs import load_run  # noqa: E402

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
RENDER_SHA = "be09a85035059fd83471b1632b5898c62f2c65b1"
FLOOR_CV = 0.0536  # reports/noise_floor_by_tier.json, current tier, df 11
NEW = ["nosamecur_s4", "nosamecur_s5", "nosamecur_s6"]
ABLATED = ["nosamecur_s1", "nosamecur_s2", "nosamecur_s3"] + NEW
CONTROL = [f"curbase_s{i}" for i in range(4, 10)]  # render-matched
ALL_NINE = [f"curbase_s{i}" for i in range(1, 10)]


def run(tag):
    d = SO / f"outer_{tag}"
    log = SO / f"sequence_{tag}.log"
    return load_run(d, log if log.is_file() else None)


def gates(tag, control_area):
    """The three registered validity gates for a NEW arm. Returns a list of failures."""
    d = SO / f"outer_{tag}"
    bad = []
    sha = (d / "VILLA_SHA").read_text().strip() if (d / "VILLA_SHA").is_file() else None
    if sha != RENDER_SHA:
        bad.append(f"rendered on {sha}, not {RENDER_SHA[:9]}")
    r = run(tag)
    bad += [f"{f.code}" for f in r.findings if f.level == "FAIL"]
    if r.log_path is None:
        bad.append("no sequence log, so stale-slice/zero-strip checks could not run")
    m = json.loads((d / "ink_metric" / "metrics.json").read_text())["summary"]
    area = m["total_pixels"]
    if abs(area / control_area - 1) > 0.10:  # amended 2026-09-28 before data: was 0.05
        bad.append(f"strip area {area:,} is {area / control_area - 1:+.1%} from the control mean")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/samewinding_extension_verdict.json")
    args = ap.parse_args()
    missing = [t for t in ABLATED + ALL_NINE if not (SO / f"outer_{t}" / "ink_metric" / "metrics.json").is_file()]
    if missing:
        raise SystemExit(f"not scored yet: {missing}. A partial sample is refused, not reported.")
    ctl_area = st.mean(
        json.loads((SO / f"outer_{t}" / "ink_metric" / "metrics.json").read_text())["summary"]["total_pixels"]
        for t in CONTROL
    )
    gate = {t: gates(t, ctl_area) for t in NEW}
    for t, g in gate.items():
        print(f"gate {t}: {'PASS' if not g else 'FAIL ' + '; '.join(g)}")
    if any(gate.values()):
        json.dump({"verdict": "GATE FAILURE", "gates": gate}, open(args.out, "w"), indent=1)
        print("GATE FAILURE: re-render the failing arm; no verdict is reported on an invalid arm.")
        return 2

    def cmp(a_tags, b_tags):
        r = compare([run(t) for t in a_tags], [run(t) for t in b_tags], "edge", "edge", cv=FLOOR_CV)
        iv = r.interval
        return {"verdict": r.verdict, "rel": iv["rel"], "lo": iv["lo"], "hi": iv["hi"], "method": iv["method"],
                "welch": iv.get("welch") or ({k: iv[k] for k in ("lo", "hi", "df")} if "df" in iv else None),
                "findings": sorted({f.code for f in r.findings})}  # fmt: skip

    res = {
        "primary 6v6 render-matched": cmp(CONTROL, ABLATED),
        "secondary 6v9 all nine controls": cmp(ALL_NINE, ABLATED),
        "replication new seeds only (3v6)": cmp(CONTROL, NEW),
        "gates": gate,
    }
    p = res["primary 6v6 render-matched"]
    if p["verdict"] == "RESOLVED (-)":
        verdict = "CONSTRAINTS BUY READING"
    elif p["verdict"] == "RESOLVED (+)":
        verdict = "REMOVING THEM HELPS"
    else:
        verdict = f"NULL, constraints buy at most {-p['lo']:.1%}" if p["lo"] < 0 else "NULL"
    res["verdict"] = verdict
    for k, v in res.items():
        if isinstance(v, dict) and "rel" in v:
            print(f"{k:34} {v['verdict']:13} {v['rel']:+.2%} [{v['lo']:+.2%}, {v['hi']:+.2%}] ({v['method']})")
    print(f"\nVERDICT: {verdict}")
    json.dump(res, open(args.out, "w"), indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
