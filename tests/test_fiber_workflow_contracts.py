"""Fiber inference and measurement boundaries, exercised without research data."""

import argparse
import json
import subprocess
import sys
from dataclasses import replace

import numpy as np
import pytest
import torch

from vesuvius_autoresearch.fibers import bench_cli, semantic
from vesuvius_autoresearch.fibers.detection import (
    detect_vesselness,
    detect_vesselness_tiled,
)
from vesuvius_autoresearch.fibers.eval_trace import score_tracing
from vesuvius_autoresearch.fibers.skeleton_io import Fiber, Skeleton


class ToyNetwork(torch.nn.Module):
    def __init__(self, kind="valid"):
        super().__init__()
        self.kind = kind
        self.calls = 0

    def forward(self, x):
        self.calls += 1
        shape = (1, 4, *x.shape[2:])
        if self.kind == "channels":
            shape = (1, 1, *x.shape[2:])
        elif self.kind == "spatial":
            shape = (1, 4, x.shape[2] + 1, *x.shape[3:])
        out = torch.zeros(shape, device=x.device)
        if self.kind in ("nan", "inf"):
            out[0, 0, 0, 0, 0] = float(self.kind)
        return out


def toy_model(kind="valid", **kwargs):
    return semantic.SemanticModel(ToyNetwork(kind), (4, 4, 4), 4, "cpu", **kwargs)


def test_semantic_covers_odd_edges_and_padding():
    for shape in [(7, 9, 11), (2, 3, 1)]:
        p = semantic.predict_volume(toy_model(), np.ones(shape), amp=False)
        assert p.shape == (4, *shape)
        np.testing.assert_allclose(p, 0.25, atol=1e-6)
        np.testing.assert_allclose(p.sum(axis=0), 1.0, atol=1e-6)


@pytest.mark.parametrize("step", [0, -0.5, 1.5, float("nan"), float("inf"), True])
def test_semantic_rejects_steps_that_leave_gaps(step):
    model = toy_model()
    with pytest.raises(ValueError, match="tile_step"):
        semantic.predict_volume(model, np.ones((12, 12, 12)), tile_step=step)
    assert model.network.calls == 0


@pytest.mark.parametrize("patch", [(0, 4, 4), (4, 4), (4.5, 4, 4), (True, 4, 4)])
def test_semantic_rejects_invalid_patch(patch):
    with pytest.raises(ValueError, match="patch"):
        semantic.predict_volume(toy_model(), np.ones((8, 8, 8)), patch_size=patch)


@pytest.mark.parametrize(
    "volume", [np.ones((4, 4)), np.ones((0, 4, 4)), np.full((4, 4, 4), np.nan)]
)
def test_semantic_rejects_invalid_volume(volume):
    with pytest.raises(ValueError, match="volume"):
        semantic.predict_volume(toy_model(), volume)


@pytest.mark.parametrize("kind", ["channels", "spatial", "nan", "inf"])
def test_semantic_rejects_invalid_logits(kind):
    with pytest.raises(ValueError, match="logits"):
        semantic.predict_volume(toy_model(kind), np.ones((4, 4, 4)))


@pytest.mark.parametrize("axes", [(3,), (0, 0), (True,)])
def test_semantic_rejects_invalid_mirror_axes(axes):
    with pytest.raises(ValueError, match="mirror"):
        semantic.predict_volume(
            toy_model(mirror_axes=axes), np.ones((4, 4, 4)), use_mirroring=True
        )


def test_semantic_mirroring_is_applied_once_per_view():
    model = toy_model(mirror_axes=(0, 2))
    p = semantic.predict_volume(model, np.ones((4, 4, 4)), use_mirroring=True)
    assert model.network.calls == 4
    np.testing.assert_allclose(p, 0.25, atol=1e-6)


