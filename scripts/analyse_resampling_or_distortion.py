"""Is the flatten's per-block rescoring RE-SAMPLING, or does it need DISTORTION?

Implements `docs/preregistration/2026-09-23_resampling_or_distortion.md`.
**Written before either arm was rendered.**

Two flattens of one surface are re-read ~0.135 (ink-weighted sd per 2048-px
block), and a rigid translation re-reads ~0.0001. This re-samples the SAME
layout by half a strip pixel (t = 0.05 cell, primary arm) and compares
per-block rescoring against the 0 vx surface it came from. A secondary arm
(t = 0.5 cell = 5 px, a translation plus the re-interpolated surface) is reported
descriptively.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_layout_rescoring import compare  # noqa: E402

ZERO = "flat_study_zero"
PRIMARY = "rs_t005"  # t = 0.05 cell = half a strip pixel: re-sampling, layout fixed
SECONDARY = "rs_t05"  # t = 0.5 cell = 5 px: translation + re-interpolated surface
REF = 0.135  # rad0 vs rad0b, the flatten's own re-layout
LO, HI = 0.02, 0.07  # registered bands on the primary arm's sd at 2048 px
BLOCK = 2048


def verdict(sd: float) -> tuple[str, str]:
    if sd >= HI:
        return "RE-SAMPLING SUFFICES", (
            "Moving every sample half a pixel, with the layout fixed, re-draws at least half "
            "the flatten's per-block rescoring: no distortion is needed to explain it."
        )
    if sd <= LO:
        return "DISTORTION REQUIRED", (
            "Re-sampling alone re-draws little; the flatten's per-block rescoring needs the "
            "layout itself to change (stretch or shear)."
        )
    return (
        "BOTH CONTRIBUTE",
        "Re-sampling explains part of the rescoring, not most of it.",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    so = Path(a.spiral_out)
    for arm in (PRIMARY, SECONDARY):
        if not (so / arm / "ink_metric" / "metrics.json").exists():
            raise SystemExit(f"{arm} not scored -- refused, not reported.")
    shas = {
        (so / x / "VILLA_SHA").read_text().strip() for x in (ZERO, PRIMARY, SECONDARY)
    }
    if len(shas) != 1:
        print("VERDICT: VOID -- the arms do not share one tree.")
        return 1

    out = {}
    print("RE-SAMPLING OR DISTORTION? same layout, sample points moved in-plane\n")
    for arm in (PRIMARY, SECONDARY):
        r = compare(so / ZERO, so / arm, blocks=(BLOCK,))
        b = r["block"][BLOCK]
        out[arm] = {
            "covered_ratio": r["covered_ratio"],
            "fg_ratio": r["fg_ratio"],
            "density_ratio": r["density_ratio"],
            "sd_2048": b["sd"],
            "lag1": b["lag1"],
            "implied_total_sd": b["implied_total_sd"],
        }
        print(
            f"  {arm:<8} covered {r['covered_ratio']:.4f}  ink {r['fg_ratio']:.4f}  "
            f"per-block sd {b['sd']:.4f}  (re-layout ref {REF}, translation ~0.0001)"
        )
    sd = out[PRIMARY]["sd_2048"]
    v, read = verdict(sd)
    print(
        f"\nVERDICT (primary, {PRIMARY}, sd {sd:.4f}; bands {LO} / {HI}): {v}\n  {read}"
    )
    print(f"  secondary {SECONDARY} (descriptive): sd {out[SECONDARY]['sd_2048']:.4f}")
    out["verdict"] = v
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
