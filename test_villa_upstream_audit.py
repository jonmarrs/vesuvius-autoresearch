from scripts import audit_villa_upstream as audit


def test_audit_villa_upstream_groups_prize_relevant_changes(monkeypatch, tmp_path):
    villa_dir = tmp_path / "villa"
    villa_dir.mkdir()

    def fake_git(args, cwd):
        if args[:2] == ["rev-parse", "HEAD"]:
            return "local"
        if args[:2] == ["rev-parse", "origin/main"]:
            return "upstream"
        if args[0] == "log":
            return "abc123 upstream change"
        raise AssertionError(args)

    monkeypatch.setattr(audit, "_git", fake_git)
    monkeypatch.setattr(
        audit,
        "_changed_paths",
        lambda villa_dir, base_ref, head_ref: [
            "lasagna/README.md",
            "ink-detection/optimized_inference/runtime_contracts.py",
            "ink-detection/train_resnet3d_3d_decoder.py",
            "volume-cartographer/apps/VC3D/CWindow.cpp",
            "vesuvius/src/vesuvius/scripts/build_chunk_occupancy.py",
            "scrollprize.org/docs/34_prizes.md",
            "README.md",
        ],
    )

    report = audit.audit_villa_upstream(villa_dir=villa_dir)

    assert report["behind"] is True
    assert report["changed_files"] == 7
    assert report["prize_relevant_areas"]["lasagna"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["optimized_inference"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["resnet3d_decoder"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["volume_cartographer"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["vesuvius_data"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["prize_docs"]["changed_files"] == 1
