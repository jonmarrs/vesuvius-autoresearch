"""Did the 2026-09-11 render-code change move the ink?

Implements `docs/preregistration/2026-09-14_render_code_rerender_test.md`, and is
written while the re-render is at band 12 of 35 -- before its ink number exists.

`curbase_s1`'s existing meshes were re-rendered with current villa code. The fit
is untouched, so any difference in `total_fg_pixels` is the render and scoring
code and nothing else.

The verdict is mechanical on purpose. The threshold was registered before the
number, and applying it by eye while looking at the number is how a +/-2% band
becomes "well, 2.3% is basically 2%".
"""

import argparse
import json
import sys
from pathlib import Path

ORIGINAL_TAG = "curbase_s1"
RERENDER_TAG = "curbase_s1rr"
BAND = 0.02  # registered
OLD_SHA_PREFIX = "d8c5f488a"  # the pre-bump render code
AREA_TOLERANCE = 0.05  # >5% strip change means something else moved


def summary(spiral_out: str, tag: str) -> dict | None:
    p = Path(spiral_out) / f"outer_{tag}" / "ink_metric" / "metrics.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())["summary"]


def villa_sha(spiral_out: str, tag: str) -> str | None:
    p = Path(spiral_out) / f"outer_{tag}" / "VILLA_SHA"
    return p.read_text().strip() if p.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    a = summary(args.spiral_out, ORIGINAL_TAG)
    b = summary(args.spiral_out, RERENDER_TAG)
    if a is None:
        raise SystemExit(f"{ORIGINAL_TAG} has no metrics; nothing to compare against")
    if b is None:
        raise SystemExit(
            f"{RERENDER_TAG} is not scored yet. A partial result is refused, not reported."
        )

    ink_a, ink_b = a["total_fg_pixels"], b["total_fg_pixels"]
    rel = ink_b / ink_a - 1
    area_rel = b["total_pixels"] / a["total_pixels"] - 1

    print(f"{'quantity':<28}{'original':>14}{'re-render':>14}{'rel':>9}")
    for k, lbl in (
        ("total_fg_pixels", "ink"),
        ("total_pixels", "strip"),
        ("overall_fg_fraction", "density"),
        ("overall_line_score", "line"),
        ("overall_column_score", "column"),
    ):
        fmt = ",.0f" if a[k] > 1 else ".5f"
        print(
            f"{lbl + '  ' + k:<28}{a[k]:>14{fmt}}{b[k]:>14{fmt}}{b[k] / a[k] - 1:>+9.2%}"
        )

    # ---- validity gate -------------------------------------------------
    sha = villa_sha(args.spiral_out, RERENDER_TAG)
    gate = []
    if sha is None:
        gate.append("re-render recorded no VILLA_SHA; cannot prove it used new code")
    elif sha.startswith(OLD_SHA_PREFIX):
        gate.append(
            f"re-render used the OLD code ({sha[:9]}); it is not a test of anything"
        )
    if abs(area_rel) > AREA_TOLERANCE:
        gate.append(
            f"strip area moved {area_rel:+.1%}, beyond {AREA_TOLERANCE:.0%} — "
            "something other than render code changed"
        )

    print("\nvalidity gate")
    print(
        f"  re-render VILLA_SHA: {sha[:9] if sha else 'MISSING'}"
        f"  (must NOT be {OLD_SHA_PREFIX})"
    )
    print(
        f"  strip area change:   {area_rel:+.2%}  (must be within "
        f"±{AREA_TOLERANCE:.0%})"
    )

    if gate:
        verdict, why = "VOID", "; ".join(gate)
    elif abs(rel) <= BAND:
        verdict = "RENDER CHANGE IS INERT"
        why = (
            "ink moved less than the registered ±2%. The 09-11 split does not bias "
            "ink, and the same-winding and anchor nulls stand unmodified."
        )
    elif rel > BAND:
        verdict = "RENDER CHANGE ADDS INK"
        why = (
            "the same-winding (+0.28%) and anchor (−0.86%) verdicts each compared a "
            "new-code arm against an old-code baseline. Both must be recomputed "
            "against re-rendered baselines before being trusted."
        )
    else:
        verdict = "RENDER CHANGE REMOVES INK"
        why = (
            "same consequence as adding, opposite sign: both published verdicts "
            "must be recomputed against re-rendered baselines."
        )

    print(
        f"\nink {ink_a:,.0f} -> {ink_b:,.0f}  ({rel:+.2%}), registered band ±{BAND:.0%}"
    )
    print(f"\nVERDICT: {verdict}\n  {why}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "original": ink_a,
                    "rerender": ink_b,
                    "rel": rel,
                    "area_rel": area_rel,
                    "band": BAND,
                    "villa_sha": sha,
                    "gate_failures": gate,
                    "verdict": verdict,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
