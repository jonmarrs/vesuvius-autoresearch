"""Benchmark reports must identify scored bytes and never replace their inputs."""

import hashlib
import json
import os
import stat

import numpy as np
import pytest
from test_fiber_workflow_contracts import bench_cube, simple_gt

from vesuvius_autoresearch.fibers import bench_cli, eval_trace


@pytest.mark.parametrize("alias", ["symlink", "hardlink", "descendant"])
def test_report_aliases_are_rejected_before_data(tmp_path, monkeypatch, alias):
    source, argv = score_fixture(tmp_path, monkeypatch)
    output = tmp_path / "report.json"
    if alias == "symlink":
        output.symlink_to(source)
    elif alias == "hardlink":
        os.link(source, output)
    else:
        output = source / "report.json"
    original = source.read_bytes()
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: pytest.fail("data loaded"))
    with pytest.raises(ValueError, match="artifact collision|cannot inspect"):
        bench_cli.main([*argv, "--json-out", str(output)])
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    "mode,target",
    [
        ("score", "cube.nml"),
        ("score", "cube_image.tif"),
        ("score", "cube_semantic.tif"),
        ("score", "cube_fiberprob.npy"),
        ("score", "plans.json"),
        ("floors", "cube_fiberprob.json"),
        ("trace", "plans.json"),
    ],
)
def test_reports_cannot_replace_ground_truth_model_or_cache(
    tmp_path, monkeypatch, mode, target
):
    output = tmp_path / target
    output.write_bytes(b"input to preserve")
    argv = [
        "--data-dir",
        str(tmp_path),
        mode,
        "--cube",
        "cube",
        "--model",
        str(tmp_path),
        "--json-out",
        str(output),
    ]
    if mode == "score":
        argv.extend(["--instances", str(tmp_path / "labels.npy")])
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: pytest.fail("data loaded"))
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli.main(argv)
    assert output.read_bytes() == b"input to preserve"


def test_all_cube_preflight_checks_later_cube_sources_before_any_inference(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(bench_cli, "CUBES", ["first", "second"])
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: pytest.fail("data loaded"))
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli.main(
            [
                "--data-dir",
                str(tmp_path),
                "floors",
                "--all-cubes",
                "--json-out",
                str(tmp_path / "second.nml"),
            ]
        )


def test_cache_publication_cannot_replace_the_cube_image(tmp_path):
    image = tmp_path / "cube_image.tif"
    image.write_bytes(b"CT")
    os.link(image, tmp_path / "cube_fiberprob.npy")
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli._fiber_prob(tmp_path, "cube", np.zeros((3, 3, 8)), tmp_path, 8)
    assert image.read_bytes() == b"CT"


def test_report_paths_are_rechecked_after_scoring(tmp_path, monkeypatch):
    source, argv = score_fixture(tmp_path, monkeypatch)
    output = tmp_path / "report.json"
    actual = eval_trace.score_tracing

    def changed(gt, labels, **kwargs):
        output.symlink_to(source)
        return actual(gt, labels, **kwargs)

    original = source.read_bytes()
    monkeypatch.setattr(eval_trace, "score_tracing", changed)
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli.main([*argv, "--json-out", str(output)])
    assert source.read_bytes() == original


def test_trace_report_identifies_the_written_npy(bench_cube):  # noqa: F811
    report, labels, _ = bench_cube()
    saved = bench_cube.data_dir / "instances.npy"
    assert report["instances_output"] == {
        "path": str(saved),
        "sha256": hashlib.sha256(saved.read_bytes()).hexdigest(),
        "size_bytes": saved.stat().st_size,
        "shape": list(labels.shape),
        "dtype": labels.dtype.str,
    }


def test_interrupted_trace_publication_removes_stale_report(bench_cube, monkeypatch):  # noqa: F811
    bench_cube()
    report = bench_cube.data_dir / "trace.json"
    assert report.exists()

    def fail(*a, **k):
        raise RuntimeError("serialization interrupted")

    monkeypatch.setattr(bench_cli, "write_json", fail)
    with pytest.raises(RuntimeError, match="serialization interrupted"):
        bench_cube()
    assert (bench_cube.data_dir / "instances.npy").exists()
    assert not report.exists()


