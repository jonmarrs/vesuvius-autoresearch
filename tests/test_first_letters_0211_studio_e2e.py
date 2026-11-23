"""Finding 124: Studio's planes from our renders, the verdict table, and the comparison on finding 121's synthetic
surfaces (a mirrored winding carries Studio maps back onto the winner's surface)."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


se = _load("studio_e2e_under_test", CONTROL / "studio_e2e.py")
f121_tests = _load(
    "f121_tests_for_studio", ROOT / "tests/test_first_letters_0211_end_to_end.py"
)


def test_the_planes_are_our_layers_41_down_to_26_and_the_reverse(tmp_path):
    import zarr

    data = np.stack([np.full((8, 12), k, np.uint8) for k in range(66)])
    zarr.open(str(tmp_path / "r.zarr"), mode="w").create_dataset(
        "0", data=data, chunks=(66, 8, 12)
    )
    assert se.planes_cmd(tmp_path / "r.zarr", tmp_path / "p.npy")["layers"] == list(
        range(41, 25, -1)
    )
    assert np.load(tmp_path / "p.npy")[:, 0, 0].tolist() == list(range(41, 25, -1))
    se.planes_cmd(tmp_path / "r.zarr", tmp_path / "q.npy", reverse=True)
    assert np.load(tmp_path / "q.npy")[:, 0, 0].tolist() == list(range(26, 42))


def _n(r, wrong, slid):
    return {
        "r": r,
        "control_wrong_side": wrong,
        "control_slid": {"largest_absolute": slid},
    }


def test_the_verdict_table():
    assert se.verdict(_n(0.70, 0.0, 0.35), 1.0) == "STUDIO_E2E_CLOSE"
    assert (
        se.verdict(_n(0.70, 0.36, 0.0), 1.0) == "STUDIO_E2E_FAR"
    )  # not twice the other side
    assert se.verdict(_n(0.69, 0.0, 0.0), 1.0) == "STUDIO_E2E_PARTLY"
    assert se.verdict(_n(0.40, 0.0, 0.0), 1.0) == "STUDIO_E2E_PARTLY"
    assert se.verdict(_n(0.39, 0.0, 0.0), 1.0) == "STUDIO_E2E_FAR"
    assert se.verdict(_n(0.9, 0.0, 0.0), 0.49) == "DOES_NOT_RUN"
    assert se.verdict(None, 1.0) == "DOES_NOT_RUN"


def test_the_lines_are_the_registrations():
    assert (se.CLOSE, se.PARTLY, se.RATIO) == (0.70, 0.40, 2.0)
    text = (
        ROOT / "docs/preregistration/2026-11-16_first_letters_0211_studio_e2e.md"
    ).read_text()
    assert (
        "| r at least 0.70, and at least twice the absolute value of each control | `STUDIO_E2E_CLOSE` |"
        in text
    )
    assert (
        "| r at least 0.40, and at least twice the absolute value of each control | `STUDIO_E2E_PARTLY` |"
        in text
    )
    assert "our layers 41 down to 26" in text


def _studio_maps(root: Path, name: str, other_same: bool = False) -> list[str]:
    """Studio's map of a mirrored winding: the winner's strokes, mirrored as the winding is (f121's convention), and
    of its reversed planes: the strokes moved along the line (or the same strokes, when other_same)."""
    import tifffile

    strokes = tifffile.imread(root / "studio.tif").astype(np.float32)
    px = se.analysis.PX_PER_NODE
    mirrored = np.roll(strokes[:, ::-1], -px, axis=1)
    rng = np.random.default_rng(7)
    reading = np.clip(
        0.1 + 0.8 * mirrored + 0.02 * rng.standard_normal(strokes.shape), 0, 1
    ).astype(np.float32)
    other = reading if other_same else np.roll(reading, 37, axis=1)
    np.save(root / f"{name}_studio.npy", reading)
    np.save(root / f"{name}_studio_reversed.npy", other)
    return [str(root / f"{name}_studio.npy"), str(root / f"{name}_studio_reversed.npy")]


def _compare(root: Path, w: dict, ours: list[list[str]]) -> tuple[int, dict]:
    import tifffile

    own = root / "own.npy"
    np.save(own, tifffile.imread(w["studio"]).astype(np.float32))
    out = root / "studio_e2e.json"
    argv = [
        "compare", str(out), "--winner-mesh", str(w["mesh"]), "--winner-maps", str(w["maps"]),
        "--winner-render", str(w["render"]), "--studio", str(w["studio"]), "--studio-mask", str(w["mask"]),
        "--ours-render-map", str(own), "--image", str(root / "three.png"),
    ]  # fmt: skip
    for paths in ours:
        argv += ["--ours-flipped", *paths]
    code = se.main(argv)
    return code, json.loads(out.read_text()) if out.exists() else {}


def test_studio_maps_of_our_windings_carried_back_onto_the_winners_surface(tmp_path):
    w = f121_tests._winner(tmp_path)
    winding = f121_tests._ours(tmp_path, w, "w035", mirror=True)
    code, record = _compare(tmp_path, w, [[*winding, *_studio_maps(tmp_path, "w035")]])
    assert code == 0 and record["verdict"] == "STUDIO_E2E_CLOSE", record.get(
        "registered"
    )
    assert record["registered"]["r"] > 0.9
    assert abs(record["registered"]["control_wrong_side"]) < 0.2
    described = record["described"]
    assert (
        described["our_render_of_the_winners_surface"]["r"] > 0.99
    )  # the winner's map itself
    assert described["by_winding"]["w035.tifxyz"]["cells"] == record["cells"]
    assert (tmp_path / "three.png").exists()


def test_a_reversed_order_that_reads_the_same_fails_the_controls(tmp_path):
    w = f121_tests._winner(tmp_path)
    winding = f121_tests._ours(tmp_path, w, "w033", mirror=True)
    code, record = _compare(
        tmp_path, w, [[*winding, *_studio_maps(tmp_path, "w033", other_same=True)]]
    )
    assert code == 0 and record["verdict"] == "STUDIO_E2E_FAR"


def test_a_winding_that_was_not_rendered_flipped_does_not_run(tmp_path):
    w = f121_tests._winner(tmp_path)
    winding = f121_tests._ours(
        tmp_path, w, "w034"
    )  # normals along the winner's: should not be marked flipped
    code, record = _compare(tmp_path, w, [[*winding, *_studio_maps(tmp_path, "w034")]])
    assert (
        code == 0 and record["verdict"] == "DOES_NOT_RUN" and "normals" in record["why"]
    )


def test_the_driver_checks_and_runs_the_winners_command_and_uploads_nothing():
    path = CONTROL / "run_studio_e2e.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl", "--upload-file", "rsync "):
        assert word not in text
    assert (
        "W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90" in text
    )
    assert (
        "CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0"
        in text
    )
    assert '--checkpoint "$WEIGHTS" --stride 64 --blend hann --batch-size 32' in text
    assert "WINDINGS=(w033 w034 w035 w036)" in text and "--reverse" in text
    order = ["step check", "step planes", "step infer", "step compare"]
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)


# --- the refusals, the verdict's other edges, and the described numbers ------------------------------------------


def _render(root: Path, layers: int, dtype=np.uint8) -> Path:
    import zarr

    path = root / f"r{layers}.zarr"
    zarr.open(str(path), mode="w").create_dataset(
        "0", data=np.zeros((layers, 8, 12), dtype), chunks=(layers, 8, 12)
    )
    return path


def test_the_planes_refuse_a_render_without_layers_26_to_41_or_not_8_bit(tmp_path):
    import pytest

    with pytest.raises(SystemExit, match="layer 41 is not in a 10-layer render"):
        se.planes_cmd(_render(tmp_path, 10), tmp_path / "a.npy")
    with pytest.raises(SystemExit, match="even count"):
        se.planes_cmd(_render(tmp_path, 31), tmp_path / "b.npy")
    with pytest.raises(SystemExit, match="not 8-bit"):
        se.planes_cmd(_render(tmp_path, 66, np.uint16), tmp_path / "c.npy")
    # a centred 20-layer render holds layers 23 to 42, so it is enough
    assert se.planes_cmd(_render(tmp_path, 20), tmp_path / "d.npy")["shape"] == [
        16,
        8,
        12,
    ]
    assert se.main(["planes", str(_render(tmp_path, 66)), str(tmp_path / "d.npy")]) == 2


def test_a_studio_map_of_another_size_is_refused(tmp_path):
    import pytest

    np.save(tmp_path / "m.npy", np.zeros((8, 12), np.float32))
    with pytest.raises(SystemExit, match="the render is"):
        se.read_studio(tmp_path / "m.npy", (8, 16))


def test_the_verdict_table_at_its_other_edges():
    assert se.verdict(_n(0.9, 0.0, 0.0), se.f118.MIN_CELL_SHARE) == "STUDIO_E2E_CLOSE"
    assert se.verdict(_n(0.72, 0.36, 0.0), 1.0) == "STUDIO_E2E_CLOSE"  # exactly twice
    assert (
        se.verdict(_n(0.70, -0.36, 0.0), 1.0) == "STUDIO_E2E_FAR"
    )  # its absolute value
    assert se.verdict(_n(0.9, None, 0.0), 1.0) == "DOES_NOT_RUN"


def test_the_r_with_background_keeps_our_maps_background_in():
    rng = np.random.default_rng(3)
    cells = np.ones((40, 40), bool)
    theirs = rng.standard_normal((40, 40))
    ours = (
        theirs + np.linspace(0.0, 30.0, 40)[None, :]
    )  # a broad background across the map
    numbers = se.score(theirs, theirs > 1.0, ours, cells)
    expected = se.f118._rounded(se.analysis.pearson(ours[cells], theirs[cells]))
    assert numbers["r_with_background"] == expected < numbers["r"]


def _base(root: Path, *, dy=0.0, studio_at_line=False):
    """finding 121's winner and one mirrored winding, read by "Studio" as in the tests above."""
    import tifffile

    w = f121_tests._winner(root)
    if studio_at_line:
        tifffile.imwrite(
            w["studio"],
            np.where(tifffile.imread(w["studio"]) >= 0.3, 0.5, 0.0).astype(np.float32),
        )
    winding = f121_tests._ours(root, w, "w035", mirror=True, dy=dy)
    maps = _studio_maps(root, "w035")
    return w, [[*winding, *maps]]


def _compare_own(root: Path, w: dict, ours: list[list[str]], own: Path) -> dict:
    out = root / f"{own.stem}.json"
    argv = [
        "compare", str(out), "--winner-mesh", str(w["mesh"]), "--winner-maps", str(w["maps"]),
        "--winner-render", str(w["render"]), "--studio", str(w["studio"]), "--studio-mask", str(w["mask"]),
        "--ours-render-map", str(own),
    ]  # fmt: skip
    for paths in ours:
        argv += ["--ours-flipped", *paths]
    assert se.main(argv) == 0
    return json.loads(out.read_text())


def test_our_renders_map_is_compared_with_the_pipelines_on_the_same_cells(tmp_path):
    import tifffile

    w, ours = _base(tmp_path)
    reading = np.load(ours[0][3])
    px = se.analysis.PX_PER_NODE
    same = (
        tmp_path / "same.npy"
    )  # the winding's own map, mirrored back: the transfer carries it exactly here
    np.save(same, np.ascontiguousarray(np.roll(reading, px, axis=1)[:, ::-1]))
    record = _compare_own(tmp_path, w, ours, same)
    assert record["described"]["r_whole_pipeline_with_our_render"] == 1.0
    # a hole in our render's map leaves those cells out of every number
    holed = tmp_path / "holed.npy"
    with_hole = tifffile.imread(w["studio"]).astype(np.float32)
    with_hole[:8, :] = np.nan  # the first two cell rows
    np.save(holed, with_hole)
    assert _compare_own(tmp_path, w, ours, holed)["cells"] < record["cells"]


def test_each_part_and_the_transfer_distances_are_the_pipelines(tmp_path):
    w, ours = _base(tmp_path, dy=np.linspace(0.0, 3.0, 11))
    code, record = _compare(tmp_path, w, ours)
    assert code == 0
    described = record["described"]
    whole = described["by_part"]["columns_0_181"]  # wider than this lattice: every cell
    assert whole["cells"] == record["cells"] and whole["r"] == record["registered"]["r"]
    distance = described["transfer_distance_voxels"]
    assert 0 < distance["p50"] < distance["p95"] <= se.analysis.ACCEPT


def test_a_winding_with_a_zero_cosine_stops_the_comparison(tmp_path, monkeypatch):
    w, ours = _base(tmp_path)
    monkeypatch.setattr(se.analysis, "normals_agree", lambda *a: 0.0)
    code, record = _compare(tmp_path, w, ours)
    assert (
        code == 0 and record["verdict"] == "DOES_NOT_RUN" and "normals" in record["why"]
    )


def test_an_unreadable_mask_stops_the_comparison(tmp_path):
    import pytest

    w, ours = _base(tmp_path)
    w["mask"].write_bytes(b"not an image")
    with pytest.raises(SystemExit, match="cannot read"):
        _compare(tmp_path, w, ours)


def test_lines_met_exactly_are_measured(tmp_path, monkeypatch):
    w, ours = _base(tmp_path, studio_at_line=True)
    code, first = _compare(tmp_path, w, ours)
    assert code == 0
    assert (
        first["described"]["whole_pipeline"]["overlap"] is not None
    )  # cells at exactly 0.5 are ink
    (tmp_path / "studio_e2e.json").unlink()
    monkeypatch.setattr(se.f118, "MIN_CELL_SHARE", first["cells"] / first["mask_cells"])
    monkeypatch.setattr(
        se.f121,
        "MIN_WINDING_CELLS",
        first["described"]["by_winding"]["w035.tifxyz"]["cells"],
    )
    code, again = _compare(tmp_path, w, ours)
    assert code == 0 and again["registered"] == first["registered"]
    assert again["described"]["by_winding"]["w035.tifxyz"]["r"] is not None
