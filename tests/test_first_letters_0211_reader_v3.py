"""Finding 120's comparison: the verdict table, the overlap measure and its control, and the whole comparison on
maps whose answer is known (finding 118's synthetic surface, with a weaker ensemble and a Reader V3 map)."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cr = _load(
    "compare_readers_under_test",
    ROOT / "repro/first_letters/pherc0211_control/compare_readers.py",
)
f118_tests = _load(
    "f118_tests_for_reader_v3", ROOT / "tests/test_first_letters_0211_reader_control.py"
)


def _reader(r, overlap, wrong=0.0, slid=0.0):
    return {
        "r": r,
        "overlap": overlap,
        "control_wrong_side": wrong,
        "control_slid": {"largest_absolute": slid},
    }


def test_the_verdict_table():
    ens = _reader(0.53, 0.30)
    assert cr.verdict(None, _reader(0.7, 0.4), 1.0) == "DOES_NOT_RUN"
    assert cr.verdict(ens, _reader(0.7, 0.4), 0.49) == "DOES_NOT_RUN"
    assert cr.verdict(ens, _reader(None, 0.4), 1.0) == "DOES_NOT_RUN"
    assert cr.verdict(ens, _reader(0.7, 0.4, wrong=0.36), 1.0) == "V3_FAILS_CONTROLS"
    assert cr.verdict(ens, _reader(0.7, 0.4, slid=-0.36), 1.0) == "V3_FAILS_CONTROLS"
    assert (
        cr.verdict(ens, _reader(0.63, 0.35), 1.0) == "V3_CLOSER"
    )  # both margins exactly
    assert cr.verdict(ens, _reader(0.63, 0.3499), 1.0) == "V3_NO_CLOSER"
    assert cr.verdict(ens, _reader(0.80, 0.31), 1.0) == "V3_NO_CLOSER"
    assert (
        cr.verdict(ens, _reader(0.43, 0.40), 1.0) == "V3_FARTHER"
    )  # r down by the margin
    assert (
        cr.verdict(ens, _reader(0.80, 0.25), 1.0) == "V3_FARTHER"
    )  # overlap down by the margin


def test_the_lines_are_the_registrations():
    assert (cr.R_MARGIN, cr.OVERLAP_MARGIN, cr.INK, cr.RATIO) == (0.10, 0.05, 0.5, 2.0)
    assert cr.DEPTH == 1 and tuple(range(-3, 3)) == cr.DEPTHS
    text = (
        ROOT / "docs/preregistration/2026-11-16_first_letters_0211_reader_v3.md"
    ).read_text()
    assert "Δr at least +0.10 and Δoverlap at least +0.05 | `V3_CLOSER`" in text
    assert "Δr at most −0.10, or Δoverlap at most −0.05 | `V3_FARTHER`" in text
    assert "probability at least 0.5" in text
    assert "at least twice the absolute value of each of its controls" in text
    assert "depths −3 to +2" in text
    fetch = (
        ROOT / "repro/first_letters/pherc0211_control/fetch_reader_v3.sh"
    ).read_text()
    assert "REVISION=aee1d64b" in fetch and "SHA256=ea405417" in fetch
    assert "revision `aee1d64b`" in text and "SHA-256 `ea405417…`" in text


def test_overlap_is_one_for_the_same_cells_and_zero_for_others():
    compared = np.ones((4, 5), bool)
    ink = np.zeros((4, 5), bool)
    ink[0, :2] = True
    same = ink.astype(float)
    assert cr.overlap(ink, same, compared) == 1.0
    other = np.zeros((4, 5))
    other[3, 3:] = 1.0
    assert cr.overlap(ink, other, compared) == 0.0
    # no ink among the compared cells, or nothing else to choose from: no number
    assert cr.overlap(np.zeros((4, 5), bool), same, compared) is None
    assert cr.overlap(np.ones((4, 5), bool), same, compared) is None


def test_the_strongest_cells_are_chosen_reproducibly_on_ties():
    compared = np.ones((1, 4), bool)
    image = np.array([[1.0, 2.0, 2.0, 0.0]])
    assert cr.strongest(image, compared, 1).tolist() == [[False, True, False, False]]
    assert cr.strongest(image, compared, 2).tolist() == [[False, True, True, False]]


def test_the_slid_overlap_leaves_out_the_cells_that_wrapped_round():
    rng = np.random.default_rng(0)
    cells = np.ones((40, 40), bool)
    ink = np.zeros((40, 40), bool)
    ink[5:9, :] = True
    ink[24:28, :] = True  # where our first rows land if a slide up by 16 wrapped round
    ours = 0.01 * rng.random((40, 40))
    ours[:4, :] += 1.0
    slid = cr.slid_overlap(ink, ours, cells, 16)
    # counted with the wrap, our strong first rows would sit on the winner's ink at rows 24-27 (overlap 0.5);
    # left out, the compared rows 0-23 hold only our faint background: chance level
    assert slid["up"] is not None and slid["up"] < 0.3
    assert slid["largest"] == max(v for k, v in slid.items() if k != "largest")


def _write_v3_maps(root: Path, reading_strength: float, other_same: bool = False):
    """Reader V3's maps at every depth: the winner's strokes at `reading_strength` on the reading side."""
    import cv2
    import tifffile

    strokes = tifffile.imread(root / "studio.tif").astype(float)
    rng = np.random.default_rng(3)
    maps = root / "v3_maps"
    maps.mkdir()
    for d in cr.DEPTHS:
        for tag, base in (
            ("_reverse", strokes),
            ("", strokes if other_same else np.roll(strokes, 37, axis=1)),
        ):
            q = np.clip(
                0.25
                + reading_strength * 0.5 * base
                + 0.02 * rng.standard_normal(base.shape),
                0,
                1,
            )
            cv2.imwrite(
                str(maps / f"v9_66__reader_v3__L66s{d + 25}{tag}.tif"),
                np.clip(64 + 128 * q, 0, 255).astype(np.uint8),
            )
    return maps


def _weaken_the_ensemble(root: Path):
    """The ensemble's reading side at depth +1: the strokes, faint, under strong noise."""
    import cv2
    import tifffile

    strokes = tifffile.imread(root / "studio.tif").astype(float)
    rng = np.random.default_rng(5)
    maps = root / "maps"
    for model in cr.analysis.MODELS:
        noisy = np.clip(
            0.4 + 0.15 * strokes + 0.12 * rng.standard_normal(strokes.shape), 0, 1
        )
        if model == "hecate":
            cv2.imwrite(
                str(maps / "v9_66__hecate__L66zc33.50_reverse.png"),
                np.round(noisy * 255).astype(np.uint8),
            )
        else:
            cv2.imwrite(
                str(maps / f"v9_66__{model}__L66s26_reverse.tif"),
                np.clip(64 + 128 * noisy, 0, 255).astype(np.uint8),
            )


