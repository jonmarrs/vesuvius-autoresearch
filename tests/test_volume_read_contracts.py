"""Requested inference preprocessing must produce real features or fail."""

import pickle
from collections import defaultdict
from types import SimpleNamespace

import numpy as np
import pytest
import torch
import zarr
from test_production_predict import production_fixture
from test_volume_inference_contracts import setup_prediction

from scripts import production_predict as production
from vesuvius_autoresearch.core import vesuvius_loader as loader


@pytest.fixture(autouse=True)
def cpu_ridges_and_fresh_warnings(monkeypatch):
    monkeypatch.setattr(loader, "_CUPY", None)
    monkeypatch.setattr(loader, "_WARNING_COUNTS", defaultdict(int))


def _volume(tmp_path, dtype="u1", value=128, **kwargs):
    path = tmp_path / "ct.zarr"
    array = zarr.open(
        str(path), mode="w", shape=(4, 8, 8), chunks=(2, 4, 4), dtype=dtype
    )
    array[:] = value
    return loader.FastVesuviusVolume(str(path), strict_reads=True, **kwargs)


@pytest.mark.parametrize("mode", ["single", "ensemble", "production"])
def test_inference_refuses_failed_ridges_before_model_execution(
    tmp_path, monkeypatch, mode
):
    if mode == "production":
        out, argv, model = production_fixture(tmp_path, monkeypatch)
        path = argv[argv.index("--checkpoint") + 1]
        checkpoint = torch.load(path, weights_only=False)
        checkpoint["config"]["use_ridges"] = True
        torch.save(checkpoint, path)
        calls = []

        def forward(x):
            calls.append(True)
            return torch.zeros((len(x), 1, 8, 8))

        monkeypatch.setattr(model, "forward", forward)
        runner = production.production_predict
    else:
        config = {"patch_size": 8, "num_layers": 2, "base_feat": 4, "use_ridges": True}
        runner, argv, models, _, _ = setup_prediction(
            tmp_path, monkeypatch, mode, [config]
        )
        out = tmp_path / "out"

    monkeypatch.setattr(loader, "_CUPY", None)
    monkeypatch.setattr(loader, "_WARNING_COUNTS", defaultdict(int))

    def broken(*args, **kwargs):
        raise np.linalg.LinAlgError("fixture ridge solver failure")

    monkeypatch.setattr(loader, "detect_ridges", broken)
    with pytest.raises(RuntimeError, match="ridge detection failed"):
        runner()
    assert not out.exists()
    if mode == "production":
        assert calls == []
    else:
        assert all(not model.inputs for model in models)


@pytest.mark.parametrize(
    "dtype,value,expected",
    [
        ("u1", 255, 1.0),
        ("<u2", 65535, 1.0),
        (">u2", 4096, 4096 / 65535),
        (">f4", 0.5, 0.5),
        ("f8", -2.5, -2.5),
    ],
)
def test_strict_readers_preserve_supported_ct_scaling(tmp_path, dtype, value, expected):
    volume = _volume(tmp_path, dtype, value)
    normalized = volume.read_ct(0, 0, 0, 4, 8, 8)
    assert normalized.dtype == np.float32
    np.testing.assert_allclose(normalized, expected, rtol=1e-6)
    torch.testing.assert_close(volume[0:4, 0:8, 0:8], torch.full((4, 8, 8), expected))
    raw = volume.get_raw_patch(0, 0, 0, 4, 8, 8)
    assert raw.isfinite().all() and raw.shape == (4, 8, 8)
    assert float(raw.flatten()[0]) == value


@pytest.mark.parametrize(
    "dtype,value", [("i2", 510), ("u4", 65535), ("bool", True), ("c8", 1j)]
)
def test_strict_readers_reject_unsupported_ct_encodings(
    tmp_path, monkeypatch, dtype, value
):
    volume = _volume(tmp_path)
    monkeypatch.setattr(
        volume.vol, "get_chunk", lambda *args: np.full((4, 8, 8), value, dtype=dtype)
    )
    with pytest.raises(ValueError, match="unsupported CT dtype"):
        volume.read_ct(0, 0, 0, 4, 8, 8)
    with pytest.raises(ValueError, match="unsupported CT dtype"):
        volume.get_raw_patch(0, 0, 0, 4, 8, 8)
    assert "ct_unknown_dtype" not in loader.warning_counts()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 1e300])
def test_strict_readers_reject_nonfinite_or_unrepresentable_ct(tmp_path, value):
    volume = _volume(tmp_path, "f8", value)
    with pytest.raises(ValueError, match="CT values must remain finite as float32"):
        volume.read_ct(0, 0, 0, 4, 8, 8)


