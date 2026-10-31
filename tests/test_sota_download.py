"""Bounded raw downloads, immutable publication and actual S3 request contracts."""

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import fsspec
import pytest

from repro.sota_data import download_artifacts as artifacts, fetch

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def bucket(tmp_path):
    fs = fsspec.filesystem("memory", skip_instance_cache=True)
    prefix = "download-tests/" + tmp_path.name
    base = artifacts.BUCKET + "/" + prefix
    for index in range(8):
        fs.pipe(f"{base}/layers/{index:02d}.tif", f"layer{index:02d}".encode())
    fs.pipe(base + "/segment_inklabels.png", b"labels")
    fs.pipe(base + "/segment_mask.png", b"mask")
    yield fs, prefix, base
    if fs.exists(base):
        fs.rm(base, recursive=True)


def plan(bucket, tmp_path, **kwargs):
    fs, prefix, _ = bucket
    return fetch.plan_segment(prefix, tmp_path / "raw", filesystem=fs, **kwargs)


def download(bucket, tmp_path, **kwargs):
    fs, prefix, _ = bucket
    return fetch.fetch_segment(prefix, str(tmp_path / "raw"), filesystem=fs, **kwargs)


def test_download_manifest_binds_bytes_and_keeps_converter_layout(bucket, tmp_path):
    fs, _, base = bucket
    assert download(bucket, tmp_path) == str(tmp_path / "raw")
    report = json.loads((tmp_path / "raw/download.json").read_text())
    assert report["status"] == "DOWNLOADED"
    assert (
        report["training_ready"]
        is report["image_geometry_verified"]
        is report["label_quality_verified"]
        is False
    )
    assert report["selected_depth_indices"] == list(range(8))
    assert report["file_count"] == 10
    assert report["total_bytes"] == sum(item["bytes"] for item in report["files"])
    for item in report["files"]:
        data = (tmp_path / "raw" / item["relative_path"]).read_bytes()
        assert data == fs.cat_file(base + "/" + item["relative_path"])
        assert item["sha256"] == hashlib.sha256(data).hexdigest()
        assert (
            item["conditional_etag_requested"] is False
        )  # the memory backend has no S3 condition
    for name, record in report["tool_sources"].items():
        data = (tmp_path / "raw/sources" / name).read_bytes()
        assert record["sha256"] == hashlib.sha256(data).hexdigest()


def test_plan_reads_only_metadata_and_creates_no_output(bucket, tmp_path, monkeypatch):
    fs, _, _ = bucket

    def body_forbidden(*args, **kwargs):
        raise AssertionError("body read during plan")

    monkeypatch.setattr(fs, "cat_file", body_forbidden)
    before = list(tmp_path.iterdir())
    report = plan(bucket, tmp_path, center_layers=4)
    assert report["status"] == "PLANNED"
    assert report["selected_depth_indices"] == [2, 3, 4, 5]
    assert list(tmp_path.iterdir()) == before


def test_center_selection_and_no_recursive_payloads(bucket, tmp_path, monkeypatch):
    fs, _, base = bucket
    fs.pipe(base + "/layers/cache/volume.zarr/0/huge", b"not downloaded")
    fs.pipe(base + "/surface-volumes/volume.zarr/0/huge", b"not downloaded")
    fs.pipe(base + "/.hidden_inklabels.png", b"glob would ignore")
    fs.pipe(base + "/Upper_Mask.PNG", b"case-sensitive glob would ignore")
    calls = []
    real = fs.cat_file

    def ranged(key, start=None, end=None, **kwargs):
        assert start is not None and end is not None
        assert 0 < end - start <= artifacts.BLOCK_BYTES
        calls.append(key)
        return real(key, start=start, end=end, **kwargs)

    monkeypatch.setattr(fs, "cat_file", ranged)

    def recursive_forbidden(*args, **kwargs):
        raise AssertionError("recursive get used")

    monkeypatch.setattr(fs, "get", recursive_forbidden)
    download(bucket, tmp_path, center_layers=4)
    assert sorted(p.name for p in (tmp_path / "raw/layers").iterdir()) == [
        "02.tif",
        "03.tif",
        "04.tif",
        "05.tif",
    ]
    assert len(calls) == 6 and all("huge" not in key for key in calls)
    assert not (tmp_path / "raw/surface-volumes").exists()


