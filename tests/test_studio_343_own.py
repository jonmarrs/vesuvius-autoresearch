"""Finding 136's analysis: the area's cells, the lattice in render pixels, and the registered verdict with its failure
branches."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

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


# --- compare run, with finding 110's side, transfer and normals stood in for: our windings' lattice is the published
# surface's, cell for cell, so the real carry moves each value to its own place; reading_frame and main ------------

LH, LW = 40, 50  # the published surface's lattice: a 160 x 200-pixel render
AREA = {
    "row0": 2,
    "row1": 158,
    "col0": 2,
    "col1": 198,
}  # lattice rows 1 to 38 and columns 1 to 48 lie wholly inside


def test_the_verdict_runs_at_exactly_half_the_cells():
    assert (
        own.verdict(_numbers(0.8), 0.5, True, [0.997, 0.998]) == "STUDIO_343_OWN_CLOSE"
    )


def _world(tmp_path, monkeypatch, cosines=(0.997, 0.998)):
    """The published surface (its row 2 not rendered, its Studio map NaN at cell (3, 5) and exactly 0.5 over cells
    10 to 13 x 20 to 23), our two windings (w048 holds exactly 1,000 cells: rows 10 to 34, columns 8 to 47; row 4
    has no winding; w047's reversed map is NaN on row 6), a 66-layer render whose layer 10 is empty over 4 reading
    cells, the sidecar and u."""
    import argparse

    import cv2
    import zarr

    rng = np.random.default_rng(13)
    published = rng.random((LH * 4, LW * 4))
    published[40:56, 80:96] = 0.5
    np.save(tmp_path / "pub.npy", published)
    np.save(tmp_path / "pub_rev.npy", rng.random((LH * 4, LW * 4)))
    studios = {}
    for k, w in enumerate(("w047", "w048")):
        studios[w] = published + rng.normal(0, 0.05 * (k + 1), published.shape)
        np.save(tmp_path / f"{w}.npy", studios[w])
        reversed_ = rng.random(published.shape)
        if w == "w047":
            reversed_[24:28] = np.nan
        np.save(tmp_path / f"{w}_rev.npy", reversed_)
    render = np.full((66, LH * 4, LW * 4), 50, np.uint8)
    render[10, 100:106, 100:106] = 0
    zarr.open(str(tmp_path / "pub_66.zarr"), mode="w").create_dataset(
        "0", data=render, chunks=render.shape
    )
    (tmp_path / "sidecar.json").write_text(json.dumps({"area": {"raw_render_px": AREA},
                                                       "orientation": {"flip_ud": False, "flip_lr": False}}))  # fmt: skip
    cv2.imwrite(
        str(tmp_path / "u.png"), rng.integers(0, 256, (156, 196)).astype(np.uint8)
    )
    ok = np.ones((LH, LW), bool)
    ok[2] = False
    design = np.zeros((LH, LW), int)
    design[10:35, 8:48] = 1
    design[4] = -1

    def side(mesh, render_):
        return {
            "points": Path(mesh).name,
            "ok": ok,
            "canvas": (LH * 4, LW * 4),
            "mesh": str(mesh),
        }

    def transfer(points, target, sides):
        which = np.where(target, design, -1)
        return (
            which,
            np.arange(LH * LW).reshape(LH, LW),
            np.repeat(np.arange(LH, dtype=float)[:, None], LW, 1),
        )

    real_read = own.f124.read_studio

    def read_studio(path, canvas):
        values = real_read(path, canvas)
        if Path(path) == tmp_path / "pub.npy":
            values[3, 5] = (
                np.nan
            )  # the published map has no value in one cell of the area
        return values

    monkeypatch.setattr(own.f131, "side", side)
    monkeypatch.setattr(own.analysis, "transfer", transfer)
    monkeypatch.setattr(
        own.analysis, "normals_agree", lambda pp, sp, which, cell, k: cosines[k]
    )
    monkeypatch.setattr(own.f124, "read_studio", read_studio)
    ours = [[tmp_path / f"{w}.tifxyz", tmp_path / f"{w}_66.zarr", tmp_path / f"{w}.npy", tmp_path / f"{w}_rev.npy"]
            for w in ("w047", "w048")]  # fmt: skip
    return argparse.Namespace(published_mesh=tmp_path / "pub.tifxyz", published_render=tmp_path / "pub_66.zarr",
                              published_studio=tmp_path / "pub.npy", published_studio_reversed=tmp_path / "pub_rev.npy",
                              sidecar=tmp_path / "sidecar.json", ink_png=tmp_path / "u.png", ours=ours,
                              image=None)  # fmt: skip


def _cells():
    cells = np.zeros((LH, LW), bool)
    cells[1:39, 1:49] = True  # the area
    target = cells.copy()
    target[2] = False  # not rendered
    target[3, 5] = False  # no published value
    cells = target.copy()
    cells[4] = False  # no winding
    cells[6] = False  # no reversed map
    return target, cells


def test_finding_127_must_come_out_again_before_anything_is_scored(
    tmp_path, monkeypatch
):
    result = own.compare(_world(tmp_path, monkeypatch))
    target, cells = _cells()
    assert (
        result["area_cells_covered_by_the_published_render"]
        == int(target.sum())
        == 1775
    )
    assert (result["cells"], result["cell_share"]) == (
        int(cells.sum()),
        round(cells.sum() / target.sum(), 4),
    )
    assert [o["cells_given"] for o in result["ours"]] == [1775 - 1000 - 48, 1000]
    assert [o["normal_cosine_median"] for o in result["ours"]] == [0.997, 0.998]
    assert result["f127_r_again"] is not None and result["f127_reproduced"] is False
    assert (result["registered"], result["verdict"]) == (None, "DOES_NOT_RUN")
    assert "described" not in result


def _reproduced(tmp_path, monkeypatch, **kw):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = own.compare(_world(tmp_path / "a", monkeypatch, **kw))
    monkeypatch.setattr(own, "F127_R", first["f127_r_again"])
    args = _world(tmp_path / "b", monkeypatch, **kw)
    return own.compare(args), args


def test_the_carried_map_is_scored_against_the_published_one_on_the_cells_both_reach(
    tmp_path, monkeypatch
):
    result, args = _reproduced(tmp_path, monkeypatch)
    a, f124 = own.analysis, own.f124
    target, cells = _cells()
    canvas = (LH * 4, LW * 4)
    theirs_raw = a.block_mean(np.load(args.published_studio))
    theirs_raw[3, 5] = np.nan
    which = np.zeros((LH, LW), int)
    which[10:35, 8:48] = 1
    which[4] = -1
    which = np.where(target, which, -1)  # the transfer gives the target's cells only
    index = np.arange(LH * LW).reshape(LH, LW)
    maps = [{"s": a.block_mean(np.load(args.ours[k][2]))} for k in range(2)]
    other_maps = [{"s": a.block_mean(np.load(args.ours[k][3]))} for k in range(2)]
    carried = own.f121.carry(maps, which, index)["s"]
    other = own.f121.carry(other_maps, which, index)["s"]
    theirs = a.highpass(theirs_raw, cells)
    numbers = f124.score(theirs, (theirs_raw >= 0.5) & cells, carried, cells, other)
    assert result["f127_reproduced"] is True
    assert result["registered"] == {
        k: numbers[k] for k in ("r", "control_wrong_side", "control_slid")
    }
    assert result["verdict"] == own.verdict(
        result["registered"], result["cell_share"], True, [0.997, 0.998]
    )
    d = result["described"]
    assert d["carried"] == numbers
    assert {w: v["cells"] for w, v in d["by_winding"].items()} == {
        "w047": int(cells.sum()) - 1000,
        "w048": 1000,
    }
    assert d["by_winding"]["w048"]["r"] is not None  # exactly 1,000 cells are enough
    p50, p95 = np.percentile(
        np.repeat(np.arange(LH, dtype=float)[:, None], LW, 1)[cells], [50, 95]
    )
    assert d["transfer_distance_voxels"] == {"p50": round(p50, 2), "p95": round(p95, 2)}
    rev = a.highpass(
        own.f120.standardise(
            a.block_mean(np.load(args.published_studio_reversed)), cells
        ),
        cells,
    )
    assert d[
        "published_surface_reversed_planes_against_its_forward"
    ] == own.f118._rounded(a.pearson(theirs[cells], rev[cells]))
    assert (
        d["f127_numbers_again"]["control_wrong_side"] is not None
    )  # the published reversed planes, as finding 127
    # against u: the reading frame's cells (4 lost to layer 10) where both carried maps have values
    sidecar = json.loads(args.sidecar.read_text())
    valid = np.ones((156, 196), bool)
    valid[98:104, 98:104] = False
    frame = a.block_mean(valid.astype(float)) == 1.0
    carried_px = own.f127.to_reading(own.lattice_to_raw(carried, canvas), sidecar)
    other_px = own.f127.to_reading(own.lattice_to_raw(other, canvas), sidecar)
    u_cells = (
        frame
        & np.isfinite(a.block_mean(carried_px))
        & np.isfinite(a.block_mean(other_px))
    )
    assert d["against_u"]["cells"] == int(u_cells.sum())
    published_u = d["against_u"]["published_surface"]
    assert (
        published_u["control_wrong_side"] != published_u["r"]
    )  # the published surface's own reversed planes


@pytest.mark.parametrize(
    ("cosines", "share_line"),
    [((0.997, 0.0), 0.5), ((None, 0.998), 0.5), ((0.997, 0.998), 0.95)],
    ids=["a-cosine-of-0", "a-winding-with-no-cells", "under-the-share"],
)
def test_the_failure_branch_scores_nothing(tmp_path, monkeypatch, cosines, share_line):
    monkeypatch.setattr(own, "MIN_CELL_SHARE", share_line)  # the share here is 0.9459
    result, _ = _reproduced(tmp_path, monkeypatch, cosines=cosines)
    assert result["f127_reproduced"] is True
    assert (result["registered"], result["verdict"]) == (None, "DOES_NOT_RUN")
    assert "described" not in result


@pytest.mark.parametrize(
    ("arrange", "message"),
    [
        ("layers", "not 66 layers"),
        ("unreadable", "cannot read"),
        ("u_shape", "the area"),
    ],
)
def test_a_render_or_ink_image_that_does_not_fit_is_refused(
    tmp_path, monkeypatch, arrange, message
):
    import cv2
    import zarr

    args = _world(tmp_path, monkeypatch)
    if arrange == "layers":
        zarr.open(str(args.published_render), mode="w").create_dataset(
            "0", data=np.full((65, 160, 200), 50, np.uint8)
        )
    elif arrange == "unreadable":
        args.ink_png.write_text("not an image")
    else:
        cv2.imwrite(str(args.ink_png), np.zeros((156, 192), np.uint8))
    with pytest.raises(SystemExit, match=message):
        own.compare(args)


@pytest.mark.parametrize(
    ("verdict", "code"), [("STUDIO_343_OWN_CLOSE", 0), ("DOES_NOT_RUN", 1)]
)
def test_the_command_writes_once_prints_without_the_described_part_and_exits_1_when_it_does_not_run(
    tmp_path, monkeypatch, capsys, verdict, code
):
    record = {"finding": 136, "verdict": verdict, "described": {"x": 1}}
    monkeypatch.setattr(own, "compare", lambda args: record)
    argv = ["compare", str(tmp_path / "o.json")]
    for flag in ("--published-mesh", "--published-render", "--published-studio", "--published-studio-reversed",
                 "--sidecar", "--ink-png"):  # fmt: skip
        argv += [flag, str(tmp_path)]
    argv += ["--ours", *[str(tmp_path)] * 4]
    assert own.main(argv) == code
    assert json.loads(capsys.readouterr().out) == {"finding": 136, "verdict": verdict}
    assert json.loads((tmp_path / "o.json").read_text()) == record
    assert own.main(argv) == 2  # written once


# --- run_studio_343_own.sh: each block taken from the script's text and run under bash -u with stand-in commands ---

SCRIPT = ROOT / "repro/first_letters/pherc343/run_studio_343_own.sh"


def _block(start, end):
    """The script's text from the line holding START to the end of the line holding END after it."""
    text = SCRIPT.read_text()
    a = text.rindex("\n", 0, text.index(start)) + 1
    return text[a : text.index("\n", text.index(end, a)) + 1]


def _function(name):
    text = SCRIPT.read_text()
    a = text.index(f"\n{name}() {{") + 1
    return text[a : text.index("\n}\n", a) + 3]


def _bash(script, path=None):
    env = {"PATH": f"{path}:/usr/bin:/bin" if path else "/usr/bin:/bin"}
    return subprocess.run(
        ["bash", "-uc", script], capture_output=True, text=True, env=env
    )


def _stub(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)
    return path


VARS = "M={t}/m B={t}/b OUT={t}/m/studio_own ENV={t}/env PYW={t}/pyw ROOT=/repo HERE=/repo/pherc343 CODE={t}/code " \
       "WEIGHTS=/w.safetensors N=N WINDINGS=(w047 w048)\n"  # fmt: skip


@pytest.mark.parametrize(
    ("missing", "message"),
    [
        (None, None),
        ("m/studio_own", "exists: finding 136 runs once"),
        ("env/bin/python", "finding 123's environment is missing"),
        (
            "m/render_recipe/w048_66.zarr/0",
            "finding 110's w048 render or mesh is missing",
        ),
        ("m/final_recipe/w047.tifxyz", "finding 110's w047 render or mesh is missing"),
        ("b/studio_343/maps/reversed.npy", "finding 127's maps are missing"),
    ],
)
def test_finding_110s_windings_and_finding_127s_maps_are_required_before_anything_runs(
    tmp_path, missing, message
):
    import shutil

    for w in ("w047", "w048"):
        (tmp_path / "m/render_recipe" / f"{w}_66.zarr" / "0").mkdir(parents=True)
        (tmp_path / "m/final_recipe" / f"{w}.tifxyz").mkdir(parents=True)
    (tmp_path / "b/studio_343/maps").mkdir(parents=True)
    for name in ("forward.npy", "reversed.npy"):
        (tmp_path / "b/studio_343/maps" / name).write_text("")
    _stub(tmp_path / "env/bin/python", "")
    if missing == "m/studio_own":
        (tmp_path / missing).mkdir()
    elif missing:
        target = tmp_path / missing
        shutil.rmtree(target) if target.is_dir() else target.unlink()
    run = _bash(
        VARS.format(t=tmp_path)
        + _block('[ -e "$OUT" ] &&', "finding 127's maps are missing")
        + "echo checked\n"
    )
    if message is None:
        assert (run.returncode, run.stdout) == (0, "checked\n")
    else:
        assert (run.returncode, run.stdout) == (2, "")
        assert message in run.stderr


def test_a_failed_step_writes_its_gate_and_stops_the_run(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "gate").mkdir()
    run = _bash(
        f"OUT={tmp_path}\n"
        + _function("step")
        + "step one true\nstep two false\necho after\n"
    )
    assert run.returncode == 1 and "after" not in run.stdout
    gates = {
        name: json.loads((tmp_path / "gate" / f"{name}.json").read_text())["exit"]
        for name in ("one", "two")
    }
    assert gates == {"one": 0, "two": 1}


@pytest.mark.parametrize("fail", [None, "w047_66.zarr"])
def test_the_planes_are_each_windings_layers_in_both_orders_and_a_failure_stops_them(
    tmp_path, fail
):
    _stub(tmp_path / "pyw", f'echo "$*" >> {tmp_path}/pyw.log\n[ "$4" = "{tmp_path}/m/render_recipe/{fail}" ] && exit 1\n'
                            ': > "$5"\n')  # fmt: skip
    (tmp_path / "m/studio_own/planes").mkdir(parents=True)
    run = _bash(VARS.format(t=tmp_path) + _function("planes") + "planes")
    calls = [
        line.split()[3:] for line in (tmp_path / "pyw.log").read_text().splitlines()
    ]
    planes = f"{tmp_path}/m/studio_own/planes"
    if fail:
        assert run.returncode == 1
        assert calls == [
            [f"{tmp_path}/m/render_recipe/w047_66.zarr", f"{planes}/w047.npy"]
        ]
    else:
        assert run.returncode == 0, run.stderr
        assert calls == [
            [
                f"{tmp_path}/m/render_recipe/{w}_66.zarr",
                f"{planes}/{w}{suffix}.npy",
                *flag,
            ]
            for w in ("w047", "w048")
            for suffix, flag in (("", []), ("_reversed", ["--reverse"]))
        ]


def _infer(tmp_path, fail=None):
    """Stand-ins: nvidia-smi writes two samples, writes its pid, and waits to be stopped; Studio waits for the first
    samples, logs its arguments, and writes its output (failing on FAIL's planes)."""
    out = tmp_path / "m/studio_own"
    (out / "planes").mkdir(parents=True)
    (out / "maps").mkdir()
    for name in ("w047", "w047_reversed", "w048", "w048_reversed"):
        (out / "planes" / f"{name}.npy").write_text("")
    _stub(tmp_path / "bin/nvidia-smi", f"exec 2>/dev/null\necho $$ > {tmp_path}/smi.pid\n"
                                       'echo "t, 900 MiB, 5 %"\necho "t, 4000 MiB, 90 %"\necho "t, 1200 MiB, 9 %"\n'
                                       "exec sleep 30\n")  # fmt: skip
    _stub(tmp_path / "env/bin/python", f"until [ -s {out}/gpu.csv ] && [ -s {tmp_path}/smi.pid ]; do sleep 0.01; done\n"
                                       f'echo "$PWD $*" >> {tmp_path}/studio.log\n'
                                       f'[ "$3" = "{out}/planes/{fail}.npy" ] && exit 1\n: > "$5"\n')  # fmt: skip
    (tmp_path / "code").mkdir()
    run = _bash(
        VARS.format(t=tmp_path) + _function("infer") + "infer", path=tmp_path / "bin"
    )
    pid = int((tmp_path / "smi.pid").read_text())
    try:
        os.kill(pid, 0)
        sampling = True
    except ProcessLookupError:
        sampling = False
    finally:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
    return run, out, sampling


def test_studio_reads_all_four_plane_sets_with_the_winners_command_and_records_the_gpu_peak(
    tmp_path,
):
    run, out, sampling = _infer(tmp_path)
    assert run.returncode == 0, run.stderr
    calls = [
        line.split() for line in (tmp_path / "studio.log").read_text().splitlines()
    ]
    names = ["w047", "w047_reversed", "w048", "w048_reversed"]
    assert calls == [[str(tmp_path / "code"), "inference.py", "--input", f"{out}/planes/{n}.npy", "--output",
                      f"{out}/maps/{n}.npy", "--checkpoint", "/w.safetensors", "--stride", "64", "--blend", "hann",
                      "--batch-size", "32"] for n in names]  # fmt: skip
    assert sorted(p.name for p in (out / "maps").iterdir()) == sorted(
        f"{n}.npy" for n in names
    )
    assert (
        list((out / "planes").iterdir()) == []
    )  # each set of planes is deleted once read
    assert json.loads((out / "gpu_peak.json").read_text()) == {
        "gpu_peak_mib_all_processes": 4000
    }
    assert not sampling


def test_a_failed_read_stops_studio_fails_the_step_and_still_stops_the_sampler(
    tmp_path,
):
    run, out, sampling = _infer(tmp_path, fail="w047_reversed")
    assert run.returncode == 1
    assert sorted(p.name for p in (out / "maps").iterdir()) == ["w047.npy"]
    assert len((tmp_path / "studio.log").read_text().splitlines()) == 2
    assert (out / "gpu_peak.json").exists() and not sampling


def test_compare_gives_each_winding_its_mesh_render_and_both_maps(tmp_path):
    _stub(tmp_path / "pyw", f'printf "%s\\n" "$@" > {tmp_path}/argv\n')
    run = _bash(VARS.format(t=tmp_path) + _function("compare") + "compare")
    assert run.returncode == 0, run.stderr
    argv = (tmp_path / "argv").read_text().splitlines()
    ours = [argv[i + 1 : i + 5] for i, a in enumerate(argv) if a == "--ours"]
    m, maps = f"{tmp_path}/m", f"{tmp_path}/m/studio_own/maps"
    assert ours == [[f"{m}/final_recipe/{w}.tifxyz", f"{m}/render_recipe/{w}_66.zarr", f"{maps}/{w}.npy",
                     f"{maps}/{w}_reversed.npy"] for w in ("w047", "w048")]  # fmt: skip
    assert (
        argv[argv.index("--published-studio-reversed") + 1]
        == f"{tmp_path}/b/studio_343/maps/reversed.npy"
    )
