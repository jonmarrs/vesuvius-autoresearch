"""Does flooring the replicate rule's SD at the field's stop near-no-op promotions and keep the one known gain?

The live rule (scripts/training/replicate_rule.py) takes Student's t of a tweak's cycles minus the other tweaks' epoch
mean, so only the tweak's own spread enters it. On 2026-10-29 it promoted lr 1e-5 at t 5.57 on +0.0002 val_f1: a
15-minute fine-tune at that rate leaves the incumbent almost unchanged, so its six cycles spread 0.00004 against the
field's 0.0019. The amendment (docs/preregistration/2026-10-31_loop_replicate_rule_sd_floor.md) floors each t's SD at
the field's: the SD of the same difference over every other tweak's cycles so far (scores(..., floor=True)).

This replays both rules, cycle by cycle as the loop would, on three windows: the 546 cycles batchgeneratorsv2 was
found in (10-17 to 10-25), the confirmation's 135 (10-25 to 10-27), and the 161 the live rule read when it promoted
lr 1e-5 (10-27 to 10-29, from the loop's cycles.jsonl as it stood on 10-30). It also gives the floored rule's
false-promotion rate under #244's two shuffle nulls on the 546 cycles, and its power under the registered window
test's simulation. All three windows were seen before the amendment was written; only the nulls and the power
simulation are not in-sample.

    python3 scripts/loop_replicate_rule_floor.py --cycles local_data/unchanged_control/cycles_2026-10-30.jsonl \
        --out reports/loop_replicate_rule_sd_floor_2026-10-31.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import loop_replicate_rule as L  # noqa: E402
from scripts.training import replicate_rule as R  # noqa: E402

DISCOVERY = "reports/loop_tweak_replication_2026-10-25.json"
CONFIRMATION = "reports/loop_tweak_confirmation_corrected_2026-10-27.json"
PROMOTION = "2026-10-29T12:40:35"  # the cycle the live rule promoted lr 1e-5 on
RULE = L.LIVE


def promotion_window(records: list[dict], started: str = PROMOTION) -> list[dict]:
    """The rows the live rule read at the end of the cycle that started at `started`, that cycle last."""
    (j,) = [i for i, r in enumerate(records) if r.get("started") == started]
    return R.rows(records[:j], records[j])


def replay(rows: list[dict], rule: dict = RULE) -> dict:
    """Both rules' scores on rows in order: each one's first firing and every tweak's best score."""
    labels = [r["tweak"] for r in rows]
    measures = L.MEASURES[rule["measures"]]
    out = {"cycles": len(rows), "tweaks": len(set(labels))}
    for name, floor in (("live", False), ("floored", True)):
        s = L.scores(rows, labels, measures, rule["min_cycles"], rule["min_others"], floor=floor)  # fmt: skip
        fired = [j for j, x in enumerate(s) if x > rule["c"]]
        best = defaultdict(lambda: -math.inf)
        for j, x in enumerate(s):
            best[labels[j]] = max(best[labels[j]], float(x))
        first = None
        if fired:
            j = fired[0]
            first = {
                "start": rows[j]["start"],
                "tweak": labels[j],
                "tweak_cycles_so_far": labels[: j + 1].count(labels[j]),
                "score": round(float(s[j]), 4),
            }
        out[name] = {
            "first_promotion": first,
            "tweaks_fired": sorted({labels[j] for j in fired}),
            "best": {
                t: L._finite(x)
                for t, x in sorted(best.items(), key=lambda kv: -kv[1])
                if math.isfinite(x)
            },  # fmt: skip
        }
    return out


def nulls(record: dict, permutations: int = L.PERMUTATIONS, seed: int = L.SEED, rule: dict = RULE) -> dict:  # fmt: skip
    """The floored rule's false promotions per window under #244's shuffle nulls (the same shuffles, same seed)."""
    rows = sorted(record["rows"], key=lambda r: r["start"])
    measures = L.MEASURES[rule["measures"]]
    rng = np.random.default_rng(seed)
    shuffles = [L.shuffled(rows, rng) for _ in range(permutations)]
    flat = L.centred(rows, measures)
    args = (measures, rule["min_cycles"], rule["min_others"])
    out = {}
    for name, base in (("shuffled", rows), ("centred", flat)):
        maxima = [round(float(L.scores(base, lab, *args, floor=True).max()), 6) for lab in shuffles]  # fmt: skip
        k = sum(m > rule["c"] for m in maxima)
        out[name] = {"false_promotions": k, "rate": k / permutations, "ci95": L.clopper_pearson(k, permutations), "maxima": maxima}  # fmt: skip
    return {"permutations": permutations, "seed": seed, **out}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--cycles", type=Path, required=True, help="the loop's cycles.jsonl as of 10-30"
    )
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    raw = args.cycles.read_bytes()
    records = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    window = promotion_window(records)
    sources = {"cycles": {"path": str(args.cycles), "sha256": hashlib.sha256(raw).hexdigest(), "records": len(records)}}  # fmt: skip
    windows = {}
    for name, path in (("discovery", DISCOVERY), ("confirmation", CONFIRMATION)):
        data = (ROOT / path).read_bytes()
        sources[name] = {"path": path, "sha256": hashlib.sha256(data).hexdigest()}
        windows[name] = replay(
            sorted(json.loads(data)["rows"], key=lambda r: r["start"])
        )
    windows["lr_1e-05_promotion"] = replay(window)
    discovery = json.loads((ROOT / DISCOVERY).read_bytes())
    out = {
        "rule": RULE,
        "sources": sources,
        "windows": windows,
        "nulls": nulls(discovery),
        "power": L.power(discovery, reg=RULE),
        "rows": {"lr_1e-05_promotion": window},
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    for name, w in windows.items():
        print(
            name,
            {
                k: (w[k]["first_promotion"] or {}).get("tweak")
                for k in ("live", "floored")
            },
        )
    print(
        "nulls",
        {k: out["nulls"][k]["false_promotions"] for k in ("shuffled", "centred")},
    )
    print("power", [(s["scale"], s["outcomes"]) for s in out["power"]["scales"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
