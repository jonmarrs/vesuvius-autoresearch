"""Finding 134: three snap passes against one at PHerc. 211's prize place. The verdict table, the consequence finding
133 reads, the arms, and the run script."""

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"


def _load():
    spec = importlib.util.spec_from_file_location(
        "snap_passes_read_under_test", CONTROL / "snap_passes_read.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sp = _load()


@pytest.mark.parametrize(
    ("r", "expected"),
    [
        ((0.8247, 0.8247, 0.83, 0.85), "SNAP3_READS_BETTER"),  # +0.02 at the 0.02 line
        ((0.8247, 0.8247, 0.83, 0.8499), "SNAP3_READS_SAME"),
        ((0.8247, 0.8247, 0.83, 0.81), "SNAP3_READS_WORSE"),
        (
            (0.8247, 0.8047, 0.83, 0.86),
            "SNAP3_READS_SAME",
        ),  # noise 0.02: the margin is 0.04
        ((0.8247, 0.8047, 0.83, 0.87), "SNAP3_READS_BETTER"),
        ((0.8247, None, 0.83, 0.87), "DOES_NOT_RUN"),
    ],
)
def test_the_verdict_uses_finding_131s_margin(r, expected):
    assert sp.verdict(*r, share=0.83, reproduces=True) == expected


def test_no_verdict_without_finding_124_or_enough_cells():
    assert (
        sp.verdict(0.8247, 0.8247, 0.83, 0.9, 0.83, reproduces=False) == "DOES_NOT_RUN"
    )
    assert sp.verdict(0.8247, 0.8247, 0.83, 0.9, 0.0, reproduces=True) == "DOES_NOT_RUN"


@pytest.mark.parametrize(
    ("verdict", "gain", "expected"),
    [
        ("SNAP3_READS_BETTER", None, "three_passes"),
        ("SNAP3_READS_BETTER", -0.01, "three_passes"),
        ("SNAP3_READS_SAME", 0.03, "three_passes"),
        ("SNAP3_READS_SAME", 0.0, "one_pass"),
        ("SNAP3_READS_SAME", None, "one_pass"),
        ("SNAP3_READS_WORSE", 0.05, "one_pass"),
        ("DOES_NOT_RUN", 0.05, "one_pass"),
    ],
)
def test_finding_133_snaps_three_times_only_if_it_reads_no_worse_and_sits_more_on_the_sheet(
    verdict, gain, expected
):
    assert sp.consequence(verdict, gain) == expected


def test_the_geometry_gain_is_the_median_of_each_windings_change():
    shares = {
        "dense2": {"a": 0.8, "b": 0.7, "c": 0.9},
        "dense2s3": {"a": 0.85, "b": 0.72, "c": 0.9},
    }
    assert sp.geometry_gain(shares) == 0.02
    assert sp.geometry_gain({"dense2": None, "dense2s3": shares["dense2s3"]}) is None
    assert sp.geometry_gain({"dense2": {"a": None}, "dense2s3": {"a": 0.9}}) is None
    assert sp.geometry_gain({"dense2": {"a": 0.8}, "dense2s3": {"b": 0.9}}) is None


def test_the_arms_are_finding_131s_and_this_one(tmp_path):
    base = ["compare", str(tmp_path / "out.json")]
    for flag in (
        "--winner-mesh",
        "--winner-maps",
        "--winner-render",
        "--studio",
        "--studio-mask",
        "--ours-render-map",
    ):
        base += [flag, str(tmp_path)]
    base += ["--windings", "w033"]
    arm = lambda n: ["--arm", n, "f", "r", "m"]  # noqa: E731
    with pytest.raises(SystemExit, match="the arms are"):
        sp.main(base + arm("f124") + arm("rerun") + arm("dense2"))
    (tmp_path / "out.json").write_text("{}")
    assert (
        sp.main(base + arm("f124") + arm("rerun") + arm("dense2") + arm("dense2s3"))
        == 2
    )  # measured once


def test_the_run_snaps_three_times_reads_with_the_winners_command_and_uploads_nothing():
    path = CONTROL / "run_snap_passes.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl", "--upload-file", "rsync "):
        assert word not in text
    assert 'step snap env FL_SNAP_PASSES=3 bash "$BAND/run_snap.sh" "$ARM"' in text
    assert (
        'ln -sfn fit_e2e_dense2 "$R/work/fit_$ARM"' in text
    )  # finding 131's densified windings
    assert "--stride 64 --blend hann" in text and "--batch-size 32" in text
    for arm in ("f124", "rerun", "dense2", "dense2s3"):
        assert f"--arm {arm} " in text
    assert '"$C/work/snap_passes.json"' in text
    shas = dict(re.findall(r"^(W_SHA|CODE_SHA)=(\w+)", text, flags=re.M))
    f131 = dict(
        re.findall(
            r"^(W_SHA|CODE_SHA)=(\w+)",
            (CONTROL / "run_dense_read.sh").read_text(),
            flags=re.M,
        )
    )
    assert shas == f131 and len(shas) == 2


