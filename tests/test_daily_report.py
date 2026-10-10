"""Daily PDF smoke exercises real rendering only inside an isolated workspace."""

from scripts.generate_daily_report import generate_pdf


def test_report_generation_smoke(tmp_path):
    results = tmp_path / "results.tsv"
    contents = (
        "timestamp\tval_bpb\tthroughput_Mvps\tnum_params_M\n"
        "2026-05-15 20:44:15\t0.4136\t10.5\t24.0\n"
    )
    results.write_text(contents)
    notes = tmp_path / "notes.md"
    notes.write_text("## [2026-05-15] Test Entry\nIntent, not a discovery claim.\n")
    pdf = generate_pdf(results, notes, tmp_path / "bundle")
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert pdf.read_bytes().rstrip().endswith(b"%%EOF")
    assert results.read_text() == contents
    assert (pdf.parent / "report.json").is_file()
