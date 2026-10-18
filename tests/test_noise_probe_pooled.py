"""scripts/noise_probe_pooled.py: the registered analysis of the pooled v3 noise probe."""

from __future__ import annotations

import copy
import json
import math
import statistics
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import noise_probe_pooled as npp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIRST = json.loads((ROOT / "reports/noise_probe_v3_2026-10-16.json").read_text())


def _probe(f1s, lift=1.2, status="COMPLETE", protocol=npp.PROTOCOL):
    return {
        "protocol": protocol,
        "runs": [
            {
                "status": status,
                "train_sampling_seed": i,
                "metrics": {"val_f1": v, "ap_prevalence_lift": lift},
            }
            for i, v in enumerate(f1s)
        ],
    }


def test_the_interval_reproduces_the_first_probes():
    # reports/noise_probe_v3_2026-10-16.md: SD 0.0025 over 4 trials, 95% CI 0.0014-0.0094.
    lo, hi = npp.sigma_interval(FIRST["f1_spread"]["sample_std"], 3)
    assert (round(lo, 4), round(hi, 4)) == (0.0014, 0.0094)


def test_the_interval_at_df_7():
    lo, hi = npp.sigma_interval(1.0, 7)
    assert lo == pytest.approx(math.sqrt(7 / 16.0128), rel=1e-4)
    assert hi == pytest.approx(math.sqrt(7 / 1.68987), rel=1e-4)


def test_false_promotion_rates_quoted_in_106():
    assert npp.false_promotion(0.01, 0.0025) == pytest.approx(0.0023, abs=1e-4)
    assert npp.false_promotion(0.01, 0.0043) == pytest.approx(0.050, abs=1e-3)
    assert npp.false_promotion(0.01, 0.0094) == pytest.approx(0.226, abs=1e-3)


def test_july_tolerance_on_the_first_probe():
    assert f"{npp.july_tolerance(FIRST['f1_spread']['sample_std']):.4f}" == "0.0059"


def test_only_completed_trials_of_the_protocol_count():
    probe = _probe([0.26, 0.27])
    probe["runs"][1]["status"] = "FAILED"
    assert [t["val_f1"] for t in npp.completed(probe)] == [0.26]
    with pytest.raises(ValueError):
        npp.completed(_probe([0.26], protocol="seeded-sample-400-v2"))


def test_fewer_than_three_new_trials_is_insufficient():
    batches = [
        npp.completed(_probe([0.26, 0.265, 0.27, 0.268])),
        npp.completed(_probe([0.26, 0.27])),
    ]
    assert npp.analyse(batches, 0.249348, 0.01)["status"] == "INSUFFICIENT"


def test_no_shift_leads_with_the_pooled_sd():
    a, b = [0.262, 0.265, 0.267, 0.264], [0.263, 0.266, 0.264, 0.267]
    r = npp.analyse(
        [npp.completed(_probe(a)), npp.completed(_probe(b))], 0.249348, 0.01
    )
    assert r["status"] == "OK" and not r["shift"]["shifted"]
    assert r["lead"]["estimate"] == "pooled" and r["lead"]["df"] == 7
    assert r["lead"]["sd"] == pytest.approx(statistics.stdev(a + b))
    assert r["false_promotion"]["point"] == pytest.approx(
        npp.false_promotion(0.01, statistics.stdev(a + b))
    )


def test_a_shift_between_batches_leads_with_the_within_batch_sd():
    a, b = [0.262, 0.265, 0.267, 0.264], [0.282, 0.285, 0.287, 0.284]
    r = npp.analyse(
        [npp.completed(_probe(a)), npp.completed(_probe(b))], 0.249348, 0.01
    )
    assert r["shift"]["shifted"] and r["lead"]["estimate"] == "within_batch"
    assert r["lead"]["df"] == 6
    within = math.sqrt((statistics.variance(a) + statistics.variance(b)) / 2)
    assert r["lead"]["sd"] == pytest.approx(within)
    assert r["pooled"]["sd"] > 3 * within  # the shift inflates the pooled SD


