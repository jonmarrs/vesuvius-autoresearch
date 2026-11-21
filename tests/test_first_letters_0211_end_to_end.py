"""Finding 121's comparison on surfaces whose answer is known: finding 118's synthetic winner, and windings of
"ours" that are that surface again (the transfer is then the identity), mirrored (normals the other way), or
moved off it (nothing to transfer)."""

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


e2e = _load("end_to_end_under_test", CONTROL / "end_to_end.py")
f118_tests = _load(
    "f118_tests_for_end_to_end",
    ROOT / "tests/test_first_letters_0211_reader_control.py",
)
MODELS = e2e.analysis.MODELS


def _winner(root: Path) -> dict:
    args = f118_tests._write_inputs(root)
    value = {args[i]: args[i + 1] for i in range(0, len(args), 2)}
    return {
        "args": args,
        "mesh": Path(value["--mesh"]),
        "maps": Path(value["--maps"]),
        "render": Path(value["--render"]),
        "studio": Path(value["--studio"]),
        "mask": Path(value["--studio-mask"]),
    }


def _ours(root: Path, w: dict, name: str, mirror=False, dy=0.0, v3=False) -> list[str]:
    """A winding of ours: the winner's mesh again (optionally mirrored left to right, or moved dy voxels
    along y, which is the sheet normal), its render copied, and the winner's maps renamed and mirrored
    with it, so its ink lies on the same scroll positions as the winner's."""
    import cv2
    import tifffile

    mesh = root / f"{name}.tifxyz"
    mesh.mkdir()
    for axis in "xyz":
        values = tifffile.imread(w["mesh"] / f"{axis}.tif")
        if mirror:
            values = values[:, ::-1]
        if axis == "y":
            values = values + dy
        tifffile.imwrite(mesh / f"{axis}.tif", np.ascontiguousarray(values))
    render = root / f"{name}_66.zarr"
    shutil.copytree(w["render"], render)
    maps = root / f"maps_{name}"
    maps.mkdir()
    for path in w["maps"].iterdir():
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if mirror:
            # pixel p sits at node p / 20, so mirroring the nodes takes pixel p to 20 * (cols - 1) - p: a flip
            # of the whole image, then one node (20 pixels) back
            px = e2e.analysis.PX_PER_NODE
            image = np.ascontiguousarray(np.roll(image[:, ::-1], -px, axis=1))
        cv2.imwrite(str(maps / path.name.replace("v9_66", f"{name}_66")), image)
        if v3 and "seed42__L66s26" in path.name:
            target = root / "v3_maps"
            target.mkdir(exist_ok=True)
            tag = "_reverse" if path.name.endswith("_reverse.tif") else ""
            cv2.imwrite(str(target / f"{name}_66__reader_v3__L66s26{tag}.tif"), image)
    return [str(mesh), str(maps), str(render)]


def _compare(
    root: Path, w: dict, ours: list[tuple[str, list[str]]], v3=False
) -> tuple[int, dict]:
    out = root / "e2e.json"
    argv = [
        "compare", str(out), "--winner-mesh", str(w["mesh"]), "--winner-maps", str(w["maps"]),
        "--winner-render", str(w["render"]), "--studio", str(w["studio"]), "--studio-mask", str(w["mask"]),
        "--image", str(root / "e2e.png"),
    ]  # fmt: skip
    for flag, paths in ours:
        argv += [flag, *paths]
    if v3:
        argv += ["--v3-maps", str(root / "v3_maps")]
    code = e2e.main(argv)
    return code, json.loads(out.read_text()) if out.exists() else {}


def test_the_verdict_table_is_finding_118s_under_this_findings_names():
    numbers = f118_tests._numbers
    assert e2e.verdict(None, 1.0) == "DOES_NOT_RUN"
    assert e2e.verdict(numbers(0.6, 0.0, 0.1), 0.49) == "DOES_NOT_RUN"
    assert e2e.verdict(numbers(0.30, 0.0, 0.15), 1.0) == "E2E_AGREES"
    assert (
        e2e.verdict(numbers(0.30, 0.0, 0.151), 1.0) == "E2E_DISAGREES"
    )  # 0.30 is not twice 0.151
    assert e2e.verdict(numbers(0.29, 0.1, 0.1), 1.0) == "E2E_PARTLY"
    assert e2e.verdict(numbers(0.14, 0.0, 0.0), 1.0) == "E2E_DISAGREES"
    assert e2e.verdict(numbers(0.6, -0.31, 0.0), 1.0) == "E2E_DISAGREES"