def _args(root: Path, v3_maps: Path) -> list[str]:
    args = f118_tests._write_inputs(root)
    return [
        *args[: args.index("--image")],
        "--v3-maps",
        str(v3_maps),
        "--image",
        str(root / "three.png"),
    ]


def test_a_reader_that_draws_the_winners_strokes_more_clearly_is_closer(tmp_path):
    args = f118_tests._write_inputs(tmp_path)
    _weaken_the_ensemble(tmp_path)
    v3_maps = _write_v3_maps(tmp_path, 1.0)
    args = [
        *args[: args.index("--image")],
        "--v3-maps",
        str(v3_maps),
        "--image",
        str(tmp_path / "three.png"),
    ]
    out = tmp_path / "readers.json"
    assert cr.main([str(out), *args]) == 0
    record = json.loads(out.read_text())
    assert record["cell_share"] >= 0.5 and record["winner_ink_cells"] > 0
    assert record["reader_v3"]["r"] > record["ensemble"]["r"] + 0.10
    assert record["reader_v3"]["overlap"] > record["ensemble"]["overlap"] + 0.05
    assert record["verdict"] == "V3_CLOSER"
    assert set(record["described"]["v3_by_depth"]) == {f"{d:+d}" for d in cr.DEPTHS}
    assert (tmp_path / "three.png").exists()
    assert cr.main([str(out), *args]) == 2  # measured once