def test_predictions():
    a = [0.2669, 0.2665, 0.2615, 0.2639]  # the first probe's val_f1, 4 d.p.
    ok = npp.analyse(
        [npp.completed(_probe(a)), npp.completed(_probe([0.264, 0.266, 0.263, 0.265]))],
        0.249348,
        0.01,
    )
    assert all(ok["predictions"].values())
    far = npp.analyse(
        [
            npp.completed(_probe(a)),
            npp.completed(_probe([0.264, 0.266, 0.263, 0.2765])),
        ],
        0.249348,
        0.01,
    )
    assert not far["predictions"]["P1_within_3sd_of_batch_1"]
    low = npp.analyse(
        [
            npp.completed(_probe(a)),
            npp.completed(_probe([0.264, 0.266, 0.263, 0.2590])),
        ],
        0.249348,
        0.01,
    )
    assert not low["predictions"]["P2_all_would_promote"]
    flat = npp.analyse(
        [
            npp.completed(_probe(a)),
            npp.completed(_probe([0.264, 0.266, 0.263], lift=1.02)),
        ],
        0.249348,
        0.01,
    )
    assert not flat["predictions"]["P2_all_would_promote"]
    wide = npp.analyse(
        [npp.completed(_probe(a)), npp.completed(_probe([0.255, 0.272, 0.258, 0.271]))],
        0.249348,
        0.01,
    )
    assert not wide["predictions"]["P3_pooled_sd_at_most_0.0043"]


SECOND = json.loads((ROOT / "reports/noise_probe_v3_2026-10-17.json").read_text())
TRAIN = "scripts/training/train.py"
RUNNER = "scripts/training/run_noise_probe.py"


def _pair():
    return copy.deepcopy(FIRST), copy.deepcopy(SECOND)


def _hash_key(probe, suffix):
    (key,) = [k for k in probe["input_hashes"] if k.endswith(suffix)]
    return key


def test_the_committed_batches_pool_with_their_registered_code_difference():
    assert npp.poolable([FIRST, SECOND], allow_code={TRAIN}) == [TRAIN]
    with pytest.raises(ValueError, match="train.py differs"):
        npp.poolable([FIRST, SECOND])


@pytest.mark.parametrize(
    "field,value", [("inputs_sha256", "0" * 64), ("usable_patches", 96)]
)
def test_a_consistent_batch_on_another_validation_sample_is_refused(field, value):
    """Every batch-2 trial agrees with the others, so f1_noise_probe.py passes the
    batch; only the comparison across batches finds the other sample."""
    first, second = _pair()
    for run in second["runs"]:
        run["validation_diag"][field] = value
    with pytest.raises(ValueError, match="sample counts or prevalence"):
        npp.poolable([first, second], allow_code={TRAIN})


def test_a_consistent_batch_at_another_prevalence_is_refused():
    first, second = _pair()
    for run in second["runs"]:
        run["metrics"]["val_positive_rate"] = 0.15
    with pytest.raises(ValueError, match="sample counts or prevalence"):
        npp.poolable([first, second], allow_code={TRAIN})


@pytest.mark.parametrize("missing", ["validation_diag", "inputs_sha256", "prevalence"])
def test_trials_that_do_not_record_their_sample_are_refused(missing):
    """Missing on every trial would otherwise compare equal."""
    first, second = _pair()
    for run in first["runs"] + second["runs"]:
        if missing == "validation_diag":
            del run["validation_diag"]
        elif missing == "inputs_sha256":
            run["validation_diag"]["inputs_sha256"] = ""
        else:
            del run["metrics"]["val_positive_rate"]
    with pytest.raises(ValueError, match="does not record its validation sample"):
        npp.poolable([first, second], allow_code={TRAIN})


def test_a_batch_from_another_configuration_is_refused():
    first, second = _pair()
    second["config"]["lr"] = 2 * second["config"]["lr"]
    with pytest.raises(ValueError, match="configurations differ"):
        npp.poolable([first, second], allow_code={TRAIN})


@pytest.mark.parametrize("name", ["best_model.pt", "config.json"])
def test_another_checkpoint_or_config_file_is_refused(name):
    first, second = _pair()
    second["input_hashes"][_hash_key(second, name)] = "0" * 64
    with pytest.raises(ValueError, match="starting checkpoints or config files"):
        npp.poolable([first, second], allow_code={TRAIN})


def test_a_missing_checkpoint_hash_is_refused():
    first, second = _pair()
    for probe in (first, second):
        del probe["input_hashes"][_hash_key(probe, "best_model.pt")]
    with pytest.raises(ValueError, match="a hash is missing"):
        npp.poolable([first, second], allow_code={TRAIN})


def test_a_code_difference_pools_only_when_named():
    """The registration names the train.py difference; any other needs its own name."""
    first, second = _pair()
    second["input_hashes"][_hash_key(second, RUNNER)] = "0" * 64
    with pytest.raises(ValueError, match="run_noise_probe.py differs"):
        npp.poolable([first, second], allow_code={TRAIN})
    assert npp.poolable([first, second], allow_code={TRAIN, RUNNER}) == [RUNNER, TRAIN]
    del second["input_hashes"][_hash_key(second, TRAIN)]
    with pytest.raises(ValueError, match="no hash for scripts/training/train.py"):
        npp.poolable([first, second], allow_code={TRAIN, RUNNER})


