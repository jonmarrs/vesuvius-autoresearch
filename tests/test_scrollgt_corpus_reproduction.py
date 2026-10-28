"""The CPU corpus check enforces its budget and retains failed commands."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "repro/fibers/verify_scrollgt_cc_corpus.py"
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux resource measurements"
)


def test_each_measurement_enforces_the_real_child_address_space_budget(tmp_path):
    log, measurement = tmp_path / "stdout.log", tmp_path / "measurement.json"
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "command": [
                    sys.executable,
                    "-c",
                    "import json,resource; print(json.dumps(resource.getrlimit(resource.RLIMIT_AS)))",
                ],
                "cwd": str(tmp_path),
                "log": str(log),
                "measurement": str(measurement),
            }
        )
    )
    subprocess.run(
        [sys.executable, str(HARNESS), "--measure", str(request)], check=True
    )
    assert json.loads(log.read_text()) == [7 * 1024**3] * 2
    observed = json.loads(measurement.read_text())
    assert observed["returncode"] == 0 and observed["error"] is None
    assert observed["peak_rss_kib"] > 0


def test_a_failed_cli_keeps_its_exit_code_and_log(tmp_path):
    log, measurement = tmp_path / "stdout.log", tmp_path / "measurement.json"
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "command": [
                    sys.executable,
                    "-c",
                    "print('measurement failed'); raise SystemExit(17)",
                ],
                "cwd": str(tmp_path),
                "log": str(log),
                "measurement": str(measurement),
            }
        )
    )
    subprocess.run(
        [sys.executable, str(HARNESS), "--measure", str(request)], check=True
    )
    assert json.loads(measurement.read_text())["returncode"] == 17
    assert log.read_text() == "measurement failed\n"


@pytest.mark.parametrize("relative", ["inside", "same", "parent"])
def test_output_cannot_overwrite_the_source_checkout(tmp_path, relative):
    checkout = tmp_path / "scrollgt"
    checkout.mkdir()
    output = {"inside": checkout / "run", "same": checkout, "parent": tmp_path}[
        relative
    ]
    run = subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--scrollgt",
            str(checkout),
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2 and "disjoint" in run.stderr
    assert list(checkout.iterdir()) == []


def test_the_report_preserves_every_published_field_and_input_identity():
    import hashlib
    import zipfile

    path = ROOT / "reports/evidence/scrollgt_corpus_reproduction_2026-10-27.json"
    record = json.loads(path.read_text())
    assert record["status"] == "EXACT" and record["all_sources_unchanged"] is True
    assert hashlib.sha256(HARNESS.read_bytes()).hexdigest() == record["harness_sha256"]
    cases = record["cases"]
    assert len(cases) == len({r["target"] for r in cases}) == 21
    assert sum(r["target"].endswith("_256") for r in cases) == 10
    assert sum(r["target"].endswith("_512") for r in cases) == 11
    assert all(
        r["exact_match"] and r["metrics"] == r["expected"] and len(r["metrics"]) == 15
        for r in cases
    )
    assert all(
        r["measurement"]["returncode"] == 0
        and r["measurement"]["address_space_limit_bytes"] == 7 * 1024**3
        for r in cases
    )
    assert (
        len([p for p in record["inputs_and_sources_sha256"] if p.startswith("data/")])
        == 21 * 3
    )
    archive = ROOT / record["raw_archive"]["path"]
    assert (
        hashlib.sha256(archive.read_bytes()).hexdigest()
        == record["raw_archive"]["sha256"]
    )
    with zipfile.ZipFile(archive) as raw:
        assert len(raw.namelist()) == record["raw_archive"]["files"] == 84
        for case in cases:
            card = raw.read(case["target"] + "/scorecard.json")
            log = raw.read(case["target"] + "/stdout.log")
            assert hashlib.sha256(card).hexdigest() == case["scorecard_sha256"]
            assert hashlib.sha256(log).hexdigest() == case["log_sha256"]
            assert json.loads(card)["metrics"] == case["metrics"]
