"""Reduce scripts/afv_generator_seam_diag.py's per-cube records to the evidence finding 106 cites.

The diagnosis ran after the verdict (not registered). For each held-out cube and arm it rebuilt main's and the patched
stitching from the chain's cached fields and followed every reference crossing of a block face through four stages
(pieces, catalogue sources, stitched chains, written fibers). This keeps, per cube and arm:

* whether the rebuild reproduced the record's row (fibers written, their length, the crossing counts);
* the crossing transitions main -> patched;
* each crossing worse (or better) with the trim, by where it first differs: **at stitching** when the patched stitched
  chains are already worse (better) than main's, **at cleanup** when only `clean()` (sharp joins cut, exterior,
  `--min-length`) makes it so;
* each such crossing by whether its copies were chained: a catalogue chain holds copies from two blocks, each covering
  at least 20% of the window, in main, with the trim, both or neither;
* for the worse crossings whose copies main chained and the trim leaves apart, why the catalogue did not link the
  trimmed copies (a crossing can have several reasons);
* for the worse crossings chained in neither, the best single written fiber's share of the window, main and patched,
  and whether every copy from the other blocks is a chain shorter than `--min-length`;
* how many written fibers cover at least 10% of each worse crossing's window, main and patched.

The diagnosis script is committed as scripts/afv_generator_seam_diag.py, reformatted and exempted from lint but with
the syntax tree of the file that ran; `--committed` checks that.

Usage: python scripts/afv_generator_seam_diag_summary.py DIAG_OUT --diag-script RAN --committed COPY --out JSON
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import afv_generator_block_seams as bs  # noqa: E402

RANK = {"whole": 2, "broken": 1, "lost": 0}
RECORD = Path(__file__).resolve().parents[1] / "reports/afv_generator_block_seams.json"

# compare()'s rejecting test (extend/overlap.py at villa 7e6b82164), as the report words it
REJECTS = {
    "if max_angle > MAX_ANGLE:": "the ends meet at more than 15°",
    "if min(sa[-1], sb[-1]) < MIN_OVERLAP:": "the overlap is shorter than 24 voxels",
    "if min(overlap_a, overlap_b) < MIN_OVERLAP:": "the overlap is shorter than 24 voxels",
    "if da[-1] > MAX_P90 or db[0] > MAX_P90:": "the copies lie more than 3 voxels apart at an end",
}


def reason(pair: dict) -> str:
    rec = pair["catalogue"]
    if rec == "candidate":
        out = set()
        for r in pair["candidates"]:
            if r["kind"] == "overlap":
                many = max(r["options_a"], r["options_b"]) > 1
                out.add("an overlap candidate made ambiguous by another at the same end" if many
                        else "an overlap candidate, the only one, not linked")  # fmt: skip
            else:
                out.add("a gap candidate, not linked")
        return "; ".join(sorted(out))
    if rec == "dup":
        return "recorded as a duplicate"
    if pair["compare"] == "duplicate":
        return "one copy lies along the other, but the catalogue keeps both"
    deepest = pair.get("deepest") or ""
    if deepest.startswith("if overlap_start_a <= MIN_UNIQUE_TAIL"):
        return "a copy has less than 8 voxels beyond the overlap"
    return REJECTS.get(deepest, f"other: {deepest}")


def cover(v: dict) -> str:
    return "a lone copy" if v["n"] == 1 else f"{v['n']} fibers"


def covering(src: dict) -> list[dict]:
    return [c for c in src["covering"] if c["share"] >= 0.2]


def chained(src: dict) -> bool:
    """A catalogue chain holds covering copies from two blocks."""
    blocks: dict[int, set] = {}
    for c in covering(src):
        if c["chain"] is not None:
            blocks.setdefault(c["chain"], set()).add(c["block"])
    return any(len(b) > 1 for b in blocks.values())


def neighbour_short(src: dict) -> bool:
    """Every covering copy from a block other than the best one's is a chain shorter than --min-length."""
    cov = covering(src)
    top = max(cov, key=lambda c: c["share"])["block"]
    return all(c["chain_length"] < bs.MIN_LENGTH for c in cov if c["block"] != top)


def join(main: bool, patched: bool) -> str:
    return {(False, True): "chained only with the trim", (True, False): "chained only in main",
            (False, False): "chained in neither", (True, True): "chained in both"}[main, patched]  # fmt: skip