def test_the_lines_are_the_registrations():
    assert (e2e.R_AGREES, e2e.R_PARTLY, e2e.RATIO, e2e.MIN_CELL_SHARE) == (
        0.30,
        0.15,
        2.0,
        0.5,
    )
    assert e2e.DEPTH == 1 and e2e.analysis.ACCEPT == 4.0
    text = (
        ROOT / "docs/preregistration/2026-11-16_first_letters_0211_end_to_end.md"
    ).read_text()
    assert (
        "r at least 0.30, and at least twice the absolute value of each control | `E2E_AGREES`"
        in text
    )
    assert (
        "r at least 0.15, and at least twice the absolute value of each control | `E2E_PARTLY`"
        in text
    )
    assert "fewer than half of the winner's mask cells" in text
    assert "w033, w034, w035 and w036" in text
    script = (CONTROL / "run_end_to_end.sh").read_text()
    assert "WINDINGS=(w033 w034 w035 w036)" in script and "DEPTH=1" in script


def test_our_own_surface_again_gives_finding_118s_numbers(tmp_path):
    w = _winner(tmp_path)
    ours = _ours(tmp_path, w, "w035", v3=True)
    code, record = _compare(tmp_path, w, [("--ours", ours)], v3=True)
    assert code == 0 and record["verdict"] == "E2E_AGREES"
    # every cell finding 118 compared on these inputs gets our ink, from distance 0
    first = tmp_path / "f118.json"
    assert e2e.f118.main([str(first), *w["args"]]) == 0
    f118 = json.loads(first.read_text())
    assert (record["cells"], record["mask_cells"]) == (
        f118["cells"],
        f118["mask_cells"],
    )
    assert record["described"]["transfer_distance_voxels"]["p95"] == 0.0
    assert record["registered"] == f118["registered"]
    # the same maps on the same cells: our numbers are finding 118's on these cells, and the two maps agree
    same = record["described"]["finding_118_on_these_cells"]
    assert record["registered"]["r"] == same["r"]
    assert record["registered"]["control_wrong_side"] == same["control_wrong_side"]
    assert record["described"]["r_with_finding_118_maps"] == 1.0
    assert (
        record["ours"][0]["normal_cosine_median"] > 0.99
        and not record["ours"][0]["render_flipped"]
    )
    assert record["described"]["reader_v3"]["r"] is not None
    assert (tmp_path / "e2e.png").exists()
    assert e2e.main(["compare", str(tmp_path / "e2e.json"), "--winner-mesh", "x", "--winner-maps", "x",
                     "--winner-render", "x", "--studio", "x", "--studio-mask", "x",
                     "--ours", *ours]) == 2  # fmt: skip


def test_a_winding_whose_normals_point_the_other_way_must_be_rendered_flipped(tmp_path):
    w = _winner(tmp_path)
    mirrored = _ours(tmp_path, w, "w033", mirror=True)
    code, record = _compare(tmp_path, w, [("--ours", mirrored)])
    assert code == 0 and record["verdict"] == "DOES_NOT_RUN"
    assert "against the winner's normals" in record["why"]
    (tmp_path / "e2e.json").unlink()
    code, record = _compare(tmp_path, w, [("--ours-flipped", mirrored)])
    assert code == 0 and record["verdict"] == "E2E_AGREES"
    assert (
        record["ours"][0]["normal_cosine_median"] < -0.99
        and record["ours"][0]["render_flipped"]
    )
    # mirrored maps on the mirrored mesh carry the ink back to the same places
    assert record["described"]["r_with_finding_118_maps"] == 1.0