def test_trace_report_keeps_its_previous_permissions(bench_cube):  # noqa: F811
    bench_cube()
    report = bench_cube.data_dir / "trace.json"
    report.chmod(0o640)
    bench_cube()
    assert stat.S_IMODE(report.stat().st_mode) == 0o640


def test_trace_without_saved_instances_does_not_claim_a_file(bench_cube):  # noqa: F811
    output = bench_cube.data_dir / "score_only.json"
    assert (
        bench_cli.main(
            [
                "--data-dir",
                str(bench_cube.data_dir),
                "trace",
                "--cube",
                "cube",
                "--json-out",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text())["instances_output"] is None
    assert not (bench_cube.data_dir / "instances.npy").exists()


def test_floor_row_cannot_overwrite_a_candidate_with_the_same_filename(
    tmp_path, monkeypatch
):
    source = tmp_path / "floor: connected components.npy"
    labels = np.arange(1, 73, dtype=np.uint64).reshape(3, 3, 8)
    np.save(source, labels)
    monkeypatch.setattr(
        bench_cli, "_load_cube", lambda *a: (np.zeros(labels.shape), simple_gt())
    )
    monkeypatch.setattr(bench_cli, "_fiber_prob", lambda *a: np.ones(labels.shape))
    monkeypatch.setattr(bench_cli, "_measurement_provenance", lambda *a: {"stub": True})
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
                str(source),
                "--with-floors",
                "--json-out",
                str(output),
            ]
        )
        == 0
    )
    record = json.loads(output.read_text())
    assert len(record["rows"]) == 2
    assert record["rows"][record["candidate_row"]]["n_pred_instances"] == 72
    assert record["rows"]["floor: connected components"]["n_pred_instances"] == 1


def score_fixture(tmp_path, monkeypatch):
    source = tmp_path / "instances.npy"
    labels = np.ones((3, 3, 8), np.uint64) * (2**32 + 1)
    np.save(source, labels)
    monkeypatch.setattr(
        bench_cli, "_load_cube", lambda *a: (np.zeros(labels.shape), simple_gt())
    )
    return source, [
        "--data-dir",
        str(tmp_path),
        "score",
        "--cube",
        "cube",
        "--instances",
        str(source),
    ]


def test_score_report_cannot_replace_its_instance_input(tmp_path, monkeypatch):
    source, argv = score_fixture(tmp_path, monkeypatch)
    before = source.read_bytes()
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli.main([*argv, "--json-out", str(source)])
    assert source.read_bytes() == before


def test_score_hash_identifies_the_loaded_instance_bytes(tmp_path, monkeypatch):
    source, argv = score_fixture(tmp_path, monkeypatch)
    original = source.read_bytes()
    actual = eval_trace.score_tracing

    def replace_path(gt, labels, **kwargs):
        result = actual(gt, labels, **kwargs)
        np.save(source, np.zeros(labels.shape, np.uint64))
        return result

    monkeypatch.setattr(eval_trace, "score_tracing", replace_path)
    output = tmp_path / "score.json"
    assert bench_cli.main([*argv, "--json-out", str(output)]) == 0
    record = json.loads(output.read_text())
    assert (
        record["provenance"]["instances_sha256"] == hashlib.sha256(original).hexdigest()
    )
    assert record["rows"]["instances"]["n_pred_instances"] == 1


def test_trace_output_alias_is_refused_before_model_or_data_work(tmp_path, monkeypatch):
    monkeypatch.setattr(
        bench_cli,
        "_load_cube",
        lambda *a: pytest.fail("data loaded before collision check"),
    )
    output = tmp_path / "same_output.npy"
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli.main(
            [
                "trace",
                "--cube",
                "cube",
                "--json-out",
                str(output),
                "--save-instances",
                str(output),
            ]
        )


@pytest.mark.parametrize("kind", ["symlink", "directory"])
def test_report_output_must_be_a_regular_file_before_data(tmp_path, monkeypatch, kind):
    # Neither aliases an input, so only the regular-file check refuses them.
    _, argv = score_fixture(tmp_path, monkeypatch)
    output = tmp_path / "report.json"
    if kind == "symlink":
        (tmp_path / "elsewhere.json").write_text("kept")
        output.symlink_to(tmp_path / "elsewhere.json")
    else:
        output.mkdir()
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: pytest.fail("data loaded"))
    with pytest.raises(ValueError, match="report output must be a nonsymlink regular"):
        bench_cli.main([*argv, "--json-out", str(output)])


