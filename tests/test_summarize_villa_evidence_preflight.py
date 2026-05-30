import json

from scripts.summarize_villa_evidence_preflight import (
    summarize_reports,
    write_gpu_queue,
    write_tsv,
)


def _write_report(path, *, index, status="PASS", failures=None, warnings=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "candidate_index": index,
                "status": status,
                "candidate": {
                    "scroll_id": "Scroll 2",
                    "short_id": "PHerc0125",
                    "division": "div_90",
                    "z": str(18176 + index),
                    "y": "4128",
                    "x": "4128",
                    "artifact_stem": f"pred_{index}",
                    "review_score": "2.35",
                    "ct_occupied_status": "true",
                    "prediction_found": "false",
                    "metadata_found": "false",
                },
                "failures": failures or [],
                "warnings": warnings or [],
            }
        )
    )


def test_summarize_reports_counts_ready_and_blocked_candidates(tmp_path):
    root = tmp_path / "evidence"
    _write_report(root / "candidate_000" / "preflight_report.json", index=0)
    _write_report(
        root / "candidate_001" / "preflight_report.json",
        index=1,
        status="FAIL",
        failures=["missing checkpoint"],
    )

    summary = summarize_reports(root)

    assert summary["total"] == 2
    assert summary["ready_for_gpu"] == 1
    assert summary["blocked"] == 1
    assert summary["rows"][0]["candidate_index"] == 0
    assert summary["rows"][1]["failure_count"] == 1


def test_write_tsv_outputs_flat_candidate_table(tmp_path):
    root = tmp_path / "evidence"
    _write_report(
        root / "candidate_000" / "preflight_report.json",
        index=0,
        warnings=["window warning"],
    )
    summary = summarize_reports(root)
    out = tmp_path / "summary.tsv"

    write_tsv(out, summary["rows"])

    text = out.read_text()
    assert "candidate_index\tstatus\tready_for_gpu" in text
    assert "pred_0" in text


def test_write_gpu_queue_keeps_only_ready_candidates(tmp_path):
    root = tmp_path / "evidence"
    _write_report(root / "candidate_000" / "preflight_report.json", index=0)
    _write_report(
        root / "candidate_001" / "preflight_report.json",
        index=1,
        status="FAIL",
        failures=["missing checkpoint"],
    )
    summary = summarize_reports(root)
    out = tmp_path / "gpu_queue.tsv"

    ready = write_gpu_queue(out, summary["rows"])

    text = out.read_text()
    assert len(ready) == 1
    assert "queue_rank\tcandidate_index" in text
    assert "pred_0" in text
    assert "pred_1" not in text