def summarize(d: dict, row: dict) -> dict:
    out = {
        "n_crossings": d["n_crossings"],
        "transitions": d["transitions_main_to_patched"],
    }
    out["reproduces_record"] = all(
        v["check"]["written"][0]
        == v["check"]["written"][1]
        == row[f"{d['arm']}/{k}"]["written"]
        and v["check"]["length"][0]
        == v["check"]["length"][1]
        == row[f"{d['arm']}/{k}"]["length"]
        and {**dict.fromkeys(RANK, 0), **v["check"]["crossings"][0]}
        == row[f"{d['arm']}/{k}"]["crossings"]
        for k, v in d["variants"].items()
    )
    split = {s: Counter() for s in ("better", "worse")}
    joins = {s: Counter() for s in ("better", "worse")}
    kinds, reasons, covers = Counter(), Counter(), Counter()
    shares, short = [], 0
    for x in d["details"]:
        m, p = x["main"], x["patched"]
        dw = RANK[p["written"]] - RANK[m["written"]]
        if dw == 0:
            continue
        side = "worse" if dw < 0 else "better"
        ds = RANK[p["stitched"]] - RANK[m["stitched"]]
        where = (
            "at stitching" if (ds < 0 if side == "worse" else ds > 0) else "at cleanup"
        )
        split[side][where] += 1
        kinds[f"{m['written']}->{p['written']} {where}"] += 1
        sm, sp = (
            next(v for v in x["sources"] if v["variant"] == k) for k in bs.VARIANTS
        )
        j = join(chained(sm), chained(sp))
        joins[side][j] += 1
        if side == "worse":
            wc = x["written_cover"]
            covers[
                f"{m['written']}->{p['written']}: main {cover(wc['main'])}, patched {cover(wc['patched'])}"
            ] += 1
            if j == "chained only in main":
                big = {c["sid"] for c in covering(sp)}
                rs = {
                    reason(q)
                    for q in sp["pairs"]
                    if q["a"] in big and q["b"] in big and q["catalogue"] != "linked"
                }
                reasons.update(rs or {"every covering pair linked"})
            elif j == "chained in neither":
                shares.append([wc["main"]["best"], wc["patched"]["best"]])
                short += neighbour_short(sp)
    out.update(
        better=dict(split["better"]), worse=dict(split["worse"]), changed_kinds=dict(sorted(kinds.items())),
        better_by_join=dict(joins["better"]), worse_by_join=dict(joins["worse"]),
        reasons_chained_only_in_main=dict(sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))),
        chained_in_neither_best_share=shares, chained_in_neither_neighbour_short=short,
        written_cover_of_worse=dict(sorted(covers.items())),
    )  # fmt: skip
    return out


def add(total: dict, part: dict) -> None:
    for k, v in part.items():
        if isinstance(v, dict):
            add(total.setdefault(k, {}), v)
        elif isinstance(v, list):
            total.setdefault(k, []).extend(v)
        elif isinstance(v, bool):
            total[k] = total.get(k, True) and v
        else:
            total[k] = total.get(k, 0) + v


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("diag_out", type=Path)
    ap.add_argument("--diag-script", type=Path, required=True, help="the file that ran")
    ap.add_argument("--committed", type=Path, required=True, help="its committed copy")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    record = json.loads(RECORD.read_text())
    result = {
        "about": __doc__.split("\n\n")[0],
        "diag_script_sha256": hashlib.sha256(args.diag_script.read_bytes()).hexdigest(),
        "committed_copy_same_syntax_tree": ast.dump(
            ast.parse(args.diag_script.read_text())
        )
        == ast.dump(ast.parse(args.committed.read_text())),
        "record": RECORD.relative_to(RECORD.parents[1]).as_posix(),
        "cubes": {},
        "totals": {},
    }
    for c in bs.HELD_OUT:
        for arm in ("real", "same"):
            d = json.loads((args.diag_out / f"{c}_{arm}.json").read_text())
            assert (d["cube"], d["arm"], d["cut_end"]) == (
                c,
                arm,
                record["cubes"][c]["cut_end"],
            )
            s = summarize(d, record["cubes"][c]["rows"])
            result["cubes"].setdefault(c, {})[arm] = s
            add(result["totals"].setdefault(arm, {}), s)
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