@pytest.mark.parametrize("method", ["read_ct", "get_raw_patch"])
@pytest.mark.parametrize(
    "box",
    [
        (-1, 0, 0, 1, 8, 8),
        (0, 0, 0, 0, 8, 8),
        (0, 0, 0, 5, 8, 8),
        (0, 0, 0, 4, 8, 9),
        (0.0, 0, 0, 4, 8, 8),
        (False, 0, 0, 4, 8, 8),
    ],
)
def test_invalid_strict_requests_never_reach_the_backend(
    tmp_path, monkeypatch, method, box
):
    volume = _volume(tmp_path)
    monkeypatch.setattr(
        volume.vol,
        "get_chunk",
        lambda *args: pytest.fail("invalid request reached backend"),
    )
    with pytest.raises(ValueError, match="CT coordinates|CT request"):
        getattr(volume, method)(*box)


@pytest.mark.parametrize("method", ["read_ct", "get_raw_patch"])
def test_incomplete_backend_reads_are_not_accepted(tmp_path, monkeypatch, method):
    volume = _volume(tmp_path)
    monkeypatch.setattr(
        volume.vol, "get_chunk", lambda *args: np.zeros((3, 8, 8), np.uint8)
    )
    with pytest.raises(ValueError, match="CT read returned shape"):
        getattr(volume, method)(0, 0, 0, 4, 8, 8)


@pytest.mark.parametrize(
    "key",
    [
        (slice(None, 4), slice(0, 8), slice(0, 8)),
        (slice(0, 4, 2), slice(0, 8), slice(0, 8)),
        (slice(0, 4), 0, slice(0, 8)),
    ],
)
def test_strict_slices_cannot_silently_ignore_noncontiguous_indexing(tmp_path, key):
    volume = _volume(tmp_path)
    with pytest.raises(ValueError, match="explicit bounds and a unit step"):
        volume[key]


def test_strict_normalization_refuses_overflowing_model_inputs(tmp_path):
    volume = _volume(tmp_path)
    with pytest.raises(ValueError, match="normalized model input must be finite"):
        volume.normalize(torch.full((1,), 1e300, dtype=torch.float64))


@pytest.mark.parametrize("shape", [(0, 8, 8), (8, 8), (1, 4, 8, 8)])
def test_strict_volume_metadata_requires_nonempty_zyx(tmp_path, monkeypatch, shape):
    path = tmp_path / "bad.zarr"
    zarr.open(str(path), mode="w", shape=shape, dtype="u1")
    monkeypatch.setattr(
        loader, "FastLocalVolume", lambda *args: SimpleNamespace(shape=shape)
    )
    with pytest.raises(ValueError, match="nonempty Z/Y/X volume"):
        loader.FastVesuviusVolume(str(path), strict_reads=True)


@pytest.mark.parametrize("mode", ["single", "ensemble", "production"])
def test_inference_cannot_apply_the_legacy_unknown_dtype_scale(
    tmp_path, monkeypatch, mode
):
    if mode == "production":
        out, argv, model = production_fixture(tmp_path, monkeypatch)
        volume = argv[argv.index("--uri") + 1]
        shape = (5, 20, 24)
        runner = production.production_predict
    else:
        runner, _, _, volume, _ = setup_prediction(tmp_path, monkeypatch, mode)
        out, shape = tmp_path / "out", (6, 24, 24)
    zarr.open(str(volume), mode="w", shape=shape, dtype="i2")[:] = 128
    with pytest.raises(ValueError, match="unsupported CT dtype"):
        runner()
    assert not out.exists()


def test_legacy_unlabeled_state_keeps_the_permissive_read_policy(tmp_path, monkeypatch):
    volume = _volume(tmp_path)
    dataset = loader.VesuviusS3Dataset(volume.uri, patch_size=8, num_layers=4)
    del dataset.strict_reads

    def unavailable(*args):
        raise OSError("fixture volume unavailable")

    monkeypatch.setattr(dataset.volume.vol, "get_chunk", unavailable)
    patch, _ = dataset[0]
    assert patch.shape == (1, 4, 8, 8) and torch.all(patch == 0)


def test_strict_unlabeled_reads_refuse_unimplemented_flattening_before_io(monkeypatch):
    monkeypatch.setattr(
        loader,
        "FastVesuviusVolume",
        lambda *args, **kwargs: pytest.fail(
            "unsupported preprocessing reached volume I/O"
        ),
    )
    with pytest.raises(ValueError, match="Lasagna preprocessing is unavailable"):
        loader.VesuviusS3Dataset("unused", strict_reads=True, use_lasagna=True)


def test_strict_ridges_allow_a_working_cpu_fallback(tmp_path, monkeypatch):
    class GpuArray(np.ndarray):
        pass

    monkeypatch.setattr(
        loader,
        "_CUPY",
        SimpleNamespace(
            asarray=lambda a: np.asarray(a).view(GpuArray), asnumpy=np.asarray
        ),
    )
    calls = []

    def ridges(ct, sigma):
        calls.append(type(ct).__name__)
        if isinstance(ct, GpuArray):
            raise RuntimeError("fixture GPU solver failure")
        return np.full_like(ct, 0.375)

    monkeypatch.setattr(loader, "detect_ridges", ridges)
    patch = _volume(tmp_path, use_ridges=True)[0:4, 0:8, 0:8]
    assert calls == ["GpuArray", "ndarray"]
    assert torch.all(patch[1] == 0.375)
    assert loader.warning_counts() == {"ridge_gpu_fallback": 1}


