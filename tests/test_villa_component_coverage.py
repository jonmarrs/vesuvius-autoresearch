from scripts.build_villa_component_coverage import (
    build_component_coverage,
    render_markdown,
)


def test_villa_component_coverage_marks_covered_partial_blocked_and_unwired(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("scripts.build_villa_component_coverage.REPO_ROOT", tmp_path)
    (tmp_path / "villa" / "vesuvius").mkdir(parents=True)
    (tmp_path / "local").mkdir()
    (tmp_path / "local" / "hook.py").write_text("")

    report = build_component_coverage(
        [
            {
                "name": "covered",
                "official_path": "villa/vesuvius",
                "prize_use": "official data access",
                "local_hooks": ["local/hook.py"],
                "next_action": "keep covered",
                "priority": "high",
            },
            {
                "name": "partial",
                "official_path": "villa/vesuvius",
                "prize_use": "official data access",
                "local_hooks": ["local/hook.py", "local/missing.py"],
                "next_action": "wire missing hook",
                "priority": "medium",
            },
            {
                "name": "unwired",
                "official_path": "villa/vesuvius",
                "prize_use": "official data access",
                "local_hooks": ["local/missing.py"],
                "next_action": "add hook",
                "priority": "medium",
            },
            {
                "name": "blocked",
                "official_path": "villa/vesuvius",
                "prize_use": "official data access",
                "local_hooks": ["local/hook.py", "local/missing.py"],
                "required_hooks": ["local/missing.py"],
                "next_action": "restore required hook",
                "priority": "high",
            },
        ]
    )

    assert report["summary"]["covered"] == 1
    assert report["summary"]["partial"] == 1
    assert report["summary"]["blocked_missing_required_hook"] == 1
    assert report["summary"]["unwired"] == 1
    assert [row["coverage_status"] for row in report["components"]] == [
        "covered",
        "partial",
        "unwired",
        "blocked_missing_required_hook",
    ]


def test_villa_component_coverage_markdown_includes_next_actions(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.build_villa_component_coverage.REPO_ROOT", tmp_path)
    report = build_component_coverage(
        [
            {
                "name": "missing",
                "official_path": "villa/missing",
                "prize_use": "review route",
                "local_hooks": ["local/missing.py"],
                "next_action": "install or port component",
                "priority": "medium",
            }
        ]
    )

    markdown = render_markdown(report)

    assert "missing_official_component" in markdown
    assert "Blocked by missing required hook" in markdown
    assert "install or port component" in markdown


def test_markdown_states_it_checks_paths_only(tmp_path, monkeypatch):
    """The caveat is rendered, so the post-sprint handoff's regeneration keeps it."""
    monkeypatch.setattr("scripts.build_villa_component_coverage.REPO_ROOT", tmp_path)
    markdown = render_markdown(build_component_coverage([]))
    assert "It checks paths only" in markdown


def test_a_component_villa_moved_to_deprecated_is_reported_as_such(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("scripts.build_villa_component_coverage.REPO_ROOT", tmp_path)
    (tmp_path / "villa" / "deprecated" / "old-tool").mkdir(parents=True)
    report = build_component_coverage(
        [
            {
                "name": "old",
                "official_path": "villa/old-tool",
                "prize_use": "review route",
                "local_hooks": [],
                "next_action": "use the deprecated copy or port it",
                "priority": "medium",
            }
        ]
    )
    (row,) = report["components"]
    assert row["coverage_status"] == "deprecated_upstream"
    assert row["deprecated_path"] == "villa/deprecated/old-tool"
    assert report["summary"]["deprecated_upstream"] == 1
    assert "Deprecated upstream" in render_markdown(report)


def test_official_paths_are_read_from_the_pinned_tree_not_the_checkout(
    tmp_path, monkeypatch
):
    """A sparse villa checkout omits directories the pin has; the pin's tree decides."""
    import subprocess

    monkeypatch.setattr("scripts.build_villa_component_coverage.REPO_ROOT", tmp_path)
    villa = tmp_path / "villa"
    (villa / "kept").mkdir(parents=True)
    (villa / "kept" / "f.txt").write_text("x")
    git = ["git", "-C", str(villa), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "pin"], check=True)
    (villa / "kept" / "f.txt").unlink()
    (villa / "kept").rmdir()
    (villa / "untracked").mkdir()

    def row(path):
        report = build_component_coverage(
            [
                {
                    "name": path,
                    "official_path": path,
                    "prize_use": "",
                    "local_hooks": [],
                    "next_action": "",
                    "priority": "low",
                }
            ]
        )
        return report["components"][0]["official_present"]

    assert row("villa/kept") is True
    assert row("villa/untracked") is False


def test_every_listed_local_hook_exists():
    """Six hooks pointed at paths a 2026-06-02 refactor had moved, so the handoff's
    regenerated report showed them missing for months."""
    from scripts.build_villa_component_coverage import COMPONENTS, REPO_ROOT

    missing = [
        hook
        for component in COMPONENTS
        for hook in component["local_hooks"]
        if not (REPO_ROOT / hook).exists()
    ]
    assert missing == []
