"""Synthetic control-flow/reporting checks; no Torch or checkpoint is loaded."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "repro/first_letters/pherc343"
BOOTSTRAP = r"""
import json, runpy, sys, types
source, encoded = sys.argv[1:]
spec = json.loads(encoded)
fake = types.ModuleType("torch")
calls = []
def load(path, **kwargs):
    calls.append({"path": path, "kwargs": kwargs})
    if path in spec["refuse"]:
        raise RuntimeError("synthetic restricted-load refusal")
    return {"state_dict": {"parameter": 1}}
fake.load = load
sys.modules["torch"] = fake
sys.argv = [source, *spec["paths"]]
try:
    runpy.run_path(source, run_name="__main__")
finally:
    print("CALLS=" + json.dumps(calls), file=sys.stderr)
"""


def check(paths: list[str], refuse: list[str]):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            BOOTSTRAP,
            str(SCRIPTS / "check_ckpt_safe.py"),
            json.dumps({"paths": paths, "refuse": refuse}),
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        env=env,
    )
    line = next(row for row in result.stderr.splitlines() if row.startswith("CALLS="))
    return result, json.loads(line[6:])


class CheckpointReporting(unittest.TestCase):
    def test_empty_batch_is_usage_failure_without_loading(self):
        result, calls = check([], [])
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)
        self.assertEqual(calls, [])

    def test_refused_batch_fails(self):
        result, _ = check(["refused"], ["refused"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("NOT_WEIGHTS_ONLY refused", result.stdout)

    def test_mixed_batch_fails(self):
        result, calls = check(["good", "refused"], ["refused"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("WEIGHTS_ONLY_OK good", result.stdout)
        self.assertIn("NOT_WEIGHTS_ONLY refused", result.stdout)
        self.assertEqual(len(calls), 2)

    def test_failure_does_not_hide_later_results(self):
        result, calls = check(["refused", "good"], ["refused"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("WEIGHTS_ONLY_OK good", result.stdout)
        self.assertIn("NOT_WEIGHTS_ONLY refused", result.stdout)
        self.assertEqual([call["path"] for call in calls], ["refused", "good"])

    def test_success_and_restricted_cpu_arguments(self):
        result, calls = check(["first", "second"], [])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.count("WEIGHTS_ONLY_OK"), 2)
        self.assertEqual(len(calls), 2)
        for call in calls:
            self.assertEqual(
                call["kwargs"],
                {"map_location": "cpu", "weights_only": True, "mmap": True},
            )

    def test_generated_record_does_not_invent_checkpoint_verification(self):
        spec = importlib.util.spec_from_file_location(
            "record_under_test", SCRIPTS / "make_record.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for directory in ("work", "logs", "src/repo/outputs"):
                (root / directory).mkdir(parents=True)
            (root / "logs/render_66.log").write_text(
                "RENDER_START 2026-01-01T00:00:00Z image=fixture threads=1 cache_gb=1 mem=1g\n"
                "Elapsed (wall clock) time: 0:01\nRENDER_EXIT 0 2026-01-01T00:00:01Z\n"
            )
            (root / "src/repo/outputs/SHA256SUMS").write_text("")
            comparison = {
                "published": str(root / "published"),
                "ours": str(root / "ours"),
                "ink_shown_iou": 1.0,
                "abs_diff": {"max": 0},
            }
            for name in ("pubstats", "ownstats"):
                (root / f"work/compare_{name}.json").write_text(json.dumps(comparison))
            (root / "work/render_check.json").write_text(
                json.dumps({"decoded_voxels_identical_where_published": True})
            )
            (root / "work/rerun_seed42_determinism.json").write_text("{}")
            out = root / "record.json"
            # These stubs replace scientific measurements, not checkpoint verification.
            # The assertions concern only the checkpoint fields written by the real builder.
            with (
                mock.patch.object(sys, "argv", ["make_record.py", str(root), str(out)]),
                mock.patch.object(module, "git", return_value="fixture"),
                mock.patch.object(module, "sha256", return_value="0" * 64),
                mock.patch.object(module, "stage_a", return_value={}),
                mock.patch.object(module, "gpu", return_value={}),
                mock.patch.object(module, "whole_image", return_value={}),
                mock.patch("builtins.print"),
            ):
                self.assertEqual(module.main(), 0)
            record = json.loads(out.read_text())
            self.assertIsNone(record["checkpoints"]["all_load_with_weights_only"])
            self.assertEqual(
                record["checkpoints"]["weights_only_verification"],
                "unverified_no_identity_bound_receipts",
            )

    def test_historical_record_is_preserved_not_recertified(self):
        record = json.loads(
            (ROOT / "reports/first_letters_343_reproduction.json").read_text()
        )
        checkpoints = record["checkpoints"]
        self.assertIsNone(checkpoints["all_load_with_weights_only"])
        self.assertEqual(
            checkpoints.pop("weights_only_verification"),
            "unverified_no_identity_bound_receipts",
        )
        self.assertIs(
            checkpoints.pop("original_reported_all_load_with_weights_only"), True
        )
        self.assertEqual(
            checkpoints.pop("original_record_provenance"),
            {
                "commit": "9fa747c5f96a77481fc75d88292742ba15930218",
                "blob": "251da028f05c8ddf42b85f0a9f5d09dc5eeb4d6e",
            },
        )
        # Reversing only the documented metadata correction recovers the exact old blob.
        checkpoints["all_load_with_weights_only"] = True
        data = (json.dumps(record, indent=2) + "\n").encode()
        blob = hashlib.sha1(
            b"blob " + str(len(data)).encode() + b"\0" + data
        ).hexdigest()
        self.assertEqual(blob, "251da028f05c8ddf42b85f0a9f5d09dc5eeb4d6e")

    def test_report_qualifies_the_historical_claim(self):
        report = " ".join(
            (ROOT / "reports/first_letters_343_reproduction.md").read_text().split()
        )
        self.assertIn("flag was hardcoded", report)
        self.assertIn("this claim is unverified", report)
        self.assertIn("does not show that any checkpoint failed or was unsafe", report)

    def test_script_readme_marks_the_post_run_correction(self):
        readme = " ".join((SCRIPTS / "README.md").read_text().split())
        self.assertIn("Checkpoint-reporting correction", readme)
        self.assertIn("At commit `9fa747c5`", readme)
        self.assertIn("all_load_with_weights_only: null", readme)


if __name__ == "__main__":
    unittest.main(verbosity=2)