def test_integer_ct_filters_match_float_without_truncation():
    v = np.random.default_rng(4).integers(0, 60000, (12, 12, 12), dtype=np.uint16)
    ref = detect_vesselness(v.astype(np.float32))
    np.testing.assert_allclose(detect_vesselness(v), ref, atol=1e-6)
    tiled = detect_vesselness_tiled(v, block_size=6, halo=10)
    assert tiled.dtype.kind == "f"
    np.testing.assert_allclose(tiled, ref, atol=1e-6)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"block_size": 0},
        {"block_size": -1},
        {"halo": -1},
        {"halo": 1},
        {"gauss_sigma": 5, "halo": 16},
    ],
)
def test_classical_tiling_rejects_invalid_geometry(kwargs):
    with pytest.raises(ValueError):
        detect_vesselness_tiled(np.ones((12, 12, 12)), **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [{"gamma": 0}, {"beta1": -1}, {"sigma": float("nan")}, {"gauss_sigma": -1}],
)
def test_classical_filters_reject_invalid_recipe(kwargs):
    with pytest.raises(ValueError):
        detect_vesselness(np.ones((12, 12, 12)), **kwargs)


@pytest.mark.parametrize("device", ["auto", "cpu"])
def test_detection_cli_works_with_cuda_masked(tmp_path, device):
    import os

    v = np.random.default_rng(8).random((8, 8, 8)).astype(np.float32)
    source, dest = tmp_path / "ct.npy", tmp_path / "nested" / "out.npy"
    np.save(source, v)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "vesuvius_autoresearch.fibers.cli",
            "--input",
            str(source),
            "--output",
            str(dest),
            "--device",
            device,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert "backend=cpu" in r.stdout
    np.testing.assert_allclose(np.load(dest), detect_vesselness(v), atol=1e-6)


def simple_gt():
    coords = np.stack([np.ones(5), np.ones(5), np.arange(1, 6)], axis=1)
    return Skeleton(
        [
            Fiber(
                1,
                "fiber",
                np.arange(5),
                coords,
                np.array([[0, 1], [1, 2], [2, 3], [3, 4]]),
            )
        ]
    )


@pytest.mark.parametrize(
    "instances",
    [
        np.full((3, 3, 8), -1),
        np.ones((3, 3, 8), dtype=float) * 1.5,
        np.ones((3, 3, 8), dtype=bool),
    ],
)
def test_scoring_rejects_invalid_instance_labels(instances):
    with pytest.raises(ValueError, match="instance"):
        score_tracing(simple_gt(), instances)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tolerance": -1},
        {"tolerance": float("nan")},
        {"step": 0},
        {"step": float("inf")},
    ],
)
def test_scoring_rejects_invalid_geometry(kwargs):
    with pytest.raises(ValueError):
        score_tracing(simple_gt(), np.ones((3, 3, 8), dtype=np.int32), **kwargs)


def test_score_is_independent_of_nml_edge_order_and_orientation():
    gt = simple_gt()
    inst = np.ones((3, 3, 8), dtype=np.int64)
    inst[:, :, 3:] = 2
    ref = score_tracing(gt, inst, tolerance=0).as_row()
    reordered = replace(gt.fibers[0], edges=gt.fibers[0].edges[[0, 2, 1, 3]][:, ::-1])
    assert score_tracing(Skeleton([reordered]), inst, tolerance=0).as_row() == ref


def prepare_model_files(path):
    path.mkdir()
    (path / "fold_0").mkdir()
    for name in ["plans.json", "dataset.json", "fold_0/checkpoint_final.pth"]:
        (path / name).write_bytes(b"model-v1")