def test_a_reader_whose_other_side_carries_the_strokes_too_fails_its_controls(tmp_path):
    args = f118_tests._write_inputs(tmp_path)
    v3_maps = _write_v3_maps(tmp_path, 1.0, other_same=True)
    args = [*args[: args.index("--image")], "--v3-maps", str(v3_maps)]
    out = tmp_path / "readers.json"
    assert cr.main([str(out), *args]) == 0
    assert json.loads(out.read_text())["verdict"] == "V3_FAILS_CONTROLS"


def test_the_ensemble_numbers_are_finding_118s(tmp_path):
    """On the same inputs the ensemble's r and controls are what compare.py registers for finding 118."""
    args = f118_tests._write_inputs(tmp_path)
    v3_maps = _write_v3_maps(tmp_path, 0.5)
    first = tmp_path / "f118.json"
    assert cr.f118.main([str(first), *args]) == 0
    out = tmp_path / "readers.json"
    assert (
        cr.main([str(out), *args[: args.index("--image")], "--v3-maps", str(v3_maps)])
        == 0
    )
    registered = json.loads(first.read_text())["registered"]
    ensemble = json.loads(out.read_text())["ensemble"]
    assert ensemble["r"] == registered["r"]
    assert ensemble["control_wrong_side"] == registered["control_wrong_side"]
    assert ensemble["control_slid"] == registered["control_slid"]


@pytest.mark.parametrize("script", ["run_reader_v3.sh", "fetch_reader_v3.sh"])
def test_the_scripts_upload_nothing_and_run_the_recipes_call(script):
    import os

    path = ROOT / "repro/first_letters/pherc0211_control" / script
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl -T", "--upload-file", "rsync "):
        assert word not in text
    if script == "run_reader_v3.sh":
        # the recipe's own flags for its ink_9um seeds, and the same 17-layer window
        assert "--overlap 0.5 --blend-mode hann" in text and "--direction both" in text
        assert "S=$(( N / 2 + d - 8 )); E=$(( S + 17 ))" in text
    else:
        assert "check_checkpoint.py" in text and "sha256sum -c" in text


def test_the_verdict_table_at_its_other_edges():
    ens = _reader(0.53, 0.30)
    closer = _reader(0.72, 0.40)
    # a cell share exactly at the line runs, and a reader exactly twice its controls clears them
    assert cr.verdict(ens, closer, cr.f118.MIN_CELL_SHARE) == "V3_CLOSER"
    assert cr.verdict(ens, _reader(0.72, 0.40, wrong=0.36), 1.0) == "V3_CLOSER"
    assert cr.verdict(ens, _reader(0.72, 0.40, slid=-0.36), 1.0) == "V3_CLOSER"
    # a missing control fails the controls; a missing number on either side does not run
    assert cr.verdict(ens, _reader(0.72, 0.40, wrong=None), 1.0) == "V3_FAILS_CONTROLS"
    assert cr.verdict(ens, _reader(0.72, 0.40, slid=None), 1.0) == "V3_FAILS_CONTROLS"
    assert cr.verdict(_reader(None, 0.30), closer, 1.0) == "DOES_NOT_RUN"
    assert cr.verdict(_reader(0.53, None), closer, 1.0) == "DOES_NOT_RUN"
    assert cr.verdict(ens, _reader(0.72, None), 1.0) == "DOES_NOT_RUN"


def test_a_constant_map_is_refused_rather_than_standardised():
    with pytest.raises(ValueError, match="constant"):
        cr.standardise(np.ones((3, 4)), np.ones((3, 4), bool))


def test_the_strongest_cells_keep_their_order_among_many_ties():
    compared = np.ones((1, 1000), bool)
    chosen = cr.strongest(np.zeros((1, 1000)), compared, 10)
    assert np.flatnonzero(chosen).tolist() == list(range(10))


def test_overlap_counts_only_the_winners_ink_among_the_compared_cells():
    compared = np.zeros((4, 5), bool)
    compared[:, :3] = True
    ink = np.zeros((4, 5), bool)
    ink[0, 0] = ink[0, 4] = True  # the second lies outside the compared cells
    ours = np.zeros((4, 5))
    ours[0, 0] = 1.0
    assert cr.overlap(ink, ours, compared) == 1.0