def test_another_scope_or_contract_is_refused():
    first, second = _pair()
    second["scope"] = "something_else"
    with pytest.raises(ValueError, match="repeatability probe"):
        npp.poolable([first, second], allow_code={TRAIN})
    first, second = _pair()
    second["contract"] = 2
    with pytest.raises(ValueError, match="contracts differ"):
        npp.poolable([first, second], allow_code={TRAIN})


def test_a_repeated_sampling_seed_is_refused():
    first, second = _pair()
    second["runs"][1]["train_sampling_seed"] = first["runs"][0]["train_sampling_seed"]
    with pytest.raises(ValueError, match="seed repeats"):
        npp.poolable([first, second], allow_code={TRAIN})


def test_the_finished_trials_of_a_failed_batch_still_pool():
    """Registered: a failed trial is reported and not replaced; the rest count.
    A failed record, as f1_noise_probe.py writes one, has no metrics or sample."""
    first, second = _pair()
    second["status"] = "FAILED"
    second["runs"][3] = {
        "run": 4,
        "directory": "run_04",
        "status": "FAILED",
        "returncode": 1,
        "error": "ValueError: trainer exited 1; emitted scores are ineligible",
        "seconds": 3.0,
    }
    npp.poolable([first, second], allow_code={TRAIN})
    batches = [npp.completed(first), npp.completed(second)]
    assert npp.analyse(batches, 0.249348, 0.01)["pooled"]["n"] == 7


def test_only_two_batches_are_pooled():
    first, second = _pair()
    with pytest.raises(ValueError, match="expected two batches, got 3"):
        npp.poolable([first, second, copy.deepcopy(second)], allow_code={TRAIN})
    with pytest.raises(ValueError, match="pools two"):
        npp.analyse([npp.completed(first)] * 3, 0.249348, 0.01)


def test_a_first_batch_without_an_sd_is_insufficient():
    batches = [
        npp.completed(_probe([0.265])),
        npp.completed(_probe([0.26, 0.265, 0.27])),
    ]
    assert npp.analyse(batches, 0.249348, 0.01)["status"] == "INSUFFICIENT"


def _main(tmp_path, monkeypatch, probes, *extra):
    paths = []
    for name, probe in zip(("a.json", "b.json"), probes, strict=True):
        (tmp_path / name).write_text(json.dumps(probe))
        paths += ["--batch", str(tmp_path / name)]
    out = tmp_path / "out.json"
    argv = [*paths, "--incumbent", "0.249348", "--tolerance", "0.01", "--out", str(out)]
    monkeypatch.setattr(sys, "argv", ["noise_probe_pooled.py", *argv, *extra])
    return npp.main(), out


def test_the_command_line_refuses_batches_that_do_not_pool(
    tmp_path, monkeypatch, capsys
):
    first, second = _pair()
    second["config"]["lr"] = 2 * second["config"]["lr"]
    with pytest.raises(SystemExit) as exit_:
        _main(tmp_path, monkeypatch, (first, second), "--allow-code-change", TRAIN)
    assert exit_.value.code == 2
    assert "configurations differ" in capsys.readouterr().err
    assert not (tmp_path / "out.json").exists()


def test_the_command_line_reproduces_the_committed_result(tmp_path, monkeypatch):
    status, out = _main(tmp_path, monkeypatch, _pair(), "--allow-code-change", TRAIN)
    result = json.loads(out.read_text())
    committed = json.loads(
        (ROOT / "reports/noise_probe_v3_pooled_2026-10-17.json").read_text()
    )
    assert status == 0
    assert {k: v for k, v in result.items() if k != "sources"} == {
        k: v for k, v in committed.items() if k != "sources"
    }


def test_the_lift_gate_is_the_loops():
    from scripts.training.train import LIFT_MARGIN

    assert pytest.approx(1 + LIFT_MARGIN) == npp.LIFT_GATE


def test_code_inputs_are_matched_on_a_path_boundary():
    assert (
        npp._code_input("/w/vesuvius-autoresearch/scripts/training/train.py") == TRAIN
    )
    assert npp._code_input(TRAIN) == TRAIN
    assert npp._code_input("/w/oldscripts/training/train.py") is None
    assert npp._code_input("/w/local_data/best_model.pt") is None