def test_probability_cache_tracks_model_input_and_patch(tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    prepare_model_files(model_dir)
    calls = []
    monkeypatch.setattr(semantic, "load_model", lambda *a, **kw: toy_model())

    def predict(model, img, **kw):
        calls.append(kw)
        return np.full((4, *img.shape), 0.25, dtype=np.float32)

    monkeypatch.setattr(semantic, "predict_volume", predict)
    img = np.zeros((4, 4, 4))
    for patch in [4, 4, 8]:
        bench_cli._fiber_prob(tmp_path, "cube", img, model_dir, patch)
    assert len(calls) == 2, "same recipe should hit; changed patch must recompute"
    img[0, 0, 0] = 1
    bench_cli._fiber_prob(tmp_path, "cube", img, model_dir, 8)
    assert len(calls) == 3
    (model_dir / "fold_0/checkpoint_final.pth").write_bytes(b"model-v2")
    bench_cli._fiber_prob(tmp_path, "cube", img, model_dir, 8)
    assert len(calls) == 4
    (tmp_path / "cube_fiberprob.npy").write_bytes(b"interrupted")
    bench_cli._fiber_prob(tmp_path, "cube", img, model_dir, 8)
    assert len(calls) == 5


def test_unattested_legacy_cache_is_recomputed(tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    prepare_model_files(model_dir)
    np.save(tmp_path / "cube_fiberprob.npy", np.ones((4, 4, 4)))
    monkeypatch.setattr(semantic, "load_model", lambda *a, **kw: toy_model())
    monkeypatch.setattr(
        semantic,
        "predict_volume",
        lambda model, img, **kw: np.full((4, *img.shape), 0.25),
    )
    fp = bench_cli._fiber_prob(tmp_path, "cube", np.zeros((4, 4, 4)), model_dir, 4)
    np.testing.assert_allclose(fp, 0.75)


def test_fetch_requested_cube_cannot_match_another_scroll(tmp_path, monkeypatch):
    import io

    listing = b'<a href="fibers_s1_00497z_01497y_03997x_256_v1.nml">1</a><a href="fibers_s5_00497z_01497y_03997x_256_v1.nml">5</a>'
    urls = []

    def urlopen(url, **kw):
        urls.append(url)
        return io.BytesIO(listing if url.endswith("nml/") else b"payload")

    monkeypatch.setattr(bench_cli.urllib.request, "urlopen", urlopen)
    bench_cli.cmd_fetch(
        argparse.Namespace(data_dir=str(tmp_path), cube="s1_00497_01497_03997_256")
    )
    assert not any("s5" in url for url in urls)
    assert (tmp_path / "s1_00497_01497_03997_256.nml").exists()


@pytest.fixture
def model_bundle(tmp_path, monkeypatch):
    """A small saved network exercises the real plans/weights loader."""

    class BundleNetwork(torch.nn.Module):
        def __init__(self, **kwargs):
            super().__init__()
            self.encoder = torch.nn.Linear(1, 1)
            self.decoder = torch.nn.Module()
            self.decoder.seg_layers = torch.nn.ModuleList([torch.nn.Linear(1, 1)])

    network = BundleNetwork()
    cfg = {
        "patch_size": [4, 4, 4],
        "normalization_schemes": ["ZScoreNormalization"],
        "use_mask_for_norm": [False],
        "architecture": {
            "network_class_name": "test.Network",
            "arch_kwargs": {"strides": [[1, 1, 1], [2, 2, 2]]},
        },
    }
    dataset = {
        "channel_names": {"0": "CT"},
        "labels": {name: i for i, name in semantic.LABELS.items()},
    }
    (tmp_path / "fold_0").mkdir()
    ck = {
        "network_weights": network.state_dict(),
        "inference_allowed_mirroring_axes": [0, 2],
    }
    monkeypatch.setattr(semantic, "_import_by_path", lambda name: BundleNetwork)

    def save():
        (tmp_path / "plans.json").write_text(
            json.dumps({"configurations": {"3d_fullres": cfg}})
        )
        (tmp_path / "dataset.json").write_text(json.dumps(dataset))
        torch.save(ck, tmp_path / "fold_0/checkpoint_final.pth")

    save()
    return tmp_path, cfg, dataset, ck, save


def test_semantic_loads_recorded_contract_and_unused_deep_heads(model_bundle):
    path, cfg, dataset, ck, save = model_bundle
    ck["network_weights"]["decoder.seg_layers.1.weight"] = torch.ones((1, 1))
    ck["network_weights"]["decoder.seg_layers.1.bias"] = torch.ones(1)
    save()
    model = semantic.load_model(path, device="cpu")
    assert not model.network.training
    assert model.patch_divisibility == (2, 2, 2)
    assert model.mirror_axes == (0, 2)
    assert model.label_names == semantic.LABELS
    with pytest.raises(ValueError, match="divisible"):
        semantic.predict_volume(model, np.ones((4, 4, 4)), patch_size=(3, 4, 4))


@pytest.mark.parametrize(
    "setting",
    [
        "normalization",
        "mask",
        "channels",
        "labels",
        "patch",
        "mirror",
        "missing_weight",
        "bogus_head",
    ],
)
def test_semantic_rejects_unsupported_saved_contract(model_bundle, setting):
    path, cfg, dataset, ck, save = model_bundle
    if setting == "normalization":
        cfg["normalization_schemes"] = ["NoNormalization"]
    elif setting == "mask":
        cfg["use_mask_for_norm"] = [True]
    elif setting == "channels":
        dataset["channel_names"]["1"] = "extra"
    elif setting == "labels":
        dataset["labels"]["intersection"] = 7
    elif setting == "patch":
        cfg["patch_size"] = [3, 4, 4]
    elif setting == "mirror":
        ck["inference_allowed_mirroring_axes"] = [3]
    elif setting == "missing_weight":
        del ck["network_weights"]["encoder.weight"]
    elif setting == "bogus_head":
        ck["network_weights"]["decoder.seg_layers.0.bogus"] = torch.ones(1)
    save()
    with pytest.raises((ValueError, RuntimeError)):
        semantic.load_model(path, device="cpu")


def test_graph_scoring_keeps_disconnected_same_id_runs_separate():
    gt = simple_gt()
    # Two disjoint edges carrying the same id cannot form a length-2 run.
    gt.fibers[0].edges = np.array([[0, 1], [3, 4]])
    s = score_tracing(gt, np.ones((3, 3, 8), dtype=np.int32), tolerance=0)
    assert s.erl == 1
    assert s.splits == 1


def test_graph_scoring_preserves_branch_connectivity():
    coords = np.array([[2, 2, 2], [2, 2, 4], [2, 4, 2], [4, 2, 2]], dtype=float)
    f = Fiber(1, "branch", np.arange(4), coords, np.array([[0, 1], [0, 2], [0, 3]]))
    inst = np.ones((7, 7, 7), dtype=np.uint64) * (2**40 + 1)
    for edges in [f.edges, f.edges[::-1, ::-1]]:
        s = score_tracing(Skeleton([replace(f, edges=edges)]), inst, tolerance=0)
        assert s.erl == 6
        assert s.splits == 0
        assert s.n_pred_instances == 1


def test_graph_scoring_keeps_a_fiber_connected_through_a_zero_length_edge():
    # WEBKNOSSOS traces contain duplicate nodes joined by a zero-length edge (821 of
    # 87,469 edges in ScrollGT's fiber cubes). The fiber is still one line.
    coords = np.array([[1, 1, 1], [1, 1, 3], [1, 1, 3], [1, 1, 5]], dtype=float)
    f = Fiber(1, "dup", np.arange(4), coords, np.array([[0, 1], [1, 2], [2, 3]]))
    inst = np.ones((3, 3, 8), dtype=np.int64)
    for edges in [f.edges, f.edges[::-1], f.edges[:, ::-1]]:
        s = score_tracing(Skeleton([replace(f, edges=edges)]), inst, tolerance=0)
        assert s.erl == 4
        assert s.splits == 0


def test_cli_score_preserves_large_instance_ids(tmp_path, monkeypatch):
    inst = np.ones((3, 3, 8), dtype=np.uint64) * 2**32
    path = tmp_path / "instances.npy"
    np.save(path, inst)
    monkeypatch.setattr(
        bench_cli, "_load_cube", lambda *a: (np.zeros(inst.shape), simple_gt())
    )
    seen = []
    actual = score_tracing

    def capture_score(gt, labels, **kw):
        seen.append(labels.copy())
        return actual(gt, labels, **kw)

    monkeypatch.setattr(
        "vesuvius_autoresearch.fibers.eval_trace.score_tracing",
        capture_score,
    )
    bench_cli.main(["score", "--cube", "cube", "--instances", str(path)])
    np.testing.assert_array_equal(seen[0], inst)


@pytest.mark.parametrize("prior_context", ["same", "different", "legacy"])
def test_floor_refresh_carries_tracer_only_with_matching_provenance(
    tmp_path, monkeypatch, prior_context
):
    context = {
        "scoring_version": 2,
        "tolerance": 2,
        "mask_threshold": 0.5,
        "inference": "new",
    }
    prior = {
        "rows": {
            "tracer_strict_relink": score_tracing(
                simple_gt(), np.ones((3, 3, 8), dtype=np.int32)
            ).as_row()
        }
    }
    if prior_context != "legacy":
        prior["provenance"] = (
            context if prior_context == "same" else dict(context, tolerance=3)
        )
    output = tmp_path / "result.json"
    output.write_text(json.dumps({"cubes": {"cube": prior}}))
    monkeypatch.setattr(bench_cli, "CUBES", ["cube"])
    monkeypatch.setattr(
        bench_cli, "_load_cube", lambda *a: (np.zeros((3, 3, 8)), simple_gt())
    )
    monkeypatch.setattr(bench_cli, "_fiber_prob", lambda *a: np.ones((3, 3, 8)))
    monkeypatch.setattr(bench_cli, "_measurement_provenance", lambda *a: context)
    bench_cli.main(["floors", "--all-cubes", "--json-out", str(output)])
    result = json.loads(output.read_text())["cubes"]["cube"]
    assert ("tracer_strict_relink" in result["rows"]) == (prior_context == "same")
    assert result["provenance"] == context


def test_interrupted_fetch_never_publishes_partial_file(tmp_path, monkeypatch):
    import io

    class Interrupted(io.BytesIO):
        def read(self, *args):
            if self.tell():
                raise OSError("interrupted transfer")
            return super().read(3)

    listing = b'<a href="fibers_s1_00497z_01497y_03997x_256_v1.nml">1</a>'
    monkeypatch.setattr(
        bench_cli.urllib.request,
        "urlopen",
        lambda url, **kw: io.BytesIO(listing)
        if url.endswith("nml/")
        else Interrupted(b"partial"),
    )
    with pytest.raises(OSError, match="interrupted"):
        bench_cli.cmd_fetch(
            argparse.Namespace(data_dir=str(tmp_path), cube="s1_00497_01497_03997_256")
        )
    assert not list(tmp_path.iterdir())


def test_gpu_allocation_failure_is_not_silently_retried_on_cpu(monkeypatch):
    from types import SimpleNamespace

    from vesuvius_autoresearch.fibers import cli

    def fail(v):
        raise MemoryError("out of GPU memory")

    fake = SimpleNamespace(
        cuda=SimpleNamespace(
            runtime=SimpleNamespace(
                getDeviceCount=lambda: 1, CUDARuntimeError=RuntimeError
            )
        ),
        asarray=fail,
    )
    monkeypatch.setitem(sys.modules, "cupy", fake)
    with pytest.raises(MemoryError, match="GPU memory"):
        cli._backend(np.ones((3, 3, 3)), "auto")


@pytest.mark.parametrize(
    "prob", [np.zeros((4, 3, 3, 3)), np.full((4, 3, 3, 3), np.nan), np.ones((3, 3, 3))]
)
def test_fiber_probability_rejects_malformed_class_probabilities(prob):
    with pytest.raises(ValueError, match="probabilities"):
        semantic.fiber_probability(prob)


def test_score_report_keeps_requested_floor_and_source_identity(tmp_path, monkeypatch):
    img = np.zeros((3, 3, 8))
    inst = np.ones(img.shape, dtype=np.uint64) * (2**32 + 1)
    source = tmp_path / "instance.npy"
    np.save(source, inst)
    (tmp_path / "cube.nml").write_text("ground truth")
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: (img, simple_gt()))
    monkeypatch.setattr(bench_cli, "_fiber_prob", lambda *a: np.ones(img.shape))
    monkeypatch.setattr(
        bench_cli,
        "_measurement_provenance",
        lambda *a: {"scoring_version": 2, "source": "test"},
    )
    out = tmp_path / "nested" / "score.json"
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
                str(out),
            ]
        )
        == 0
    )
    record = json.loads(out.read_text())
    assert set(record["rows"]) == {"instance", "floor: connected components"}
    assert record["rows"]["instance"]["n_pred_instances"] == 1
    assert record["provenance"]["shape"] == list(img.shape)
    assert record["floor_provenance"]["scoring_version"] == 2