def test_the_registration_fixes_the_rule_finding_133_reads():
    reg = " ".join(
        (ROOT / "docs/preregistration/2026-11-20_first_letters_0211_snap_passes.md")
        .read_text()
        .split()
    )
    assert (
        "Finding 134" in reg
        and "before any winding has been snapped more than once at PHerc. 211" in reg
    )
    for word in (
        "`SNAP3_READS_BETTER`",
        "`SNAP3_READS_SAME`",
        "`SNAP3_READS_WORSE`",
        "`three_passes`",
        "`one_pass`",
    ):
        assert word in reg
    assert "max(0.02, 2 × |r(rerun) − r(f124)|)" in reg
    controls = (
        ROOT / "repro/first_letters/eligible_band/run_after_controls.sh"
    ).read_text()
    assert (
        '"$CTRL/work/snap_passes.json" consequence' in controls
        and '"$C134" = three_passes' in controls
    )
    record_keys = json.dumps({"consequence": sp.consequence("SNAP3_READS_SAME", 0.01)})
    assert "three_passes" in record_keys


# --- the comparison's own reckoning, with finding 110's side and transfer stood in for, as round #217 tested finding
# 131's; the command line; and the run script's own steps, each run from the script's text with stand-ins -----------

H, W = 24, 32  # the winner's lattice cells
COMMON_ROWS = [r for r in range(H) if r not in (0, 1, 2, 3, 5, 7)]
NOISE = {"f124": 0.05, "rerun": 0.1, "dense2": 0.15, "dense2s3": 0.2}


def _compare(tmp_path, monkeypatch, cosines=None, noise=None, shares=None):
    """A Studio map, mask and our render's map on the winner's 96 x 128-pixel canvas, and the four arms, whose carried
    maps are the winner's plus noise of each arm's scale (arms of the same scale carry the same map). Each arm lacks a
    different row of cells: f124 row 0 (no winding), rerun rows 1 (no winding) and 3 (no other side), dense2 row 2 (no
    map), dense2s3 row 7 (no other side). The mask leaves out the first one and a half columns of cells, and our
    render's map row 5. With shares, a distance field is given and each arm's sheet share is the one named."""
    import argparse

    import cv2
    import tifffile

    tmp_path.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    px = rng.random((H * 4, W * 4))
    tifffile.imwrite(tmp_path / "studio.tif", px.astype(np.float32))
    mask = np.full(px.shape, 255, np.uint8)
    mask[:, :6] = 0
    cv2.imwrite(str(tmp_path / "mask.png"), mask)
    own = px.copy()
    own[20:24] = np.nan  # our render's map has no value on cell row 5
    np.save(tmp_path / "own.npy", own.astype(np.float32))
    studio = sp.f131.analysis.block_mean(px)
    monkeypatch.setattr(
        sp.f131.tm,
        "side",
        lambda *a, **k: {"ok": np.ones((H, W), bool), "points": None},
    )
    noise = noise or NOISE
    draws = {s: rng.normal(0, 1, (H, W)) for s in sorted(set(noise.values()))}
    other = rng.random((H, W))
    arms = {}
    for k, name in enumerate(("f124", "rerun", "dense2", "dense2s3")):
        which = np.zeros((H, W), int)
        carried = studio + noise[name] * draws[noise[name]]
        theirs = other.copy()
        if name == "f124":
            which[0] = -1
        elif name == "rerun":
            which[1] = -1
            theirs[3] = np.nan
        elif name == "dense2":
            carried[2] = np.nan
        else:
            theirs[7] = np.nan
        dist = (
            np.repeat(np.arange(H, dtype=float)[:, None], W, axis=1) + k
        )  # each cell's row, plus the arm's index
        arms[name] = {"which": which, "dist": dist, "cosines": (cosines or {}).get(name, [-0.99]),
                      "carried": carried, "other": theirs, "meshes": [name]}  # fmt: skip
    monkeypatch.setattr(
        sp.f131,
        "carry_arm",
        lambda winner, windings, finals, renders, maps: arms[finals.name],
    )
    monkeypatch.setattr(
        sp.f131,
        "sheet_share",
        lambda sdt, finals, windings: None
        if sdt is None
        else (shares or {})[finals.name],
    )
    arm = [[n, str(tmp_path / n), str(tmp_path / n), str(tmp_path / n)] for n in arms]
    return argparse.Namespace(winner_mesh=tmp_path, winner_maps=tmp_path, winner_render=tmp_path,
                              studio=tmp_path / "studio.tif", studio_mask=tmp_path / "mask.png",
                              ours_render_map=tmp_path / "own.npy", windings=["w033"],
                              sdt=tmp_path / "sdt" if shares else None, arm=arm)  # fmt: skip


