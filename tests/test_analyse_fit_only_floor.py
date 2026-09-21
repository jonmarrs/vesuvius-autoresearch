"""The fit-only floor rule, tested before any arm scored.

The property that matters most: a CV is never printed without its interval, and
a partial sample is refused. Both are structural answers to a pattern this
project has repeated three times.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyse_fit_only_floor.py"


def _fake(tmp: Path, det: dict, stock: dict) -> Path:
    for tag, v in stock.items():
        d = tmp / f"outer_{tag}" / "ink_metric"
        d.mkdir(parents=True)
        (d / "metrics.json").write_text(json.dumps({"summary": {"total_fg_pixels": v}}))
    for tag, v in det.items():
        i = tag.split("_s")[1]
        d = tmp / f"detfit_s{i}" / "ink_metric"
        d.mkdir(parents=True)
        (d / "metrics.json").write_text(json.dumps({"summary": {"total_fg_pixels": v}}))
    return tmp


def run(tmp: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--spiral-out", str(tmp)],
        capture_output=True,
        text=True,
    )


TAGS = [f"curbase_s{i}" for i in range(4, 10)]
BASE = 3_000_000


def test_partial_sample_is_refused(tmp_path):
    stock = {t: BASE for t in TAGS}
    det = {t: BASE for t in TAGS[:5]}  # five of six
    r = run(_fake(tmp_path, det, stock))
    assert r.returncode != 0
    assert "refused" in (r.stdout + r.stderr)


def test_cv_is_never_printed_without_its_interval(tmp_path):
    stock = {t: BASE for t in TAGS}
    det = {t: BASE * (1 + 0.01 * k) for k, t in enumerate(TAGS)}
    r = run(_fake(tmp_path, det, stock))
    assert r.returncode == 0, r.stderr
    for line in r.stdout.splitlines():
        if "CV" in line and re.search(r"\b0\.\d{4}\b", line):
            assert "95% CI" in line and "df=" in line, f"bare CV: {line!r}"


def test_bands_follow_the_registration(tmp_path):
    stock = {t: BASE for t in TAGS}
    tight = {t: BASE * (1 + 0.005 * k) for k, t in enumerate(TAGS)}  # CV ~0.9%
    loose = {t: BASE * (1 + 0.05 * k) for k, t in enumerate(TAGS)}  # CV ~8%
    assert "FLATTEN WAS MOST OF IT" in run(_fake(tmp_path / "a", tight, stock)).stdout
    assert "FIT RNG DOMINATES" in run(_fake(tmp_path / "b", loose, stock)).stdout


def test_thresholds_match_the_registration():
    assert "LO, HI = 0.030, 0.055" in SCRIPT.read_text()


def test_interval_arithmetic_is_chi_square():
    sys.path.insert(0, str(REPO / "scripts"))
    from analyse_fit_only_floor import cv_ci

    lo, hi = cv_ci(0.0742, 5)
    assert 0.046 < lo < 0.047 and 0.18 < hi < 0.183  # known df=5 values
