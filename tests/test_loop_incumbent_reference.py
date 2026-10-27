"""Saved-reference identity, rounding bounds, and separation from the live window."""

import hashlib
import importlib.util
import io
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "loop_incumbent_reference", ROOT / "scripts/loop_incumbent_reference.py"
)
reference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reference)


def _checkpoint(**updates):
    saved = {
        "config": {"val_uri": "local_data/PHercParis2Fr143/surface_volume.zarr"},
        "val_protocol": "seeded-sample-400-v3+z1-27",
        "validation_diag": {
            "protocol": "seeded-sample-400-v3+z1-27",
            "complete": True,
            "requested_patches": 400,
            "scored_patches": 400,
            "batch_errors": 0,
        },
        "val_f1": np.float64(0.25),
        "roc_auc": 0.5742016897,
        "ap_prevalence_lift": 1.169277,
        "model_state_dict": {"unused": torch.ones(1)},
        **updates,
    }
    stream = io.BytesIO()
    torch.save(saved, stream)
    return stream.getvalue()


def _record():
    rows = [
        {
            "start": f"2026-10-24T10:0{i}:00",
            "incumbent": 0.25,
            "val_f1": 0.26,
            "roc_auc": auc,
            "ap_lift": 1.2,
            "tweak": tweak,
        }
        for i, (auc, tweak) in enumerate(
            [
                (0.5743, "aug_mode_batchgeneratorsv2"),
                (0.5742, "aug_mode_batchgeneratorsv2"),
                (0.5741, "other"),
            ]
        )
    ]
    return {"incumbent": 0.25, "rows": rows}


def test_metadata_uses_captured_bytes_and_does_not_construct_a_model():
    raw = _checkpoint()
    before = torch.serialization.get_safe_globals().copy()
    got = reference.checkpoint_metadata(raw)
    assert got["metrics"]["val_f1"] == 0.25
    assert got["sha256"] == hashlib.sha256(raw).hexdigest()
    assert "model_state_dict" not in got
    assert set(torch.serialization.get_safe_globals()) == set(before)


@pytest.mark.parametrize(
    "updates",
    [
        {"val_protocol": "another-sample"},
        {
            "validation_diag": {
                "protocol": "seeded-sample-400-v3+z1-27",
                "complete": False,
            }
        },
        {"roc_auc": float("nan")},
    ],
)
def test_unusable_saved_measurement_is_refused(updates):
    with pytest.raises(ValueError):
        reference.checkpoint_metadata(_checkpoint(**updates))


def test_logged_rounding_is_not_counted_as_an_exact_win_or_loss():
    got = reference.compare(_record(), reference.checkpoint_metadata(_checkpoint()))
    auc = got["groups"]["all_cycles"]["metrics"]["roc_auc"]
    assert (
        auc["definitely_above"],
        auc["definitely_below"],
        auc["rounding_overlap"],
    ) == (1, 1, 1)


@pytest.mark.parametrize(
    "change", ["record_incumbent", "cycle_incumbent", "window", "nonfinite"]
)
def test_another_incumbent_or_live_window_is_refused(change):
    record = _record()
    if change == "record_incumbent":
        record["incumbent"] = 0.24
    elif change == "cycle_incumbent":
        record["rows"][0]["incumbent"] = 0.24
    elif change == "window":
        record["rows"][0]["start"] = reference.REGISTERED["since"]
    else:
        record["rows"][0]["roc_auc"] = float("inf")
    with pytest.raises(ValueError):
        reference.compare(record, reference.checkpoint_metadata(_checkpoint()))


def test_output_cannot_overwrite_the_checkpoint_or_cycle_record(tmp_path):
    checkpoint, record = tmp_path / "model.pt", tmp_path / "cycles.json"
    checkpoint.write_bytes(_checkpoint())
    record.write_text(json.dumps(_record()))
    original = checkpoint.read_bytes(), record.read_bytes()
    for output in (checkpoint, record):
        with pytest.raises(ValueError, match="must not replace"):
            reference.main(
                [
                    "--checkpoint",
                    str(checkpoint),
                    "--record",
                    str(record),
                    "--out",
                    str(output),
                ]
            )
    assert (checkpoint.read_bytes(), record.read_bytes()) == original


def test_published_reference_regenerates_from_the_committed_inputs(
    tmp_path, monkeypatch
):
    # The live incumbent advances. Reproduce this historical record from its
    # recorded immutable blob, keeping the original relative source paths.
    published = ROOT / "reports/loop_incumbent_reference_2026-10-27.json"
    blob = json.loads(published.read_text())["reference"]["git_blob_sha1"]
    saved = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "blob", blob],
        capture_output=True,
        check=False,
    )
    if saved.returncode:
        pytest.skip("the historical checkpoint blob is absent from this checkout")
    (tmp_path / "best_model.pt").write_bytes(saved.stdout)
    source = Path("reports/loop_tweak_replication_2026-10-25.json")
    (tmp_path / source.parent).mkdir()
    (tmp_path / source).write_bytes((ROOT / source).read_bytes())
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "reference.json"
    reference.main(
        [
            "--checkpoint",
            "best_model.pt",
            "--record",
            "reports/loop_tweak_replication_2026-10-25.json",
            "--out",
            str(output),
        ]
    )
    assert output.read_bytes() == published.read_bytes()
    record = json.loads(output.read_text())
    assert (
        record["reference"]["git_blob_sha1"]
        == "932dbb4614a9ba89711761688bf4d0482ced932c"
    )
    assert (
        record["reference"]["sha256"]
        == "6e06598b941bdb6588ccc39499bcaee181decd060a2ab8c8385b426cf01b225a"
    )
    assert (
        record["cycles"] == 546 and record["last_start"] < reference.REGISTERED["since"]
    )
    auc = record["groups"]["batchgeneratorsv2"]["metrics"]["roc_auc"]
    assert (
        auc["definitely_above"],
        auc["definitely_below"],
        auc["rounding_overlap"],
    ) == (25, 1, 0)
