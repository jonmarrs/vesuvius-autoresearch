from scripts import audit_villa_upstream as audit


def test_audit_villa_upstream_groups_prize_relevant_changes(monkeypatch, tmp_path):
    villa_dir = tmp_path / "villa"
    villa_dir.mkdir()

    def fake_git(args, cwd):
        if args[:2] == ["rev-parse", "HEAD"]:
            return "local"
        if args[:2] == ["rev-parse", "origin/main"]:
            return "upstream"
        if args[:1] == ["merge-base"]:
            return "base"
        if args[:2] == ["rev-list", "--count"]:
            if args[2] == "base..origin/main":
                return "5"
            if args[2] == "base..local":
                return "2"
        if args[0] == "log":
            return "abc123 upstream change"
        raise AssertionError(args)

    def fake_changed_paths(villa_dir, base_ref, head_ref):
        if (base_ref, head_ref) == ("base", "origin/main"):
            return [
                "lasagna/README.md",
                "ink-detection/optimized_inference/runtime_contracts.py",
                "ink-detection/train_resnet3d_3d_decoder.py",
                "volume-cartographer/apps/VC3D/CWindow.cpp",
                "vesuvius/src/vesuvius/scripts/build_chunk_occupancy.py",
                "scrollprize.org/docs/34_prizes.md",
                "README.md",
            ]
        if (base_ref, head_ref) == ("base", "local"):
            return [
                "foundation/datasets/fibers-dataset/tools.py",
                "volume-cartographer/scripts/local_patch.sh",
            ]
        if (base_ref, head_ref) == ("local", "origin/main"):
            return [
                "lasagna/README.md",
                "volume-cartographer/apps/VC3D/CWindow.cpp",
                "foundation/datasets/fibers-dataset/tools.py",
            ]
        raise AssertionError((base_ref, head_ref))

    monkeypatch.setattr(audit, "_git", fake_git)
    monkeypatch.setattr(audit, "_changed_paths", fake_changed_paths)

    report = audit.audit_villa_upstream(villa_dir=villa_dir)

    assert report["behind"] is True
    assert report["diverged"] is True
    assert report["upstream_ahead_commits"] == 5
    assert report["local_ahead_commits"] == 2
    assert report["changed_files"] == 7
    assert report["direct_tree_changed_files"] == 3
    assert report["local_changed_files"] == 2
    assert report["prize_relevant_areas"]["lasagna"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["optimized_inference"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["resnet3d_decoder"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["volume_cartographer"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["vesuvius_data"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["prize_docs"]["changed_files"] == 1
    assert report["local_prize_relevant_areas"]["volume_cartographer"]["changed_files"] == 1


def test_audit_villa_upstream_handles_fast_forward_pin(monkeypatch, tmp_path):
    villa_dir = tmp_path / "villa"
    villa_dir.mkdir()

    def fake_git(args, cwd):
        if args[:2] == ["rev-parse", "HEAD"]:
            return "base"
        if args[:2] == ["rev-parse", "origin/main"]:
            return "upstream"
        if args[:1] == ["merge-base"]:
            return "base"
        if args[:2] == ["rev-list", "--count"]:
            if args[2] == "base..origin/main":
                return "1"
            if args[2] == "base..base":
                return "0"
        if args[0] == "log":
            return "abc123 upstream change"
        raise AssertionError(args)

    def fake_changed_paths(villa_dir, base_ref, head_ref):
        if (base_ref, head_ref) == ("base", "origin/main"):
            return ["volume-cartographer/apps/VC3D/CWindow.cpp"]
        if (base_ref, head_ref) == ("base", "base"):
            return []
        raise AssertionError((base_ref, head_ref))

    monkeypatch.setattr(audit, "_git", fake_git)
    monkeypatch.setattr(audit, "_changed_paths", fake_changed_paths)

    report = audit.audit_villa_upstream(villa_dir=villa_dir)

    assert report["behind"] is True
    assert report["diverged"] is False
    assert report["local_ahead_commits"] == 0
    assert report["prize_relevant_areas"]["volume_cartographer"]["changed_files"] == 1
