"""Finding 136's analysis: the area's cells, the lattice in render pixels, and the registered verdict with its failure
branches."""

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


own = _load(
    "studio_343_own_under_test", ROOT / "repro/first_letters/pherc343/studio_343_own.py"
)


def _numbers(r, wrong=0.05, slid=0.2):
    return {
        "r": r,
        "control_wrong_side": wrong,
        "control_slid": {"largest_absolute": slid},
    }


def test_the_area_holds_only_cells_wholly_inside_it():
    sidecar = {
        "area": {"raw_render_px": {"row0": 5, "row1": 17, "col0": 8, "col1": 20}}
    }
    cells = own.area_cells((6, 7), sidecar)  # 4-pixel cells
    assert cells.shape == (6, 7)
    assert np.flatnonzero(cells.any(axis=1)).tolist() == [
        2,
        3,
    ]  # rows 8-11 and 12-15; 4-7 and 16-19 stick out
    assert np.flatnonzero(cells.any(axis=0)).tolist() == [2, 3, 4]  # columns 8-19


def test_a_lattice_map_covers_its_pixels_and_leaves_the_rest_empty():
    values = np.arange(6, dtype=float).reshape(2, 3)
    raw = own.lattice_to_raw(values, (10, 13))
    assert raw.shape == (10, 13)
    assert raw[0, 0] == 0 and raw[3, 3] == 0 and raw[4, 4] == 4 and raw[7, 11] == 5
    assert np.isnan(raw[8:, :]).all() and np.isnan(raw[:, 12:]).all()


def test_the_verdict_follows_finding_124s_lines():
    ok = (0.9, True, [0.997, 0.998])
    assert own.verdict(_numbers(0.70), *ok) == "STUDIO_343_OWN_CLOSE"
    assert own.verdict(_numbers(0.6999), *ok) == "STUDIO_343_OWN_PARTLY"
    assert own.verdict(_numbers(0.40), *ok) == "STUDIO_343_OWN_PARTLY"
    assert own.verdict(_numbers(0.3999), *ok) == "STUDIO_343_OWN_FAR"
    # a control at more than half of r keeps the read out of CLOSE and PARTLY
    assert own.verdict(_numbers(0.80, slid=0.41), *ok) == "STUDIO_343_OWN_FAR"
    assert own.verdict(_numbers(0.80, wrong=-0.40), *ok) == "STUDIO_343_OWN_CLOSE"
    assert own.verdict(_numbers(0.80, wrong=-0.401), *ok) == "STUDIO_343_OWN_FAR"


def test_the_failure_branch_gives_no_read_even_when_r_is_high():
    good = _numbers(0.95)
    assert (
        own.verdict(good, 0.9, False, [0.997, 0.998]) == "DOES_NOT_RUN"
    )  # finding 127 not reproduced
    assert (
        own.verdict(good, 0.49, True, [0.997, 0.998]) == "DOES_NOT_RUN"
    )  # too few cells
    assert (
        own.verdict(good, 0.9, True, [0.997, -0.2]) == "DOES_NOT_RUN"
    )  # a render samples the other way
    assert (
        own.verdict(good, 0.9, True, [0.997, None]) == "DOES_NOT_RUN"
    )  # a winding gives no cells
    assert own.verdict(good, 0.9, True, []) == "DOES_NOT_RUN"
    assert own.verdict(None, 0.9, True, [0.997, 0.998]) == "DOES_NOT_RUN"
    assert own.verdict(_numbers(None), 0.9, True, [0.997, 0.998]) == "DOES_NOT_RUN"
    assert (
        own.verdict(_numbers(0.95, slid=None), 0.9, True, [0.997, 0.998])
        == "DOES_NOT_RUN"
    )
