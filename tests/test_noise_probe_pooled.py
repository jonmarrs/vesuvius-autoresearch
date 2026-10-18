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


def _pair():
    return copy.deepcopy(FIRST), copy.deepcopy(SECOND)


def test_the_committed_batches_are_poolable():
    npp.poolable([FIRST, SECOND])


def test_a_batch_scored_on_another_validation_sample_is_refused():
    """f1_noise_probe.py checks one sample within a batch; pooling crosses batches."""
    first, second = _pair()
    second["runs"][2]["validation_diag"]["usable_patches"] = 96
    with pytest.raises(ValueError, match="sample counts or prevalence"):
        npp.poolable([first, second])
    first, second = _pair()
    second["runs"][0]["metrics"]["val_positive_rate"] = 0.15
    with pytest.raises(ValueError, match="sample counts or prevalence"):
        npp.poolable([first, second])


def test_a_batch_from_another_configuration_or_checkpoint_is_refused():
    first, second = _pair()
    second["config"]["lr"] = 2 * second["config"]["lr"]
    with pytest.raises(ValueError, match="configurations differ"):
        npp.poolable([first, second])
    first, second = _pair()
    (checkpoint,) = [k for k in second["input_hashes"] if k.endswith("best_model.pt")]
    second["input_hashes"][checkpoint] = "0" * 64
    with pytest.raises(ValueError, match="starting checkpoints or config files"):
        npp.poolable([first, second])


def test_a_training_code_difference_is_allowed():
    """The registration names the one train.py difference between the batches."""
    first, second = _pair()
    (runner,) = [k for k in second["input_hashes"] if k.endswith("run_noise_probe.py")]
    second["input_hashes"][runner] = "0" * 64
    npp.poolable([first, second])


def test_a_repeated_sampling_seed_is_refused():
    first, second = _pair()
    second["runs"][1]["train_sampling_seed"] = first["runs"][0]["train_sampling_seed"]
    with pytest.raises(ValueError, match="seed repeats"):
        npp.poolable([first, second])


def test_the_finished_trials_of_a_failed_batch_still_pool():
    """Registered: a failed trial is reported and not replaced; the rest count."""
    first, second = _pair()
    second["status"] = "FAILED"
    second["runs"][3]["status"] = "FAILED"
    npp.poolable([first, second])
    batches = [npp.completed(first), npp.completed(second)]
    assert npp.analyse(batches, 0.249348, 0.01)["pooled"]["n"] == 7


def test_only_two_batches_are_pooled():
    first, second = _pair()
    with pytest.raises(ValueError, match="compares two"):
        npp.poolable([first, second, copy.deepcopy(second)])
    with pytest.raises(ValueError, match="pools two"):
        npp.analyse([npp.completed(first)] * 3, 0.249348, 0.01)


def test_a_first_batch_without_an_sd_is_insufficient():
    batches = [
        npp.completed(_probe([0.265])),
        npp.completed(_probe([0.26, 0.265, 0.27])),
    ]
    assert npp.analyse(batches, 0.249348, 0.01)["status"] == "INSUFFICIENT"


def test_the_command_line_refuses_batches_that_do_not_pool(tmp_path, monkeypatch):
    first, second = _pair()
    second["config"]["lr"] = 2 * second["config"]["lr"]
    paths = []
    for name, probe in (("a.json", first), ("b.json", second)):
        (tmp_path / name).write_text(json.dumps(probe))
        paths += ["--batch", str(tmp_path / name)]
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["noise_probe_pooled.py", *paths, "--incumbent", "0.249348"]
        + ["--tolerance", "0.01", "--out", str(out)],
    )
    with pytest.raises(ValueError, match="configurations differ"):
        npp.main()
    assert not out.exists()


def test_the_lift_gate_is_the_loops():
    sys.path.insert(0, str(ROOT / "scripts" / "training"))
    from train import LIFT_MARGIN

    assert npp.LIFT_GATE == 1 + LIFT_MARGIN
