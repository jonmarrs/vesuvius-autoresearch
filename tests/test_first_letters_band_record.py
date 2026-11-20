"""The band read's record: assembled from the run's gates and summaries, failures counted, numbers only."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "repro/first_letters/eligible_band/band_record.py"
    spec = importlib.util.spec_from_file_location("band_record_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


br = _load()


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _run(tmp_path: Path) -> Path:
    r = tmp_path / "band"
    work = r / "work"
    names = ["w010", "w011", "w012"]
    (work).mkdir(parents=True)
    (work / "windings_a.txt").write_text("\n".join(names) + "\n")
    gates = work / "gate_a"
    for stage, seconds in (("snap", 224), ("orient", 3), ("summarise", 40)):
        _write(gates / f"studio_{stage}.json", {"exit": 0, "seconds": seconds})
    for w, secs in zip(names, (80, 90, 100), strict=True):
        _write(gates / f"studio_flatten_{w}.json", {"exit": 0, "seconds": secs})
    _write(gates / "studio_render_w010.json", {"exit": 0, "seconds": 190})
    _write(gates / "studio_render_w011.json", {"exit": 0, "seconds": 200})
    _write(
        gates / "studio_render_w012.json", {"exit": 1, "seconds": 5}
    )  # dropped from Studio
    _write(gates / "studio_studio_w010.json", {"exit": 0, "seconds": 210})
    _write(gates / "studio_studio_w011.json", {"exit": 0, "seconds": 230})
    studio = work / "studio_a"
    _write(studio / "orient.json", {"windings": {
        "w010": {"share_of_normals_pointing_inward": 0.49, "render": "keep"},
        "w011": {"share_of_normals_pointing_inward": 0.9, "render": "flip"},
        "w012": {"share_of_normals_pointing_inward": 0.95, "render": "flip"},
    }})  # fmt: skip
    _write(studio / "summary" / "summary.json", {"windings": {
        "w010": {"ink_share": 0.1, "largest_tile_ink_share": 0.2, "tiles_scored": 4, "rendered_pixels": 1000},
        "w011": {"ink_share": 0.3, "largest_tile_ink_share": 0.5, "tiles_scored": 0, "rendered_pixels": 3000},
    }})  # fmt: skip
    _write(studio / "summary" / "orientation.json", {
        "w010": {"flip_lr": False, "flip_ud": False}, "w011": {"flip_lr": True, "flip_ud": False},
    })  # fmt: skip
    _write(
        studio / "stacked.json",
        {"pairs": {"w010-w011": 0.1}, "stacked": [], "line": 0.3},
    )
    _write(
        work / "quality_a.json",
        {
            "windings": {
                "w010": {"excess": -0.02},
                "w011": {"excess": 0.2},
                "w012": None,
            }
        },
    )
    (r / "logs").mkdir()
    (r / "logs" / "studio_a_gpu_mib.log").write_text("1 0\n2 14481\n3 900\n4\n")
    return r


def test_the_record_counts_each_step_and_carries_a_failure_forward(tmp_path):
    rec = br.record(_run(tmp_path), "a")
    s = rec["steps"]
    assert s["snap"] == {"exit": 0, "seconds": 224}
    assert s["flatten"] == {"attempted": 3, "exited_zero": 3, "failed": [], "seconds_total": 270,
                            "seconds_median": 90, "seconds_max": 100}  # fmt: skip
    assert s["render"]["failed"] == ["w012"] and s["render"]["exited_zero"] == 2
    assert s["studio"]["attempted"] == 2 and s["studio"]["seconds_total"] == 440
    assert rec["read"] == 2 and rec["windings"] == 3
    assert rec["by_winding"]["w012"] == {"render": "flip", "share_of_normals_pointing_inward": 0.95,
                                         "excess": None, "read": False}  # fmt: skip


def test_the_record_summarises_orientation_ink_and_gpu(tmp_path):
    rec = br.record(_run(tmp_path), "a")
    assert rec["render_orientation"]["flip"] == 2 and rec["render_orientation"][
        "keep"
    ] == ["w010"]
    assert rec["reading_orientation"] == {
        "unturned": 1,
        "mirrored only": 1,
        "upside down only": 0,
        "both": 0,
    }
    assert rec["ink_share"] == {"median": 0.2, "min": 0.1, "max": 0.3}
    assert rec["largest_tile_ink_share"]["max"] == 0.5
    assert rec["tiles_scored"] == 4 and rec["windings_with_no_tile_scored"] == ["w011"]
    assert rec["rendered_pixels"] == 4000
    assert rec["inspection_order_first_ten"] == ["w011", "w010"]
    assert (
        rec["stacked"]["stacked"] == [] and rec["gpu_peak_mib_all_processes"] == 14481
    )
    assert (
        rec["by_winding"]["w011"]["flip_lr"] is True
        and rec["by_winding"]["w010"]["excess"] == -0.02
    )


def test_the_cli_refuses_to_overwrite_a_record(tmp_path):
    r = _run(tmp_path)
    out = tmp_path / "rec.json"
    assert br.main([str(r), "a", str(out)]) == 0
    assert json.loads(out.read_text())["finding"] == 125
    try:
        br.main([str(r), "a", str(out)])
    except SystemExit as e:
        assert "exists" in str(e)
    else:
        raise AssertionError("overwrote the record")
