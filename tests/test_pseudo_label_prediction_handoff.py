"""Exercise pseudo-label input checks with the real prediction producer layout."""

import json
from types import SimpleNamespace

import numpy as np
import pytest
import zarr

from scripts.inference.predict import save_vc3d_zarr, write_prediction_metadata
from scripts.labeling.generate_3d_ink_labels import generate_3d_ink_labels


@pytest.fixture
def prediction(tmp_path):
    ct = tmp_path / "ct volume.zarr"
    zarr.array(np.ones((7, 7, 7), np.float32), store=str(ct))
    return SimpleNamespace(
        ct=ct,
        predicted=tmp_path / "region_ink.zarr",
        canonical=tmp_path / "region_meta.json",
        legacy=tmp_path / "region_ink_meta.json",
        output=tmp_path / "labels.zarr",
    )


def produce(prediction, *, partial=False, file_uri=False):
    source = prediction.ct.as_uri() if file_uri else str(prediction.ct)
    save_vc3d_zarr(
        prediction.predicted,
        np.full((7, 7), 255, np.uint8),
        name="ink",
        source_uri=source,
        origin_xyz=[0, 0, 0],
    )
    args = SimpleNamespace(
        uri=source,
        x=0,
        y=0,
        z=0,
        width=7,
        height=7,
        patch_size=1,
        voxel_size_um=7.91,
        num_parts=2 if partial else 1,
        part_id=0,
        coverage_fraction=0.5 if partial else 1.0,
    )
    write_prediction_metadata(
        prediction.canonical,
        args,
        {},
        prediction.predicted,
        None,
        {"mean": 1.0, "max": 1.0},
    )
    return json.loads(prediction.canonical.read_text())


def generate(prediction, **settings):
    return generate_3d_ink_labels(
        str(prediction.ct),
        str(prediction.predicted),
        str(prediction.output),
        0,
        7,
        0,
        7,
        0,
        7,
        aligned_prediction=True,
        **settings,
    )


def record(prediction):
    return zarr.open(str(prediction.output), mode="r").attrs["ink_label_completion"][
        "alignment"
    ]["run_metadata"]


def test_partial_prediction_is_rejected_using_the_real_sidecar_name(prediction):
    produce(prediction, partial=True)
    with pytest.raises(ValueError, match="partial|coverage"):
        generate(prediction)
    assert not prediction.output.exists()


def test_complete_prediction_records_the_canonical_run_metadata(prediction):
    produce(prediction)
    generate(prediction)
    assert record(prediction)["path"] == str(prediction.canonical)
    assert record(prediction)["metadata"]["prediction_complete"] is True


def test_interrupted_producer_without_run_sidecar_is_not_caller_declared_complete(
    prediction,
):
    produce(prediction)
    prediction.canonical.unlink()
    with pytest.raises(ValueError, match="metadata"):
        generate(prediction)
    assert not prediction.output.exists()


@pytest.mark.parametrize("explicit", [False, True])
def test_a_different_complete_sidecar_cannot_hide_partial_canonical_metadata(
    prediction, explicit
):
    metadata = produce(prediction, partial=True)
    metadata.update(prediction_complete=True, num_parts=1, coverage_fraction=1.0)
    prediction.legacy.write_text(json.dumps(metadata))
    settings = {"prediction_metadata": str(prediction.legacy)} if explicit else {}
    with pytest.raises(ValueError, match="partial|coverage"):
        generate(prediction, **settings)
    assert not prediction.output.exists()


def test_invalid_legacy_metadata_is_not_hidden_by_explicit_complete_metadata(
    prediction,
):
    metadata = produce(prediction)
    metadata["prediction_complete"] = False
    prediction.legacy.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="partial|coverage"):
        generate(prediction, prediction_metadata=str(prediction.canonical))
    assert not prediction.output.exists()


def test_broken_canonical_sidecar_is_not_treated_as_missing(prediction):
    produce(prediction)
    prediction.canonical.unlink()
    prediction.canonical.symlink_to(prediction.ct.parent / "missing.json")
    with pytest.raises(ValueError, match="metadata|regular file"):
        generate(prediction)
    assert not prediction.output.exists()


def test_local_file_uri_from_the_real_producer_matches_the_ct_path(prediction):
    produce(prediction, file_uri=True)
    generate(prediction)
    assert record(prediction)["metadata"]["source_uri"] == prediction.ct.as_uri()


def test_custom_sidecar_can_complete_a_producer_without_the_canonical_sidecar(
    prediction,
):
    produce(prediction)
    custom = prediction.ct.parent / "custom.json"
    prediction.canonical.rename(custom)
    generate(prediction, prediction_metadata=str(custom))
    assert record(prediction)["path"] == str(custom)


@pytest.mark.parametrize(
    ("shape", "dtype"),
    [
        ((100_000, 100_000), np.float32),
        ((1, 100_000, 100_000), np.float32),
        ((7, 7), np.uint16),
        ((7, 7), np.complex64),
    ],
)
def test_invalid_prediction_geometry_or_dtype_fails_before_any_pixel_reads(
    prediction, monkeypatch, shape, dtype
):
    # Metadata-only sparse arrays model a wrong full-scroll prediction without
    # allocating it. Rejection must precede both CT and prediction payload reads.
    prediction.predicted = prediction.ct.parent / "external.zarr"
    zarr.create(
        shape=shape,
        chunks=tuple(min(64, n) for n in shape),
        dtype=dtype,
        store=str(prediction.predicted),
    )
    monkeypatch.setattr(
        zarr.Array,
        "__getitem__",
        lambda *a, **kw: pytest.fail("read pixels before metadata validation"),
    )
    with pytest.raises(ValueError, match="shape|probabilities"):
        generate(prediction)
    assert not prediction.output.exists()