@pytest.mark.parametrize("kind", ["relative", "bucket", "uri"])
def test_prefix_forms_have_identical_selection(bucket, tmp_path, kind):
    fs, prefix, base = bucket
    value = {"relative": prefix, "bucket": base, "uri": "s3://" + base}[kind]
    report = fetch.plan_segment(value + "/", tmp_path / "raw", filesystem=fs)
    assert report["source"] == "s3://" + base


@pytest.mark.parametrize(
    "prefix",
    [
        "",
        "/absolute",
        "../escape",
        "a//b",
        "a/./b",
        "a\\b",
        "s3://other-bucket/segment",
        "https://example.invalid/segment",
        "a\nb",
    ],
)
def test_bad_prefixes_fail_before_remote_access(tmp_path, prefix, monkeypatch):
    def forbidden():
        raise AssertionError("filesystem created")

    monkeypatch.setattr(fetch, "_filesystem", forbidden)
    with pytest.raises(ValueError):
        fetch.plan_segment(prefix, tmp_path / "raw")
    assert not (tmp_path / "raw").exists()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_bytes": 1},
        {"max_file_bytes": 1},
        {"max_files": 1},
        {"max_entries": 2},
        {"center_layers": 9},
        {"center_layers": 0},
        {"center_layers": True},
        {"max_bytes": 0},
        {"max_bytes": True},
        {"max_bytes": 64 * 1024**3 + 1},
        {"max_file_bytes": 2 * 1024**3 + 1},
        {"max_entries": 4097},
        {"max_files": 1025},
    ],
)
def test_budget_or_settings_failures_read_no_payloads(
    bucket, tmp_path, monkeypatch, kwargs
):
    fs, _, _ = bucket

    def forbidden(*args, **kwargs):
        raise AssertionError("payload read")

    monkeypatch.setattr(fs, "cat_file", forbidden)
    with pytest.raises(ValueError):
        download(bucket, tmp_path, **kwargs)
    assert not (tmp_path / "raw").exists()


@pytest.mark.parametrize(
    "kind",
    [
        "missing_label",
        "duplicate_labels",
        "duplicate_masks",
        "directory_mask",
        "duplicate_depth",
        "invalid_depth",
        "gap",
        "no_layers",
        "no_numeric_layers",
    ],
)
def test_ambiguous_or_incomplete_raw_layout_is_rejected(bucket, tmp_path, kind):
    fs, _, base = bucket
    if kind == "missing_label":
        fs.rm(base + "/segment_inklabels.png")
    elif kind == "duplicate_labels":
        fs.pipe(base + "/other_inklabels.png", b"other")
    elif kind == "duplicate_masks":
        fs.pipe(base + "/other_mask.png", b"other")
    elif kind == "directory_mask":
        fs.pipe(base + "/masks/nested.png", b"other")
    elif kind == "duplicate_depth":
        fs.pipe(base + "/layers/0.tif", b"other")
    elif kind == "invalid_depth":
        fs.pipe(base + "/layers/depth.tif", b"other")
    elif kind == "gap":
        fs.rm(base + "/layers/03.tif")
    elif kind == "no_layers":
        fs.rm(base + "/layers", recursive=True)
    elif kind == "no_numeric_layers":
        fs.rm(base + "/layers", recursive=True)
        fs.pipe(base + "/layers/info.txt", b"other")
    with pytest.raises(ValueError):
        download(bucket, tmp_path)
    assert not (tmp_path / "raw").exists()