def _reproducing(tmp_path, monkeypatch, **kw):
    """The comparison with finding 124's r set to what f124 gives on its own cells here, so that the verdict runs."""
    first = sp.compare_cmd(_compare(tmp_path / "a", monkeypatch, **kw))
    monkeypatch.setattr(
        sp.f131, "F124_R", first["described"]["each_arm_on_its_own_cells"]["f124"]["r"]
    )
    return sp.compare_cmd(_compare(tmp_path / "b", monkeypatch, **kw))


def test_the_four_arms_are_scored_on_the_cells_every_arm_reaches_and_f124_on_its_own(
    tmp_path, monkeypatch
):
    result = sp.compare_cmd(_compare(tmp_path, monkeypatch))
    # the mask's whole cells: columns 2 to 31; every arm, and our render's map, reach the common rows of them
    assert (result["mask_cells"], result["cells"], result["cell_share"]) == (
        24 * 30,
        18 * 30,
        0.75,
    )
    d = result["described"]
    assert {
        n: a["cells"] for n, a in d["each_arm_on_the_common_cells"].items()
    } == dict.fromkeys(("f124", "rerun", "dense2", "dense2s3"), 540)
    assert {n: a["cells"] for n, a in d["each_arm_on_its_own_cells"].items()} == {
        "f124": 22 * 30, "rerun": 21 * 30, "dense2": 22 * 30, "dense2s3": 22 * 30,
    }  # fmt: skip
    for k, name in enumerate(
        ("f124", "rerun", "dense2", "dense2s3")
    ):  # over the common cells only
        p50, p95 = np.percentile(
            np.repeat(np.array(COMMON_ROWS, float) + k, 30), [50, 95]
        )
        assert d["transfer_distance_voxels"][name] == {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
        }
    reg = result["registered"]
    r = reg["r"]
    assert reg["noise_rerun_minus_f124"] == round(r["rerun"] - r["f124"], 4) != 0
    assert (
        reg["change_dense2s3_minus_dense2"]
        == round(r["dense2s3"] - r["dense2"], 4)
        != 0
    )
    assert reg["margin"] == sp.f131.margin(r["rerun"] - r["f124"])
    # finding 124's r is not given again on f124's own cells here, so the comparison does not run
    assert result["f124_reproduced_on_its_own_cells"] is False
    assert (result["verdict"], result["consequence"]) == ("DOES_NOT_RUN", "one_pass")
    assert d["final_nodes_within_2_of_the_predicted_sheet"] == dict.fromkeys(
        ("f124", "rerun", "dense2", "dense2s3")
    )
    assert result["geometry_gain_dense2s3_minus_dense2"] is None


