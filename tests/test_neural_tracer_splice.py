"""scripts/neural_tracer_splice.py: chains, joints, and a run directory read as villa's tracing.volume writes it."""

from __future__ import annotations

import json
import sys
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


@pytest.mark.parametrize("name", ["spliced", "spliced.NPZ", "spliced.npy", "spliced.npz"])
def test_the_actual_numpy_output_path_is_checked_before_splicing(
    tmp_path, name, monkeypatch
):
    out = tmp_path / name
    actual = out if name.endswith(".npz") else Path(str(out) + ".npz")
    np.savez(actual, existing_result=np.array([123]))
    before = actual.read_bytes()

    # Even a missing input must not be read when the actual output already exists.
    def unexpected_read(*args):
        pytest.fail("existing output must be checked before reading the run")

    monkeypatch.setattr(sp, "load_run", unexpected_read)
    with pytest.raises(SystemExit, match="exists"):
        sp.main([str(tmp_path / "missing-run"), "--write", str(out)])
    assert actual.read_bytes() == before


def test_omitted_npz_suffix_still_writes_the_expected_fibers(tmp_path):
    pieces = {1: line(0, 10, 11)}
    write_run(tmp_path / "run", pieces, {})
    run_bytes = (tmp_path / "run/run.json").read_bytes()
    tile = next((tmp_path / "run/tiles").glob("*.npz"))
    tile_bytes = tile.read_bytes()
    out = tmp_path / "spliced"
    assert sp.main([str(tmp_path / "run"), "--write", str(out)]) == 0
    assert not out.exists()
    with np.load(tmp_path / "spliced.npz") as result:
        np.testing.assert_allclose(result["points"], pieces[1])
        assert result["offsets"].tolist() == [0, len(pieces[1])]
        assert result["id"].tolist() == [1]
        assert result["members"].tolist() == [1]
    assert (tmp_path / "run/run.json").read_bytes() == run_bytes
    assert tile.read_bytes() == tile_bytes


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
