#!/usr/bin/env python3
"""
Summarize Villa evidence preflight reports into a candidate triage table.

This is a non-GPU companion to run_post_sprint_villa_handoff.py. It lets us
review which Scroll 2/3 candidates are ready for inference and why others are
blocked before spending GPU time.
"""
import argparse
import csv
import json
from pathlib import Path


def _load_report(path):
    with open(path) as f:
        report = json.load(f)
    candidate = report.get("candidate", {})
    failures = report.get("failures", []) or []
    warnings = report.get("warnings", []) or []
    return {
        "candidate_index": report.get("candidate_index"),
        "status": report.get("status", "UNKNOWN"),
        "ready_for_gpu": report.get("status") == "PASS" and not failures,
        "scroll_id": candidate.get("scroll_id", ""),
        "short_id": candidate.get("short_id", ""),
        "division": candidate.get("division", ""),
        "z": candidate.get("z", ""),
        "y": candidate.get("y", ""),
        "x": candidate.get("x", ""),
        "artifact_stem": candidate.get("artifact_stem", ""),
        "review_score": candidate.get("review_score", ""),
        "ct_occupied_status": candidate.get("ct_occupied_status", ""),
        "prediction_found": candidate.get("prediction_found", ""),
        "metadata_found": candidate.get("metadata_found", ""),
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
        "report_path": str(path),
    }


def summarize_reports(root):
    root = Path(root)
    reports = sorted(root.glob("candidate_*/preflight_report.json"))
    rows = [_load_report(path) for path in reports]
    rows.sort(key=lambda row: (not row["ready_for_gpu"], row["candidate_index"] if row["candidate_index"] is not None else 10**9))
    return {
        "root": str(root),
        "total": len(rows),
        "ready_for_gpu": sum(1 for row in rows if row["ready_for_gpu"]),
        "blocked": sum(1 for row in rows if not row["ready_for_gpu"]),
        "rows": rows,
    }


def write_tsv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "candidate_index",
        "status",
        "ready_for_gpu",
        "scroll_id",
        "short_id",
        "division",
        "z",
        "y",
        "x",
        "artifact_stem",
        "review_score",
        "ct_occupied_status",
        "prediction_found",
        "metadata_found",
        "failure_count",
        "warning_count",
        "report_path",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_gpu_queue(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "queue_rank",
        "candidate_index",
        "scroll_id",
        "short_id",
        "division",
        "z",
        "y",
        "x",
        "artifact_stem",
        "review_score",
        "report_path",
    ]
    ready_rows = [row for row in rows if row.get("ready_for_gpu")]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for rank, row in enumerate(ready_rows):
            payload = {field: row.get(field, "") for field in fields}
            payload["queue_rank"] = rank
            writer.writerow(payload)
    return ready_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="reports/scroll23_evidence")
    parser.add_argument("--out-json", default="reports/scroll23_evidence_preflight_summary.json")
    parser.add_argument("--out-tsv", default="reports/scroll23_evidence_preflight_summary.tsv")
    parser.add_argument("--gpu-queue", default="reports/scroll23_gpu_inference_queue.tsv")
    args = parser.parse_args()

    summary = summarize_reports(args.root)
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2) + "\n")
    write_tsv(args.out_tsv, summary["rows"])
    ready_rows = write_gpu_queue(args.gpu_queue, summary["rows"])
    summary["gpu_queue"] = args.gpu_queue
    summary["gpu_queue_ready"] = len(ready_rows)
    out_json.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