def test_the_verdict_takes_one_pass_then_three_in_that_order(tmp_path, monkeypatch):
    # f124, the rerun and dense2 carry the same map: no noise, so the margin is 0.02; dense2s3 carries a noisier one
    noise = {"f124": 0.05, "rerun": 0.05, "dense2": 0.05, "dense2s3": 0.4}
    result = _reproducing(tmp_path, monkeypatch, noise=noise)
    reg = result["registered"]
    assert result["f124_reproduced_on_its_own_cells"] is True
    assert (reg["noise_rerun_minus_f124"], reg["margin"]) == (0.0, 0.02)
    assert reg["change_dense2s3_minus_dense2"] <= -0.02
    assert (result["verdict"], result["consequence"]) == (
        "SNAP3_READS_WORSE",
        "one_pass",
    )


@pytest.mark.parametrize(
    ("dense2", "dense2s3", "gain", "expected"),
    [(0.80, 0.85, 0.05, "three_passes"), (0.85, 0.80, -0.05, "one_pass")],
)
def test_a_same_reading_snaps_three_times_only_when_the_windings_sit_more_on_the_sheet(
    tmp_path, monkeypatch, dense2, dense2s3, gain, expected
):
    shares = {
        "f124": {"w033": 0.7},
        "rerun": {"w033": 0.7},
        "dense2": {"w033": dense2},
        "dense2s3": {"w033": dense2s3},
    }
    result = _reproducing(
        tmp_path, monkeypatch, noise=dict.fromkeys(NOISE, 0.05), shares=shares
    )
    assert result["verdict"] == "SNAP3_READS_SAME"
    assert result["described"]["final_nodes_within_2_of_the_predicted_sheet"] == shares
    assert result["geometry_gain_dense2s3_minus_dense2"] == gain
    assert result["consequence"] == expected


@pytest.mark.parametrize(
    ("cosines", "stops"),
    [({"dense2s3": [-0.99, 0.0]}, True), ({"f124": [None, -0.99]}, False)],
    ids=["a-zero-cosine-stops", "a-winding-without-a-cosine-does-not"],
)
def test_a_render_against_the_winners_normals_stops_the_comparison_at_one_pass(
    tmp_path, monkeypatch, cosines, stops
):
    result = sp.compare_cmd(_compare(tmp_path, monkeypatch, cosines))
    assert (
        result.get("why") == "a render samples against the winner's normals"
    ) is stops
    assert ("cells" in result) is not stops
    assert result["consequence"] == "one_pass"
    if stops:
        assert result["verdict"] == "DOES_NOT_RUN"


def test_an_unreadable_mask_stops_the_comparison(tmp_path, monkeypatch):
    args = _compare(tmp_path, monkeypatch)
    args.studio_mask.write_text("not an image")
    with pytest.raises(SystemExit, match="cannot read"):
        sp.compare_cmd(args)


def test_the_verdict_runs_at_exactly_half_the_mask_and_not_without_a_share_or_finding_124s_r():
    assert (
        sp.verdict(0.8247, 0.8247, 0.83, 0.85, 0.5, reproduces=True)
        == "SNAP3_READS_BETTER"
    )
    assert (
        sp.verdict(0.8247, 0.8247, 0.83, 0.85, None, reproduces=True) == "DOES_NOT_RUN"
    )
    assert sp.verdict(None, 0.8247, 0.83, 0.85, 0.83, reproduces=True) == "DOES_NOT_RUN"


def test_no_geometry_gain_without_any_winding_or_with_one_unmeasured_after_three_passes():
    assert sp.geometry_gain({"dense2": {}, "dense2s3": {}}) is None
    assert sp.geometry_gain({"dense2": {"a": 0.8}, "dense2s3": {"a": None}}) is None


