"""How much does the post-#1146 slice step move total_fg_pixels, across surfaces?

Implements `docs/preregistration/2026-09-27_step2_across_surfaces.md`. **Written, with its tests,
before any step-2 arm rendered.** Per surface: effect = step2 / default - 1, where default is the
surface's existing `detfit_*` score (published image, step 1) and step2 is the same saved flat
re-sampled by the published image with `--slice-step 2`. `up1` enters via its measured
source-build score (`tif_score_pr1905`), which equals step 2 to rounding.
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

SPIRAL_OUT = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
PAIRS = {  # surface -> (default-step work dir, step-2 work dir)
    "up1": ("detfit_up1", "tif_score_pr1905"),
    "s4": ("detfit_s4", "step2_s4"),
    "s5": ("detfit_s5", "step2_s5"),
    "s6": ("detfit_s6", "step2_s6"),
}
RESCORE_FLOOR = 59 / 3_279_498  # identical slices re-scored (smp_pub vs detfit_up1)


def effects(ink: dict[str, float]) -> dict:
    missing = [d for pair in PAIRS.values() for d in pair if d not in ink]
    if missing:
        raise ValueError(f"partial sample refused: missing {missing}")
    per = {s: ink[b] / ink[a] - 1.0 for s, (a, b) in PAIRS.items()}
    vals = list(per.values())
    return {
        "per_surface": per,
        "mean": st.mean(vals),
        "min": min(vals),
        "max": max(vals),
        "all_positive": all(v > 0 for v in vals),
        "all_clear_floor": all(abs(v) > 10 * RESCORE_FLOOR for v in vals),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ink = {}
    for pair in PAIRS.values():
        for d in pair:
            f = SPIRAL_OUT / d / "ink_metric" / "metrics.json"
            if f.exists():
                ink[d] = float(json.loads(f.read_text())["summary"]["total_fg_pixels"])
    res = effects(ink)
    res["ink"] = ink
    a.out.write_text(json.dumps(res, indent=2) + "\n")
    for s, v in res["per_surface"].items():
        print(f"  {s}: {v:+.2%}")
    print(
        f"mean {res['mean']:+.2%}  range [{res['min']:+.2%}, {res['max']:+.2%}]  all positive: {res['all_positive']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
