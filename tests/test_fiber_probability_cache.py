"""A benchmark's probability identity must describe the values it actually used."""

import json
from pathlib import Path

import numpy as np
import pytest
from test_fiber_workflow_contracts import prepare_model_files, simple_gt

from vesuvius_autoresearch.fibers import (
    bench_cli,
    benchmark_artifacts as artifacts,
    eval_trace,
    semantic,
)
from vesuvius_autoresearch.fibers.provenance import file_sha256


def cached_cube(tmp_path, monkeypatch):
    model = tmp_path / "model"
    prepare_model_files(model)
    img = np.zeros((3, 3, 8), np.uint8)
    calls = []
    monkeypatch.setattr(semantic, "load_model", lambda *a, **k: object())

    def predict(model, image, **kwargs):
        calls.append(kwargs)
        return np.full((4, *image.shape), 0.25, np.float32)

    monkeypatch.setattr(semantic, "predict_volume", predict)
    bench_cli._fiber_prob(tmp_path, "cube", img, model, 4, "cpu")
    return (
        model,
        img,
        calls,
        tmp_path / "cube_fiberprob.npy",
        tmp_path / "cube_fiberprob.json",
    )


def test_cache_load_cannot_use_bytes_replaced_after_hashing(tmp_path, monkeypatch):
    model, img, calls, cache, _ = cached_cube(tmp_path, monkeypatch)
    load = np.load

    def changed(path, *args, **kwargs):
        if Path(path) == cache:
            np.save(cache, np.full(img.shape, 0.125, np.float32))
        return load(path, *args, **kwargs)

    monkeypatch.setattr(np, "load", changed)
    actual = bench_cli._fiber_prob(tmp_path, "cube", img, model, 4, "cpu")
    np.testing.assert_array_equal(actual, np.full(img.shape, 0.75))
    assert len(calls) == 1


def test_floor_provenance_cannot_reread_replaced_metadata(tmp_path, monkeypatch):
    model, img, _, _, metadata = cached_cube(tmp_path, monkeypatch)
    expected = json.loads(metadata.read_text())
    labels = tmp_path / "labels.npy"
    np.save(labels, np.ones(img.shape, np.uint32))
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: (img, simple_gt()))
    score = eval_trace.score_tracing
    calls = []

    def replace_after_scoring(gt, instances, **kwargs):
        result = score(gt, instances, **kwargs)
        calls.append(True)
        if len(calls) == 2:
            metadata.write_text(
                json.dumps(
                    {"inference": {"different": True}, "probability_sha256": "f" * 64}
                )
            )
        return result

    monkeypatch.setattr(eval_trace, "score_tracing", replace_after_scoring)
    output = tmp_path / "score.json"
    assert (
        bench_cli.main(
            [
                "--data-dir",
                str(tmp_path),
                "score",
                "--cube",
                "cube",
                "--instances",
                str(labels),
                "--with-floors",
                "--model",
                str(model),
                "--patch",
                "4",
                "--device",
                "cpu",
                "--json-out",
                str(output),
            ]
        )
        == 0
    )
    actual = json.loads(output.read_text())["floor_provenance"]
    assert actual["probability_sha256"] == expected["probability_sha256"]
    assert actual["inference"] == expected["inference"]


def test_probability_capture_survives_path_replacement(tmp_path, monkeypatch):
    model, img, calls, cache, metadata = cached_cube(tmp_path, monkeypatch)
    expected = json.loads(metadata.read_text())
    capture = artifacts.capture_bytes

    def replace_after_capture(path, limit):
        captured = capture(path, limit)
        if Path(path) == cache:
            np.save(cache, np.full(img.shape, 0.125, np.float32))
        return captured

    monkeypatch.setattr(artifacts, "capture_bytes", replace_after_capture)
    result = bench_cli._fiber_probability(tmp_path, "cube", img, model, 4, "cpu")
    np.testing.assert_array_equal(result.probability, 0.75)
    assert result.record == expected
    assert result.record["probability_sha256"] != file_sha256(cache)
    assert result.cache["status"] == "HIT"
    assert len(calls) == 1
    with pytest.raises(ValueError, match="read-only"):
        result.probability[0, 0, 0] = 0


@pytest.mark.parametrize("dtype,fortran", [("f2", False), ("f4", True), (">f8", False)])
def test_matching_numeric_cache_layouts_still_hit(
    tmp_path, monkeypatch, dtype, fortran
):
    model, img, calls, cache, metadata = cached_cube(tmp_path, monkeypatch)
    value = np.full(img.shape, 0.375, dtype=dtype, order="F" if fortran else "C")
    np.save(cache, value)
    record = json.loads(metadata.read_text())
    record["probability_sha256"] = file_sha256(cache)
    metadata.write_text(json.dumps(record))
    result = bench_cli._fiber_probability(tmp_path, "cube", img, model, 4, "cpu")
    np.testing.assert_array_equal(result.probability, value)
    assert result.cache["status"] == "HIT"
    assert result.record == record
    assert len(calls) == 1
    legacy = bench_cli._fiber_prob(tmp_path, "cube", img, model, 4, "cpu")
    assert legacy.dtype == np.dtype(float) and legacy.flags.writeable
    legacy[0, 0, 0] = 1
    assert np.load(cache)[0, 0, 0] == 0.375


