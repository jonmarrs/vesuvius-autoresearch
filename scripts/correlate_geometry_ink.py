"""Across every scored fit we hold: does `satisfied_area` predict recovered ink?

Four pre-registered studies each found the two moving independently. This asks
the same question of the whole corpus at once, which is a different and stronger
form of the claim -- and, more usefully, bounds how large a relationship the data
can still hide.

**The headline is the interval, not the point estimate.** At n=24 a correlation
of -0.12 carries a 95% interval of roughly [-0.50, +0.30]. That is not "no
relationship": it excludes a STRONG POSITIVE one, which is precisely what a
usable guard would need (higher satisfaction should mean more ink). Reporting the
point estimate alone would overclaim in the direction we already believe, which
is the error this project keeps having to correct.

Deliberately observational. The arms differ in patch selection, config flags and
constraint sets, so this is a correlation across heterogeneous manipulations, not
a controlled comparison. Subgroups are printed for that reason.
"""

import argparse
import glob
import json
import math
import statistics as st
import sys

BASELINES = ("baseline01", "seed02", "seed03", "seed04", "seed05", "seed06")

# Fits come in two NON-COMPARABLE tiers. Current villa recovers 67.6% more ink
# than the pinned tree through a byte-identical scorer
# (reports/current_code_baseline.md), so pooling them manufactures a spread that
# is the code change rather than a relationship. Before this split the script
# silently reported 27 fits at "100% spread" and r = -0.090, an artefact.
CURRENT_TREE_PREFIXES = ("curbase_", "nosamecur_")


def tier_of(tag: str) -> str:
    return "current" if tag.startswith(CURRENT_TREE_PREFIXES) else "pinned"


def collect(spiral_out):
    rows = []
    for m in sorted(glob.glob(f"{spiral_out}/outer_*/ink_metric/metrics.json")):
        tag = m.split("/outer_")[1].split("/")[0]
        sat = glob.glob(f"{spiral_out}/*patch_{tag}/satisfaction_metrics_fitted.json")
        if not sat:
            continue
        rows.append(
            {
                "tag": tag,
                "satisfied_area": json.load(open(sat[0]))["summary"][
                    "satisfied_area_fraction"
                ],
                "total_fg_pixels": json.load(open(m))["summary"]["total_fg_pixels"],
            }
        )
    return rows


def pearson(xs, ys):
    if len(xs) < 2:
        return float("nan")
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys, strict=False))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return num / den if den else float("nan")


def fisher_ci(r, n, z=1.96):
    """95% interval on r. Returns None below n=4, where it is meaningless."""
    if n < 4 or not -1 < r < 1:
        return None
    zz = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    return math.tanh(zz - z * se), math.tanh(zz + z * se)


def subgroups(rows):
    return {
        "all fits in tier": rows,
        "seed-only baselines": [r for r in rows if r["tag"] in BASELINES],
        "patch-selection arms": [
            r for r in rows if r["tag"].startswith(("boot090", "rand090", "strip090"))
        ],
        "constraint-ablation arms": [r for r in rows if r["tag"].startswith("nosame_")],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    args = ap.parse_args()

    rows = collect(args.spiral_out)
    if not rows:
        raise SystemExit(
            f"no scored fits with satisfaction found under {args.spiral_out}"
        )

    tiers = {"pinned": [], "current": []}
    for r in rows:
        tiers[tier_of(r["tag"])].append(r)

    print(f"{len(rows)} fits with both endpoints, in TWO NON-COMPARABLE TIERS.")
    print(
        "  Current villa recovers 67.6% more ink than the pinned tree through a\n"
        "  byte-identical scorer, so a POOLED correlation is an artefact and is\n"
        "  deliberately not computed."
    )

    for tier in ("pinned", "current"):
        trows = tiers[tier]
        if not trows:
            continue
        inks = [x["total_fg_pixels"] for x in trows]
        print(
            f"\n=== {tier} tree: {len(trows)} fits, "
            f"ink {min(inks):,.0f} .. {max(inks):,.0f} ==="
        )
        print(f"  {'group':<26}{'n':>4}{'r':>9}{'95% CI':>22}")
        for name, g in subgroups(trows).items():
            if len(g) < 3:
                continue
            r = pearson(
                [x["satisfied_area"] for x in g], [x["total_fg_pixels"] for x in g]
            )
            c = fisher_ci(r, len(g))
            cs = f"[{c[0]:+.2f}, {c[1]:+.2f}]" if c else "n too small for a CI"
            print(f"  {name:<26}{len(g):>4}{r:>9.3f}{cs:>22}")
        if len(trows) >= 4:
            r_t = pearson(
                [x["satisfied_area"] for x in trows],
                [x["total_fg_pixels"] for x in trows],
            )
            c = fisher_ci(r_t, len(trows))
            print(
                f"  a guard needs a meaningfully POSITIVE r; this tier tops out "
                f"at {c[1]:+.2f}"
            )
        else:
            print("  too few fits in this tier for a tier-level interval")

    print(
        "\n  Observational across heterogeneous manipulations -- not a controlled "
        "comparison."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