def test_missing_mask_remains_explicit(bucket, tmp_path):
    fs, _, base = bucket
    fs.rm(base + "/segment_mask.png")
    download(bucket, tmp_path)
    report = json.loads((tmp_path / "raw/download.json").read_text())
    assert report["mask_present"] is False


@pytest.mark.parametrize("kind", ["existing", "file", "symlink"])
def test_existing_destinations_are_preserved_and_never_contact_s3(
    tmp_path, monkeypatch, kind
):
    output = tmp_path / "raw"
    if kind == "existing":
        output.mkdir()
        (output / "user.txt").write_text("keep")
    elif kind == "file":
        output.write_text("keep")
    else:
        output.symlink_to(tmp_path / "missing")

    def forbidden():
        raise AssertionError("filesystem created")

    monkeypatch.setattr(fetch, "_filesystem", forbidden)
    with pytest.raises(ValueError):
        fetch.fetch_segment("segment", output)
    assert output.exists() or output.is_symlink()
    if kind == "existing":
        assert (output / "user.txt").read_text() == "keep"
    elif kind == "file":
        assert output.read_text() == "keep"


@pytest.mark.parametrize(
    "output",
    [
        "s3://some-bucket/raw",
        Path("s3://some-bucket/raw"),
        "https://example.invalid/raw",
    ],
)
def test_remote_output_uris_cannot_become_local_directories(output, monkeypatch):
    def forbidden():
        raise AssertionError("filesystem created")

    monkeypatch.setattr(fetch, "_filesystem", forbidden)
    with pytest.raises(ValueError, match="local filesystem"):
        fetch.plan_segment("segment", output)


@pytest.mark.parametrize(
    "mutation",
    ["outside_prefix", "duplicate_entry", "wrong_size", "bad_etag", "missing_etag_s3"],
)
def test_invalid_listing_metadata_cannot_form_a_plan(
    bucket, tmp_path, monkeypatch, mutation
):
    fs, _, _ = bucket
    real = fs.ls

    def listing(path, detail=True, **kwargs):
        entries = [dict(item) for item in real(path, detail=detail, **kwargs)]
        if path.endswith("/layers"):
            if mutation == "outside_prefix":
                entries[0]["name"] = "/" + artifacts.BUCKET + "/elsewhere/00.tif"
            elif mutation == "duplicate_entry":
                entries.append(entries[0])
            elif mutation == "wrong_size":
                entries[0]["size"] = -1
            elif mutation == "bad_etag":
                entries[0]["ETag"] = "invalid\nheader"
        return entries

    monkeypatch.setattr(fs, "ls", listing)
    if mutation == "missing_etag_s3":
        monkeypatch.setattr(fs, "protocol", ("s3",))
    with pytest.raises(ValueError):
        download(bucket, tmp_path)
    assert not (tmp_path / "raw").exists()


@pytest.mark.parametrize("fault", ["failure", "short", "long"])
def test_failed_transfer_publishes_no_partial_raw_directory(
    bucket, tmp_path, monkeypatch, fault
):
    fs, _, _ = bucket
    real = fs.cat_file

    def broken(key, start=None, end=None, **kwargs):
        data = real(key, start=start, end=end, **kwargs)
        if "inklabels" in key:
            if fault == "failure":
                raise OSError("injected transfer failure")
            if fault == "short":
                return data[:-1]
            return data + b"x"
        return data

    monkeypatch.setattr(fs, "cat_file", broken)
    with pytest.raises((OSError, ValueError)):
        download(bucket, tmp_path)
    assert not (tmp_path / "raw").exists()
    assert not list(tmp_path.glob(".raw-*"))


