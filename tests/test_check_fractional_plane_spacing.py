"""The fractional plane-spacing harness behind villa #2258's evidence.

`repro/fibers/check_fractional_plane_spacing.py` compiles four seed functions
out of villa's `volume.py` and compares them before and after the fix, on
three published ScrollGT masks; its example checks one mask's plane placement.
The evidence JSON and the upstream PR rest on what these scripts refuse:

- running anything else in `volume.py` (its model imports are not installed);
- a source whose seed functions changed shape;
- a mask that is not the published one;
- a default spacing whose seed arrays moved;
- overwriting an evidence file.

Nothing tested any of it. Each test here drives the scripts on a stand-in
`volume.py` and synthetic masks, so no villa checkout or data is needed.
"""

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from repro.fibers import (
    check_fractional_plane_spacing as cf,
    check_fractional_plane_spacing_example as ex,
)

_REPORTS = Path(__file__).resolve().parent.parent / "reports"
_REPORT = _REPORTS / "villa_fractional_plane_spacing_2026-10-20.md"


def _flat_report():
    return " ".join(_REPORT.read_text().split())


# A stand-in for villa's tracing/volume.py: the four seed functions and three
# constants the harness takes, plus module-level code it must never run.
_SEEDING = """
import torch_that_is_not_installed  # the model imports volume.py really has
raise RuntimeError("module-level code ran")

HESSIAN_SIGMA = 1.5
HESSIAN_RADIUS = 3
_KERNELS = None


def unit(v):
    return v / np.linalg.norm(v)


def _hessian_kernels():
    return HESSIAN_SIGMA


def ridge_directions(volume):
    return ndimage.gaussian_filter(volume.astype(float), HESSIAN_SIGMA)


def tile_dots(presence, lo, hi, settings):
    depth = presence.shape[0]
    {planes}
    labels = [f"z{{z}}" for z in planes] + ["fill"]
    return {{
        "xyz": np.array([[0.0, 0.0, float(z)] for z in planes] + [[1.0, 1.0, 1.0]]),
        "plane": np.array(labels),
    }}
"""
# villa before the fix: the fractional part of the step is dropped
_BEFORE = "planes = list(range(0, depth, int(settings.plane_spacing)))"
# after: each global multiple is quantised on its own
_AFTER = (
    "planes = sorted({int(k * settings.plane_spacing) for k in range(depth)"
    " if k * settings.plane_spacing < depth})"
)


def _volume(tmp_path, name, planes):
    path = tmp_path / name
    path.write_text(_SEEDING.format(planes=planes))
    return path


def _mask(path, shape, fill):
    """A ScrollGT-style packed binary mask: np.packbits of the flat volume."""
    mask = np.zeros(shape, np.uint8)
    fill(mask)
    np.savez(path, shape=np.array(shape), packed=np.packbits(mask.ravel()))
    return mask


def _accept_any_mask(monkeypatch, module, reject=()):
    # the published masks are not in the repository; trust the stand-ins' hashes,
    # except for the scrolls in `reject`, and hash every other file for real
    hashes = {
        scroll: (cube, "hash-" + scroll) for scroll, (cube, _) in cf.MASKS.items()
    }
    real = cf.sha256

    def fake(path):
        scroll = path.name.split("_")[0]
        if path.name.endswith("_mask.npz") and scroll not in reject:
            return "hash-" + scroll
        return real(path)

    monkeypatch.setattr(module, "MASKS", hashes)
    monkeypatch.setattr(module, "sha256", fake)


def test_load_seeding_takes_the_four_functions_and_nothing_else(tmp_path):
    seeding = cf.load_seeding(_volume(tmp_path, "volume.py", _AFTER))
    # the module's import and raise never ran, and the functions work
    assert seeding.HESSIAN_SIGMA == 1.5 and seeding._KERNELS is None
    assert np.allclose(seeding.unit(np.array([3.0, 4.0])), [0.6, 0.8])
    settings = SimpleNamespace(plane_spacing=64 * 7.91 / 9.6)
    dots = seeding.tile_dots(np.zeros((128, 4, 4)), None, None, settings)
    assert list(dots["plane"]) == ["z0", "z52", "z105", "fill"]


@pytest.mark.parametrize(
    "rename", [("def ridge_directions", "def ridges"), ("HESSIAN_RADIUS =", "RADIUS =")]
)
def test_load_seeding_refuses_a_source_whose_seed_functions_changed(tmp_path, rename):
    path = _volume(tmp_path, "volume.py", _AFTER)
    path.write_text(path.read_text().replace(*rename))
    with pytest.raises(ValueError, match="Seed functions/constants changed"):
        cf.load_seeding(path)