@pytest.mark.parametrize(
    ("verdict", "code"), [("SNAP3_READS_SAME", 0), ("DOES_NOT_RUN", 1)]
)
def test_the_command_writes_its_whole_record_prints_it_without_the_described_part_and_exits_1_when_it_does_not_run(
    tmp_path, monkeypatch, capsys, verdict, code
):
    record = {
        "finding": 134,
        "verdict": verdict,
        "consequence": "one_pass",
        "described": {"x": 1},
    }
    monkeypatch.setattr(sp, "compare_cmd", lambda args: record)
    argv = ["compare", str(tmp_path / "o.json")]
    for flag in (
        "--winner-mesh",
        "--winner-maps",
        "--winner-render",
        "--studio",
        "--studio-mask",
        "--ours-render-map",
    ):
        argv += [flag, str(tmp_path)]
    argv += ["--windings", "w033"]
    for name in ("f124", "rerun", "dense2", "dense2s3"):
        argv += ["--arm", name, str(tmp_path), str(tmp_path), str(tmp_path)]
    assert sp.main(argv) == code
    assert json.loads((tmp_path / "o.json").read_text()) == record
    assert json.loads(capsys.readouterr().out) == {
        k: v for k, v in record.items() if k != "described"
    }


SCRIPT = CONTROL / "run_snap_passes.sh"


def _block(start, end):
    """The run script's text from the line holding START to the end of the line holding END after it."""
    text = SCRIPT.read_text()
    a = text.rindex("\n", 0, text.index(start)) + 1
    return text[a : text.index("\n", text.index(end, a)) + 1]


def _function(name):
    text = SCRIPT.read_text()
    a = text.index(f"\n{name}() {{") + 1
    return text[a : text.index("\n}\n", a) + 3]


def _bash(script):
    return subprocess.run(["bash", "-uc", script], capture_output=True, text=True)


def _stub(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)
    return path


def test_each_winding_is_rendered_as_orient_decided_and_one_without_a_decision_stops_the_render(
    tmp_path,
):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs/snap_passes_orient.log").write_text(
        "w033.tifxyz flip\nw034.tifxyz keep\nw0350.tifxyz flip\n"
    )
    _stub(tmp_path / "band/run_render.sh", f'echo "$@" >> {tmp_path}/renders\n')
    run = _bash(
        f"C={tmp_path} BAND={tmp_path}/band ARM=e2e_dense2s3 WINDINGS=(w033 w034 w035)\n"
        + _function("render_arm")
        + "render_arm"
    )
    assert run.returncode == 2
    assert "no orientation for w035" in run.stderr
    assert (tmp_path / "renders").read_text().split("\n") == [
        "e2e_dense2s3 w033 flip",
        "e2e_dense2s3 w034",
        "",
    ]


def test_the_first_pass_is_described_as_finding_131s_snap_only_when_all_three_coordinates_are_identical(
    tmp_path,
):
    for arm in ("snap_e2e_dense2s3.pass1", "snap_e2e_dense2"):
        for w in ("w033", "w034"):
            (tmp_path / "work" / arm / w).mkdir(parents=True)
            for c in "xyz":
                (tmp_path / "work" / arm / w / f"{c}.tif").write_bytes(
                    b"same " + c.encode()
                )
    (tmp_path / "work/snap_e2e_dense2s3.pass1/w034/y.tif").write_bytes(b"differs")
    run = _bash(
        f"R={tmp_path} OUT={tmp_path} ARM=e2e_dense2s3 WINDINGS=(w033 w034)\n"
        + _block(
            'for w in "${WINDINGS[@]}"; do  # described',
            'done > "$OUT/pass1_same_as_finding_131.txt"',
        )
    )
    assert run.returncode == 0, run.stderr
    assert (
        tmp_path / "pass1_same_as_finding_131.txt"
    ).read_text() == "w033 yes\nw034 no\n"


@pytest.mark.parametrize(
    ("csv", "peak"),
    [
        (
            "2026/11/20 10:00:00.000, 900 MiB, 50 %\n2026/11/20 10:00:05.000, 12000 MiB, 99 %\n"
            "2026/11/20 10:00:10.000, 3000 MiB, 10 %\n",
            12000,
        ),
        ("", None),
    ],  # fmt: skip
)
def test_the_gpu_peak_is_the_largest_sample(tmp_path, csv, peak):
    (tmp_path / "gpu.csv").write_text(csv)
    run = _bash(f"OUT={tmp_path}\n" + _block("peak=$(", '> "$OUT/gpu_peak.json"'))
    assert run.returncode == 0, run.stderr
    assert json.loads((tmp_path / "gpu_peak.json").read_text()) == {
        "gpu_peak_mib_all_processes": peak
    }


