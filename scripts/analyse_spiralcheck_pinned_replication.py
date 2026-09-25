"""Does any spiralcheck metric track ink within config on the PINNED tier?

Implements `docs/preregistration/2026-09-25_spiralcheck_pinned_replication.md`.
**Written, with its tests, before spiralcheck was run on any pinned-tier fit.**

The first validation (`reports/spiralcheck_is_not_discriminating_here.md`) found no
within-config relation on 12 current-tier fits, but at df 8 only |r| >= 0.750 could
register. The pinned tier has 24 scored fits in six configs, which is independent data
at df 17 (critical |r| 0.561). Same four metrics, same scored windings (w120-w129),
same Bonferroni alpha 0.0125, same functions -- imported, not re-implemented.

Gates: every repeat run identical; every arm's scored meshes byte-identical to the
fit's; all 24 present. Any failure withholds the verdict.
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_spiralcheck_validation import (  # noqa: E402
    ALPHA,
    METRICS,
    SCORED_WINDINGS,
    SPIRAL_OUT,
    SPIRALCHECK,
    SPIRALCHECK_COMMIT,
    _run_intrinsic,
    _scored_subset,
    metric_row,
    q3_verdict,
    r_critical,
)

# fit tag -> config. Stock-flatten ink lives in outer_<tag>.
ARMS: dict[str, str] = {
    **{
        t: "baseline"
        for t in ("baseline01", "seed02", "seed03", "seed04", "seed05", "seed06")
    },
    **{
        t: "gap133"
        for t in ("gap133", "gap133s2", "gap133s3", "gap133s4", "gap133s5", "gap133s6")
    },
    **{t: "boot090" for t in ("boot090s1", "boot090s2", "boot090s3")},
    **{t: "rand090" for t in ("rand090s1", "rand090s2", "rand090s3")},
    **{t: "strip090" for t in ("strip090s1", "strip090s2", "strip090s3")},
    **{t: "nosame" for t in ("nosame_s1", "nosame_s2", "nosame_s3")},
}
N_CONFIGS = 6
DF = len(ARMS) - N_CONFIGS - 1  # 17


def decide(data: dict) -> dict:
    rows = data["fits"]
    if set(rows) != set(ARMS):
        raise ValueError(
            f"partial sample refused: missing {sorted(set(ARMS) - set(rows))}, "
            f"unexpected {sorted(set(rows) - set(ARMS))}"
        )
    bad = sorted(
        t for t, r in rows.items() if not (r["deterministic"] and r["meshes_match"])
    )
    if bad:
        return {
            "verdict": "INVALID",
            "detail": f"nondeterministic run or mesh mismatch on {bad}; no verdict issued",
        }
    tags = sorted(rows)
    groups = [ARMS[t] for t in tags]
    ink = [float(rows[t]["total_fg_pixels"]) for t in tags]
    q3 = {
        m: q3_verdict([rows[t]["scored"][m] for t in tags], ink, groups)
        for m in METRICS
    }
    tracks = [m for m, v in q3.items() if v[0].startswith("TRACKS INK")]
    if tracks:
        head = "READING-RELEVANT ON PINNED"
    elif all(v[0] == "UNINFORMATIVE" for v in q3.values()):
        head = "UNINFORMATIVE"
    else:
        head = "NO DETECTED RELATION"
    return {
        "verdict": head,
        "alpha": ALPHA,
        "df": DF,
        "r_critical": r_critical(DF),
        "q3_scored": {m: {"verdict": v[0], **v[1]} for m, v in q3.items()},
    }


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def meshes_match(fitted: Path, work: Path, tag: str) -> bool:
    """The rendered windings are the fit's own, byte for byte."""
    for w in SCORED_WINDINGS:
        src = fitted / f"w{w:03d}_spliced_{tag}"
        dst = work / "meshes" / src.name
        if not dst.is_dir():
            return False
        if any(_md5(src / f"{c}.tif") != _md5(dst / f"{c}.tif") for c in "xyz"):
            return False
    return True


def collect(out_dir: Path) -> dict:
    import subprocess

    head = subprocess.run(
        ["git", "-C", str(SPIRALCHECK), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip
    if head != SPIRALCHECK_COMMIT:
        raise RuntimeError(f"spiralcheck at {head}, registered {SPIRALCHECK_COMMIT}")
    fits = {}
    for tag in ARMS:
        run_dir = next(SPIRAL_OUT.glob(f"*-patch_{tag}"))
        fitted = run_dir / "meshes" / f"fitted_{tag}"
        scored_in = _scored_subset(fitted, tag, out_dir / tag / "scored_in")
        a = _run_intrinsic(scored_in, out_dir / tag / "run1")
        b = _run_intrinsic(scored_in, out_dir / tag / "run2")
        work = SPIRAL_OUT / f"outer_{tag}"
        ink = json.loads((work / "ink_metric" / "metrics.json").read_text())
        fits[tag] = {
            "fit_dir": str(fitted),
            "deterministic": a["intrinsic"] == b["intrinsic"],
            "meshes_match": meshes_match(fitted, work, tag),
            "scored": metric_row(a["intrinsic"]),
            "total_fg_pixels": ink["summary"]["total_fg_pixels"],
        }
        print(tag, fits[tag]["deterministic"], fits[tag]["meshes_match"], flush=True)
    return {"spiralcheck_commit": head, "fits": fits}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--work", type=Path, required=True)
    c.add_argument("--json", type=Path, required=True)
    a = sub.add_parser("analyse")
    a.add_argument("--json", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "collect":
        args.json.write_text(json.dumps(collect(args.work), indent=2) + "\n")
        return 0
    res = decide(json.loads(args.json.read_text()))
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    print(res["verdict"])
    for m, v in res.get("q3_scored", {}).items():
        r = v.get("r", math.nan)
        print(f"  {m:24s} {v['verdict']:22s} r {r:+.3f}  p {v.get('p', math.nan):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