def test_presence_is_the_2x2x2_block_mean_scaled_to_uint8(tmp_path):
    def fill(m):
        m[0:2, 0:2, 0:2] = 1  # a full block
        m[2, 0, 0] = 1  # one voxel of eight
        m[2:4, 2:4, 2] = 1  # half a block

    mask = _mask(tmp_path / "s1_mask.npz", (4, 4, 6), fill)
    shape, presence = cf.presence_from_mask(tmp_path / "s1_mask.npz")
    assert shape == mask.shape and presence.shape == (2, 2, 3)
    assert presence.dtype == np.uint8
    assert presence[0, 0, 0] == 255 and presence[1, 0, 0] == 32
    assert presence[1, 1, 1] == 128 and presence.sum() == 255 + 32 + 128


def _run_main(monkeypatch, tmp_path, before_planes, after_planes):
    data = tmp_path / "data"
    data.mkdir()
    for scroll in cf.MASKS:
        # 256 deep, as the Scroll-1 and Scroll-5 cubes are: 128 after the 2x2x2 mean,
        # deep enough for the fractional spacings to place different planes
        _mask(data / f"{scroll}_mask.npz", (256, 4, 4), lambda m: m.fill(1))
    out = tmp_path / "evidence.json"
    argv = [
        "check",
        "--before", str(_volume(tmp_path, "before.py", before_planes)),
        "--after", str(_volume(tmp_path, "after.py", after_planes)),
        "--data", str(data),
        "--out", str(out),
    ]  # fmt: skip
    monkeypatch.setattr("sys.argv", argv)
    return out, cf.main


def test_main_records_each_cube_and_spacing(monkeypatch, tmp_path):
    _accept_any_mask(monkeypatch, cf)
    out, main = _run_main(monkeypatch, tmp_path, _BEFORE, _AFTER)
    assert main() == 0
    result = json.loads(out.read_text())
    rows = result["rows"]
    assert len(rows) == 3 * len(cf.MASKS)
    assert {r["cube"] for r in rows} == {cube for cube, _ in cf.MASKS.values()}
    # the fix is inert at 64 and at 77.67 on 128 planes, and moves one plane at 52.73
    by_spacing = {round(r["spacing"], 3): r for r in rows}
    assert by_spacing[64.0]["identical"] and by_spacing[77.674]["identical"]
    moved = by_spacing[52.733]
    assert not moved["identical"]
    assert moved["before"]["planes"] == ["z0", "z104", "z52"]
    assert moved["after"]["planes"] == ["z0", "z105", "z52"]
    assert moved["after"]["dots"] == 4 and moved["after"]["plane_dots"] == 3
    assert moved["after"]["fill_dots"] == 1
    assert set(moved["after"]["array_sha256"]) == {"xyz", "plane"}
    # each source file is hashed for itself
    before, after = (Path(sys.argv[i]) for i in (2, 4))
    assert result["before_source_sha256"] == cf.sha256(before)
    assert result["after_source_sha256"] == cf.sha256(after)
    assert result["before_source_sha256"] != result["after_source_sha256"]


def test_main_runs_the_settings_and_spacings_the_report_states(monkeypatch, tmp_path):
    _accept_any_mask(monkeypatch, cf)
    calls, load = [], cf.load_seeding

    def recording(source):
        seeding = load(source)
        inner = seeding.tile_dots

        def tile_dots(presence, lo, hi, settings):
            calls.append((presence.shape, lo, hi, settings))
            return inner(presence, lo, hi, settings)

        seeding.tile_dots = tile_dots
        return seeding

    monkeypatch.setattr(cf, "load_seeding", recording)
    out, main = _run_main(monkeypatch, tmp_path, _BEFORE, _AFTER)
    assert main() == 0
    report = _flat_report()
    for shape, lo, hi, s in calls:
        assert list(lo) == [0, 0, 0] and tuple(hi) == shape[::-1]
        assert (
            f"threshold {s.threshold:.0f}, dot radius {s.dot_radius:.0f} and fill spacing "
            f"{s.fill_spacing:.0f}"
        ) in report
    final = json.loads(
        (_REPORTS / "villa_fractional_plane_spacing_final_2026-10-20.json").read_text()
    )
    ran = sorted({s.plane_spacing for *_, s in calls})
    assert ran == sorted({r["spacing"] for r in final["rows"]})
    assert ran == sorted({64.0, 64 * 7.91 / 9.6, 64 * 9.6 / 7.91})


def test_main_refuses_a_patch_that_moves_the_default_spacing(monkeypatch, tmp_path):
    _accept_any_mask(monkeypatch, cf)
    shifted = "planes = list(range(1, depth, int(settings.plane_spacing)))"
    out, main = _run_main(monkeypatch, tmp_path, _BEFORE, shifted)
    # at the default spacing the planes are 0 and 64; the shifted patch moves them
    with pytest.raises(ValueError, match="default seed arrays changed"):
        main()
    assert not out.exists()