def test_orient_says_flip_for_the_mirrored_winding_and_keep_for_the_same_one(
    tmp_path, capsys
):
    w = _winner(tmp_path)
    same = Path(_ours(tmp_path, w, "w035")[0])
    mirrored = Path(_ours(tmp_path, w, "w033", mirror=True)[0])
    out = tmp_path / "orient.json"
    assert e2e.main(["orient", str(out), str(w["mesh"]), str(same), str(mirrored)]) == 0
    printed = capsys.readouterr().out.split("\n")
    assert "w035.tifxyz keep" in printed and "w033.tifxyz flip" in printed
    record = json.loads(out.read_text())
    assert (
        record["w033.tifxyz"]["normal_cosine_median"]
        < 0
        < record["w035.tifxyz"]["normal_cosine_median"]
    )


def test_a_winding_off_the_sheet_gives_no_ink_and_does_not_run(tmp_path):
    w = _winner(tmp_path)
    off = _ours(
        tmp_path, w, "w034", dy=10.0
    )  # 10 voxels along the normal: beyond the 4-voxel transfer
    code, record = _compare(tmp_path, w, [("--ours", off)])
    assert (
        code == 0
        and record["verdict"] == "DOES_NOT_RUN"
        and record["cell_share"] == 0.0
    )


def test_the_nearest_winding_gives_the_ink(tmp_path):
    w = _winner(tmp_path)
    on = _ours(tmp_path, w, "w035")
    near = _ours(tmp_path, w, "w036", dy=3.0)  # within 4 voxels, but farther than w035
    code, record = _compare(tmp_path, w, [("--ours", near), ("--ours", on)])
    assert code == 0
    given = {Path(o["mesh"]).name: o["cells_given"] for o in record["ours"]}
    assert given["w035.tifxyz"] > 0 and given["w036.tifxyz"] == 0
    assert record["described"]["by_winding"]["w036.tifxyz"] == {"cells": 0, "r": None}


def test_the_part_masks_are_finding_119s_columns():
    shape = (10, 301 * e2e.CELLS_PER_NODE)
    first = e2e.part_mask(shape, e2e.PARTS["columns_0_181"])
    second = e2e.part_mask(shape, e2e.PARTS["columns_193_300"])
    assert first[:, : 182 * 5].all() and not first[:, 182 * 5 :].any()
    assert second[:, 193 * 5 :].all() and not second[:, : 193 * 5].any()


def test_the_driver_runs_the_registered_steps_in_order_and_uploads_nothing():
    path = CONTROL / "run_end_to_end.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl -T", "--upload-file", "rsync "):
        assert word not in text
    order = [
        'run_snap.sh" "$ARM"',
        'run_flatten.sh" "$ARM"',
        'end_to_end.py" orient',
        'run_render.sh" "$ARM" "$w" flip',
        'step "ink_$w"',
        'step "reader_v3_$w"',
        'end_to_end.py" compare',
    ]
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)
    assert 'run_depth_sweep.sh" "$render" "$out" "$DEPTH" "$DEPTH"' in text
    assert "sha256sum -c" in text and "check_checkpoint.py" in text
    assert (
        'gate "$ARM" "chain_$name"' in text
    )  # the chain's gates never overwrite the band scripts'
    assert "finding 121 runs once" in text


def test_the_band_render_flips_only_when_asked():
    text = (ROOT / "repro/first_letters/eligible_band/run_render.sh").read_text()
    assert "flip) FLIP=(--flip-normals); FLIPPED=true ;;" in text
    assert '"") ;;' in text and "FLIP=(); FLIPPED=false" in text
    assert '--slice-step 1 "${FLIP[@]}"' in text
    assert '"\\"flipped\\": $FLIPPED, \\"slices\\": $SLICES"' in text


@pytest.mark.parametrize("bad", ["yes", "--flip-normals"])
def test_the_band_render_refuses_any_other_third_argument(tmp_path, bad):
    import subprocess

    env = {"PATH": "/usr/bin:/bin", "FL_ROOT": str(tmp_path)}
    done = subprocess.run(
        ["bash", str(ROOT / "repro/first_letters/eligible_band/run_render.sh"), "arm", "w001", bad],
        env=env, capture_output=True, text=True,
    )  # fmt: skip
    assert done.returncode == 2 and "is 'flip' or nothing" in done.stderr
