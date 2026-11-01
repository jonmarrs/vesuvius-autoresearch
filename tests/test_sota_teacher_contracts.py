"""Synthetic teacher ingestion, cache publication and pseudolabel boundaries."""

import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import fsspec
import numpy as np
import pytest
import tifffile

from repro.sota_data import teacher_artifacts as ta
from repro.sota_data.distill_prep import prep_distill_fragment, teacher_region_for


@pytest.fixture
def bucket(tmp_path):
    fs = fsspec.filesystem("memory")
    prefix = f"{ta.transport.BUCKET}/teacher-tests/{tmp_path.name}"
    buffer = io.BytesIO()
    tifffile.imwrite(buffer, np.full((8, 8), 200, np.uint8))
    fs.pipe(prefix + "/prediction.tif", buffer.getvalue())
    yield fs, prefix
    fs.rm(prefix, recursive=True)


def _fetch(bucket, tmp_path, **kwargs):
    fs, prefix = bucket
    return ta.fetch_teacher(prefix, tmp_path / "cache", filesystem=fs, **kwargs)


def test_failed_transfer_is_never_a_reusable_teacher(bucket, tmp_path, monkeypatch):
    fs, _ = bucket
    real = fs.cat_file
    monkeypatch.setattr(ta.transport, "BLOCK_BYTES", 16)
    calls = 0

    def interrupted(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("interrupted download")
        return real(*args, **kwargs)

    monkeypatch.setattr(fs, "cat_file", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        _fetch(bucket, tmp_path)
    assert not (tmp_path / "cache").exists()
    assert not list(tmp_path.glob(".cache-*"))
    monkeypatch.setattr(fs, "cat_file", real)
    pixels, record = ta.read_teacher(_fetch(bucket, tmp_path))
    assert np.all(pixels == 200)
    assert record["source"].endswith("/prediction.tif")


def test_remote_plan_reads_no_object_bodies_and_creates_no_output(
    bucket, tmp_path, monkeypatch
):
    fs, _ = bucket
    monkeypatch.setattr(
        fs, "cat_file", lambda *a, **k: pytest.fail("no payloads during planning")
    )
    plan = _fetch(bucket, tmp_path, dry_run=True)
    assert plan["status"] == "METADATA_PLAN_ONLY"
    assert plan["ground_truth"] is False
    assert not (tmp_path / "cache").exists()


def test_ambiguous_teacher_needs_an_explicit_source(bucket, tmp_path):
    fs, prefix = bucket
    fs.pipe(prefix + "/another.tif", fs.cat_file(prefix + "/prediction.tif"))
    with pytest.raises(ValueError, match="ambiguous"):
        _fetch(bucket, tmp_path)
    path = _fetch(bucket, tmp_path, source="prediction.tif")
    _, provenance = ta.read_teacher(path)
    assert provenance["source"].endswith("/prediction.tif")
    assert len(provenance["candidates"]) == 2
    with pytest.raises(ValueError, match="different prediction"):
        _fetch(bucket, tmp_path, source="another.tif")


@pytest.mark.parametrize(
    "name", ["../prediction.tif", "missing.tif", "/prediction.tif"]
)
def test_source_selection_is_an_exact_basename(bucket, tmp_path, name):
    with pytest.raises(ValueError, match="basename"):
        _fetch(bucket, tmp_path, source=name)


def test_encoded_budget_is_enforced_before_transfer(bucket, tmp_path, monkeypatch):
    fs, _ = bucket
    monkeypatch.setattr(
        fs, "cat_file", lambda *a, **k: pytest.fail("budget must precede transfer")
    )
    with pytest.raises(ValueError, match="max_file_bytes"):
        _fetch(bucket, tmp_path, max_bytes=10)
    assert not (tmp_path / "cache").exists()


def test_valid_cache_rechecks_hashes_without_remote_access(
    bucket, tmp_path, monkeypatch
):
    path = _fetch(bucket, tmp_path)
    fs, _ = bucket
    monkeypatch.setattr(
        fs, "ls", lambda *a, **k: pytest.fail("cache reuse must be local")
    )
    assert _fetch(bucket, tmp_path) == path
    tifffile.imwrite(path, np.full((8, 8), 201, np.uint8))
    with pytest.raises(ValueError, match="changed"):
        _fetch(bucket, tmp_path)


def test_cached_metadata_plan_does_not_claim_a_hash_check(
    bucket, tmp_path, monkeypatch
):
    _fetch(bucket, tmp_path)
    monkeypatch.setattr(
        ta.transport, "_verify_local", lambda *a: pytest.fail("metadata-only plan")
    )
    result = _fetch(bucket, tmp_path, dry_run=True)
    assert result["status"] == "CACHED_METADATA_ONLY"
    assert result["payload_hash_checked"] is False


@pytest.mark.parametrize(
    "problem",
    [
        "missing manifest",
        "bad JSON",
        "wrong source",
        "hash",
        "status",
        "candidates",
        "ground truth",
        "extra file",
        "symlink",
    ],
)
def test_incomplete_or_modified_caches_fail_closed(bucket, tmp_path, problem):
    path = Path(_fetch(bucket, tmp_path))
    manifest = path.parent / "teacher.json"
    record = json.loads(manifest.read_text())
    if problem == "missing manifest":
        manifest.unlink()
    elif problem == "bad JSON":
        manifest.write_text("{")
    elif problem == "extra file":
        (path.parent / "other.txt").write_text("unexpected")
    elif problem == "symlink":
        saved = tmp_path / "saved.tif"
        path.rename(saved)
        path.symlink_to(saved)
    else:
        if problem == "wrong source":
            record["prefix"] += "/other"
        elif problem == "hash":
            record["payload"]["sha256"] = "broken"
        elif problem == "status":
            record["status"] = "METADATA_PLAN_ONLY"
        elif problem == "candidates":
            record["candidates"] = ["s3://outside-bucket/a.tif"]
        elif problem == "ground truth":
            record["ground_truth"] = True
        manifest.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        _fetch(bucket, tmp_path)
    with pytest.raises(ValueError):
        ta.read_teacher(path)


def test_listing_change_blocks_publication(bucket, tmp_path, monkeypatch):
    fs, prefix = bucket
    original = ta.plan_teacher
    calls = 0

    def plan(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            fs.pipe(prefix + "/new_prediction.tif", b"changed")
        return original(*args, **kwargs)

    monkeypatch.setattr(ta, "plan_teacher", plan)
    with pytest.raises(ValueError, match="ambiguous|changed"):
        _fetch(bucket, tmp_path)
    assert not (tmp_path / "cache").exists()


def test_read_teacher_decodes_the_hash_bound_bytes(bucket, tmp_path, monkeypatch):
    path = Path(_fetch(bucket, tmp_path))
    original = tifffile.imread
    seen = []

    def read(buffer):
        assert isinstance(buffer, io.BytesIO)
        seen.append(hashlib.sha256(buffer.getvalue()).hexdigest())
        return original(buffer)

    monkeypatch.setattr(tifffile, "imread", read)
    pixels, record = ta.read_teacher(path)
    assert pixels.dtype == np.uint8
    assert seen == [record["input"]["sha256"]]
    assert record["input"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert record["ground_truth"] is False


@pytest.mark.parametrize("shape", [(4, 4, 3), (2, 4, 4)])
def test_color_or_stack_teacher_cannot_be_cached(bucket, tmp_path, shape):
    fs, prefix = bucket
    buffer = io.BytesIO()
    tifffile.imwrite(
        buffer,
        np.zeros(shape, np.uint8),
        photometric="rgb" if shape[-1] == 3 else "minisblack",
    )
    fs.pipe(prefix + "/prediction.tif", buffer.getvalue())
    with pytest.raises(ValueError, match="2D|stack"):
        _fetch(bucket, tmp_path)
    assert not (tmp_path / "cache").exists()


def test_teacher_pixel_budget_is_checked_before_decoding(tmp_path, monkeypatch):
    path = tmp_path / "oversized.tif"
    tifffile.imwrite(path, np.zeros((4, 4), np.uint8))
    with tifffile.TiffFile(path, mode="r+b") as image:
        # 4 columns, so one more row than the budget allows (a uint32 tag).
        image.pages[0].tags["ImageLength"].overwrite(ta.MAX_PIXELS // 4 + 1)
    monkeypatch.setattr(
        tifffile,
        "imread",
        lambda *a, **k: pytest.fail("must inspect header before decoding"),
    )
    with pytest.raises(ValueError, match="max_pixels"):
        ta.read_teacher(path)


@pytest.mark.parametrize("fault", [None, "precondition"])
def test_teacher_publication_through_the_actual_s3_sdk(tmp_path, monkeypatch, fault):
    import s3fs
    from aiobotocore.stub import AioStubber

    fs = s3fs.S3FileSystem(anon=True, skip_instance_cache=True)
    fs.connect()
    prefix = ta.transport.BUCKET + "/sdk-teacher-test/ink-detection"
    buffer = io.BytesIO()
    tifffile.imwrite(buffer, np.full((4, 4), 200, np.uint8))
    data = buffer.getvalue()
    key = prefix + "/prediction.tif"
    etag = '"teacher-etag"'
    monkeypatch.setattr(
        fs,
        "ls",
        lambda *a, **k: [
            {"name": key, "type": "file", "size": len(data), "ETag": etag}
        ],
    )

    class AsyncBody(io.BytesIO):
        async def read(self, amount=-1):  # type: ignore[override]
            return super().read(min(amount, 7))

    body = AsyncBody(data)
    parameters = {
        "Bucket": ta.transport.BUCKET,
        "Key": key.removeprefix(ta.transport.BUCKET + "/"),
        "Range": f"bytes=0-{len(data) - 1}",
        "IfMatch": etag,
    }
    try:
        with AioStubber(fs.s3) as stub:
            if fault:
                stub.add_client_error(
                    "get_object",
                    service_error_code="PreconditionFailed",
                    http_status_code=412,
                    expected_params=parameters,
                )
                with pytest.raises(OSError):
                    ta.fetch_teacher(prefix, tmp_path / "cache", filesystem=fs)
                assert not (tmp_path / "cache").exists()
            else:
                stub.add_response(
                    "get_object",
                    {
                        "Body": body,
                        "ContentLength": len(data),
                        "ContentRange": f"bytes 0-{len(data) - 1}/{len(data)}",
                        "ETag": etag,
                    },
                    parameters,
                )
                path = ta.fetch_teacher(prefix, tmp_path / "cache", filesystem=fs)
                pixels, provenance = ta.read_teacher(path)
                assert np.all(pixels == 200)
                assert provenance["input"]["sha256"] == hashlib.sha256(data).hexdigest()
                assert body.closed
            stub.assert_no_pending_responses()
    finally:
        fs.close_session(fs.loop, fs._s3creator)


def test_cli_dry_run_download_and_invalid_cache(bucket, tmp_path, monkeypatch, capsys):
    import s3fs

    from repro.sota_data.teacher_cache import main

    fs, prefix = bucket
    monkeypatch.setattr(s3fs, "S3FileSystem", lambda **k: fs)
    args = ["--prefix", prefix, "--out", str(tmp_path / "cache")]
    assert main([*args, "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "METADATA_PLAN_ONLY"
    assert main(args) == 0
    assert Path(json.loads(capsys.readouterr().out)["teacher"]).is_file()
    (tmp_path / "cache/teacher.json").unlink()
    assert main(args) == 1
    assert "teacher cache failed" in capsys.readouterr().err


@pytest.mark.parametrize("threshold", [np.nan, np.inf, -1, 256, True, 128.5])
def test_invalid_threshold_cannot_publish_pseudolabels(tmp_path, threshold):
    with pytest.raises(ValueError, match="threshold"):
        prep_distill_fragment(
            np.zeros((26, 4, 4), np.uint8),
            np.full((4, 4), 200, np.uint8),
            tmp_path,
            "s",
            threshold,
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("shape", [(4, 4, 3), (4,), (0, 4)])
def test_scalar_teacher_required_in_array_preparation(tmp_path, shape):
    with pytest.raises(ValueError, match="2D"):
        prep_distill_fragment(
            np.zeros((26, 4, 4), np.uint8), np.zeros(shape, np.uint8), tmp_path, "s"
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "box",
    [
        (-2, 0, 10, 10),
        (0, 0, 11, 10),
        (5, 0, 4, 4),
        (0, 0, 0, 4),
        (True, 0, 4, 4),
        (0.5, 0, 4, 4),
    ],
)
def test_region_box_cannot_wrap_clip_or_truncate(box):
    with pytest.raises(ValueError, match="region_box"):
        teacher_region_for(np.zeros((10, 10), np.uint8), (10, 10), box)


def test_legacy_cache_is_not_reused_or_overwritten(tmp_path, monkeypatch):
    from repro.sota_data import distill_run as dr

    monkeypatch.setattr(dr, "TEACHER_DIR", str(tmp_path))
    legacy = tmp_path / "scroll1_segment.tif"
    legacy.write_bytes(b"partial TIFF")
    monkeypatch.setattr(
        dr, "_fs", lambda: pytest.fail("legacy refusal must precede remote access")
    )
    with pytest.raises(ValueError, match="legacy"):
        dr.fetch_teacher("segment")
    assert legacy.read_bytes() == b"partial TIFF"


@pytest.mark.parametrize("runner", ["single", "cross-scroll"])
def test_orchestrators_keep_the_full_teachers_float_units(
    tmp_path, monkeypatch, runner
):
    from repro.sota_data import distill_run as dr, xscroll_run as xr

    teacher = np.full((8, 8), 0.75, np.float32)
    teacher[-1, -1] = 2  # outside the chosen crop: global encoding is byte
    path = tmp_path / "source.tif"
    tifffile.imwrite(path, teacher)
    monkeypatch.setattr(dr, "fetch_teacher", lambda *a, **k: str(path))
    monkeypatch.setattr(
        dr,
        "extract_region",
        lambda *a, **k: (np.zeros((26, 4, 4), np.uint8), (8, 8), (0, 0, 4, 4)),
    )
    output = tmp_path / "out"
    if runner == "single":
        monkeypatch.setattr(dr, "DATA_ROOT", str(output))
        monkeypatch.setattr(dr, "TRAIN_SEGS", {})
        monkeypatch.setattr(dr, "HELD_SEG", "segment")
        monkeypatch.setattr(dr, "HELD_REGION", (0, 0))
        dr.cmd_prep()
        fid = dr.frag_id("segment", 0, 0)
    else:
        monkeypatch.setattr(xr, "DATA_ROOT", str(output))
        xr._prep_targets([("scroll1", "segment", 0, 0)])
        fid = dr.xfrag_id("scroll1", "segment", 0, 0)
    label = cv2.imread(str(output / fid / f"{fid}_inklabels.png"), 0)
    assert not label.any()  # 0.75 in byte units -> 0, not 191 -> ink
    provenance = json.loads(
        (output / fid / f"{fid}_render_provenance.json").read_text()
    )
    assert provenance["kind"] == "TEACHER_PSEUDOLABEL"
    assert provenance["teacher_encoding_applied"] == "byte"
    assert (
        provenance["teacher_source"]["input"]["sha256"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )


def test_help_is_available_without_image_s3_or_ml_imports(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    script = """
import runpy, sys
sys.argv = ['teacher_cache', '--help']
try:
    runpy.run_module('repro.sota_data.teacher_cache', run_name='__main__')
except SystemExit as exc:
    assert exc.code == 0
assert not {'numpy', 'tifffile', 'cv2', 'torch', 's3fs'}.intersection(sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(repo)},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "--dry-run" in result.stdout and "--source" in result.stdout


def _claiming(shape):
    """A small TIFF whose header claims `shape`: headers are checked, never decoded."""
    written = io.BytesIO()
    tifffile.imwrite(written, np.zeros((4, 4), np.uint8))
    buffer = io.BytesIO(written.getvalue())
    with tifffile.TiffFile(buffer, mode="r+b") as image:
        image.pages[0].tags["ImageLength"].overwrite(shape[0])
        image.pages[0].tags["ImageWidth"].overwrite(shape[1])
    return buffer.getvalue()


# The teachers recorded in reports/detector/sota_distill_measurement.json and
# cross_scroll_distill.json; the largest is 34880 x 97280 = 3,393,126,400 pixels.
@pytest.mark.parametrize("shape", [(34880, 97280), (41600, 79600), (51000, 39980)])
def test_the_runners_recorded_teachers_fit_the_pixel_budget(bucket, tmp_path, shape):
    fs, prefix = bucket
    fs.pipe(prefix + "/prediction.tif", _claiming(shape))
    path = Path(_fetch(bucket, tmp_path))
    assert json.loads((path.parent / "teacher.json").read_text())["header"][
        "shape"
    ] == list(shape)


def test_an_object_that_is_not_a_tiff_is_an_input_error(bucket, tmp_path):
    fs, prefix = bucket
    fs.pipe(prefix + "/prediction.tif", b"<html>error page</html>")
    with pytest.raises(ValueError, match="not a readable TIFF"):
        _fetch(bucket, tmp_path)
    assert not (tmp_path / "cache").exists()


def test_a_same_size_corrupted_cache_is_an_input_error(bucket, tmp_path):
    path = Path(_fetch(bucket, tmp_path))
    path.write_bytes(b"\0" * path.stat().st_size)
    with pytest.raises(ValueError):
        _fetch(bucket, tmp_path)
    with pytest.raises(ValueError):
        ta.read_teacher(path)


def test_a_repixelled_bundle_disagrees_with_its_record(bucket, tmp_path):
    path = Path(_fetch(bucket, tmp_path))
    size = path.stat().st_size
    tifffile.imwrite(path, np.full((8, 8), 7, np.uint8))
    assert path.stat().st_size == size
    with pytest.raises(ValueError, match="disagree"):
        ta.read_teacher(path)


def test_a_same_name_replacement_during_download_is_refused(
    bucket, tmp_path, monkeypatch
):
    fs, prefix = bucket
    original, calls = ta.plan_teacher, 0

    def plan(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            buffer = io.BytesIO()
            tifffile.imwrite(buffer, np.full((16, 16), 9, np.uint8))
            fs.pipe(prefix + "/prediction.tif", buffer.getvalue())
        return original(*args, **kwargs)

    monkeypatch.setattr(ta, "plan_teacher", plan)
    with pytest.raises(ValueError, match="changed during download"):
        _fetch(bucket, tmp_path)
    assert not (tmp_path / "cache").exists()