@pytest.mark.parametrize(
    "bad",
    [
        "integer",
        "object",
        "shape",
        "nan",
        "negative",
        "large",
        "truncated",
        "trailing",
        "npz",
        "allocation",
    ],
)
def test_invalid_probability_capture_is_recomputed(tmp_path, monkeypatch, bad):
    model, img, calls, cache, metadata = cached_cube(tmp_path, monkeypatch)
    value = np.full(img.shape, 0.5, np.float32)
    if bad == "integer":
        value = value.astype(np.uint8)
    elif bad == "object":
        value = value.astype(object)
    elif bad == "shape":
        value = value[:1]
    elif bad in {"nan", "negative", "large"}:
        value[0, 0, 0] = {"nan": np.nan, "negative": -0.1, "large": 1.1}[bad]
    np.save(cache, value)
    if bad == "truncated":
        cache.write_bytes(cache.read_bytes()[:-1])
    elif bad == "trailing":
        cache.write_bytes(cache.read_bytes() + b"extra")
    elif bad == "npz":
        with cache.open("wb") as stream:
            np.savez(stream, value=value)
    elif bad == "allocation":
        with cache.open("wb") as stream:
            np.lib.format.write_array_header_1_0(
                stream,
                {"descr": "<f8", "fortran_order": False, "shape": (10**12, 3, 8)},
            )
    record = json.loads(metadata.read_text())
    # Even a matching file hash cannot make malformed probabilities valid.
    record["probability_sha256"] = file_sha256(cache)
    metadata.write_text(json.dumps(record))
    result = bench_cli._fiber_probability(tmp_path, "cube", img, model, 4, "cpu")
    assert result.cache["status"] == "REFRESHED"
    assert result.cache["reason"] == "invalid_probability"
    np.testing.assert_array_equal(result.probability, 0.75)
    assert result.record == json.loads(metadata.read_text())
    assert result.record["probability_sha256"] == file_sha256(cache)
    assert len(calls) == 2


@pytest.mark.parametrize(
    "bad,reason",
    [
        ("digest", "digest_mismatch"),
        ("recipe", "inference_changed"),
        ("list", "invalid_manifest"),
        ("json", "invalid_manifest"),
        ("oversize", "invalid_manifest"),
        ("missing", "missing_metadata"),
    ],
)
def test_unattested_caches_explain_refresh(tmp_path, monkeypatch, bad, reason):
    model, img, calls, _, metadata = cached_cube(tmp_path, monkeypatch)
    record = json.loads(metadata.read_text())
    if bad == "digest":
        record["probability_sha256"] = "0" * 64
    elif bad == "recipe":
        record["inference"]["recipe"]["patch_size"] = [8] * 3
    elif bad == "list":
        record = []
    metadata.write_text(json.dumps(record))
    if bad == "json":
        metadata.write_bytes(b"interrupted")
    elif bad == "oversize":
        metadata.write_bytes(b" " * (1024**2 + 1))
    elif bad == "missing":
        metadata.unlink()
    result = bench_cli._fiber_probability(tmp_path, "cube", img, model, 4, "cpu")
    assert result.cache["status"] == "REFRESHED"
    assert result.cache["reason"] == reason
    assert len(calls) == 2


def test_model_change_during_hit_refuses_the_result(tmp_path, monkeypatch):
    model, img, calls, cache, metadata = cached_cube(tmp_path, monkeypatch)
    prior = cache.read_bytes(), metadata.read_bytes()
    read = bench_cli.read_probabilities

    def changed(*args):
        result = read(*args)
        (model / "fold_0/checkpoint_final.pth").write_bytes(b"changed")
        return result

    monkeypatch.setattr(bench_cli, "read_probabilities", changed)
    with pytest.raises(ValueError, match="changed during cache validation"):
        bench_cli._fiber_probability(tmp_path, "cube", img, model, 4, "cpu")
    assert (cache.read_bytes(), metadata.read_bytes()) == prior
    assert len(calls) == 1


def test_refresh_failure_preserves_pair_until_publication(tmp_path, monkeypatch):
    model, img, _, cache, metadata = cached_cube(tmp_path, monkeypatch)
    prior = cache.read_bytes(), metadata.read_bytes()

    def failed(*a, **k):
        raise RuntimeError("inference failed")

    monkeypatch.setattr(semantic, "predict_volume", failed)
    with pytest.raises(RuntimeError, match="inference failed"):
        bench_cli._fiber_probability(tmp_path, "cube", img, model, 4, "cpu", True)
    assert (cache.read_bytes(), metadata.read_bytes()) == prior


