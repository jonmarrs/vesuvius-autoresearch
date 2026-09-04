"""Patch-bootstrap study: BOOTSTRAP vs RANDOM, ink and geometry together.

**Written 2026-09-03 while boot090s1 was still fitting**, before any of the six new
arms produced a number. Implements
`docs/preregistration/2026-09-03_patch_bootstrap.md` and nothing else.

The one rule worth stating in code rather than prose: **a geometry gain with a
null or negative ink result is a FAILURE of the method, not a partial success.**
`reports/gap_fix_costs_ink_established.md` established that a change can raise
`satisfied_area` by 7-10 sd while costing 10.35% of the ink objective. A method
that selects patches *by* satisfaction is at obvious risk of that circularity, so
the verdict function refuses to call a geometry-only move a win.

The comparison that carries the claim is BOOTSTRAP vs RANDOM. Contrasts against
BASELINE are printed for context and explicitly carry no claim: they confound
evidence quality with evidence quantity, which is the entire reason RANDOM exists.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyse_gap_ink_arm import separation, welch  # noqa: E402

ALPHA = 0.05
INK = "total_fg_pixels"
GEOM = "satisfied_area_fraction"
SECONDARY = ("overall_fg_fraction", "overall_line_score", "overall_column_score")

BOOTSTRAP_ARMS = ("boot090s1", "boot090s2", "boot090s3")
RANDOM_ARMS = ("rand090s1", "rand090s2", "rand090s3")
BASELINE_ARMS = ("baseline01", "seed02", "seed03", "seed04", "seed05", "seed06")
REQUIRED_PER_NEW_ARM = 3

# reports/outer_winding_noise_floor.md; used only to state what a null excludes.
OUTER_CV = 0.0421
PREDICTION = "ink NULL and geometry UP, i.e. the method fails by the registered rule"


def load(spec: str) -> dict:
    tag, _, paths = spec.partition("=")
    mp, _, sp = paths.partition(",")
    m = json.loads(Path(mp).read_text())["summary"]
    row = {"tag": tag, INK: m[INK], **{k: m[k] for k in SECONDARY}}
    if sp:
        row[GEOM] = json.loads(Path(sp).read_text())["summary"][GEOM]
    return row


def mde(n_a: int, n_b: int, cv: float = OUTER_CV) -> float:
    return 2.802 * cv * (1 / n_a + 1 / n_b) ** 0.5


def verdict(ink: dict, geom: dict | None) -> tuple[str, str]:
    """The registered decision rule. Note the third branch."""
    ink_sig = (not ink["degenerate"]) and ink["p"] < ALPHA
    geom_up = (
        geom is not None
        and (not geom["degenerate"])
        and geom["p"] < ALPHA
        and geom["rel_diff"] > 0
    )

    if ink_sig and ink["rel_diff"] > 0:
        return "WORKS", (
            "ink is up and significant: selecting on the fit's own satisfaction "
            "produces better winding constraints, which answers villa's named avenue."
        )
    if ink_sig and ink["rel_diff"] < 0:
        return (
            "HARMS",
            "ink is down and significant: the method actively harms recovery.",
        )
    if geom_up:
        return "FAILURE", (
            "geometry improved while ink did not follow. Registered as a FAILURE of the "
            "method, NOT a partial success: this is the gap133 pattern repeating, and a "
            "method that selects patches by satisfaction improving satisfaction is close "
            "to circular."
        )
    return (
        "NULL",
        "neither endpoint moved; the avenue is not promising at this threshold.",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="tag=metrics.json[,satisfaction.json]")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = [load(s) for s in args.arms]
    tags = [r["tag"] for r in rows]
    if len(set(tags)) != len(tags):
        raise SystemExit(f"an arm was passed twice: {tags}")
    known = BOOTSTRAP_ARMS + RANDOM_ARMS + BASELINE_ARMS
    unknown = [t for t in tags if t not in known]
    if unknown:
        raise SystemExit(f"unregistered arm(s) {unknown}")

    boot = [r for r in rows if r["tag"] in BOOTSTRAP_ARMS]
    rand = [r for r in rows if r["tag"] in RANDOM_ARMS]
    base = [r for r in rows if r["tag"] in BASELINE_ARMS]
    if len(boot) != REQUIRED_PER_NEW_ARM or len(rand) != REQUIRED_PER_NEW_ARM:
        raise SystemExit(
            f"needs exactly {REQUIRED_PER_NEW_ARM} BOOTSTRAP and {REQUIRED_PER_NEW_ARM} "
            f"RANDOM arms, got {len(boot)} and {len(rand)}. A partial sample is refused, "
            "not reported."
        )

    print(f"PATCH BOOTSTRAP, alpha = {ALPHA}. Claim rests on BOOTSTRAP vs RANDOM.")
    print(f"\n{'fit':<12}{'arm':<11}{'geometry':>10}{'total_fg':>12}")
    for r in boot + rand + base:
        arm = (
            "BOOTSTRAP"
            if r["tag"] in BOOTSTRAP_ARMS
            else "RANDOM"
            if r["tag"] in RANDOM_ARMS
            else "baseline"
        )
        g = r.get(GEOM)
        print(
            f"{r['tag']:<12}{arm:<11}{(f'{g:.4f}' if g is not None else '-'):>10}"
            f"{r[INK]:>12,.0f}"
        )

    m = mde(len(boot), len(rand))
    print(
        f"\nn = {len(boot)} vs {len(rand)}; smallest ink effect at 80% power: {m:.1%}"
    )

    ink = welch([r[INK] for r in rand], [r[INK] for r in boot])
    geom = None
    if all(GEOM in r for r in boot + rand):
        geom = welch([r[GEOM] for r in rand], [r[GEOM] for r in boot])

    print(f"\n{'endpoint':<26}{'RANDOM':>13}{'BOOTSTRAP':>13}{'rel':>9}{'p':>9}")
    print(
        f"{'ink  ' + INK:<26}{ink['mean_base']:>13,.4g}{ink['mean_gap']:>13,.4g}"
        f"{ink['rel_diff']:>9.2%}{ink['p']:>9.4f}"
    )
    if geom:
        print(
            f"{'geom ' + GEOM:<26}{geom['mean_base']:>13.4f}{geom['mean_gap']:>13.4f}"
            f"{geom['rel_diff']:>9.2%}{geom['p']:>9.4f}"
        )
    print(
        f"  ink separation: {separation([r[INK] for r in rand], [r[INK] for r in boot])}"
    )

    tag, why = verdict(ink, geom)
    print(f"\nVERDICT: {tag}\n  {why}")
    if not ((not ink["degenerate"]) and ink["p"] < ALPHA):
        print(
            f"  NULL READING on ink: no effect larger than about {m:.0%}. NOT 'no effect'."
        )

    met = tag == "FAILURE"
    print(
        f"\nregistered prediction: {PREDICTION}\n  -> "
        f"{'MET' if met else 'MISS, recorded as a miss'}"
    )

    if base:
        print("\ncontext only, CARRIES NO CLAIM (confounds quality with quantity):")
        for lbl, arm in (("BOOTSTRAP", boot), ("RANDOM", rand)):
            w = welch([r[INK] for r in base], [r[INK] for r in arm])
            print(f"  {lbl:<10} vs baseline ink {w['rel_diff']:+.2%} (p={w['p']:.4f})")

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {
                    "alpha": ALPHA,
                    "mde": m,
                    "ink": ink,
                    "geometry": geom,
                    "verdict": tag,
                    "prediction_met": met,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
