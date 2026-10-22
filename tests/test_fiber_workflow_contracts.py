"""Fiber inference and measurement boundaries, exercised without research data."""

import argparse
import inspect
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, replace

import numpy as np
import pytest
import torch

from vesuvius_autoresearch.fibers import (
    bench_cli,
    detection,
    eval_trace,
    semantic,
    trace as fiber_trace,
)
from vesuvius_autoresearch.fibers.detection import (
    detect_vesselness,
    detect_vesselness_tiled,
    fiber_direction,
    hessian,
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


def test_disconnected_same_id_pieces_are_separate_runs_but_not_a_split():
    """ScrollGT's definition (scoring version 4 here): each connected stretch is walked on its own.

    Two disjoint edges carrying one id cannot form a length-2 run. A gap between stretches is not
    something the tracer could have bridged, so it is not counted as a split. (Version 3 counted it.)
    """
    gt = simple_gt()
    gt.fibers[0].edges = np.array([[0, 1], [3, 4]])
    s = score_tracing(gt, np.ones((3, 3, 8), dtype=np.int32), tolerance=0)
    assert s.erl == 1
    assert sorted(s.run_lengths) == [1.0, 1.0]
    assert s.splits == 0


def test_a_branch_point_ends_a_stretch_under_the_scrollgt_definition():
    """At a branch the walk continues along the lowest-numbered neighbour, and the other arm is a new stretch.

    A three-armed star (arms of length 2) labelled with one id therefore scores runs of 4 and 2,
    ERL 20/6, not one run of 6 as version 3's graph components did. Which arm continues depends
    on node numbering. This is ScrollGT's documented residual: 31 branch nodes in its data move a
    score by up to 2.8% under renumbering. It is accepted here so the two projects share one
    definition.
    """
    coords = np.array([[2, 2, 2], [2, 2, 4], [2, 4, 2], [4, 2, 2]], dtype=float)
    f = Fiber(1, "branch", np.arange(4), coords, np.array([[0, 1], [0, 2], [0, 3]]))
    inst = np.ones((7, 7, 7), dtype=np.uint64) * (2**40 + 1)
    for edges in [f.edges, f.edges[::-1, ::-1]]:
        s = score_tracing(Skeleton([replace(f, edges=edges)]), inst, tolerance=0)
        assert sorted(s.run_lengths) == [2.0, 4.0]
        assert s.erl == pytest.approx(20 / 6)
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
        ("--detect-block", "-1"),
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


# docs/preregistration/2026-10-05_tracer_rescore.md, "Tracer": `bench_cli trace` at its published defaults.
# The registration names the flags; the rest are the defaults they ran with, unchanged since before the run.
PUBLISHED_TRACE = {
    "seed_percentile": 85.0,
    "continue_threshold": 0.5,
    "min_length": 15.0,
    "max_angle_deg": 25.0,
    "claim_radius": 3.5,
    "tangent_window": 1,
    "max_skip_steps": 0,
    "seed_nms_radius": 0.0,
    "seed_threshold": 0.5,  # unused: seed_percentile is set
    "step": 0.7,
    "max_steps": 4000,
    "seed_stride": 2,
}
PUBLISHED_RELINK = {
    "max_gap": 10.0,
    "max_link_angle_deg": 30.0,
    "max_tangent_angle_deg": 35.0,
    "endpoint_window": 4,
    "gap_weight": 1.0,
    "angle_weight": 0.15,
    "gap_fill_step": 0.7,
}
PUBLISHED_RECIPE = {
    "detect_block": 0,
    "orientation": {"source": "fiber_probability", "gauss_sigma": 2, "sigma": 3},
    "seed_response": {
        "filter": "vesselness",
        "gauss_sigma": 1,
        "sigma": 2,
        "normalization": "max",
    },
    "rasterization_radius": 1.0,
}


def _gapped_tubes():
    """Two straight fibers along x. The first has a 4-voxel gap that only relinking bridges."""
    n = 40
    z, y, _ = np.mgrid[:n, :n, :n].astype(float)
    fp = np.zeros((n, n, n))
    fibers = []
    for i, (cz, cy) in enumerate([(12, 12), (27, 26)]):
        tube = np.exp(-((z - cz) ** 2 + (y - cy) ** 2) / 4.5)
        if i == 0:
            tube[:, :, 19:23] = 0
        fp = np.maximum(fp, tube)
        xs = np.arange(2, n - 2, dtype=float)
        coords = np.stack([np.full_like(xs, cz), np.full_like(xs, cy), xs], axis=1)
        edges = np.stack([np.arange(len(xs) - 1), np.arange(1, len(xs))], axis=1)
        fibers.append(Fiber(i + 1, f"f{i}", np.arange(len(xs)), coords, edges))
    return fp, Skeleton(fibers)


@pytest.fixture
def bench_cube(tmp_path, monkeypatch):
    """Stub the gapped tubes in as `cube` and record each stage's arguments by name.

    `run(*flags)` runs `bench_cli trace` on it. Tracing and relinking also keep what they returned.
    """
    fp, gt = _gapped_tubes()
    # The CT is not the probability, so orientation read from it would show.
    img = np.full(fp.shape, 7, dtype=np.uint8)
    (tmp_path / "cube.nml").write_text("<things/>")
    (tmp_path / "cube_fiberprob.json").write_text(
        json.dumps({"inference": {"model": "m"}, "probability_sha256": "ab"})
    )
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: (img, gt))
    monkeypatch.setattr(bench_cli, "_fiber_prob", lambda *a: fp.copy())
    calls = defaultdict(list)

    def spy(module, name, keep_result=False):
        real = getattr(module, name)
        signature = inspect.signature(real)

        def wrapped(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            named = dict(bound.arguments)
            named.update(named.pop("kwargs", {}))
            calls[name].append(named)
            result = real(*args, **kwargs)
            if keep_result:
                named["returned"] = result
            return result

        monkeypatch.setattr(module, name, wrapped)

    for name in [
        "fiber_direction_tiled",
        "detect_vesselness",
        "detect_vesselness_tiled",
    ]:
        spy(detection, name)
    for name in ["trace_fibers", "relink_fragments"]:
        spy(fiber_trace, name, keep_result=True)
    spy(eval_trace, "score_tracing")

    def run(*extra):
        calls.clear()
        out, inst = tmp_path / "trace.json", tmp_path / "instances.npy"
        argv = ["--data-dir", str(tmp_path), "trace", "--cube", "cube"]
        argv += ["--json-out", str(out), "--save-instances", str(inst), *extra]
        assert bench_cli.main(argv) == 0
        return json.loads(out.read_text()), np.load(inst), defaultdict(list, calls)

    run.fp, run.gt, run.data_dir = fp, gt, tmp_path
    return run


def _ran_with(calls):
    (traced,) = calls["trace_fibers"]
    relinked = calls["relink_fragments"]
    return traced["params"], relinked[0]["params"] if relinked else None


def test_trace_defaults_are_the_published_configuration(bench_cube):
    record, _, calls = bench_cube()
    params, relink = _ran_with(calls)
    assert asdict(params) == record["trace_parameters"] == PUBLISHED_TRACE
    assert asdict(relink) == record["relink_parameters"] == PUBLISHED_RELINK
    assert record["tracing_recipe"] == PUBLISHED_RECIPE
    provenance = record["provenance"]
    assert (provenance["tolerance"], provenance["mask_threshold"]) == (2.0, 0.5)
    assert [c["tolerance"] for c in calls["score_tracing"]] == [2.0, 2.0]


def test_trace_runs_and_records_every_parameter_it_is_given(bench_cube):
    record, _, calls = bench_cube(
        *"--seed-percentile 80 --continue-threshold 0.45 --min-length 12 --max-angle 28".split(),
        *"--claim-radius 3 --tangent-window 5 --max-skip-steps 1 --seed-nms-radius 1.5".split(),
        *"--relink-gap 8 --relink-angle 35 --tolerance 3 --mask-threshold 0.4".split(),
    )
    params, relink = _ran_with(calls)
    given = {
        "seed_percentile": 80.0,
        "continue_threshold": 0.45,
        "min_length": 12.0,
        "max_angle_deg": 28.0,
        "claim_radius": 3.0,
        "tangent_window": 5,
        "max_skip_steps": 1,
        "seed_nms_radius": 1.5,
    }
    assert asdict(params) == record["trace_parameters"] == {**PUBLISHED_TRACE, **given}
    assert type(params.tangent_window) is type(params.max_skip_steps) is int
    links = {"max_gap": 8.0, "max_link_angle_deg": 35.0, "max_tangent_angle_deg": 40.0}
    assert (
        asdict(relink) == record["relink_parameters"] == {**PUBLISHED_RELINK, **links}
    )
    provenance = record["provenance"]
    assert (provenance["tolerance"], provenance["mask_threshold"]) == (3.0, 0.4)
    assert [c["tolerance"] for c in calls["score_tracing"]] == [3.0, 3.0]
    np.testing.assert_array_equal(
        calls["score_tracing"][1]["instances"],
        eval_trace.floor_connected_components(bench_cube.fp >= 0.4),
    )


@pytest.mark.parametrize("block", [0, 16])
def test_trace_runs_the_recipe_it_records(bench_cube, block):
    record, instances, calls = bench_cube("--detect-block", str(block))
    recipe = record["tracing_recipe"]
    assert recipe == {**PUBLISHED_RECIPE, "detect_block": block}
    orientation, seeding = recipe["orientation"], recipe["seed_response"]
    if block:
        (field,) = calls["fiber_direction_tiled"]
        (seed,) = calls["detect_vesselness_tiled"]
        assert field["block_size"] == seed["block_size"] == block
        np.testing.assert_array_equal(field["volume"], bench_cube.fp)
        assert (field["gauss_sigma"], field["sigma"]) == (2, 3)
    else:
        assert not calls["fiber_direction_tiled"]
        assert not calls["detect_vesselness_tiled"]
        (seed,) = calls["detect_vesselness"]
    np.testing.assert_array_equal(seed["volume"], bench_cube.fp)
    # The blocked filters equal the whole-volume ones exactly (tests/test_fiber_direction_tiled.py),
    # so both routes must hand the tracer what the recorded recipe computes on the probability.
    J, _ = hessian(
        bench_cube.fp.copy(), orientation["gauss_sigma"], orientation["sigma"]
    )
    directions, valid = fiber_direction(J)
    raw = np.asarray(
        detect_vesselness(
            bench_cube.fp.copy(),
            gauss_sigma=seeding["gauss_sigma"],
            sigma=seeding["sigma"],
        ),
        dtype=float,
    )
    (traced,) = calls["trace_fibers"]
    np.testing.assert_array_equal(traced["response"], bench_cube.fp)
    np.testing.assert_array_equal(traced["directions"], directions)
    np.testing.assert_array_equal(traced["valid"], valid)
    np.testing.assert_array_equal(traced["seed_response"], raw / raw.max())
    (relinked,) = calls["relink_fragments"]
    assert relinked["result"] is traced["returned"]
    radius = recipe["rasterization_radius"]
    np.testing.assert_array_equal(
        instances, relinked["returned"].to_instances(radius=radius)
    )


def test_blocked_detection_traces_the_same_labelling(bench_cube):
    dense, dense_instances, _ = bench_cube()
    blocked, blocked_instances, _ = bench_cube("--detect-block", "16")
    np.testing.assert_array_equal(dense_instances, blocked_instances)
    assert dense["rows"] == blocked["rows"]


def test_trace_saves_the_labelling_it_scored_and_relinks_only_when_asked(bench_cube):
    record, instances, calls = bench_cube()
    assert record["cube"] == "cube"
    (traced,) = calls["trace_fibers"]
    (relinked,) = calls["relink_fragments"]
    assert (
        record["stop_counts"]
        == relinked["returned"].stop_counts
        == traced["returned"].stop_counts
    )
    np.testing.assert_array_equal(calls["score_tracing"][0]["instances"], instances)
    tracer = record["rows"]["tracer"]
    assert tracer == score_tracing(bench_cube.gt, instances, tolerance=2.0).as_row()
    assert tracer["n_pred_instances"] == 2  # the gap is bridged
    unlinked, instances, calls = bench_cube("--no-relink")
    assert not calls["relink_fragments"]
    assert unlinked["relink_parameters"] is None
    (traced,) = calls["trace_fibers"]
    np.testing.assert_array_equal(
        instances, traced["returned"].to_instances(radius=1.0)
    )
    assert unlinked["rows"]["tracer"]["n_pred_instances"] == 3


def test_single_cube_floors_need_a_cube_and_record_the_floors_they_scored(bench_cube):
    out = bench_cube.data_dir / "floors.json"
    argv = ["--data-dir", str(bench_cube.data_dir), "floors", "--json-out", str(out)]
    assert bench_cli.main(argv) == 2
    assert not out.exists()
    argv += ["--cube", "cube", "--tolerance", "3", "--mask-threshold", "0.4"]
    assert bench_cli.main(argv) == 0
    record = json.loads(out.read_text())
    assert record["cube"] == "cube"
    provenance = record["provenance"]
    assert (provenance["tolerance"], provenance["mask_threshold"]) == (3.0, 0.4)
    assert list(record["rows"]) == [
        "oracle",
        "floor_single_instance",
        "floor_connected_components",
        "floor_voxel_instances",
        "floor_random_instances",
    ]
    components = eval_trace.floor_connected_components(bench_cube.fp >= 0.4)
    expected = score_tracing(bench_cube.gt, components, tolerance=3.0).as_row()
    assert record["rows"]["floor_connected_components"] == expected
