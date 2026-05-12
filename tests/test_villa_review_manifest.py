import json

from scripts.build_villa_review_manifest import build_review_manifest, render_markdown


def test_villa_review_manifest_builds_candidate_commands(tmp_path):
    queue = tmp_path / "queue.tsv"
    matrix = tmp_path / "matrix.json"
    queue.write_text(
        "\t".join(
            [
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
        )
        + "\n"
        + "\t".join(
            [
                "0",
                "2",
                "Scroll 2",
                "PHerc0125",
                "div_90",
                "18176",
                "4128",
                "4000",
                "pred_18176_4128_4000_64x64",
                "2.35",
                "reports/scroll23_evidence/candidate_002/preflight_report.json",
            ]
        )
        + "\n"
    )
    matrix.write_text(
        json.dumps(
            {
                "villa_local_ref": "local",
                "villa_upstream_ref": "upstream",
                "actions": [
                    {
                        "id": "villa-issue-191",
                        "track": "first_letters",
                        "title": "Surface and fiber predictions",
                        "readiness": "ready_now",
                        "review_artifact": "reports/lasagna_fiber_worklist.tsv",
                    }
                ],
            }
        )
    )

    manifest = build_review_manifest(
        gpu_queue=queue,
        action_matrix=matrix,
        ranked="ranked.tsv",
        evidence_root="evidence",
        checkpoint="best_model.pt",
        python_executable="python",
    )

    assert manifest["candidate_count"] == 1
    assert manifest["ready_actions"][0]["id"] == "villa-issue-191"
    candidate = manifest["candidates"][0]
    assert candidate["candidate_index"] == 2
    assert "scripts/run_villa_prize_evidence_chain.py" in candidate["evidence_command"]
    assert "--ranked ranked.tsv" in candidate["evidence_command"]
    assert "--candidate-index 2" in candidate["evidence_command"]
    assert "evidence/candidate_002/predictions/pred_18176_4128_4000_64x64_meta.json" in candidate["validate_command"]
    assert any("launch_vc3d.py" in command for command in candidate["review_commands"])


def test_villa_review_manifest_markdown_lists_empty_queue(tmp_path):
    queue = tmp_path / "empty.tsv"
    matrix = tmp_path / "matrix.json"
    queue.write_text("")
    matrix.write_text(json.dumps({"actions": []}))

    markdown = render_markdown(build_review_manifest(gpu_queue=queue, action_matrix=matrix))

    assert "No GPU-ready candidates" in markdown
