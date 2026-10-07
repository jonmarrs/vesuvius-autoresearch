#!/usr/bin/env python3
"""Prepare ranked CT candidates for Lasagna; optionally run separate CT evidence.

This command publishes candidate crops and structure tensors. Surface fitting
requires its own upstream configuration and is not launched here. --with-evidence
runs CT prediction/readiness after preprocessing, using masks supplied per row.
"""

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_lasagna_fiber_worklist import _artifact_stem, build_worklist
from scripts.candidate_artifacts import (
    ARTIFACT_ERRORS,
    array_3d,
    crop_matches,
    integer,
    tensor_matches,
    tensor_settings,
    write_json,
)
from scripts.validate_prize_artifact import validate


def _zarr_array_exists(path):
    try:
        array_3d(path)
        return True
    except ARTIFACT_ERRORS:
        return False


def _structure_tensor_complete(path, source=None, sigma=2.0):
    return tensor_matches(path, source, sigma)


def _evidence_passed(evidence_dir, artifact_stem, item=None, checkpoint=None):
    root = Path(evidence_dir)
    try:
        report = json.loads((root / "PRIZE_READINESS_REPORT.json").read_text())
        metadata_path = root / "evidence_metadata.json"
        metadata = json.loads(metadata_path.read_text())
        candidate = metadata["candidate"]
        if report.get("status") != "PASS" or _artifact_stem(candidate) != artifact_stem:
            return False
        if item is not None:
            manifest = json.loads((root / "manifest.json").read_text())
            if manifest.get("candidate_index") != item["candidate_index"]:
                return False
            for key in ("x", "y", "z", "width", "height"):
                if integer(candidate[key], key) != item[key]:
                    return False
            if str(Path(candidate["local_uri"]).resolve()) != str(
                Path(item["local_uri"]).resolve()
            ):
                return False
            for key in ("train_mask_path", "predict_mask_path"):
                if (
                    item.get(key)
                    and str(Path(metadata.get(key, "")).resolve()) != item[key]
                ):
                    return False
        if checkpoint is not None:
            if metadata.get("checkpoint_path") != str(Path(checkpoint).resolve()):
                return False
            if not Path(checkpoint).is_file():
                return False
        return validate(metadata_path).get("status") == "PASS"
    except ARTIFACT_ERRORS:
        return False


def run_step(name, cmd, env=None):
    print(f"{name}: {shlex.join(cmd)}", flush=True)
    try:
        subprocess.run(cmd, check=True, env=env)
        return True
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"{name} failed: {exc}", file=sys.stderr, flush=True)
        return False


def process_candidate(
    item,
    force=False,
    with_evidence=False,
    checkpoint="best_model.pt",
    sigma=2.0,
    gpus="all",
):
    result = {
        "rank": item["rank"],
        "candidate_index": item["candidate_index"],
        "artifact_stem": item["artifact_stem"],
        "stages": {},
        "status": "FAIL",
    }
    requested = (item["z"], item["y"], item["x"])
    shape = (item["depth"], item["height"], item["width"])
    crop = item["cropped_volume_uri"]
    tensors = item["structure_tensor_output"]
    if not force and crop_matches(crop, item["local_uri"], requested, shape):
        result["stages"]["crop"] = "REUSED"
    else:
        if not run_step("Crop", shlex.split(item["crop_command"])):
            result["failure"] = "crop command failed"
            return result
        if not crop_matches(crop, item["local_uri"], requested, shape):
            result["failure"] = "crop command did not publish a matching completed crop"
            return result
        result["stages"]["crop"] = "CREATED"
    if not force and _structure_tensor_complete(tensors, crop, sigma):
        result["stages"]["structure_tensor"] = "REUSED"
    else:
        command = shlex.split(item["structure_tensor_command"]) + [
            "--sigma",
            str(sigma),
            "--gpus",
            gpus,
        ]
        if not run_step("Structure tensors", command):
            result["failure"] = "structure tensor command failed"
            return result
        if not _structure_tensor_complete(tensors, crop, sigma):
            result["failure"] = (
                "structure tensor command did not publish matching complete outputs"
            )
            return result
        result["stages"]["structure_tensor"] = "CREATED"
    if with_evidence:
        if not force and _evidence_passed(
            item["evidence_output_dir"], item["artifact_stem"], item, checkpoint
        ):
            result["stages"]["ct_evidence"] = "REUSED"
        else:
            command = shlex.split(item["evidence_command"])
            command[command.index("--checkpoint") + 1] = str(checkpoint)
            if not run_step("CT evidence", command):
                result["failure"] = "CT evidence command failed"
                return result
            if not _evidence_passed(
                item["evidence_output_dir"], item["artifact_stem"], item, checkpoint
            ):
                result["failure"] = (
                    "CT evidence did not pass current readiness validation"
                )
                return result
            result["stages"]["ct_evidence"] = "CREATED"
    result["status"] = "PASS"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument("--output-root", default="reports/lasagna_fiber_candidates")
    parser.add_argument("--report", default="reports/lasagna_pipeline_execution.json")
    parser.add_argument("--sigma", type=float, default=2.0)
    parser.add_argument("--gpus", default="all")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute crops/tensors and requested CT evidence",
    )
    parser.add_argument(
        "--with-evidence",
        action="store_true",
        help="Also run CT evidence; ranked rows must supply train_mask_path and predict_mask_path",
    )
    args = parser.parse_args(argv)
    write_json(
        args.report,
        {"status": "FAIL", "failure": "candidate pipeline has not completed"},
    )
    try:
        tensor_settings(args.sigma, args.gpus)
        items = build_worklist(
            args.ranked, args.output_root, args.limit, sys.executable
        )
        if not items:
            raise ValueError("no eligible local candidates in the ranked worklist")
        if args.with_evidence:
            for item in items:
                for key in ("train_mask_path", "predict_mask_path"):
                    if not item.get(key) or not Path(item[key]).is_file():
                        raise ValueError(
                            f"{item['artifact_stem']}: --with-evidence requires a supplied readable {key}"
                        )
    except (OSError, ValueError) as exc:
        write_json(args.report, {"status": "FAIL", "failure": str(exc)})
        parser.exit(1, f"Candidate pipeline preflight failed: {exc}\n")
    results = [
        process_candidate(
            item, args.force, args.with_evidence, args.checkpoint, args.sigma, args.gpus
        )
        for item in items
    ]
    failed = sum(result["status"] != "PASS" for result in results)
    report = {
        "scope": "CT preprocessing and optional CT evidence; no surface fitting",
        "ranked_path": str(Path(args.ranked).resolve()),
        "candidates": results,
        "status": "FAIL" if failed else "PASS",
    }
    output = Path(args.report)
    write_json(output, report)
    print(
        f"Candidate preprocessing: {len(results) - failed} completed, {failed} failed. Report: {output}"
    )
    if failed:
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    main()