@pytest.mark.parametrize(
    "change", ["object", "selection", "payload", "code_copy", "extra"]
)
def test_remote_or_local_mutation_blocks_completion(
    bucket, tmp_path, monkeypatch, change
):
    fs, _, base = bucket
    real_listing, real_plan = fs.ls, artifacts.build_plan

    def listing(path, detail=True, **kwargs):
        entries = [dict(item) for item in real_listing(path, detail=detail, **kwargs)]
        for item in entries:
            if item["type"] == "file":
                # A server-side identity; do not read payloads through the client API.
                item["ETag"] = hashlib.sha256(
                    fs.store[item["name"]].getvalue()
                ).hexdigest()
        return entries

    monkeypatch.setattr(fs, "ls", listing)
    count = 0

    def build(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 2:
            if change == "object":
                fs.pipe(base + "/layers/02.tif", b"changed")
            elif change == "selection":
                fs.pipe(base + "/layers/08.tif", b"layer08")
            else:
                staging = next(tmp_path.glob(".raw-*/new.zarr"))
                path = staging / (
                    "layers/02.tif"
                    if change == "payload"
                    else "layers/01.tif"
                    if change == "extra"
                    else "sources/fetch.py"
                )
                path.write_bytes(b"changed")
        return real_plan(*args, **kwargs)

    monkeypatch.setattr(artifacts, "build_plan", build)
    # fetch imported the planner directly; keep both boundaries on the same observer.
    monkeypatch.setattr(fetch, "build_plan", build)
    with pytest.raises(ValueError, match="changed"):
        download(bucket, tmp_path, center_layers=4)
    assert not (tmp_path / "raw").exists()


def test_no_completion_manifest_exists_during_rechecks(bucket, tmp_path, monkeypatch):
    from scripts.text_snapshot import Snapshot

    real = Snapshot.verify
    observed = []

    def verify(item):
        observed.append(True)
        assert not list(tmp_path.glob(".raw-*/new.zarr/download.json"))
        return real(item)

    monkeypatch.setattr(Snapshot, "verify", verify)
    download(bucket, tmp_path)
    assert observed


@pytest.fixture
def s3():
    import s3fs

    fs = s3fs.S3FileSystem(anon=True, skip_instance_cache=True)
    fs.connect()
    yield fs
    fs.close_session(fs.loop, fs._s3creator)


class AsyncBody(io.BytesIO):
    # SDK stub validation accepts an IO body; aiobotocore consumes it asynchronously.
    async def read(self, amount=-1):  # type: ignore[override]
        return super().read(min(amount, 3))  # exercise fragmented HTTP bodies


@pytest.mark.parametrize("fault", [None, "short", "long", "length", "range", "etag"])
def test_actual_s3_sdk_receives_range_and_ifmatch_and_closes_body(s3, fault):
    from aiobotocore.stub import AioStubber

    item = {
        "key": artifacts.BUCKET + "/segment/layers/00.tif",
        "bytes": 6,
        "etag": '"etag"',
    }
    body = AsyncBody(
        b"abcde" if fault == "short" else b"abcdefg" if fault == "long" else b"abcdef"
    )
    response = {
        "Body": body,
        "ContentLength": 6,
        "ContentRange": "bytes 0-5/6",
        "ETag": '"etag"',
    }
    if fault == "length":
        response["ContentLength"] = 5
    elif fault == "range":
        response["ContentRange"] = "bytes 0-5/7"
    elif fault == "etag":
        response["ETag"] = '"other"'
    with AioStubber(s3.s3) as stub:
        stub.add_response(
            "get_object",
            response,
            {
                "Bucket": artifacts.BUCKET,
                "Key": "segment/layers/00.tif",
                "Range": "bytes=0-5",
                "IfMatch": '"etag"',
            },
        )
        if fault is None:
            assert artifacts._read_range(s3, item, 0, 6) == b"abcdef"
        else:
            with pytest.raises(ValueError):
                artifacts._read_range(s3, item, 0, 6)
        stub.assert_no_pending_responses()
    assert body.closed


def test_actual_sdk_segment_publication_roundtrips_protocol_tuple(
    s3, bucket, tmp_path, monkeypatch
):
    from aiobotocore.stub import AioStubber

    memory, prefix, _ = bucket
    real_listing = memory.ls

    def listing(path, detail=True):
        entries = [dict(item) for item in real_listing(path, detail=detail)]
        for item in entries:
            if item["type"] == "file":
                item["ETag"] = (
                    '"'
                    + hashlib.sha256(memory.store[item["name"]].getvalue()).hexdigest()
                    + '"'
                )
        return entries

    monkeypatch.setattr(s3, "ls", listing)
    planned = fetch.plan_segment(
        prefix, tmp_path / "raw", filesystem=s3, center_layers=2
    )
    with AioStubber(s3.s3) as stub:
        for item in planned["files"]:
            data = memory.store["/" + item["key"]].getvalue()
            stub.add_response(
                "get_object",
                {
                    "Body": AsyncBody(data),
                    "ContentLength": len(data),
                    "ContentRange": f"bytes 0-{len(data) - 1}/{len(data)}",
                    "ETag": item["etag"],
                },
                {
                    "Bucket": artifacts.BUCKET,
                    "Key": item["key"].removeprefix(artifacts.BUCKET + "/"),
                    "Range": f"bytes=0-{len(data) - 1}",
                    "IfMatch": item["etag"],
                },
            )
        fetch.fetch_segment(prefix, tmp_path / "raw", filesystem=s3, center_layers=2)
        stub.assert_no_pending_responses()
    record = json.loads((tmp_path / "raw/download.json").read_text())
    assert record["runtime"]["filesystem_protocol"] == ["s3", "s3a"]
    assert all(item["conditional_etag_requested"] for item in record["files"])


def test_actual_sdk_precondition_failure_aborts_download(s3, tmp_path, monkeypatch):
    from aiobotocore.stub import AioStubber

    monkeypatch.setattr(artifacts, "BLOCK_BYTES", 4)
    item = {
        "key": artifacts.BUCKET + "/segment/layers/00.tif",
        "bytes": 6,
        "etag": '"etag"',
    }
    with AioStubber(s3.s3) as stub:
        stub.add_response(
            "get_object",
            {
                "Body": AsyncBody(b"abcd"),
                "ContentLength": 4,
                "ContentRange": "bytes 0-3/6",
                "ETag": '"etag"',
            },
            {
                "Bucket": artifacts.BUCKET,
                "Key": "segment/layers/00.tif",
                "Range": "bytes=0-3",
                "IfMatch": '"etag"',
            },
        )
        stub.add_client_error(
            "get_object",
            service_error_code="PreconditionFailed",
            http_status_code=412,
            expected_params={
                "Bucket": artifacts.BUCKET,
                "Key": "segment/layers/00.tif",
                "Range": "bytes=4-5",
                "IfMatch": '"etag"',
            },
        )
        with pytest.raises(OSError):
            artifacts._download(s3, item, tmp_path / "partial")
        stub.assert_no_pending_responses()


def test_cli_plan_and_execution_report_errors_and_counts(
    bucket, tmp_path, monkeypatch, capsys
):
    fs, prefix, _ = bucket
    monkeypatch.setattr(fetch, "_filesystem", lambda: fs)
    args = [prefix, str(tmp_path / "raw"), "--center-layers", "4"]
    assert fetch.main(args + ["--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["file_count"] == 6
    assert not (tmp_path / "raw").exists()
    assert fetch.main(args) == 0
    assert "Downloaded raw segment" in capsys.readouterr().out
    assert fetch.main(args) == 1  # no overwrite
    assert "already exists" in capsys.readouterr().err


def test_help_from_other_directory_does_not_import_sdk_or_ml(tmp_path):
    code = """
import builtins,runpy,sys
original=builtins.__import__
def guarded(name,*args,**kwargs):
 if name.split('.')[0] in {'s3fs','torch','numpy','zarr','wandb'}: raise RuntimeError(name)
 return original(name,*args,**kwargs)
builtins.__import__=guarded
sys.argv=[sys.argv[1],'--help'];runpy.run_path(sys.argv[0],run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(ROOT / "repro/sota_data/fetch.py")],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--center-layers" in result.stdout and "--dry-run" in result.stdout