def _wrapping_case():
    """slid_overlap's up case from the test above: what wraps round would land on the winner's ink."""
    rng = np.random.default_rng(0)
    ink = np.zeros((40, 40), bool)
    ink[5:9, :] = True
    ink[24:28, :] = True
    ours = 0.01 * rng.random((40, 40))
    ours[:4, :] += 1.0
    return ink, ours


@pytest.mark.parametrize(
    ("direction", "turn"),
    [
        ("down", np.flipud),
        ("left", np.transpose),
        ("right", lambda a: np.fliplr(a.T)),
    ],
)
def test_each_slide_leaves_out_the_cells_that_wrapped_round(direction, turn):
    ink, ours = (turn(a) for a in _wrapping_case())
    slid = cr.slid_overlap(ink, ours, np.ones((40, 40), bool), 16)
    assert slid[direction] is not None and slid[direction] < 0.3


def test_the_largest_slid_overlap_passes_over_a_slide_with_no_ink():
    ink = np.zeros((40, 40), bool)
    ink[:4, :] = True  # sliding down by 16 leaves only rows 16-39 compared: no ink
    ours = np.random.default_rng(1).random((40, 40))
    slid = cr.slid_overlap(ink, ours, np.ones((40, 40), bool), 16)
    assert slid["down"] is None
    assert slid["largest"] == max(slid[k] for k in ("up", "right", "left"))


def test_the_bootstrap_resamples_blocks_with_cells_and_measures_b_minus_a():
    rng = np.random.default_rng(2)
    cells = np.zeros((128, 128), bool)
    cells[:64, :64] = cells[64:, :64] = cells[:64, 64:] = True
    cells[100, 100] = True  # a block holding one cell is left out
    theirs = rng.standard_normal(cells.shape)
    unrelated = rng.standard_normal(cells.shape)
    close = theirs + 0.5 * rng.standard_normal(cells.shape)
    out = cr.block_bootstrap(theirs, unrelated, close, cells)
    assert out["blocks"] == 3
    assert 0 < out["low"] < out["high"]


def _shifted_alignment(monkeypatch, shift, aligned):
    monkeypatch.setattr(
        cr.f118,
        "alignment",
        lambda layers, ct: {"shift_pixels": list(shift), "aligned": aligned},
    )


@pytest.mark.parametrize("shift", [(16, 0), (-16, 0), (0, 16)])
def test_a_shift_at_the_edge_of_the_search_does_not_run(tmp_path, monkeypatch, shift):
    v3_maps = _write_v3_maps_after_inputs(tmp_path)
    _shifted_alignment(monkeypatch, shift, aligned=False)
    out = tmp_path / "readers.json"
    assert cr.main([str(out), *_args_without_image(tmp_path, v3_maps)]) == 0
    record = json.loads(out.read_text())
    assert record["verdict"] == "DOES_NOT_RUN" and "ensemble" not in record


def _write_v3_maps_after_inputs(root: Path) -> Path:
    f118_tests._write_inputs(root)
    return _write_v3_maps(root, 1.0)


def _args_without_image(root: Path, v3_maps: Path) -> list[str]:
    args = [
        "--mesh", str(root / "v9" / "normalized-tifxyz"), "--maps", str(root / "maps"),
        "--render", str(root / "v9_66.zarr"), "--studio", str(root / "studio.tif"),
        "--studio-mask", str(root / "mask.png"), "--winner-ct", str(root / "ct.tif"),
    ]  # fmt: skip
    return [*args, "--v3-maps", str(v3_maps)]


@pytest.mark.parametrize(
    ("shift", "aligned", "applied"),
    [((0, -1), True, [0, 0]), ((0, -8), False, [0, -8])],
)
def test_the_shift_is_applied_only_when_out_of_tolerance_and_to_every_depth(
    tmp_path, monkeypatch, shift, aligned, applied
):
    v3_maps = _write_v3_maps_after_inputs(tmp_path)
    _shifted_alignment(monkeypatch, shift, aligned)
    out = tmp_path / "readers.json"
    assert cr.main([str(out), *_args_without_image(tmp_path, v3_maps)]) == 0
    record = json.loads(out.read_text())
    assert record["shift_applied_pixels"] == applied
    # the registered depth, read again among the described ones, is moved by the same shift
    at_depth = record["described"]["v3_by_depth"][f"{cr.DEPTH:+d}"]
    for key in ("r", "control_wrong_side", "overlap"):
        assert at_depth[key] == record["reader_v3"][key]


