"""Split volume-frame ink-placement agreement into FIT and LAYOUT parts.

Reads the JSON written by `compare_ink_in_volume.py --prefix '' --arms ...` over:
the same meshes flattened twice (`radial_work_rad0` / `rad0b`), an identical-strip
control (`flat_study_probe`), six fits flattened stock (`outer_curbase_s4..s9`) and
the SAME six fits flattened deterministically (`detfit_s4..s9`).

    python scripts/summarise_placement_decomposition.py reports/layout_rescoring/placement_volume_frame.json
"""

import json
import re
import statistics as st
import sys


def category(a: str, b: str) -> str | None:
    pair = {a, b}
    if pair == {"radial_work_rad0", "flat_study_probe"}:
        return "control: identical strips"
    if pair == {"radial_work_rad0", "radial_work_rad0b"}:
        return "same meshes, two stock flattens (layout only)"
    sa, sb = re.search(r"_s(\d)$", a), re.search(r"_s(\d)$", b)
    if not (sa and sb):
        return None
    ka, kb = a.split("_s")[0], b.split("_s")[0]
    same_seed = sa.group(1) == sb.group(1)
    if ka != kb and same_seed:
        return "same fit, deterministic vs stock flatten (layout only)"
    if ka == kb == "outer_curbase":
        return "different fits, both stock flatten"
    if ka == kb == "detfit":
        return "different fits, both deterministic flatten"
    if ka != kb:
        return "different fits, deterministic vs stock"
    return None


def summarise(d: dict) -> dict[str, dict[str, float]]:
    cats: dict[str, list[float]] = {}
    for p in d["pairs"]:
        c = category(p["a"], p["b"])
        if c:
            cats.setdefault(c, []).append(p["r"])
    return {
        c: {"n": len(v), "mean": st.mean(v), "min": min(v), "max": max(v)}
        for c, v in cats.items()
    }


def main() -> int:
    d = json.load(open(sys.argv[1]))
    for c, s in summarise(d).items():
        print(
            f"{c:<58} n={s['n']:>2}  mean {s['mean']:.3f}  [{s['min']:.3f}, {s['max']:.3f}]"
        )
    print(f"null (theta-rotated): {', '.join(f'{x:.3f}' for x in d['null_rotated'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