def test_atomic_report_failure_preserves_existing_file(tmp_path):
    from vesuvius_autoresearch.fibers.provenance import write_json

    dest = tmp_path / "result.json"
    dest.write_text('{"prior": true}\n')
    with pytest.raises(ValueError):
        write_json(dest, {"bad": float("nan")})
    assert dest.read_text() == '{"prior": true}\n'
    assert list(tmp_path.iterdir()) == [dest]


def test_model_change_during_inference_cannot_publish_cache(tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    prepare_model_files(model_dir)
    monkeypatch.setattr(semantic, "load_model", lambda *a, **kw: toy_model())

    def changed(model, img, **kw):
        (model_dir / "fold_0/checkpoint_final.pth").write_bytes(b"changed")
        return np.full((4, *img.shape), 0.25)

    monkeypatch.setattr(semantic, "predict_volume", changed)
    with pytest.raises(ValueError, match="changed during"):
        bench_cli._fiber_prob(tmp_path, "cube", np.zeros((4, 4, 4)), model_dir, 4)
    assert not list(tmp_path.glob("cube_fiberprob.*"))


@pytest.mark.parametrize(
    "flag,value",
    [
        ("--tolerance", "nan"),
        ("--mask-threshold", "2"),
        ("--patch", "0"),
        ("--tangent-window", "0"),
        ("--continue-threshold", "2"),
        ("--relink-angle", "nan"),
    ],
)
def test_bad_benchmark_options_fail_before_data_access(monkeypatch, flag, value):
    monkeypatch.setattr(
        bench_cli, "_load_cube", lambda *a: pytest.fail("invalid recipe accessed data")
    )
    with pytest.raises(SystemExit) as exc:
        bench_cli.main(["trace", "--cube", "cube", flag, value])
    assert exc.value.code == 2


def test_graph_scores_survive_node_permutation_with_asymmetric_mask():
    gt = simple_gt()
    inst = np.zeros((3, 3, 8), dtype=np.uint64)
    inst[1, 1, 1:3] = 2**40 + 1
    f = gt.fibers[0]
    order = np.array([2, 0, 4, 1, 3])
    inverse = np.argsort(order)
    other = replace(
        f,
        node_ids=f.node_ids[order],
        coords=f.coords[order],
        edges=inverse[f.edges[::-1, ::-1]],
    )
    assert (
        score_tracing(gt, inst, tolerance=0).as_row()
        == score_tracing(Skeleton([other]), inst, tolerance=0).as_row()
    )
