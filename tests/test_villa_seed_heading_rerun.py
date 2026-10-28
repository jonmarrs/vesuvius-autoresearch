"""scripts/villa_seed_heading_rerun.py reads a run's fibers from its finished tiles, as villa's exporters do, so a run
at a villa without the .afv export (#2316) compares and scores as the .afv runs did."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_ct_context as cc  # noqa: E402
import villa_seed_heading_rerun as rr  # noqa: E402

_spec = importlib.util.spec_from_file_location("afv_fixture", ROOT / "tests/test_afv_to_labels.py")  # fmt: skip
afv_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(afv_fixture)

# two fibers in trace-grid xyz, inside the padded cube once doubled
GRID = {3: [[70, 80, 90], [71, 80, 90], [72, 81, 90]], 9: [[100, 100, 100], [100, 101, 102]]}  # fmt: skip


def _run(path: Path, fibers=GRID, scale=2.0, tile="z0_y0_x0") -> Path:
    (path / "tiles").mkdir(parents=True)
    (path / "run.json").write_text(json.dumps({"grid_scale": scale}))
    ids = sorted(fibers)
    pts = [np.asarray(fibers[i], np.float32) for i in ids]
    offsets = np.cumsum([0] + [len(p) for p in pts])
    np.savez(
        path / "tiles" / f"{tile}.npz",
        points=np.concatenate(pts),
        offsets=offsets,
        id=ids,
    )
    return path


def test_tile_fibers_are_the_points_times_grid_scale_by_id(tmp_path):
    run = _run(tmp_path / "run")
    (run / "tiles" / "z1_y0_x0.partial.npz").write_bytes(b"an interrupted tile")
    got = rr.tile_fibers(run)
    assert sorted(got) == [3, 9]
    for i, p in GRID.items():
        assert got[i].dtype == np.float64
        assert np.array_equal(
            got[i], np.asarray(p, np.float32).astype(np.float64) * 2.0
        )


def test_a_run_without_finished_tiles_is_refused(tmp_path):
    run = tmp_path / "run"
    (run / "tiles").mkdir(parents=True)
    (run / "run.json").write_text(json.dumps({"grid_scale": 2.0}))
    with pytest.raises(SystemExit, match="no finished tiles"):
        rr.tile_fibers(run)


def test_a_fiber_in_two_tiles_is_refused(tmp_path):
    run = _run(tmp_path / "run")
    _run(tmp_path / "other", fibers={9: [[1, 1, 1], [2, 2, 2]]})
    (tmp_path / "other/tiles/z0_y0_x0.npz").rename(run / "tiles/z1_y0_x0.npz")
    with pytest.raises(ValueError, match="fiber 9 in two tiles"):
        rr.tile_fibers(run)


def test_tile_labels_are_the_afv_labels(tmp_path):
    """The scored labels from tiles equal labels_in_cube on the .afv of the same fibers."""
    run = _run(tmp_path / "run")
    afv_fixture.write_afv(run / "fibers.afv", rr.tile_fibers(run))
    assert np.count_nonzero(cc.labels_in_cube(run / "fibers.afv")) > 0
    assert np.array_equal(cc.labels_of_fibers(rr.tile_fibers(run)), cc.labels_in_cube(run / "fibers.afv"))  # fmt: skip


def test_a_run_whose_afv_differs_from_its_tiles_is_refused(tmp_path):
    run = _run(tmp_path / "run")
    fibers = rr.tile_fibers(run)
    got = rr.run_fibers(run)
    assert got["tiles_match_afv"] is None and sorted(got["fibers"]) == sorted(fibers)
    afv_fixture.write_afv(run / "fibers.afv", fibers)
    assert rr.run_fibers(run)["tiles_match_afv"] is True
    (run / "fibers.afv").unlink()
    afv_fixture.write_afv(run / "fibers.afv", {3: fibers[3]})
    with pytest.raises(SystemExit, match="fibers.afv differs from its tiles"):
        rr.run_fibers(run)


def test_same_fibers_ignores_ids_but_not_points(tmp_path):
    a = rr.tile_fibers(_run(tmp_path / "a"))
    b = {i + 100: p for i, p in a.items()}
    assert rr.same_fibers(a, b)
    b[109] = b[109] + 0.5
    assert not rr.same_fibers(a, b)


def test_a_run_counts_only_once_its_chain_logged_it_done(tmp_path):
    (tmp_path / "chain.log").write_text(
        "CHAIN_START repo 1234567 villa 39a8cf3a1  t\nTRACE before s5_a  t\nDONE before s5_a  t\n"
        "TRACE after s5_a  t\nFAILED after s5_a rc=1  t\n"
    )
    assert rr.logged_done(tmp_path, "before", "s5_a")
    assert not rr.logged_done(tmp_path, "after", "s5_a")
    assert not rr.logged_done(tmp_path, "before", "s5")
