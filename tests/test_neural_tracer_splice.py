"""scripts/neural_tracer_splice.py: chains, joints, and a run directory read as villa's tracing.volume writes it;
and scripts/neural_tracer_splice_check.py's scoring and gate, with stand-ins for ScrollGT."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import neural_tracer_link_splice as ls  # noqa: E402
import neural_tracer_splice as sp  # noqa: E402


def line(x0, x1, n, y=0.0):
    """xyz points along x."""
    x = np.linspace(x0, x1, n)
    return np.stack([x, np.full_like(x, y), np.zeros_like(x)], axis=1)


def test_chains_are_read_from_a_free_end_with_orientations():
    # 1's end -> 2's start; 3's start -> 2's end (3 runs backwards)
    assert sp.chains([1, 2, 3, 4], [(1, 1, 2, 0), (3, 0, 2, 1)]) == [
        [(1, False), (2, False), (3, False)],
        [(4, False)],
    ]
    assert sp.chains([1, 2], [(1, 0, 2, 0)]) == [[(1, True), (2, False)]]


def test_rings_and_reused_ends_are_refused():
    with pytest.raises(ValueError, match="twice"):
        sp.chains([1, 2, 3], [(1, 1, 2, 0), (3, 1, 2, 0)])
    with pytest.raises(ValueError, match="ring"):
        sp.chains([1, 2], [(1, 1, 2, 0), (2, 1, 1, 0)])


def test_a_joint_drops_the_duplicated_overlap_and_keeps_order():
    a = line(0, 52, 53)
    b = line(40, 100, 61, y=0.5)  # starts 12 voxels before a's end
    poly, info = sp.join({1: a, 2: b}, [(1, False), (2, False)])
    assert info["dropped"] == [13]  # b's points x = 40..52 lie beside a's last 12
    assert info["gaps"][0] == pytest.approx(np.hypot(1.0, 0.5))
    assert np.all(np.diff(poly[:, 0]) > 0) and (poly[0, 0], poly[-1, 0]) == (0, 100)
    assert len(poly) == 53 + 61 - 13


def test_reversed_pieces_join_the_same_way():
    a = line(52, 0, 53)  # a's first point is at x 52
    b = line(100, 40, 61, y=0.5)  # b's last point is at x 40
    poly, info = sp.join({1: a, 2: b}, sp.chains([1, 2], [(1, 0, 2, 1)])[0])
    assert {round(poly[0, 0]), round(poly[-1, 0])} == {0, 100}
    assert np.all(np.abs(np.diff(poly[:, 0])) <= 1.5)


def write_run(
    out: Path, pieces: dict, links: dict, grid_scale=2.0, overlap=16, tiles=1
):
    """A tracing.volume OUT directory: run.json and tiles/*.npz, in villa's tile schema, points on the trace grid."""
    (out / "tiles").mkdir(parents=True)
    (out / "run.json").write_text(
        json.dumps({"grid_scale": grid_scale, "overlap": overlap})
    )
    ids = sorted(pieces)
    for t in range(tiles):
        mine = ids[t::tiles]
        pts = [pieces[i] / grid_scale for i in mine]
        np.savez(out / "tiles" / f"z{t:05d}_y00000_x00000.npz",
                 points=np.concatenate(pts).astype(np.float32), offsets=np.cumsum([0] + [len(p) for p in pts]),
                 id=np.array(mine, int), seed=np.zeros((len(mine), 3)), family=np.array(["H"] * len(mine)),
                 plane=np.array(["z0"] * len(mine)), reasons=np.array([("bounds", "owned_or_live")] * len(mine)),
                 links=np.array([links.get(i, (-1, -1)) for i in mine], int).reshape(-1, 2))  # fmt: skip


def test_a_run_directory_is_spliced_and_written(tmp_path):
    pieces = {
        3: line(0, 52, 53),
        8: line(40, 100, 61, y=0.5),
        9: line(0, 20, 21, y=40.0),
    }
    write_run(tmp_path / "run", pieces, {3: (-1, 8)}, tiles=2)
    got, meta, run = sp.load_run(tmp_path / "run")
    assert set(got) == {3, 8, 9} and all(
        np.allclose(got[k], pieces[k], atol=1e-4) for k in got
    )
    assert meta[3] == (("bounds", "owned_or_live"), (-1, 8))
    polys, members, summary = sp.splice(
        got, meta, float(run["overlap"]) * float(run["grid_scale"])
    )
    assert members == {3: [3, 8], 9: [9]}
    assert (
        summary["splices"] == 1
        and summary["fibers"] == 2
        and summary["dropped_points"] == 13
    )
    assert summary["arc_limit"] == 32.0 == ls.SPLICE_ARC
    out = tmp_path / "spliced.npz"
    assert sp.main([str(tmp_path / "run"), "--write", str(out)]) == 0
    z = np.load(out)
    assert (
        z["id"].tolist() == [3, 9]
        and z["members"].tolist() == [3, 8, 9]
        and z["member_offsets"].tolist() == [0, 2, 3]
    )
    assert np.allclose(z["points"][z["offsets"][0] : z["offsets"][1]], polys[3])
    with pytest.raises(SystemExit, match="exists"):
        sp.main([str(tmp_path / "run"), "--write", str(out)])


def test_the_arc_limit_follows_the_runs_overlap(tmp_path):
    """A piece end 12 voxels into the next fiber splices at overlap 16 x grid 2 (32), not at overlap 4 x grid 2 (8)."""
    pieces = {1: line(0, 52, 53), 2: line(40, 100, 61, y=0.5)}
    for overlap, splices in ((16, 1), (4, 0)):
        d = tmp_path / f"o{overlap}"
        write_run(d, pieces, {1: (-1, 2)}, overlap=overlap)
        got, meta, run = sp.load_run(d)
        assert (
            sp.splice(got, meta, float(run["overlap"]) * float(run["grid_scale"]))[2][
                "splices"
            ]
            == splices
        )


def test_a_piece_written_twice_or_an_empty_run_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="no finished tile"):
        (tmp_path / "e" / "tiles").mkdir(parents=True)
        (tmp_path / "e" / "run.json").write_text(
            json.dumps({"grid_scale": 2, "overlap": 16})
        )
        sp.load_run(tmp_path / "e")
    d = tmp_path / "twice"
    write_run(d, {1: line(0, 10, 11)}, {})
    z = dict(np.load(d / "tiles" / "z00000_y00000_x00000.npz"))
    np.savez(d / "tiles" / "z00001_y00000_x00000.npz", **z)
    with pytest.raises(SystemExit, match="written twice"):
        sp.load_run(d)


def test_a_chain_is_keyed_by_its_smallest_piece_wherever_it_lies():
    # piece 1 lies between 5 and 7: the chain is read from 5's free end, and keyed 1
    pieces = {
        5: line(0, 52, 53),
        1: line(40, 100, 61, y=0.5),
        7: line(88, 150, 63, y=1.0),
    }
    polys, members, _ = sp.splice(
        pieces, {5: ((), (-1, 1)), 1: ((), (-1, 7)), 7: ((), (-1, -1))}, 32.0
    )
    assert members == {1: [5, 1, 7]} and list(polys) == [1]


def test_the_command_line_scales_the_overlap_by_the_grid(tmp_path, capsys):
    """A piece end 20 voxels into the next fiber: within overlap 16 x grid 2 = 32, beyond 16."""
    pieces = {1: line(0, 60, 61), 2: line(40, 100, 61, y=0.5)}
    write_run(tmp_path / "run", pieces, {1: (-1, 2)})
    assert sp.main([str(tmp_path / "run"), "--write", str(tmp_path / "s.npz")]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["arc_limit"] == 32.0 and summary["splices"] == 1


def test_an_unfinished_tile_is_not_read(tmp_path):
    """villa's save_tile writes TILE.partial.npz and renames it when the tile is done; its load_done skips the rest."""
    write_run(tmp_path / "run", {1: line(0, 10, 11)}, {})
    write_run(tmp_path / "other", {2: line(0, 10, 11, y=5.0)}, {})
    (tmp_path / "other" / "tiles" / "z00000_y00000_x00000.npz").rename(
        tmp_path / "run" / "tiles" / "z00001_y00000_x00000.partial.npz"
    )
    assert set(sp.load_run(tmp_path / "run")[0]) == {1}
    (tmp_path / "run" / "tiles" / "z00000_y00000_x00000.npz").unlink()
    with pytest.raises(SystemExit, match="no finished tile"):
        sp.load_run(tmp_path / "run")


def test_the_written_file_is_the_one_checked(tmp_path):
    """np.savez adds .npz to a name without it, past the exists check: such a name is refused."""
    write_run(tmp_path / "run", {1: line(0, 10, 11)}, {})
    (tmp_path / "s.npz").write_bytes(b"an earlier result")
    with pytest.raises(SystemExit, match=r"must end in \.npz"):
        sp.main([str(tmp_path / "run"), "--write", str(tmp_path / "s")])
    assert (tmp_path / "s.npz").read_bytes() == b"an earlier result"


def test_a_link_to_piece_zero_is_a_link():
    """villa numbers pieces from 0."""
    pieces = {0: line(40, 100, 61, y=0.5), 1: line(0, 52, 53)}
    _, members, summary = sp.splice(pieces, {0: ((), (-1, -1)), 1: ((), (-1, 0))}, 32.0)
    assert summary["links"] == 1 and summary["splices"] == 1
    assert members == {0: [0, 1]}


def test_the_joint_gaps_are_summarized_by_their_median_and_maximum():
    """The report quotes these: each cube's median joint gap, and the largest."""
    pieces = {
        1: line(0, 52, 53),
        2: line(40, 100, 61, y=0.5),
        3: line(88, 150, 63, y=3.5),
        4: line(138, 200, 63, y=3.5),
    }
    meta = {1: ((), (-1, 2)), 2: ((), (-1, 3)), 3: ((), (-1, 4)), 4: ((), (-1, -1))}
    _, members, summary = sp.splice(pieces, meta, 32.0)
    assert members == {1: [1, 2, 3, 4]}
    # gaps, in chain order: hypot(1, 0.5), hypot(1, 3), 1
    assert summary["joint_gap_median"] == pytest.approx(np.hypot(1.0, 0.5))
    assert summary["joint_gap_max"] == pytest.approx(np.hypot(1.0, 3.0))


def test_splices_that_break_the_chain_rules_are_refused(monkeypatch):
    pieces = {1: line(0, 52, 53), 2: line(40, 100, 61, y=0.5)}
    monkeypatch.setattr(sp.ls, "choose_splices", lambda c: [(1, 1, 2, 0), (1, 1, 2, 0)])
    with pytest.raises(ValueError, match="chain rules"):
        sp.splice(pieces, {1: ((), (-1, 2)), 2: ((), (-1, -1))}, 32.0)


def fake_scrollgt(monkeypatch, fields):
    """Stand-ins for ScrollGT's scorer: ERLpen is the largest label's voxel count, ERL one more, coverage the labelled
    voxels, merges the number of labels; growing changes nothing."""

    def row(vol):
        labs, n = np.unique(vol[vol > 0], return_counts=True)
        out = dict.fromkeys(fields, 0.0)
        out.update(erl=float(n.max()) + 1, erl_merge_penalized=float(n.max()),
                   coverage=float(n.sum()), merges=len(labs))  # fmt: skip
        return out

    eval_trace = types.ModuleType("scrollgt.fibers.eval_trace")
    eval_trace.score_tracing = lambda gt, vol, tolerance: types.SimpleNamespace(
        as_row=lambda: row(vol)
    )
    eval_trace._dilate_labels = lambda lab, tol: lab
    target = types.ModuleType("scrollgt.fibers.target")
    target.load_fiber_target = lambda path: (None, None, None)
    for name, mod in (("scrollgt", types.ModuleType("scrollgt")), ("scrollgt.fibers", types.ModuleType("scrollgt.fibers")),
                      ("scrollgt.fibers.eval_trace", eval_trace), ("scrollgt.fibers.target", target)):  # fmt: skip
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setattr(sys, "path", list(sys.path))
    return row


def test_the_polyline_check_scores_the_tool_and_gates_on_finding_105(
    tmp_path, monkeypatch
):
    """neural_tracer_splice_check.main on one 16-voxel cube with stand-ins for ScrollGT: it scores the tool's polylines
    against the unspliced pieces, and its gate catches another splice count, another baseline row and another arc."""
    import neural_tracer_splice_check as chk

    c, size, m = "t_00000_00000_00000_16", 16, chk.cs.MARGIN
    # 3's end lies 2 voxels into 0 (cube-local x 0..8 and 6..15 at y = z = 8); 7 lies apart
    pieces = {
        k: v + [m, m, m + 8]
        for k, v in {
            3: line(0, 8, 9, y=8.0),
            0: line(6, 15, 10, y=8.0),
            7: line(0, 3, 4, y=2.0),
        }.items()
    }
    row = fake_scrollgt(monkeypatch, chk.FIELDS)
    monkeypatch.setattr(chk.ls, "HELD_OUT", [c])
    monkeypatch.setattr(chk.ls, "IN_SAMPLE", [])
    monkeypatch.setattr(chk, "F105", tmp_path / "f105.json")
    for overlap in (16, 8):
        write_run(tmp_path / f"o{overlap}" / c, pieces, {3: (-1, 0)}, overlap=overlap)
    zyx = {
        k: chk.afv_to_labels.to_cube_zyx(v, (m,) * 3)
        for k, v in sp.load_run(tmp_path / "o16" / c)[0].items()
    }
    base = row(chk.afv_to_labels.rasterize(zyx, (size,) * 3))
    # piece 0, which wins the voxels it shares with 3
    assert base["erl_merge_penalized"] == 10

    def check(name, splices=1, base_row=base, overlap=16):
        rec = {
            t: {"base": base_row, "splice": {"gain": 0.25}} for t in ("tol2", "tol4")
        }
        (tmp_path / "f105.json").write_text(
            json.dumps({"per_cube": {c: {"splices": splices, **rec}}})
        )
        monkeypatch.setitem(chk.cs.RUNS, size, tmp_path / f"o{overlap}")
        assert chk.main(["--out", str(tmp_path / name)]) == 0
        return json.loads((tmp_path / name).read_text())

    d = check("ok.json")
    assert d["status"] == "OK" and d["gate"] == {c: []}
    r = d["per_cube"][c]
    assert r["splices"] == 1 and r["fibers"] == 2 and r["arc_limit"] == 32.0
    for t in ("tol2", "tol4"):
        # the chain 3 + 0 is one label over x 0..15
        assert r[t]["poly"]["erl_merge_penalized"] == 16
        assert r[t]["poly_gain"] == pytest.approx(16 / 10 - 1)
        assert r[t]["labelling_gain"] == 0.25
    assert d["summary"]["held_out"]["tol2"]["cubes_gaining"] == 1
    with pytest.raises(SystemExit, match="written once"):
        chk.main(["--out", str(tmp_path / "ok.json")])
    assert check("n.json", splices=2)["gate"] == {c: ["splices"]}
    assert check("b.json", base_row=dict(base, merges=9))["gate"] == {
        c: ["tol2:base:merges", "tol4:base:merges"]
    }
    d = check("a.json", overlap=8)
    assert d["status"] == "GATE_FAILED" and d["gate"] == {c: ["arc_limit"]}


def test_a_cube_without_a_gain_is_not_counted_as_gaining():
    import neural_tracer_splice_check as chk

    def rec(g):
        side = {"merges": 1, "coverage": 0.5, "precision": 0.5}
        return {
            t: {"poly_gain": g, "labelling_gain": g, "base": side, "poly": side}
            for t in ("tol2", "tol4")
        }

    s = chk.summarize({"a": rec(0.0), "b": rec(0.1)}, ["a", "b"])
    assert s["tol2"]["cubes_gaining"] == s["tol4"]["cubes_gaining"] == 1
