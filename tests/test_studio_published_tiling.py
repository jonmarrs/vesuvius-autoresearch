"""Finding 128: Studio's published tiling against the winner's. The verdict table, the comparison on synthetic maps,
and the run script's command."""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"


def _load():
    spec = importlib.util.spec_from_file_location(
        "studio_tiling_under_test", CONTROL / "studio_tiling.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


st = _load()


@pytest.mark.parametrize(
    ("gate", "r", "same", "expected"),
    [
        (0, 0.98, 0.98, "PUBLISHED_TILING_ADOPTED"),
        (0, 0.979, 0.99, "WINNERS_TILING_KEPT"),
        (0, 0.99, 0.979, "WINNERS_TILING_KEPT"),
        (1, 0.99, 0.99, "DOES_NOT_RUN"),
        (None, 0.99, 0.99, "DOES_NOT_RUN"),
    ],
)
def test_the_verdict_table(gate, r, same, expected):
    assert st.verdict(gate, {"r": r, "share_same_side_of_half": same}) == expected


def _write(tmp_path, noise):
    import cv2

    rng = np.random.default_rng(0)
    slow = rng.uniform(0, 1, (64, 96)).astype(np.float32)
    fast = np.clip(slow + rng.normal(0, noise, slow.shape), 0, 1).astype(np.float32)
    np.save(tmp_path / "fast.npy", fast)
    np.save(tmp_path / "slow.npy", slow)
    mask = np.zeros((64, 96), np.uint8)
    mask[8:56, 8:88] = 255
    cv2.imwrite(str(tmp_path / "mask.png"), mask)
    (tmp_path / "gate.json").write_text(json.dumps({"exit": 0, "seconds": 33}))
    return [str(tmp_path / "out.json"), str(tmp_path / "fast.npy"), str(tmp_path / "slow.npy"),
            str(tmp_path / "mask.png"), "--gate", str(tmp_path / "gate.json")]  # fmt: skip


def test_a_close_map_is_adopted_and_measured_once(tmp_path):
    argv = _write(tmp_path, 0.005)
    assert st.main(argv) == 0
    out = json.loads((tmp_path / "out.json").read_text())
    assert (
        out["verdict"] == "PUBLISHED_TILING_ADOPTED"
        and out["numbers"]["pixels"] == 48 * 80
    )
    assert out["infer"]["seconds"] == 33 and out["seconds_winners_tiling"] == 75
    assert st.main(argv) == 2


def test_a_different_map_is_not_adopted(tmp_path):
    st.main(_write(tmp_path, 0.2))
    assert (
        json.loads((tmp_path / "out.json").read_text())["verdict"]
        == "WINNERS_TILING_KEPT"
    )


def test_the_run_uses_the_published_tiling_and_uploads_nothing():
    path = CONTROL / "run_studio_tiling.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl", "--upload-file", "rsync "):
        assert word not in text
    infer = text[text.index("infer() {") : text.index("step check")]
    assert "inference.py" in infer and "--batch-size 32" in infer
    assert "--stride" not in infer and "--blend" not in infer
    f123 = (CONTROL / "run_studio_reproduction.sh").read_text()
    for sha in ("W_SHA", "P_SHA", "CODE_SHA"):
        assert re.search(rf"^{sha}=(\w+)", text, flags=re.M).group(1) == re.search(
            rf"^{sha}=(\w+)", f123, flags=re.M
        ).group(1)
    registration = (
        ROOT / "docs/preregistration/2026-11-20_studio_published_tiling.md"
    ).read_text()
    assert "r ≥ 0.98 and at least 98% of pixels on the same side of 0.5" in registration
    assert (st.R_LINE, st.SAME_SIDE_LINE) == (0.98, 0.98)