@pytest.mark.parametrize(
    ("missing", "message"),
    [
        (None, None),
        (
            "work/fit_e2e_dense2/densified/meshes/fitted/w034/x.tif",
            "finding 131's densified w034 is missing",
        ),
        (
            "d131/maps/e2e_rerun/w034_reversed.npy",
            "finding 131's e2e_rerun w034 is missing",
        ),
    ],
)
def test_finding_131s_windings_maps_and_densified_windings_are_required_before_anything_runs(
    tmp_path, missing, message
):
    _stub(tmp_path / "env/bin/python", "")
    for w in ("w033", "w034"):
        files = [f"work/fit_e2e_dense2/densified/meshes/fitted/{w}/x.tif"]
        for a in ("e2e_rerun", "e2e_dense2"):
            files += [
                f"work/final_{a}/{w}.tifxyz/x.tif",
                f"d131/maps/{a}/{w}.npy",
                f"d131/maps/{a}/{w}_reversed.npy",
            ]
        for f in files:
            (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / f).write_text("")
    if missing:
        (tmp_path / missing).unlink()
    run = _bash(
        f"OUT={tmp_path}/out R={tmp_path} ARM=e2e_dense2s3 ENV={tmp_path}/env D131={tmp_path}/d131 "
        "WINDINGS=(w033 w034)\n"
        + _block('[ -e "$OUT" ] &&', "finding 131's densified $w is missing")
        + "done\n"
        "echo checked\n"
    )
    if message is None:
        assert (run.returncode, run.stdout) == (0, "checked\n")
    else:
        assert (run.returncode, run.stdout) == (2, "")
        assert message in run.stderr


def test_a_failed_step_records_its_gate_and_stops_the_run(tmp_path):
    (tmp_path / "logs").mkdir()
    run = _bash(
        f"C={tmp_path}\n"
        f'control_gate() {{ echo "GATE $1 $2" >> {tmp_path}/gates; }}\n'
        + _function("step")
        + "step one true\nstep two false\necho after\n"
    )
    assert run.returncode == 1
    assert "after" not in run.stdout and "STEP_EXIT two 1" in run.stdout
    assert (
        tmp_path / "gates"
    ).read_text() == "GATE snap_passes_one 0\nGATE snap_passes_two 1\n"


def test_studio_reads_both_orders_of_each_windings_planes_with_the_winners_command_and_deletes_the_planes(
    tmp_path,
):
    pyw = _stub(
        tmp_path / "pyw",
        'if [ "${@: -1}" = --reverse ]; then : > "${@: -2:1}"; else : > "${@: -1}"; fi\n',
    )
    _stub(
        tmp_path / "env/bin/python", f'echo "$PWD $*" >> {tmp_path}/studio\n: > "$5"\n'
    )
    (tmp_path / "code").mkdir()
    (tmp_path / "out/planes").mkdir(parents=True)
    run = _bash(
        f"OUT={tmp_path}/out ARM=e2e_dense2s3 WINDINGS=(w033) PYW={pyw} HERE={tmp_path} R={tmp_path} "
        f"CODE={tmp_path}/code ENV={tmp_path}/env WEIGHTS=/w.safetensors\n"
        + _function("studio_arm")
        + "studio_arm"
    )
    assert run.returncode == 0, run.stderr
    out = tmp_path / "out"
    assert sorted(p.name for p in (out / "maps/e2e_dense2s3").iterdir()) == [
        "w033.npy",
        "w033_reversed.npy",
    ]
    assert list((out / "planes").iterdir()) == []
    calls = (tmp_path / "studio").read_text().split("\n")[:-1]
    for name, call in zip(("w033", "w033_reversed"), calls, strict=True):
        assert call.split() == [str(tmp_path / "code"), "inference.py", "--input", f"{out}/planes/{name}.npy",
                                "--output", f"{out}/maps/e2e_dense2s3/{name}.npy", "--checkpoint", "/w.safetensors",
                                "--stride", "64", "--blend", "hann", "--batch-size", "32"]  # fmt: skip
