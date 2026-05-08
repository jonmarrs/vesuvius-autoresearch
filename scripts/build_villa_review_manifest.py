#!/usr/bin/env python3
"""
Build a Villa-native review manifest for GPU-ready prize candidates.

The action matrix says which official Villa opportunities matter. This manifest
turns the current GPU queue into per-candidate commands and expected artifacts
for ink/fiber inference, evidence validation, and VC3D/Crackle review.
"""
import argparse
import csv
import json
import shlex
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _load_json(path, default):
    path = _resolve(path)
    if not path.exists():
        return default
    with open(path, "r") as f:
        return json.load(f)


def _load_tsv(path):
    path = _resolve(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    with open(path, "r", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _first_ready_actions(action_matrix):
    return [
        action
        for action in action_matrix.get("actions", [])
        if action.get("readiness") in {"ready_now", "training_ablation"}
    ][:5]


def _candidate_item(row, python_executable, ranked, evidence_root, checkpoint):
    index = int(row.get("candidate_index", row.get("queue_rank", 0)) or 0)
    artifact = row.get("artifact_stem") or f"candidate_{index:03d}"
    evidence_dir = Path(evidence_root) / f"candidate_{index:03d}"
    prediction_dir = evidence_dir / "predictions"
    prediction_image = prediction_dir / f"{artifact}.png"
    prediction_metadata = prediction_dir / f"{artifact}_meta.json"
    prize_report = evidence_dir / "PRIZE_READINESS_REPORT.json"

    evidence_command = [
        python_executable,
        "scripts/run_villa_prize_evidence_chain.py",
        "--ranked",
        ranked,
        "--candidate-index",
        str(index),
        "--out-dir",
        str(evidence_dir),
        "--execute",
        "--checkpoint",
        checkpoint,
    ]
    validate_command = [
        python_executable,
        "scripts/validate_prize_artifact.py",
        "--metadata",
        str(prediction_metadata),
        "--out",
        str(evidence_dir / "validation_report.json"),
    ]
    review_commands = [
        [python_executable, "scripts/launch_crackle_viewer.py"],
        [python_executable, "scripts/launch_vc3d.py"],
    ]

    return {
        "candidate_index": index,
        "queue_rank": int(row.get("queue_rank", index) or index),
        "scroll_id": row.get("scroll_id"),
        "short_id": row.get("short_id"),
        "division": row.get("division"),
        "z": row.get("z"),
        "y": row.get("y"),
        "x": row.get("x"),
        "artifact_stem": artifact,
        "review_score": row.get("review_score"),
        "preflight_report": row.get("report_path"),
        "expected_prediction_image": str(prediction_image),
        "expected_prediction_metadata": str(prediction_metadata),
        "expected_evidence_dir": str(evidence_dir),
        "expected_prize_report": str(prize_report),
        "evidence_command": shlex.join(evidence_command),
        "validate_command": shlex.join(validate_command),
        "review_commands": [shlex.join(command) for command in review_commands],
        "villa_review_route": [
            "Run GPU inference/evidence chain",
            "Validate prize mechanics and VC3D/Zarr scale metadata",
            "Open prediction image and overlays in Crackle Viewer / VC3D",
            "Promote legible candidates into a submission package",
        ],
    }


def build_review_manifest(
    gpu_queue="reports/scroll23_gpu_inference_queue.tsv",
    action_matrix="reports/villa_prize_action_matrix.json",
    ranked="reports/scroll23_ranked_candidates.tsv",
    evidence_root="reports/scroll23_evidence",
    checkpoint="best_model.pt",
    python_executable=".venv/bin/python",
):
    matrix = _load_json(action_matrix, {"actions": []})
    rows = _load_tsv(gpu_queue)
    candidates = [
        _candidate_item(row, python_executable, ranked, evidence_root, checkpoint)
        for row in rows
    ]
    return {
        "source_gpu_queue": str(gpu_queue),
        "source_action_matrix": str(action_matrix),
        "source_ranked_candidates": str(ranked),
        "villa_local_ref": matrix.get("villa_local_ref"),
        "villa_upstream_ref": matrix.get("villa_upstream_ref"),
        "ready_actions": _first_ready_actions(matrix),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def render_markdown(manifest):
    lines = [
        "# Villa Review Manifest",
        "",
        "This manifest maps GPU-ready Autoresearch candidates to official Villa review workflows.",
        "",
        "## Official Villa Context",
        "",
        f"- Villa local ref: `{manifest.get('villa_local_ref')}`",
        f"- Villa upstream ref: `{manifest.get('villa_upstream_ref')}`",
        f"- GPU-ready candidates: `{manifest.get('candidate_count')}`",
        f"- Source queue: `{manifest.get('source_gpu_queue')}`",
        "",
        "## Ready Villa Hooks",
        "",
    ]
    actions = manifest.get("ready_actions", [])
    if not actions:
        lines.append("- None.")
    for action in actions:
        lines.append(
            "- `{id}` `{track}`: {title} -> {review_artifact}".format(
                id=action.get("id"),
                track=action.get("track"),
                title=action.get("title"),
                review_artifact=action.get("review_artifact"),
            )
        )

    lines.extend(["", "## Candidate Review Queue", ""])
    candidates = manifest.get("candidates", [])
    if not candidates:
        lines.append("- No GPU-ready candidates.")
    for item in candidates:
        lines.extend(
            [
                f"### Candidate {item['candidate_index']:03d}: `{item['artifact_stem']}`",
                "",
                f"- Location: {item.get('scroll_id')} {item.get('division')} z={item.get('z')} y={item.get('y')} x={item.get('x')}",
                f"- Review score: `{item.get('review_score')}`",
                f"- Preflight report: `{item.get('preflight_report')}`",
                f"- Expected prediction image: `{item.get('expected_prediction_image')}`",
                f"- Expected prediction metadata: `{item.get('expected_prediction_metadata')}`",
                f"- Evidence command: `{item.get('evidence_command')}`",
                f"- Validate command: `{item.get('validate_command')}`",
                f"- Review commands: `{'; '.join(item.get('review_commands', []))}`",
                "",
            ]
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu-queue", default="reports/scroll23_gpu_inference_queue.tsv")
    parser.add_argument("--action-matrix", default="reports/villa_prize_action_matrix.json")
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--evidence-root", default="reports/scroll23_evidence")
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument("--out-json", default="reports/villa_review_manifest.json")
    parser.add_argument("--out-md", default="reports/villa_review_manifest.md")
    parser.add_argument("--python-executable", default=".venv/bin/python")
    args = parser.parse_args()

    manifest = build_review_manifest(
        gpu_queue=args.gpu_queue,
        action_matrix=args.action_matrix,
        ranked=args.ranked,
        evidence_root=args.evidence_root,
        checkpoint=args.checkpoint,
        python_executable=args.python_executable,
    )
    out_json = _resolve(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(manifest, indent=2) + "\n")

    out_md = _resolve(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(manifest))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
