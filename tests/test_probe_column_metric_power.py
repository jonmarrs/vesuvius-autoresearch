"""Tests for the column-metric power calibration.

The result exonerates a metric we publish, which is the direction that earns the
most scepticism. So the tests pin the two ways a favourable answer could be
manufactured: injecting into the wrong place and getting a fake failure, or
injecting into a background so benign that anything would be detected.
"""

import json
import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import probe_column_metric_power as mod  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

needs_target = pytest.mark.skipif(
    not os.path.isdir(mod.TARGET), reason="scrollgt column target not present"
)
ARTIFACT = os.path.join(_REPO, "reports", "column_metric_power.txt")


@needs_target
def test_the_indicator_reads_the_field_the_scorer_reads():
    """The bug caught before the run. The scorer keys on `transcription`; an
    earlier version of the indicator keyed on `status`, which does not exist in
    the file, so it would have injected nothing, raised no error, and reported a
    fake 'blunt metric' verdict."""
    cols = json.load(open(os.path.join(mod.TARGET, "columns.json")))
    entries = cols["columns"]
    assert all("transcription" in c for c in entries)
    assert not any("status" in c for c in entries)
    ind = mod.column_indicator(cols, (64, 30097))
    assert ind.max() == 1.0, "the indicator selected no columns"
    assert 0.4 < float(ind[0].mean()) < 0.9, (
        "text columns should cover much of the grid"
    )


def test_the_noise_is_correlated_not_white():
    """A white background would average away inside a region of thousands of
    pixels and make any metric look sensitive. The calibration is only honest if
    the background is as correlated as a real detector's errors."""
    rng = np.random.default_rng(0)
    f = mod.correlated_noise((256, 2048), rng)
    lag1 = float(np.corrcoef(f[:, :-1].ravel(), f[:, 1:].ravel())[0, 1])
    assert lag1 > 0.9, (
        f"background lag-1 {lag1:.3f} is not smooth enough to be realistic"
    )


def test_zero_amplitude_sits_at_chance():
    """The null. If injecting nothing scored above chance, the sweep would be
    measuring something other than the injected signal."""
    text = open(ARTIFACT).read()
    line = next(ln for ln in text.splitlines() if ln.strip().startswith("0.000"))
    auc = float(line.split()[1])
    assert 0.4 < auc < 0.6


def test_the_metric_saturates_rather_than_creeping():
    """What makes the verdict safe: the response is a step, not a slow climb, so
    the first-crossing amplitude is not an artifact of where the threshold was
    put."""
    text = open(ARTIFACT).read()
    vals = {}
    for ln in text.splitlines():
        p = ln.split()
        if len(p) >= 2 and p[0].replace(".", "").isdigit():
            try:
                vals[float(p[0])] = float(p[1])
            except ValueError:
                continue
    assert vals[0.5] > 0.99
    assert vals[4.0] == pytest.approx(1.0)


def test_the_artifact_states_what_it_does_not_settle():
    """The registration is a separate question with separate evidence, and the
    artifact must not be read as clearing it."""
    text = open(ARTIFACT).read()
    assert "says nothing about whether the column registration is correct" in text
