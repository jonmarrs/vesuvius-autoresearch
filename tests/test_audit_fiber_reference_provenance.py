import hashlib
import io
import json

import pytest

from scripts.audit_fiber_reference_provenance import audit_folder
from repro.fibers import fetch_reference_annotations as fetcher


def write_fiber(tmp_path, points, **extra):
    value = {"type": "vc3d_fiber", "control_points": points,
             "vc_open_data_coordinate_space": "scroll/scan@L0", **extra}
    path = tmp_path / "fiber.json"
    path.write_text(json.dumps(value))
    return path


def test_span_metadata_belongs_to_start_and_lengths_are_chords(tmp_path):
    path = write_fiber(tmp_path, [
        {"position": [0, 0, 0], "segment_to_next": {
            "interp_mode": "trace", "config": {"beam_width": 8}, "fiber_manifest": "prediction-A"}},
        {"position": [3, 4, 0], "segment_to_next": {"interp_mode": "cspline"}},
        {"position": [3, 4, 12], "segment_to_next": {"interp_mode": "lasagna"}},
    ], line_points=[[0, 0, 0], [1000, 1000, 1000]], optimization_mode="trace")
    result = audit_folder(tmp_path)
    modes = result["by_coordinate_frame"]["scroll/scan@L0"]["by_interp_mode"]
    assert modes["trace"]["control_chord_length"] == 5
    assert modes["cspline"]["control_chord_length"] == 12
    assert "lasagna" not in modes
    assert result["trace_configs"] == [{"config": {"beam_width": 8}, "spans": 1}]
    assert result["trace_fiber_manifest_spans"] == {"prediction-A": 1}
    assert result["inputs"][0]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_missing_metadata_is_unknown_and_zero_length_has_no_share(tmp_path):
    write_fiber(tmp_path, [{"position": [0, 0, 0]}, {"position": [0, 0, 0]}],
                optimization_mode="native_fiber_trace3d")
    assert audit_folder(tmp_path)["by_coordinate_frame"]["scroll/scan@L0"]["by_interp_mode"] == {
        "unknown": {"spans": 1, "control_chord_length": 0, "control_chord_share": None}}


@pytest.mark.parametrize("position", [[0, 0], [0, 0, float("nan")], [0, True, 0]])
def test_invalid_coordinates_rejected(tmp_path, position):
    write_fiber(tmp_path, [{"position": position}])
    with pytest.raises(ValueError, match="three finite"):
        audit_folder(tmp_path)


def test_mixed_frames_are_not_pooled_and_missing_frame_is_unknown(tmp_path):
    path = write_fiber(tmp_path, [{"position": [0, 0, 0]}, {"position": [1, 0, 0]}])
    value = json.loads(path.read_bytes())
    value["vc_open_data_coordinate_space"] = "other/scan@L0"
    value["control_points"][1]["position"] = [10, 0, 0]
    (tmp_path / "other.json").write_text(json.dumps(value))
    del value["vc_open_data_coordinate_space"]
    (tmp_path / "unknown.json").write_text(json.dumps(value))
    result = audit_folder(tmp_path)
    assert result["by_coordinate_frame"]["scroll/scan@L0"]["total_control_chord_length"] == 1
    assert result["by_coordinate_frame"]["other/scan@L0"]["total_control_chord_length"] == 10
    assert result["by_coordinate_frame"]["unknown"]["file_count"] == 1
    assert result["interp_mode_span_counts"] == {"unknown": 3}


def test_empty_folder_rejected(tmp_path):
    with pytest.raises(ValueError, match="no annotation"):
        audit_folder(tmp_path)


def test_download_snapshot_hashes_same_bytes_as_audit(tmp_path, monkeypatch):
    captured = json.dumps({"type": "vc3d_fiber", "control_points": []}).encode()
    def open_url(url, **kwargs):
        if url.endswith("/"):
            return io.BytesIO(b'<a href="fiber.json">fiber</a><a href="../outside.json">skip</a>')
        assert url == "https://example.org/fibers/fiber.json"
        return io.BytesIO(captured)
    monkeypatch.setattr(fetcher, "urlopen", open_url)
    destination = tmp_path / "snapshot"
    monkeypatch.setattr(fetcher.sys, "argv", ["fetch", "https://example.org/fibers/", str(destination)])
    fetcher.main()
    manifest = json.loads((destination / "download_manifest.json").read_bytes())
    assert manifest["files"] == audit_folder(destination / "annotations")["inputs"]
    assert (destination / "annotations/fiber.json").read_bytes() == captured


def test_failed_download_never_writes_success_manifest(tmp_path, monkeypatch):
    def open_url(url, **kwargs):
        if url.endswith("/"):
            return io.BytesIO(b'<a href="broken.json">fiber</a>')
        raise OSError("download interrupted")
    monkeypatch.setattr(fetcher, "urlopen", open_url)
    destination = tmp_path / "snapshot"
    monkeypatch.setattr(fetcher.sys, "argv", ["fetch", "https://example.org/fibers/", str(destination)])
    with pytest.raises(OSError, match="interrupted"):
        fetcher.main()
    assert not (destination / "download_manifest.json").exists()
