"""STRIPMATCH: does selection help once outer evidence is held equal?

**Written before the first STRIPMATCH fit was started**, implementing
`docs/preregistration/2026-09-04_stripmatch_followup.md` and nothing else.

The parent study returned FAILURE: BOOTSTRAP raised `satisfied_area` 17.66% and
moved `total_fg_pixels` not at all. It could not say why, because its RANDOM
control matched BOOTSTRAP on GLOBAL area while BOOTSTRAP carried ~11% less
relative area inside the scored strip. STRIPMATCH equalises the strip, so a
remaining difference is selection quality alone.

The decision rule is the parent's, deliberately unchanged, including the branch
that matters: **a geometry-only gain is a FAILURE, not a partial success.** The
geometry comparison here is even more circular than the parent's -- BOOTSTRAP is
selected on satisfaction and scored on satisfaction, and STRIPMATCH is not -- so
a large positive geometry number is expected and means nothing on its own.

What would count as the method working: BOOTSTRAP beating STRIPMATCH on ink. My
registered prediction, made blind, is that it does not.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyse_gap_ink_arm import separation, welch  # noqa: E402

ALPHA = 0.05
INK = "total_fg_pixels"
GEOM = "satisfied_area_fraction"
SECONDARY = ("overall_fg_fraction", "overall_line_score", "overall_column_score")

BOOTSTRAP_ARMS = ("boot090s1", "boot090s2", "boot090s3")
STRIPMATCH_ARMS = ("strip090s1", "strip090s2", "strip090s3")
REQUIRED_PER_ARM = 3

OUTER_CV = 0.0421
PREDICTION = "no ink advantage for BOOTSTRAP; equalising outer evidence does not rescue the method"


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
    """The parent study's rule, unchanged."""
    ink_sig = (not ink["degenerate"]) and ink["p"] < ALPHA
    geom_up = (
        geom is not None
        and (not geom["degenerate"])
        and geom["p"] < ALPHA
        and geom["rel_diff"] > 0
    )

    if ink_sig and ink["rel_diff"] > 0:
        return "WORKS", (
            "ink is up and significant with in-strip evidence held equal, so the "
            "parent study's null WAS masking a real selection effect. Selecting on "
            "satisfaction helps once coverage is preserved -- a usable refinement of "
            "villa's avenue, and a MISS against my registered prediction."
        )
    if ink_sig and ink["rel_diff"] < 0:
        return "HARMS", (
            "ink is down and significant even with coverage equalised: selecting on "
            "satisfaction picks worse evidence for reading, independent of how much."
        )
    if geom_up:
        return "FAILURE", (
            "geometry improved while ink did not follow, with in-strip evidence held "
            "equal. Registered as a FAILURE, NOT a partial success. This is the "
            "circular result again and it now survives removing the coverage "
            "explanation, so the outer deficit was a side effect rather than the cause."
        )
    return (
        "NULL",
        "neither endpoint moved; nothing here rescues the avenue at this budget.",
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
    known = BOOTSTRAP_ARMS + STRIPMATCH_ARMS
    unknown = [t for t in tags if t not in known]
    if unknown:
        raise SystemExit(f"unregistered arm(s) {unknown}")

    boot = [r for r in rows if r["tag"] in BOOTSTRAP_ARMS]
    strip = [r for r in rows if r["tag"] in STRIPMATCH_ARMS]
    if len(boot) != REQUIRED_PER_ARM or len(strip) != REQUIRED_PER_ARM:
        raise SystemExit(
            f"needs exactly {REQUIRED_PER_ARM} BOOTSTRAP and {REQUIRED_PER_ARM} "
            f"STRIPMATCH arms, got {len(boot)} and {len(strip)}. A partial sample is "
            "refused, not reported."
        )

    print(f"STRIPMATCH, alpha = {ALPHA}. Claim rests on BOOTSTRAP vs STRIPMATCH.")
    print(f"\n{'fit':<13}{'arm':<12}{'geometry':>10}{'total_fg':>12}")
    for r in boot + strip:
        arm = "BOOTSTRAP" if r["tag"] in BOOTSTRAP_ARMS else "STRIPMATCH"
        g = r.get(GEOM)
        print(
            f"{r['tag']:<13}{arm:<12}{(f'{g:.4f}' if g is not None else '-'):>10}"
            f"{r[INK]:>12,.0f}"
        )

    m = mde(len(boot), len(strip))
    print(
        f"\nn = {len(boot)} vs {len(strip)}; smallest ink effect at 80% power: {m:.1%}"
    )

    ink = welch([r[INK] for r in strip], [r[INK] for r in boot])
    geom = None
    if all(GEOM in r for r in boot + strip):
        geom = welch([r[GEOM] for r in strip], [r[GEOM] for r in boot])

    print(f"\n{'endpoint':<26}{'STRIPMATCH':>13}{'BOOTSTRAP':>13}{'rel':>9}{'p':>9}")
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
            "  NOTE: BOOTSTRAP is selected ON satisfaction and STRIPMATCH is not, so a "
            "large positive geometry number here is expected and carries no credit."
        )
    print(
        f"  ink separation: {separation([r[INK] for r in strip], [r[INK] for r in boot])}"
    )

    tag, why = verdict(ink, geom)
    print(f"\nVERDICT: {tag}\n  {why}")
    if not ((not ink["degenerate"]) and ink["p"] < ALPHA):
        print(
            f"  NULL READING on ink: no effect larger than about {m:.0%}. NOT 'no effect'."
        )

    met = tag in ("FAILURE", "NULL")
    print(
        f"\nregistered prediction: {PREDICTION}\n  -> "
        f"{'MET' if met else 'MISS, recorded as a miss'}"
    )

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