def test_score_with_floors_plans_the_probability_cache_as_an_output(
    tmp_path, monkeypatch
):
    _, argv = score_fixture(tmp_path, monkeypatch)
    (tmp_path / "elsewhere.npy").write_bytes(b"kept")
    (tmp_path / "cube_fiberprob.npy").symlink_to(tmp_path / "elsewhere.npy")
    load_cube = bench_cli._load_cube
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: pytest.fail("data loaded"))
    with pytest.raises(ValueError, match="cache output must be a nonsymlink regular"):
        bench_cli.main([*argv, "--with-floors"])
    # Without floors, score only reads the cache's paths and never writes them.
    monkeypatch.setattr(bench_cli, "_load_cube", load_cube)
    assert bench_cli.main(argv) == 0


def test_cache_paths_are_rechecked_after_inference(tmp_path, monkeypatch):
    from vesuvius_autoresearch.fibers import semantic

    image = tmp_path / "cube_image.tif"
    image.write_bytes(b"CT")
    cache = tmp_path / "cube_fiberprob.npy"

    def infer(model, img, **kwargs):
        cache.symlink_to(image)
        return np.zeros((2, *img.shape), np.float32)

    monkeypatch.setattr(bench_cli, "inference_identity", lambda *a: {"model": "m"})
    monkeypatch.setattr(semantic, "load_model", lambda *a, **k: object())
    monkeypatch.setattr(semantic, "predict_volume", infer)
    monkeypatch.setattr(semantic, "fiber_probability", lambda prob: prob[0])
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli._fiber_prob(tmp_path, "cube", np.zeros((3, 3, 8)), tmp_path, 8, "cpu")
    assert cache.is_symlink() and image.read_bytes() == b"CT"


def swap_for_model_directory(reports, model):
    # The report's directory becomes the model's: a write that is not refused
    # replaces the model's own plans.json.
    reports.rmdir()
    reports.symlink_to(model, target_is_directory=True)


def model_with_reports(root):
    model, reports = root / "model", root / "reports"
    model.mkdir()
    reports.mkdir()
    (model / "plans.json").write_text("model plans")
    return model, reports


def test_all_cube_report_path_is_rechecked_after_inference(tmp_path, monkeypatch):
    model, reports = model_with_reports(tmp_path)

    def infer(*a):
        swap_for_model_directory(reports, model)
        return np.ones((3, 3, 8))

    monkeypatch.setattr(bench_cli, "CUBES", ["cube"])
    monkeypatch.setattr(
        bench_cli, "_load_cube", lambda *a: (np.zeros((3, 3, 8)), simple_gt())
    )
    monkeypatch.setattr(bench_cli, "_fiber_prob", infer)
    monkeypatch.setattr(bench_cli, "_floor_rows", lambda *a: {})
    monkeypatch.setattr(bench_cli, "_measurement_provenance", lambda *a: {"stub": True})
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli.main(
            [
                "--data-dir",
                str(tmp_path),
                "floors",
                "--all-cubes",
                "--model",
                str(model),
                "--json-out",
                str(reports / "plans.json"),
            ]
        )
    assert (model / "plans.json").read_text() == "model plans"


def test_trace_report_path_is_rechecked_after_saving_instances(
    bench_cube,  # noqa: F811
    monkeypatch,
):
    data_dir = bench_cube.data_dir
    model, reports = model_with_reports(data_dir)
    digest = bench_cli.stream_sha256

    def swap_while_saving(f):
        swap_for_model_directory(reports, model)
        return digest(f)

    monkeypatch.setattr(bench_cli, "stream_sha256", swap_while_saving)
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli.main(
            [
                "--data-dir",
                str(data_dir),
                "trace",
                "--cube",
                "cube",
                "--model",
                str(model),
                "--json-out",
                str(reports / "plans.json"),
                "--save-instances",
                str(data_dir / "instances.npy"),
            ]
        )
    assert (model / "plans.json").read_text() == "model plans"
