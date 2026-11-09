"""scripts/afv_generator_seam_diag_summary.py, which reduced the diagnosis behind finding 106's lost crossings: its
counts on a hand-made diagnosis record, its refusal of a record for another trim, and the committed diagnosis script
the evidence says ran."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_seam_diag_summary as su  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "scripts/afv_generator_seam_diag.py"


def copy(sid, block, share, chain, chain_length=300.0):
    return {"sid": sid, "block": f"block-{block}", "length": chain_length, "share": share, "chain": chain,
            "chain_length": chain_length}  # fmt: skip


def crossing(main, patched, sources, cover=None):
    """``main`` and ``patched``: the (stitched, written) kinds; ``sources``: per variant, the covering copies and pairs."""
    cover = cover or {v: {"best": 1.0, "union": 1.0, "n": 1} for v in bs.VARIANTS}
    return {"main": dict(zip(("stitched", "written"), main, strict=True)),
            "patched": dict(zip(("stitched", "written"), patched, strict=True)),
            "sources": [{"variant": v, "covering": c, "pairs": p} for v, (c, p) in sources.items()],
            "written_cover": cover}  # fmt: skip


def overlap(a, b, *options):
    return {"a": a, "b": b, "catalogue": "candidate",
            "candidates": [{"kind": "overlap", "options_a": x, "options_b": y} for x, y in options]}  # fmt: skip


def rejected(a, b, compare=None, deepest=None):
    return {"a": a, "b": b, "catalogue": "none", "compare": compare, "deepest": deepest}


# fmt: off
APART = ([copy(1, 0, 0.6, 10), copy(2, 1, 0.5, 11)], [])
JOINED = ([copy(1, 0, 0.6, 20), copy(2, 1, 0.5, 20)], [])
DETAILS = [
    # better at stitching: the copies main left apart, chained with the trim
    crossing(("broken", "broken"), ("whole", "whole"), {"main": APART, "patched": JOINED}),
    # the same kind with and without the trim: not counted
    crossing(("whole", "whole"), ("whole", "whole"), {"main": APART, "patched": APART}),
    # worse at cleanup, a join lost. Copy 7 shares chain 30 with copy 5 but covers under 20% of the window, so the
    # trimmed copies are not chained, and its pair with copy 5 gives no reason.
    crossing(("whole", "whole"), ("whole", "lost"), {
        "main": ([copy(1, 0, 0.9, 40), copy(2, 1, 0.5, 40)], []),
        "patched": ([copy(5, 0, 0.7, 30), copy(6, 1, 0.4, 31), copy(7, 1, 0.15, 30), copy(9, 2, 0.3, 34)],
                    [overlap(5, 6, (2, 1)), rejected(5, 7, compare="duplicate"),
                     rejected(6, 9, deepest="if max_angle > MAX_ANGLE:"),
                     {"a": 5, "b": 9, "catalogue": "dup"}])}),
    # worse at stitching, a join lost: a lone overlap candidate, a gap candidate, and a short unique tail
    crossing(("broken", "broken"), ("lost", "lost"), {
        "main": ([copy(1, 0, 0.9, 41), copy(2, 1, 0.5, 41)], []),
        "patched": ([copy(5, 0, 0.7, 30), copy(6, 1, 0.4, 31), copy(8, 3, 0.25, 35)],
                    [overlap(5, 6, (1, 1)),
                     {"a": 5, "b": 8, "catalogue": "candidate", "candidates": [{"kind": "gap"}]},
                     rejected(6, 8, deepest="if overlap_start_a <= MIN_UNIQUE_TAIL and x:")])}),
    # worse, chained in neither: the other block's covering copy is a chain under --min-length (copy 15 is longer
    # but covers under 20% of the window)
    crossing(("whole", "whole"), ("broken", "broken"), {
        "main": ([copy(11, 0, 0.95, 50), copy(12, 1, 0.3, 51, 60.0)], []),
        "patched": ([copy(13, 0, 0.9, 60), copy(14, 1, 0.3, 61, 60.0), copy(15, 1, 0.12, 62, 500.0)], [])},
        {"main": {"best": 0.97, "union": 1.0, "n": 2}, "patched": {"best": 0.73, "union": 0.9, "n": 1}}),
    # worse at cleanup, chained in neither: the other block's chain is exactly --min-length, which clean() keeps
    crossing(("whole", "whole"), ("whole", "lost"), {
        "main": ([copy(11, 0, 0.95, 50)], []),
        "patched": ([copy(16, 0, 0.8, 70), copy(17, 1, 0.5, 71, 100.0)], [])},
        {"main": {"best": 1.0, "union": 1.0, "n": 1}, "patched": {"best": 0.0, "union": 0.0, "n": 0}}),
]
# fmt: on


def check(row):
    return {
        "written": [row["written"]] * 2,
        "length": [row["length"]] * 2,
        "crossings": [row["crossings"]] * 2,
    }


ROW = {f"real/{v}": {"written": 10, "length": 1234.5, "crossings": {"whole": 3, "broken": 2, "lost": 1}}
       for v in bs.VARIANTS}  # fmt: skip


def diag(cube="c", arm="real", cut_end=16.0, row=ROW, details=DETAILS):
    return {"cube": cube, "arm": arm, "cut_end": cut_end, "n_crossings": 6, "transitions_main_to_patched": {},
            "variants": {v: {"check": check(row[f"{arm}/{v}"])} for v in bs.VARIANTS}, "details": details}  # fmt: skip


def test_each_changed_crossing_is_counted_by_side_stage_join_and_reason():
    s = su.summarize(diag(), ROW)
    assert s["reproduces_record"]
    assert (s["better"], s["worse"]) == (
        {"at stitching": 1},
        {"at cleanup": 2, "at stitching": 2},
    )
    assert s["changed_kinds"] == {"broken->lost at stitching": 1, "broken->whole at stitching": 1,
                                  "whole->broken at stitching": 1, "whole->lost at cleanup": 2}  # fmt: skip
    assert s["better_by_join"] == {"chained only with the trim": 1}
    assert s["worse_by_join"] == {"chained only in main": 2, "chained in neither": 2}
    assert s["reasons_chained_only_in_main"] == {
        "a copy has less than 8 voxels beyond the overlap": 1,
        "a gap candidate, not linked": 1,
        "an overlap candidate made ambiguous by another at the same end": 1,
        "an overlap candidate, the only one, not linked": 1,
        "recorded as a duplicate": 1,
        "the ends meet at more than 15°": 1,
    }
    # main's best written fiber first, then the trimmed one's; one of the two has only short copies elsewhere
    assert s["chained_in_neither_best_share"] == [[0.97, 0.73], [1.0, 0.0]]
    assert s["chained_in_neither_neighbour_short"] == 1
    assert (
        s["written_cover_of_worse"]["whole->broken: main 2 fibers, patched a lone copy"]
        == 1
    )


def test_a_rebuild_that_misses_any_figure_of_the_record_does_not_reproduce_it():
    for field, wrong in (
        ("written", 11),
        ("length", 1234.0),
        ("crossings", {"whole": 4, "broken": 2, "lost": 0}),
    ):
        row = {k: dict(v) for k, v in ROW.items()}
        row["real/patched"] = dict(row["real/patched"], **{field: wrong})
        assert not su.summarize(diag(row=row, details=[]), ROW)["reproduces_record"], (
            field
        )


def test_the_totals_add_counts_join_lists_and_require_every_reproduction():
    total = {}
    su.add(
        total,
        {"n": 2, "reproduces_record": True, "shares": [[1.0, 0.5]], "by": {"x": 1}},
    )
    su.add(
        total,
        {
            "n": 3,
            "reproduces_record": False,
            "shares": [[0.9, 0.7]],
            "by": {"x": 2, "y": 1},
        },
    )
    assert total == {
        "n": 5,
        "reproduces_record": False,
        "shares": [[1.0, 0.5], [0.9, 0.7]],
        "by": {"x": 3, "y": 1},
    }


def test_the_summary_refuses_a_diagnosis_of_another_trim_and_the_committed_script_is_the_one_cited(
    tmp_path, monkeypatch
):
    record = json.loads(su.RECORD.read_text())
    out = tmp_path / "diag"
    out.mkdir()
    for c in bs.HELD_OUT:
        for arm in ("real", "same"):
            rows = record["cubes"][c]["rows"]
            d = diag(c, arm, record["cubes"][c]["cut_end"], rows, [])
            (out / f"{c}_{arm}.json").write_text(json.dumps(d))
    argv = [
        "x",
        str(out),
        "--diag-script",
        str(DIAG),
        "--committed",
        str(DIAG),
        "--out",
        str(tmp_path / "s.json"),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    su.main()
    s = json.loads((tmp_path / "s.json").read_text())
    assert (
        s["committed_copy_same_syntax_tree"]
        and s["totals"]["real"]["reproduces_record"]
    )
    # the evidence was written with this script's syntax tree; the script itself is pinned, as reformatted
    assert hashlib.sha256(DIAG.read_bytes()).hexdigest() == (
        "7294deeef4ae0a1d64e03e8329cd5c6a050073381478fe047f3995b571f4ec6d"
    )
    c = bs.HELD_OUT[0]
    (out / f"{c}_real.json").write_text(
        json.dumps(diag(c, "real", 12.0, record["cubes"][c]["rows"], []))
    )
    with pytest.raises(AssertionError):
        su.main()
