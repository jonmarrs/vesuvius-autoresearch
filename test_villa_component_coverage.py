from scripts.build_villa_component_coverage import build_component_coverage, render_markdown


def test_villa_component_coverage_marks_covered_partial_blocked_and_unwired(tmp_path, monkeypatch):
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
