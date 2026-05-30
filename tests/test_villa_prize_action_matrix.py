import json

from scripts.build_villa_prize_action_matrix import build_action_matrix, render_markdown


def test_villa_prize_action_matrix_joins_opportunities_to_ready_candidates(tmp_path):
    opportunities = tmp_path / "opportunities.json"
    preflight = tmp_path / "preflight.json"
    opportunities.write_text(
        json.dumps(
            {
                "villa_local_ref": "local",
                "villa_upstream_ref": "upstream",
                "villa_behind": True,
                "villa_diverged": True,
                "opportunities": [
                    {
                        "id": "villa-issue-191",
                        "official_issue": "https://github.com/ScrollPrize/villa/issues/191",
                        "title": "Surface and fiber predictions",
                        "track": "first_letters",
                        "villa_area": "lasagna",
                        "local_hook": "reports/scroll23_ranked_candidates.tsv",
                        "why_it_matters": "Hard geometry needs preprocessing.",
                        "next_action": "Route candidates through Lasagna.",
                        "priority_score": 104,
                    }
                ],
            }
        )
    )
    preflight.write_text(
        json.dumps(
            {
                "total": 1,
                "ready_for_gpu": 1,
                "blocked": 0,
                "gpu_queue": "queue.tsv",
                "rows": [
                    {
                        "ready_for_gpu": True,
                        "artifact_stem": "pred_1_2_3_64x64",
                        "scroll_id": "Scroll 2",
                        "division": "div_90",
                        "z": "1",
                        "y": "2",
                        "x": "3",
                        "review_score": "2.35",
                        "report_path": "report.json",
                    }
                ],
            }
        )
    )

    matrix = build_action_matrix(
        opportunities_path=opportunities, preflight_path=preflight
    )

    assert matrix["villa_diverged"] is True
    assert matrix["candidate_digest"]["ready_for_gpu"] == 1
    assert matrix["actions"][0]["readiness"] == "ready_now"
    assert "Lasagna/fiber preprocessing" in matrix["actions"][0]["autoresearch_action"]


def test_villa_prize_action_matrix_markdown_includes_issue_and_queue(tmp_path):
    opportunities = tmp_path / "opportunities.json"
    preflight = tmp_path / "preflight.json"
    opportunities.write_text(
        json.dumps(
            {
                "opportunities": [
                    {
                        "id": "villa-issue-201",
                        "official_issue": "https://github.com/ScrollPrize/villa/issues/201",
                        "title": "Scroll-specific 3D augmentations",
                        "track": "progress_and_first_letters",
                        "villa_area": "resnet3d_decoder",
                        "priority_score": 95,
                    }
                ]
            }
        )
    )
    preflight.write_text(
        json.dumps(
            {
                "total": 0,
                "ready_for_gpu": 0,
                "blocked": 0,
                "gpu_queue": "queue.tsv",
                "rows": [],
            }
        )
    )

    markdown = render_markdown(
        build_action_matrix(opportunities_path=opportunities, preflight_path=preflight)
    )

    assert "villa-issue-201" in markdown
    assert "`training_ablation`" in markdown
    assert "queue.tsv" in markdown
