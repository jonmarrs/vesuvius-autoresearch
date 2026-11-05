"""reports/fiber_boundary_halo_2026-11-05.md and docs/FIBER_DETECTION.md, bound to the CPU replay's receipt
(reports/evidence/fiber_boundary_halo_2026-11-05.json) and to the source-window helper they describe."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from vesuvius_autoresearch.fibers.detection import _block_bounds

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "reports/fiber_boundary_halo_2026-11-05.md").read_text()
REPORT = " ".join(RAW.split())
DOC = " ".join((ROOT / "docs/FIBER_DETECTION.md").read_text().split())
E = json.loads(
    (ROOT / "reports/evidence/fiber_boundary_halo_2026-11-05.json").read_text()
)


def test_the_table_quotes_the_receipt():
    rows = {r["filter"]: r for r in E["filter_comparisons"]}
    assert sorted(rows) == ["ridges", "vesselness"]
    for name, r in rows.items():
        assert r["candidate_exact_dense"] and r["candidate_stream_exact_float32_dense"]
        assert r["default_halo16_unchanged"]
        error = format(Decimal(repr(r["baseline_max_abs_error"])), "f")
        line = f"| {name.capitalize()} | {r['baseline_differing_voxels']:,} voxels | {error} | 0 |"
        assert line in RAW, line
    o = E["orientation_comparison"]
    assert o["candidate_exact_dense"] and o["candidate_validity_exact_dense"]
    assert o["baseline_validity_differing_voxels"] == 0
    line = f"| Orientation | {o['baseline_differing_components']:,} vector components | Not summarized | 0 |"
    assert line in RAW, line


def test_the_report_states_the_receipts_inputs_and_parameters():
    p = E["parameters"]
    assert p["minimum_halo"] == int(4 * p["gauss_sigma"] + 0.5) + 2
    assert (
        f"Block size is {p['block_size']}, halo {p['minimum_halo']}, Gaussian sigma {p['gauss_sigma']} "
        f"and Hessian scale {p['sigma']}." in REPORT
    )
    assert E["ct_shape"] == [17, 17, 17] and E["fixture_slice_zyx"] == ["0:17"] * 3
    assert "`ct[:17, :17, :17]`" in REPORT
    assert f"`{E['fixture_sha256']}`" in REPORT
    assert E["fixture_villa_commit"] in REPORT
    assert E["fixture_repository_path"] in REPORT
    assert f"block_size={p['block_size']}, halo={p['minimum_halo']}" in RAW
    assert f"block_size={p['block_size']}, halo={p['default_halo_check']}" in RAW


def test_singleton_face_tiles_get_the_one_sided_stencils_context():
    """Two composed second-order one-sided gradients reach three smoothed voxels in from a face, so the window
    reaches the Gaussian support plus four; interior tiles keep the plain halo."""
    for sigma in (0, 1, 2):
        support = int(4 * sigma + 0.5)
        halo = support + 2  # the accepted minimum
        assert _block_bounds(0, 100, 1, halo, sigma) == (0, support + 4)
        assert _block_bounds(99, 100, 1, halo, sigma) == (100 - support - 4, 100)
        assert _block_bounds(50, 100, 1, halo, sigma) == (50 - halo, 51 + halo)
    assert (
        "two composed one-sided derivatives reach three smoothed voxels inward" in DOC
    )


def test_windows_keep_the_transfer_bound():
    """`block_size + 2 * halo` on each axis, as the report and the doc say."""
    assert "the `block_size + 2 * halo` transfer bound are preserved" in REPORT
    assert "`block_size + 2 * halo` bound on each transferred axis" in DOC
    for sigma in (0, 1, 2):
        halo = int(4 * sigma + 0.5) + 2
        for block in range(1, 6):
            for extent in range(1, 3 * halo):
                for start in range(0, extent, block):
                    lower, upper = _block_bounds(start, extent, block, halo, sigma)
                    assert (
                        0
                        <= lower
                        <= start
                        < min(start + block, extent)
                        <= upper
                        <= extent
                    )
                    assert upper - lower <= block + 2 * halo