def test_strict_policy_survives_pickling_and_legacy_states_remain_permissive(
    tmp_path, monkeypatch
):
    volume = _volume(tmp_path, use_ridges=True)
    strict = pickle.loads(pickle.dumps(volume))
    legacy_state = volume.__getstate__()
    legacy_state.pop("strict_reads")
    legacy = loader.FastVesuviusVolume.__new__(loader.FastVesuviusVolume)
    legacy.__setstate__(legacy_state)

    def broken(*args, **kwargs):
        raise RuntimeError("fixture ridge failure")

    monkeypatch.setattr(loader, "detect_ridges", broken)
    with pytest.raises(RuntimeError, match="ridge detection failed"):
        strict[0:4, 0:8, 0:8]
    assert legacy.strict_reads is False
    assert torch.all(legacy[0:4, 0:8, 0:8][1] == 0)


def test_unpickled_strict_volume_checks_the_source_it_reopens(tmp_path, monkeypatch):
    # A DataLoader worker unpickles the volume and reopens its source. A strict
    # volume must check that reopened source, not trust the pickled shape.
    pickled = pickle.dumps(_volume(tmp_path))
    smaller = zarr.open(
        str(tmp_path / "ct.zarr"), mode="w", shape=(2, 8, 8), chunks=(2, 4, 4)
    )
    smaller[:] = 128
    reopened = pickle.loads(pickled)
    assert reopened.shape == (2, 8, 8)
    with pytest.raises(ValueError, match="within volume shape"):
        reopened.read_ct(0, 0, 0, 4, 8, 8)

    monkeypatch.setattr(
        loader, "FastLocalVolume", lambda *args: SimpleNamespace(shape=(0, 8, 8))
    )
    with pytest.raises(ValueError, match="nonempty Z/Y/X volume"):
        pickle.loads(pickled)


@pytest.mark.parametrize("strict", [False, True])
def test_unlabeled_read_errors_obey_the_selected_policy(tmp_path, monkeypatch, strict):
    volume = _volume(tmp_path)
    dataset = loader.VesuviusS3Dataset(
        volume.uri, patch_size=8, num_layers=4, strict_reads=strict
    )
    assert dataset.volume.strict_reads is strict

    def unavailable(*args):
        raise OSError("fixture volume unavailable")

    monkeypatch.setattr(dataset.volume.vol, "get_chunk", unavailable)
    if strict:
        with pytest.raises(
            RuntimeError, match="failed to read unlabeled patch 0"
        ) as error:
            dataset[0]
        assert isinstance(error.value.__cause__, OSError)
        assert "s3_zero_patch" not in loader.warning_counts()
    else:
        patch, _ = dataset[0]
        assert patch.shape == (1, 4, 8, 8) and torch.all(patch == 0)
        assert loader.warning_counts()["s3_zero_patch"] == 1


@pytest.mark.parametrize(
    "bad",
    [
        torch.zeros((3, 8, 8)),
        torch.full((4, 8, 8), float("nan")),
        torch.zeros((4, 8, 8), dtype=torch.uint8),
    ],
)
def test_strict_unlabeled_samples_must_be_complete_finite_float_tensors(
    tmp_path, monkeypatch, bad
):
    class Volume:
        shape = (4, 8, 8)

        def __getitem__(self, key):
            return bad

    monkeypatch.setattr(loader, "FastVesuviusVolume", lambda *args, **kwargs: Volume())
    dataset = loader.VesuviusS3Dataset(
        "fixture", patch_size=8, num_layers=4, strict_reads=True
    )
    with pytest.raises(
        RuntimeError, match="unlabeled patch must be finite floating point"
    ):
        dataset[0]


@pytest.mark.parametrize(
    "factory",
    [
        loader.FastVesuviusVolume,
        loader.VesuviusS3Dataset,
        lambda uri, **kwargs: loader.VesuviusLabeledDataset(uri, "unused", **kwargs),
    ],
)
@pytest.mark.parametrize("flag", ["true", 1, None])
def test_strict_policy_is_an_explicit_boolean(factory, flag):
    with pytest.raises(ValueError, match="strict_reads must be a boolean"):
        factory("unused", strict_reads=flag)


def test_failed_preprocessing_preserves_the_previous_prediction_set(
    tmp_path, monkeypatch
):
    config = {"patch_size": 8, "num_layers": 2, "base_feat": 4, "use_ridges": True}
    runner, _, models, _, _ = setup_prediction(
        tmp_path, monkeypatch, "single", [config]
    )
    runner()
    out = tmp_path / "out"
    before = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    for model in models:
        model.inputs.clear()

    def broken(*args, **kwargs):
        raise RuntimeError("fixture preprocessing failure")

    monkeypatch.setattr(loader, "detect_ridges", broken)
    with pytest.raises(RuntimeError, match="ridge detection failed"):
        runner()
    assert {
        p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()
    } == before
    assert all(not model.inputs for model in models)
