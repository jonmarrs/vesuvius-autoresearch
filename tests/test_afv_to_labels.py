"""scripts/afv_to_labels.py on small .afv files written to villa's format (volume-cartographer/docs/fiber-collections.md)."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import afv_to_labels as a  # noqa: E402


def write_afv(
    path: Path, fibers: dict[int, np.ndarray], block: int = 256, complete: bool = True
) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        PRAGMA application_id=0x56434643; PRAGMA user_version=1;
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE fibers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, family TEXT NOT NULL,
          point_count INTEGER NOT NULL, length REAL NOT NULL, min_x REAL NOT NULL, max_x REAL NOT NULL,
          min_y REAL NOT NULL, max_y REAL NOT NULL, min_z REAL NOT NULL, max_z REAL NOT NULL, annotation TEXT NOT NULL);
        CREATE TABLE blocks(id INTEGER PRIMARY KEY, fiber_id INTEGER NOT NULL, first_segment INTEGER NOT NULL,
          points BLOB NOT NULL, UNIQUE(fiber_id, first_segment));
        CREATE VIRTUAL TABLE block_bounds USING rtree(id, min_x, max_x, min_y, max_y, min_z, max_z);
        """
    )
    con.execute("INSERT INTO metadata VALUES ('complete', ?)", (json.dumps(complete),))
    bid = 0
    for fid, p in fibers.items():
        lo, hi = p.min(0), p.max(0)
        con.execute("INSERT INTO fibers VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (fid, f"f{fid}", "", len(p), 0.0, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], "{}"))  # fmt: skip
        for s in range(0, len(p) - 1, block):
            chunk = p[s : s + block + 1]
            bid += 1
            con.execute(
                "INSERT INTO blocks VALUES (?,?,?,?)",
                (bid, fid, s, chunk.astype("<f8").tobytes()),
            )
            c0, c1 = chunk.min(0), chunk.max(0)
            con.execute(
                "INSERT INTO block_bounds VALUES (?,?,?,?,?,?,?)",
                (bid, c0[0], c1[0], c0[1], c1[1], c0[2], c1[2]),
            )
    con.commit()
    con.close()


def test_blocks_concatenate_without_duplicating_shared_points(tmp_path):
    p = np.stack([np.arange(600.0), np.full(600, 5.0), np.full(600, 7.0)], axis=1)
    write_afv(
        tmp_path / "f.afv", {3: p}, block=256
    )  # three blocks sharing boundary points
    got = a.read_afv(tmp_path / "f.afv")
    assert list(got) == [3] and np.array_equal(got[3], p)


def test_bbox_selects_only_intersecting_fibers(tmp_path):
    near = np.array([[1.0, 1, 1], [5, 1, 1]])
    far = np.array([[100.0, 100, 100], [105, 100, 100]])
    write_afv(tmp_path / "f.afv", {1: near, 2: far})
    got = a.read_afv(tmp_path / "f.afv", (np.array([0, 0, 0]), np.array([10, 10, 10])))
    assert list(got) == [1]


def test_incomplete_file_is_refused(tmp_path):
    write_afv(
        tmp_path / "f.afv", {1: np.array([[0.0, 0, 0], [1, 0, 0]])}, complete=False
    )
    with pytest.raises(ValueError, match="incomplete"):
        a.read_afv(tmp_path / "f.afv")


def test_xyz_to_cube_zyx_with_origin_shift_and_affine():
    xyz = np.array([[10.0, 20.0, 30.0]])
    assert np.array_equal(a.to_cube_zyx(xyz, (5, 5, 5)), [[25.0, 15.0, 5.0]])
    aff = np.eye(4)
    aff[:3, 3] = [1, 2, 3]
    assert np.array_equal(
        a.to_cube_zyx(xyz, (0, 0, 0), aff, shift_zyx=(1, 1, 1)), [[32.0, 21.0, 10.0]]
    )


def test_straight_line_labels_every_voxel_it_crosses_and_nothing_else():
    lab = a.rasterize({7: np.array([[4.0, 4.0, 0.0], [4.0, 4.0, 9.0]])}, (10, 10, 10))
    assert set(np.unique(lab)) == {0, 1}
    assert np.array_equal(np.argwhere(lab == 1), [[4, 4, x] for x in range(10)])


def test_nearest_sample_wins_and_ties_go_to_the_lower_id():
    shape = (8, 8, 8)
    # Two lines through voxel row (3, 3, *): one exactly on it, one 0.4 away; the exact one wins regardless of id.
    lab = a.rasterize(
        {
            1: np.array([[3.4, 3.0, 0.0], [3.4, 3.0, 7.0]]),
            2: np.array([[3.0, 3.0, 0.0], [3.0, 3.0, 7.0]]),
        },
        shape,
    )
    assert np.all(lab[3, 3, :] == 2)
    # Identical lines: the lower fiber id (rank 1) takes every voxel.
    same = np.array([[1.0, 1.0, 0.0], [1.0, 1.0, 7.0]])
    lab = a.rasterize({5: same, 9: same.copy()}, shape)
    assert np.all(lab[1, 1, :] == 1) and not np.any(lab == 2)


def test_points_outside_the_cube_are_dropped():
    lab = a.rasterize({1: np.array([[2.0, 2.0, -5.0], [2.0, 2.0, 3.0]])}, (4, 4, 4))
    assert np.array_equal(np.argwhere(lab == 1), [[2, 2, x] for x in range(4)])
