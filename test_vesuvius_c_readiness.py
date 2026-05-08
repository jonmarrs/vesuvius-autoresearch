from scripts.build_vesuvius_c_readiness import build_readiness, render_markdown


def test_vesuvius_c_readiness_runs_fallback_smoke_for_missing_sample(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.build_vesuvius_c_readiness.REPO_ROOT", tmp_path)
    (tmp_path / "vesuvius_c_wrapper").mkdir()
    (tmp_path / "vesuvius_c_wrapper" / "vesuvius_c.py").write_text("")
    (tmp_path / "villa" / "vesuvius-c" / "python").mkdir(parents=True)
    (tmp_path / "villa" / "vesuvius-c" / "python" / "vesuvius_c.py").write_text("")

    report = build_readiness(sample_zarr="missing.zarr")

    assert report["fallback_smoke"]["status"] == "pass"
    assert report["loader_slice_smoke"]["status"] == "pass"
    assert report["sample_probe"]["status"] == "missing_sample"
    assert report["prize_claim_status"] == "ready_for_local_data"


def test_vesuvius_c_readiness_markdown_names_benchmark_command():
    report = {
        "prize_claim_status": "fallback_only",
        "checks": {
            "wrapper_present": True,
            "upstream_present": True,
            "native_library_present": False,
            "native_probe_requested": False,
        },
        "fallback_smoke": {"status": "pass"},
        "loader_slice_smoke": {"status": "pass"},
        "sample_probe": {"status": "pass", "backend": "zarr"},
        "benchmark_command": "VESUVIUS_C_BUILD=1 python benchmark_vesuvius_c.py",
        "next_action": "Run benchmark.",
    }

    markdown = render_markdown(report)

    assert "Vesuvius-C Readiness" in markdown
    assert "fallback_only" in markdown
    assert "benchmark_vesuvius_c.py" in markdown
