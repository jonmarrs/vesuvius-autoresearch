import csv

from scripts.build_lasagna_fiber_worklist import build_worklist


def _write_ranked(path, rows):
    fields = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def test_lasagna_fiber_worklist_filters_and_scores_candidates(tmp_path):
    ranked = tmp_path / "ranked.tsv"
    base = {
        "scroll_id": "Scroll 2",
        "short_id": "PHerc0125",
        "division": "div_90",
        "z": "18176",
        "y": "4128",
        "x": "4128",
        "width": "64",
        "height": "64",
        "patch_size": "64",
        "local_uri": "local_data/PHerc0125_Divisions/div_90/0",
        "submittable_window": "true",
        "review_score": "2.0",
        "prediction_found": "true",
        "ct_occupied_status": "true",
        "ct_chunk_coord": "142.32.32",
        "ink_max": "0.2",
        "ink_std": "0.05",
        "fiber_mean": "0.3",
        "artifact_stem": "pred_good",
    }
    _write_ranked(
        ranked,
        [
            base,
            dict(
                base,
                artifact_stem="pred_best",
                ink_max="0.4",
                fiber_mean="0.5",
                x="4000",
            ),
            dict(
                base, artifact_stem="pred_empty", ct_occupied_status="false", x="3900"
            ),
            dict(base, artifact_stem="pred_missing_local", local_uri="", x="3800"),
        ],
    )

    rows = build_worklist(
        ranked, output_root=tmp_path / "work", limit=10, python_executable="python"
    )

    assert [row["artifact_stem"] for row in rows] == ["pred_best", "pred_good"]
    assert rows[0]["official_issue"].endswith("/191")
    assert rows[0]["depth"] == 128
    assert rows[0]["cropped_volume_uri"].endswith("candidate_crop.zarr")
    assert "scripts/crop_candidate_zarr.py" in rows[0]["crop_command"]
    assert rows[0]["cropped_volume_uri"] in rows[0]["structure_tensor_command"]
    assert "scripts/compute_structure_tensors.py" in rows[0]["structure_tensor_command"]
    assert (
        "local_data/PHerc0125_Divisions/div_90/0"
        not in rows[0]["structure_tensor_command"]
    )
    assert "scripts/run_villa_prize_evidence_chain.py" in rows[0]["evidence_command"]


def test_lasagna_fiber_worklist_respects_limit(tmp_path):
    ranked = tmp_path / "ranked.tsv"
    row = {
        "scroll_id": "Scroll 2",
        "short_id": "PHerc0125",
        "division": "div_90",
        "z": "1",
        "y": "2",
        "x": "3",
        "width": "64",
        "height": "64",
        "patch_size": "64",
        "local_uri": "local_data/vol/0",
        "submittable_window": "true",
        "review_score": "1.0",
        "prediction_found": "false",
        "ct_occupied_status": "true",
        "ct_chunk_coord": "0.0.0",
        "ink_max": "0.0",
        "ink_std": "0.0",
        "fiber_mean": "0.0",
        "artifact_stem": "pred_a",
    }
    _write_ranked(
        ranked, [dict(row, artifact_stem=f"pred_{idx}", z=str(idx)) for idx in range(3)]
    )

    rows = build_worklist(ranked, limit=2)

    assert len(rows) == 2
