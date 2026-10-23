"""The fiber reference provenance report must state what its audits recorded.

`reports/fiber_reference_provenance_2026-10-23.md` and the villa draft it
supports were typed from two audit JSONs and a snapshot record. The record also
binds the audit and download scripts, and both audits, by SHA-256: editing one
of them means the snapshot no longer describes it, and needs a new snapshot or a
note. These tests read every figure back from the evidence.
"""

import ast
import hashlib
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EVIDENCE = _REPO / "reports" / "evidence"
_REPORT = _REPO / "reports" / "fiber_reference_provenance_2026-10-23.md"
_DRAFT = _REPO / "docs" / "VILLA_DRAFT_fiber_reference_provenance.md"
_PATCH = _REPO / "docs" / "villa_pr_fiber_reference_provenance.patch"
_SNAPSHOTS = _EVIDENCE / "fiber_reference_snapshots_2026-10-23.json"
_FOLDERS = ("0139", "0332")


def _audit(folder):
    return json.loads(
        (_EVIDENCE / f"fiber_reference_pherc{folder}_2026-10-23.json").read_text()
    )


def _flat(path):
    return " ".join(path.read_text().split())


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_snapshot_record_binds_the_committed_scripts_and_audits():
    record = json.loads(_SNAPSHOTS.read_text())
    assert record["audit_script_sha256"] == _sha(
        _REPO / "scripts" / "audit_fiber_reference_provenance.py"
    )
    assert record["fetch_script_sha256"] == _sha(
        _REPO / "repro" / "fibers" / "fetch_reference_annotations.py"
    )
    # the shell commands' line continuations aside
    report = _flat(_REPORT).replace(" \\ ", " ")
    for folder in _FOLDERS:
        snap, audit = record["snapshots"][folder], _audit(folder)
        assert _sha(_REPO / snap["audit_path"]) == snap["audit_sha256"]
        assert snap["file_count"] == audit["file_count"] == len(audit["inputs"])
        assert snap["bytes"] == sum(i["bytes"] for i in audit["inputs"])
        # the commands that made the snapshot, and what the downloader printed
        assert (
            f"{snap['source_url']} /workspace/villa-fiber-reference-evidence/pherc{folder}"
            in report
        )
        assert (
            f"# Downloaded all {snap['file_count']} listed JSON files ({snap['bytes']} bytes)"
            in report
        )


def test_the_folder_table_and_totals_are_the_audits():
    report = _flat(_REPORT)
    files = total = 0
    for folder in _FOLDERS:
        a = _audit(folder)
        spans = a["interp_mode_span_counts"]
        row = (
            f"| PHerc{folder} | {a['file_count']} | {a['control_point_count']:,} | "
            f"{a['line_point_count']:,} | {spans['trace']:,} | {spans['cspline']:,} | "
            f"{spans['lasagna']:,} |"
        )
        assert row in report
        files += a["file_count"]
        total += sum(i["bytes"] for i in a["inputs"])
    a, b = (_audit(f)["file_count"] for f in _FOLDERS)
    assert f"All {a} PHerc0139 and {b} PHerc0332 JSON files" in report
    assert f"The {total:,} original bytes stay outside the repository." in report
    assert f"all {files} saved files" in report and f"All {files} saved files" in report


def test_the_frame_table_is_each_frames_trace_share():
    report = _flat(_REPORT)
    absent = []
    for folder in _FOLDERS:
        a = _audit(folder)
        for frame, group in a["by_coordinate_frame"].items():
            share = 100 * group["by_interp_mode"]["trace"]["control_chord_share"]
            label = (
                f"PHerc{folder} frame field absent"
                if frame == "unknown"
                else f"`{frame}`"
            )
            assert f"| {label} | {group['file_count']} | {share:.4f}% |" in report
        # the files without a frame are the files without a source resolution
        missing = a["coordinate_frame_files"]["unknown"]
        assert a["source_original_resolution_files"]["unknown"] == missing
        absent.append(missing)
    assert (
        f"The {absent[0]} and {absent[1]} files also omit "
        "`vc_open_data_source_original_resolution`." in report
    )


def test_one_trace_configuration_and_the_local_manifest_spans():
    report, draft = _flat(_REPORT), _flat(_DRAFT)
    local = []
    for folder in _FOLDERS:
        a = _audit(folder)
        (only,) = a["trace_configs"]
        assert only["spans"] == a["interp_mode_span_counts"]["trace"]
        c = only["config"]
        stated = (
            f"beam width {c['beam_width']}, lookahead {c['beam_lookahead_steps']} "
            f"and cone angle {c['cone_angle_degrees']:g} degrees"
        )
        assert stated in report and stated in draft
        manifests = a["trace_fiber_manifest_spans"]
        assert sum(manifests.values()) == only["spans"]
        local.append(
            sum(n for k, n in manifests.items() if not k.startswith("https://"))
        )
    assert (
        f"({local[0]:,} PHerc0139 trace spans; {local[1]:,} PHerc0332 trace spans)"
        in report
    )


def test_the_draft_and_patch_size_are_the_evidence():
    draft, report = _flat(_DRAFT), _flat(_REPORT)
    a, b = (_audit(f) for f in _FOLDERS)
    assert (
        f"all {a['file_count']} PHerc0139 and {b['file_count']} PHerc0332 published annotation JSON files"
        in draft
    )
    traces = (
        a["interp_mode_span_counts"]["trace"],
        b["interp_mode_span_counts"]["trace"],
    )
    assert f"found {traces[0]:,} and {traces[1]:,} `trace` spans" in draft
    assert f"all {a['file_count'] + b['file_count']} listed files" in draft

    added = [
        x
        for x in _PATCH.read_text().split("\n@@", 1)[1].splitlines()
        if x.startswith("+") and not x.startswith("+++")
    ]
    removed = [
        x
        for x in _PATCH.read_text().split("\n@@", 1)[1].splitlines()
        if x.startswith("-") and not x.startswith("---")
    ]
    words = {8: "eight"}
    assert not removed
    assert f"The [{words[len(added)]}-line patch]" in report


def test_the_test_count_is_the_test_file():
    tree = ast.parse(
        (_REPO / "tests" / "test_audit_fiber_reference_provenance.py").read_text()
    )
    cases = 0
    for f in tree.body:
        if isinstance(f, ast.FunctionDef) and f.name.startswith("test_"):
            n = 1
            for d in f.decorator_list:
                if (
                    isinstance(d, ast.Call)
                    and getattr(d.func, "attr", "") == "parametrize"
                ):
                    n *= len(d.args[1].elts)
            cases += n
    words = {9: "Nine"}
    assert f"{words[cases]} audit tests pass again" in _flat(_REPORT)
    assert f"# {cases} passed in" in _REPORT.read_text()
    assert f"pass ({cases} tests)" in _flat(_DRAFT)