def test_main_checks_every_mask_not_only_the_first(monkeypatch, tmp_path):
    _accept_any_mask(monkeypatch, cf, reject={"s3"})
    out, main = _run_main(monkeypatch, tmp_path, _BEFORE, _AFTER)
    with pytest.raises(ValueError, match="s3_mask.npz: not the published"):
        main()
    assert not out.exists()


def test_main_refuses_an_unpublished_mask_and_an_existing_output(monkeypatch, tmp_path):
    out, main = _run_main(monkeypatch, tmp_path, _BEFORE, _AFTER)
    with pytest.raises(ValueError, match="not the published ScrollGT v0.8.1 mask"):
        main()
    out.write_text("earlier evidence")
    with pytest.raises(FileExistsError):
        main()
    assert out.read_text() == "earlier evidence"


@pytest.mark.parametrize(("planes", "code"), [(_BEFORE, 1), (_AFTER, 0)])
def test_the_example_passes_only_the_global_placement(
    monkeypatch, tmp_path, capsys, planes, code
):
    _accept_any_mask(monkeypatch, ex)
    mask = tmp_path / "s1_mask.npz"
    _mask(mask, (256, 4, 4), lambda m: m.fill(1))
    volume = _volume(tmp_path, "volume.py", planes)
    monkeypatch.setattr(
        "sys.argv", ["ex", "--volume", str(volume), "--mask", str(mask)]
    )
    assert ex.main() == code
    shown = capsys.readouterr().out
    assert ("Observed z planes: 0, 52, 104" in shown) == (code == 1)
    assert ("PASS: global plane placement" in shown) == (code == 0)


def test_the_example_refuses_an_unpublished_mask(monkeypatch, tmp_path):
    mask = tmp_path / "s1_mask.npz"
    _mask(mask, (4, 4, 4), lambda m: None)
    monkeypatch.setattr(
        "sys.argv", ["ex", "--volume", str(tmp_path / "v.py"), "--mask", str(mask)]
    )
    with pytest.raises(ValueError, match="not the published ScrollGT"):
        ex.main()


def test_the_report_table_is_the_final_evidence():
    final = json.loads(
        (_REPORTS / "villa_fractional_plane_spacing_final_2026-10-20.json").read_text()
    )
    first = json.loads(
        (_REPORTS / "villa_fractional_plane_spacing_2026-10-20.json").read_text()
    )
    report = _REPORT.read_text()
    # "Every result row, including every seed-array hash, equals the initial measurement"
    assert len(final["rows"]) == 9 and final["rows"] == first["rows"]
    assert final["after_source_sha256"] != first["after_source_sha256"]
    by_cube = {}
    for r in final["rows"]:
        by_cube.setdefault(r["cube"], []).append(r)
    # the column headers are the spacings the rows ran, truncated to six places
    spacings = [r["spacing"] for r in next(iter(by_cube.values()))]
    heads = [f"{math.floor(s * 1e6) / 1e6:.6f}..." for s in spacings[1:]]
    assert (
        f"| Cube | Default spacing {spacings[0]:.0f} | Spacing {heads[0]} | Spacing {heads[1]} |"
        in report
    )
    for cube, rows in by_cube.items():
        cells = " | ".join(
            f"{r['before']['dots']} → {r['after']['dots']}" for r in rows
        )
        assert f"| `{cube}` | {cells} |" in report, cube
        # "At spacing 64, all five seed arrays are byte-identical"
        default = next(r for r in rows if r["spacing"] == 64.0)
        assert default["identical"] and len(default["before"]["array_sha256"]) == 5


def test_the_report_states_the_patch_it_ships():
    patch = (
        Path(__file__).resolve().parent.parent
        / "docs/villa_pr_fiber_fractional_plane_spacing.patch"
    ).read_text()
    counts = {}
    for chunk in patch.split("diff --git ")[1:]:
        name = chunk.split("\n", 1)[0].split(" b/")[-1]
        lines = chunk.split("\n@@", 1)[1].splitlines()
        counts[name.rsplit("/", 1)[-1]] = (
            sum(x.startswith("+") and not x.startswith("+++") for x in lines),
            sum(x.startswith("-") and not x.startswith("---") for x in lines),
        )
    (plus, minus), (tests, _) = counts["volume.py"], counts["test_volume_seeding.py"]
    report = _REPORT.read_text()
    assert (
        f"The upstream diff is **+{plus}/-{minus} production lines**, plus {tests} lines of tests."
        in report
    )