def test_a_winners_cell_exactly_at_the_ink_line_is_ink(tmp_path):
    import tifffile

    v3_maps = _write_v3_maps_after_inputs(tmp_path)
    studio = tmp_path / "studio.tif"
    # the strokes at exactly 0.5 and nothing else: every 4-pixel block of the map is one cell's value
    at_line = np.where(tifffile.imread(studio) >= 0.3, 0.5, 0.0).astype(np.float32)
    tifffile.imwrite(studio, at_line)
    out = tmp_path / "readers.json"
    assert cr.main([str(out), *_args_without_image(tmp_path, v3_maps)]) == 0
    record = json.loads(out.read_text())
    assert 0 < record["winner_ink_cells"] < record["cells"]


def test_a_cell_share_exactly_at_the_line_is_measured(tmp_path, monkeypatch):
    v3_maps = _write_v3_maps_after_inputs(tmp_path)
    first = tmp_path / "first.json"
    assert cr.main([str(first), *_args_without_image(tmp_path, v3_maps)]) == 0
    record = json.loads(first.read_text())
    share = float(record["cells"]) / record["mask_cells"]
    monkeypatch.setattr(cr.f118, "MIN_CELL_SHARE", share)
    out = tmp_path / "readers.json"
    assert cr.main([str(out), *_args_without_image(tmp_path, v3_maps)]) == 0
    again = json.loads(out.read_text())
    assert again["ensemble"] == record["ensemble"]
    assert again["verdict"] == record["verdict"] != "DOES_NOT_RUN"


ck = _load(
    "check_checkpoint_under_test",
    ROOT / "repro/first_letters/pherc0211_control/check_checkpoint.py",
)


class _MakesADirectory:
    """Pickles as a call to os.makedirs: an unrestricted load would create the directory."""

    def __init__(self, path):
        self.path = path

    def __reduce__(self):
        import os

        return (os.makedirs, (self.path,))


def test_a_checkpoint_of_tensors_loads_and_its_configuration_is_described(
    tmp_path, capsys
):
    torch = pytest.importorskip("torch")
    path = tmp_path / "reader.pth"
    config = {"model": {"model_type": "timesformer"}, "patch_size": 64}
    torch.save({"state_dict": {"w": torch.zeros(2)}, "config": config}, path)
    assert ck.main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "weights_only_load": "ok",
        "top_level_keys": ["config", "state_dict"],
        "model_type": "timesformer",
        "patch_size": 64,
    }


def test_a_checkpoint_that_would_run_code_is_refused_and_the_code_never_runs(
    tmp_path, capsys
):
    torch = pytest.importorskip("torch")
    marker = tmp_path / "made_by_the_checkpoint"
    path = tmp_path / "reader.pth"
    torch.save({"w": torch.zeros(2), "x": _MakesADirectory(str(marker))}, path)
    assert ck.main([str(path)]) == 1
    assert "REFUSED" in capsys.readouterr().err
    assert not marker.exists()


@pytest.mark.parametrize("argv", [[], ["a.pth", "b.pth"]], ids=["none", "two"])
def test_the_checker_takes_exactly_one_checkpoint(argv, capsys):
    assert ck.main(argv) == 2
    assert "usage: check_checkpoint.py" in capsys.readouterr().err


def test_the_description_reads_flat_and_nested_configurations():
    flat = {"config": {"model_type": "resnet3d", "crop_size": 32}}
    assert ck.describe(flat) == {
        "top_level_keys": ["config"],
        "model_type": "resnet3d",
        "patch_size": 32,
    }
    nested = {"config": {"model": {"depth": 4}, "model_type": "unet", "patch_size": 48}}
    assert ck.describe(nested)["model_type"] == "unet"
    assert ck.describe({"config": "unet"}) == {"top_level_keys": ["config"]}
    assert ck.describe([1, 2]) == {"top_level_keys": None}