def test_failed_manifest_publication_invalidates_previous_record(tmp_path, monkeypatch):
    model, img, _, cache, metadata = cached_cube(tmp_path, monkeypatch)

    def failed(*a, **k):
        raise OSError("manifest failed")

    monkeypatch.setattr(bench_cli, "write_json", failed)
    with pytest.raises(OSError, match="manifest failed"):
        bench_cli._fiber_probability(tmp_path, "cube", img, model, 4, "cpu", True)
    assert cache.is_file() and not metadata.exists()


def test_explicit_refresh_preserves_permissions_and_scientific_identity(
    tmp_path, monkeypatch
):
    model, img, calls, cache, metadata = cached_cube(tmp_path, monkeypatch)
    before = json.loads(metadata.read_text())
    cache.chmod(0o640)
    metadata.chmod(0o644)
    result = bench_cli._fiber_probability(tmp_path, "cube", img, model, 4, "cpu", True)
    assert result.cache["status"] == "REFRESHED"
    assert result.cache["reason"] == "explicit_refresh"
    assert result.record == before
    assert result.cache["cache_path"] == str(cache.resolve())
    assert cache.stat().st_mode & 0o777 == 0o640
    assert metadata.stat().st_mode & 0o777 == 0o644
    assert len(calls) == 2


@pytest.mark.parametrize("mode", ["floors", "all-cubes", "score"])
def test_report_cache_status_is_separate_from_floor_provenance(
    tmp_path, monkeypatch, mode
):
    model, img, calls, _, _ = cached_cube(tmp_path, monkeypatch)
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: (img, simple_gt()))
    monkeypatch.setattr(bench_cli, "CUBES", ["cube"])
    labels = tmp_path / "labels.npy"
    np.save(labels, np.ones(img.shape, np.uint32))
    output = tmp_path / "report.json"
    flags = [
        "--data-dir",
        str(tmp_path),
        "score" if mode == "score" else "floors",
        "--cube",
        "cube",
        "--model",
        str(model),
        "--patch",
        "4",
        "--device",
        "cpu",
        "--json-out",
        str(output),
    ]
    if mode == "score":
        flags += ["--instances", str(labels), "--with-floors"]
    elif mode == "all-cubes":
        flags += ["--all-cubes"]
    provenance_key = "floor_provenance" if mode == "score" else "provenance"
    assert bench_cli.main(flags) == 0
    report = json.loads(output.read_text())
    cube = report["cubes"]["cube"] if mode == "all-cubes" else report
    before = cube[provenance_key]
    assert cube["probability_cache"]["status"] == "HIT"
    if mode == "all-cubes":
        prior_tracer = {**cube["rows"]["floor_connected_components"], "preserved": True}
        cube["rows"]["tracer_strict_relink"] = prior_tracer
        output.write_text(json.dumps(report))
    assert bench_cli.main([*flags, "--refresh-cache"]) == 0
    report = json.loads(output.read_text())
    cube = report["cubes"]["cube"] if mode == "all-cubes" else report
    assert cube[provenance_key] == before
    assert cube["probability_cache"]["reason"] == "explicit_refresh"
    if mode == "all-cubes":
        assert cube["rows"]["tracer_strict_relink"] == prior_tracer
    assert len(calls) == 2


def test_score_cannot_silently_ignore_refresh_cache(capsys):
    with pytest.raises(SystemExit) as exc:
        bench_cli.main(
            [
                "score",
                "--cube",
                "missing",
                "--instances",
                "missing.npy",
                "--refresh-cache",
            ]
        )
    assert exc.value.code == 2
    assert "--refresh-cache requires --with-floors" in capsys.readouterr().err


def test_score_without_floors_remains_model_free(tmp_path, monkeypatch):
    img = np.zeros((3, 3, 8), np.uint8)
    labels = tmp_path / "labels.npy"
    np.save(labels, np.ones(img.shape, np.uint32))
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: (img, simple_gt()))

    def unexpected(*args):
        raise AssertionError("score-only must not load probability caches or a model")

    monkeypatch.setattr(bench_cli, "_fiber_probability", unexpected)
    output = tmp_path / "report.json"
    assert (
        bench_cli.main(
            [
                "--data-dir",
                str(tmp_path),
                "score",
                "--cube",
                "cube",
                "--instances",
                str(labels),
                "--json-out",
                str(output),
            ]
        )
        == 0
    )
    report = json.loads(output.read_text())
    assert report["probability_cache"] is None
    assert report["floor_provenance"] is None
