from scripts.build_volume_cartographer_readiness import build_readiness, render_markdown


def test_volume_cartographer_readiness_runs_local_smoke_for_missing_sample(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "scripts.build_volume_cartographer_readiness.REPO_ROOT", tmp_path
    )
    (tmp_path / "volume_cartographer_wrapper").mkdir()
    (tmp_path / "volume_cartographer_wrapper" / "volume.py").write_text("")
    (
        tmp_path
        / "villa"
        / "volume-cartographer"
        / "core"
        / "include"
        / "vc"
        / "core"
        / "types"
    ).mkdir(parents=True)
    (
        tmp_path
        / "villa"
        / "volume-cartographer"
        / "core"
        / "include"
        / "vc"
        / "core"
        / "types"
        / "Volume.hpp"
    ).write_text("")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "launch_vc3d.py").write_text("")

    report = build_readiness(sample_zarr="missing.zarr")

    assert report["local_volume_smoke"]["status"] == "pass"
    assert report["loader_slice_smoke"]["status"] == "pass"
    assert report["sample_probe"]["status"] == "missing_sample"
    assert report["prize_claim_status"] == "ready_for_local_data"


def test_volume_cartographer_readiness_markdown_names_alignment_status():
    report = {
        "prize_claim_status": "volume_cartographer_aligned",
        "checks": {
            "wrapper_present": True,
            "official_component_present": True,
            "volume_header_present": True,
            "vc3d_launcher_present": True,
        },
        "local_volume_smoke": {"status": "pass"},
        "loader_slice_smoke": {"status": "pass"},
        "sample_probe": {"status": "pass", "backend": "volume-cartographer-zarr"},
        "next_action": "Keep VC3D overlay validation in the prize handoff gate.",
    }

    markdown = render_markdown(report)

    assert "Volume Cartographer Readiness" in markdown
    assert "volume_cartographer_aligned" in markdown
    assert "volume-cartographer" in markdown
