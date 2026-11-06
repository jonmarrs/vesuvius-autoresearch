"""scripts/neural_tracer_link_splice.py: the splice rule, the chain gate and the registered decision table."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import neural_tracer_link_splice as ls  # noqa: E402


def line(x0, x1, n=41, y=0.0):
    """A straight fiber along x (zyx points), from x0 to x1."""
    x = np.linspace(x0, x1, n)
    return np.stack([np.zeros_like(x), np.full_like(x, y), x], axis=1)


def test_a_piece_overlapping_a_fibers_start_and_heading_into_it_is_a_candidate():
    # P runs +x and ends at x = 52; Q starts at x = 40 and runs on: P's end is 12 voxels into Q, as the tracer's kept
    # overlap leaves it.
    fibers = {1: line(0, 52), 2: line(40, 140, n=51, y=0.5)}
    meta = {
        1: (("bounds", "owned_or_live"), (-1, 2)),
        2: (("bounds", "bounds"), (-1, -1)),
    }
    cands, missing = ls.splice_candidates(fibers, meta)
    assert missing == 0
    assert [c[1:] for c in cands] == [(1, 1, 2, 0)]
    assert cands[0][0] == pytest.approx(0.5)


def test_heading_away_from_the_fiber_or_attaching_mid_body_is_not():
    # P's last point is at x = 52, 12 voxels into Q, but P arrives from +x: leaving that end it heads to -x, out of Q
    away = {1: line(120, 52, y=3.0), 2: line(40, 140, y=0.5)}
    meta = {
        1: (("bounds", "owned_or_live"), (-1, 2)),
        2: (("bounds", "bounds"), (-1, -1)),
    }
    assert ls.splice_candidates(away, meta)[0] == []
    # the same piece reversed is the same geometry: its first end, leaving toward +x... still heads out of Q
    rev = {1: line(52, 120, y=3.0), 2: line(40, 140, y=0.5)}
    assert (
        ls.splice_candidates(
            rev, {1: (("owned_or_live", "bounds"), (2, -1)), 2: meta[2]}
        )[0]
        == []
    )
    mid = {
        1: line(0, 90),
        2: line(40, 140, y=0.5),
    }  # P's end is 50 voxels into Q: mid-body
    meta = {
        1: (("bounds", "owned_or_live"), (-1, 2)),
        2: (("bounds", "bounds"), (-1, -1)),
    }
    assert ls.splice_candidates(mid, meta)[0] == []
    edge = {1: line(0, 40 + ls.SPLICE_ARC + 0.5, n=200), 2: line(40, 140, n=401, y=0.5)}
    assert ls.splice_candidates(edge, meta)[0] == []
    inside = {
        1: line(0, 40 + ls.SPLICE_ARC - 0.5, n=200),
        2: line(40, 140, n=401, y=0.5),
    }
    assert len(ls.splice_candidates(inside, meta)[0]) == 1


def test_no_link_a_missing_target_and_a_self_link_give_nothing():
    fibers = {1: line(0, 52), 2: line(40, 140, y=0.5)}
    meta = {
        1: (("bounds", "owned_or_live"), (1, 7)),
        2: (("bounds", "bounds"), (-1, -1)),
    }
    cands, missing = ls.splice_candidates(fibers, meta)
    assert cands == [] and missing == 1


def test_each_end_splices_once_nearest_first_and_rings_are_refused():
    cands = [(0.9, 1, 1, 2, 0), (0.2, 3, 1, 2, 0), (0.5, 2, 1, 4, 0), (0.6, 4, 1, 3, 0)]
    # 3's end takes 2's start (0.2 beats 0.9); 2's end takes 4's start; 4's end to 3's start would close 3-2-4-3
    assert ls.choose_splices(cands) == [(3, 1, 2, 0), (2, 1, 4, 0)]
    assert ls.chain_problems(ls.choose_splices(cands), cands) == []


def test_the_chain_gate_catches_a_reused_end_a_ring_and_a_stranger():
    cands = [(0.1, 1, 1, 2, 0), (0.2, 3, 1, 2, 0), (0.3, 2, 1, 1, 0)]
    assert "end_reused" in ls.chain_problems([(1, 1, 2, 0), (3, 1, 2, 0)], cands)
    assert "ring" in ls.chain_problems([(1, 1, 2, 0), (2, 1, 1, 0)], cands)
    assert "not_a_candidate" in ls.chain_problems([(1, 0, 2, 0)], cands)


def test_relabel_joins_chains_and_leaves_the_rest():
    grown = np.array([[0, 1, 2], [3, 4, 4]], dtype=np.int32)
    assert (ls.relabel(grown, []) == grown).all()
    assert ls.relabel(grown, [(2, 3), (3, 4)]).tolist() == [[0, 1, 2], [2, 2, 2]]


def test_kinds():
    cov = {1: {0}, 2: {0, 1}, 3: {2}, 4: set()}
    assert ls.kinds([(1, 2), (1, 3), (1, 4), (5, 1)], cov) == {
        "same": 1,
        "different": 1,
        "unknown": 2,
    }


def cube(gain2, gain4, merges=(10, 10), kinds=(9, 0, 1)):
    row = lambda g, m: {"gain": g, "merges": m}  # noqa: E731
    return {
        "tol2": {
            "splice": row(gain2, merges[1]),
            "base": {"merges": merges[0]},
            "kinds": {
                "splice": dict(
                    zip(("same", "different", "unknown"), kinds, strict=False)
                )
            },
        },  # fmt: skip
        "tol4": {"splice": row(gain4, merges[1])},
    }


def verdict_of(gain2, gain4, **kw):
    return ls.verdict(
        {c: cube(gain2, gain4, **kw) for c in ls.HELD_OUT}, {c: [] for c in ls.HELD_OUT}
    )


def test_the_decision_table():
    assert verdict_of(0.12, 0.3)["decision"] == "SUPPORTED"
    assert verdict_of(0.05, 0.3)["decision"] == "SUPPORTED_AT_TOL4_ONLY"
    assert verdict_of(0.05, 0.05)["decision"] == "NOT_SUPPORTED"
    assert verdict_of(0.5, 0.5, merges=(100, 106))["decision"] == "COSTS_MERGES"
    assert (
        verdict_of(0.5, 0.5, merges=(100, 105))["decision"] == "SUPPORTED"
    )  # 5% is allowed
    v = verdict_of(0.10, 0.10, kinds=(95, 5, 3))
    assert (
        v["decision"] == "SUPPORTED"
        and v["predictions"]["P4"]
        and v["wrong_share_tol2"] == pytest.approx(0.05)
    )
    assert not verdict_of(0.10, 0.10, kinds=(94, 6, 3))["predictions"]["P4"]


def test_no_verdict_on_a_gate_failure_a_partial_set_or_no_baseline():
    per = {c: cube(0.5, 0.5) for c in ls.HELD_OUT}
    gate = {c: [] for c in ls.HELD_OUT}
    assert (
        ls.verdict(per, dict(gate, **{ls.HELD_OUT[0]: ["tol2:row:erl"]}))["status"]
        == "GATE_FAILED"
    )
    assert ls.verdict({c: per[c] for c in ls.HELD_OUT[1:]}, gate)["status"] == "PARTIAL"
    per[ls.HELD_OUT[0]] = cube(None, 0.5)
    assert ls.verdict(per, gate)["status"] == "NO_BASELINE"


def test_the_held_out_cubes_decide_and_the_record_is_written_once(tmp_path):
    assert len(ls.HELD_OUT) == 10 and not set(ls.HELD_OUT) & set(ls.IN_SAMPLE)
    out = tmp_path / "r.json"
    out.write_text("{}")
    with pytest.raises(SystemExit, match="written once"):
        ls.main(["--out", str(out)])