def test_the_seam_profile_finds_differences_on_the_window_edges():
    rng = np.random.default_rng(0)
    slow = rng.random((192, 288)).astype(np.float32)
    fast = slow.copy()
    fast[:, 95::96] += 0.3  # the last column of each 96-pixel window
    fast[:, 0::96] += 0.3  # and the first
    mask = np.ones(slow.shape, bool)
    mask[:, :5] = False  # masked pixels are left out
    prof = st.seam_profile(fast, slow, mask)
    assert prof["period"] == 96
    assert prof["columns"]["edge"] == pytest.approx(0.3, abs=1e-6)
    assert prof["columns"]["middle"] == pytest.approx(0.0, abs=1e-6)
    assert prof["rows"]["edge"] == pytest.approx(prof["rows"]["middle"], abs=1e-6)
    assert prof["pixels"] == int(mask.sum())


def test_the_seams_command_writes_its_own_record_once(tmp_path):
    argv = _write(tmp_path, 0.2)
    out = tmp_path / "seams.json"
    seams = ["seams", str(out), *argv[1:4]]
    assert st.main(seams) == 0
    rec = json.loads(out.read_text())
    assert rec["finding"] == 128 and rec["described_after_the_verdict"] is True
    assert set(rec["seam_profile"]) == {"period", "pixels", "columns", "rows"}
    assert st.main(seams) == 2


# --- each position of the window, an empty edge, an unreadable mask or pickled map, and a run that did not happen ---


def test_the_seam_profile_takes_both_window_edges_and_the_middle_third_exactly():
    # per column position: first 0.1, last 0.3, 31 and 64 just outside the middle, 32 its first pixel, 33 to 63 0.2
    offset = np.zeros(96)
    offset[[0, 95, 31, 32, 64]] = [0.1, 0.3, 0.7, 0.6, 0.9]
    offset[33:64] = 0.2
    slow = np.zeros((4, 192), np.float32)
    fast = slow + np.tile(offset, 2)[None, :].astype(np.float32)
    columns = st.seam_profile(fast, slow, np.ones(slow.shape, bool))["columns"]
    assert columns["edge"] == pytest.approx(0.2, abs=1e-6)
    assert columns["middle"] == pytest.approx((0.6 + 31 * 0.2) / 32, abs=1e-6)


def test_a_mask_with_no_window_edge_gives_no_edge_number():
    mask = np.zeros((96, 96), bool)
    mask[32:64, 32:64] = True
    prof = st.seam_profile(
        np.ones((96, 96), np.float32), np.zeros((96, 96), np.float32), mask
    )
    assert prof["columns"] == {"edge": None, "middle": 1.0}
    assert prof["rows"] == {"edge": None, "middle": 1.0}


def test_an_unreadable_mask_stops_both_commands(tmp_path):
    argv = _write(tmp_path, 0.005)
    (tmp_path / "mask.png").write_text("not an image")
    with pytest.raises(SystemExit, match="cannot read"):
        st.main(argv)
    with pytest.raises(SystemExit, match="cannot read"):
        st.main(["seams", str(tmp_path / "seams.json"), *argv[1:4]])


def test_a_map_holding_python_objects_is_refused_by_both_commands(tmp_path):
    argv = _write(tmp_path, 0.005)
    fast = np.load(tmp_path / "fast.npy")
    np.save(tmp_path / "fast.npy", fast.astype(object), allow_pickle=True)
    with pytest.raises(ValueError, match="allow_pickle"):
        st.main(argv)
    with pytest.raises(ValueError, match="allow_pickle"):
        st.main(["seams", str(tmp_path / "seams.json"), *argv[1:4]])


@pytest.mark.parametrize("missing", ["gate.json", "fast.npy"])
def test_without_the_gate_or_the_published_map_the_comparison_does_not_run(
    tmp_path, missing
):
    argv = _write(tmp_path, 0.005)
    (tmp_path / missing).unlink()
    assert st.main(argv) == 0
    out = json.loads((tmp_path / "out.json").read_text())
    assert out["verdict"] == "DOES_NOT_RUN" and out["numbers"] is None
    assert out["infer"] == (
        {"exit": None} if missing == "gate.json" else {"exit": 0, "seconds": 33}
    )
