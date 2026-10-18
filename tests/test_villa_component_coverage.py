import os
import shutil
import subprocess

import pytest

from scripts.build_villa_component_coverage import (
    build_component_coverage,
    render_markdown,
)

MODULE = "scripts.build_villa_component_coverage"


def _component(path):
    return {
        "name": path,
        "official_path": path,
        "prize_use": "",
        "local_hooks": [],
        "next_action": "",
        "priority": "low",
    }


@pytest.fixture
def pinned(tmp_path, monkeypatch):
    """A superproject whose HEAD pins a villa repository holding kept/ and
    deprecated/old-tool/; no locator variables or global git config inherited."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    for name in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_PREFIX",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    def git(cwd, *args):
        return subprocess.run(
            [
                "git",
                "-C",
                str(cwd),
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@t",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    villa = tmp_path / "villa"
    for directory in ("kept", "deprecated/old-tool"):
        (villa / directory).mkdir(parents=True)
        (villa / directory / "f.txt").write_text("x")
    git(villa, "init", "-q")
    git(villa, "add", ".")
    git(villa, "commit", "-q", "-m", "pin")
    pin = git(villa, "rev-parse", "HEAD")
    git(tmp_path, "init", "-q")
    git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{pin},villa")
    git(tmp_path, "commit", "-q", "-m", "pin villa")
    monkeypatch.setattr(f"{MODULE}.REPO_ROOT", tmp_path)
    return tmp_path, villa, pin, git


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


def test_official_paths_are_read_from_the_pinned_tree_not_the_checkout(pinned):
    """A sparse villa checkout omits directories the pin has; the pin's tree decides,
    and the row also says the path is not checked out."""
    _, villa, pin, _ = pinned
    shutil.rmtree(villa / "kept")
    (villa / "untracked").mkdir()

    report = build_component_coverage(
        [_component("villa/kept"), _component("villa/untracked")]
    )
    kept, untracked = report["components"]
    assert kept["official_present"] is True
    assert kept["official_checked_out"] is False
    assert untracked["official_present"] is False
    assert report["villa_commit"] == pin
    assert report["summary"]["villa_path_not_checked_out"] == 1
    markdown = render_markdown(report)
    assert pin[:9] in markdown
    assert "`villa/kept` (not checked out)" in markdown


def test_the_pin_is_the_superprojects_gitlink_not_villas_head(pinned):
    """A villa checked out at another commit, as while reviewing a pin bump, does not
    change what the pin holds."""
    _, villa, pin, git = pinned
    git(villa, "rm", "-q", "-r", "kept")
    (villa / "later").mkdir()
    (villa / "later" / "f.txt").write_text("x")
    git(villa, "add", "later")
    git(villa, "commit", "-q", "-m", "after the pin")

    report = build_component_coverage(
        [_component("villa/kept"), _component("villa/later")]
    )
    kept, later = report["components"]
    assert (kept["official_present"], later["official_present"]) == (True, False)
    assert report["villa_commit"] == pin


def test_a_hook_exported_git_dir_does_not_redirect_the_lookup(pinned, monkeypatch):
    """Git exports GIT_DIR to hooks run from a linked worktree; unstripped, every
    call reads that repository instead of villa."""
    root, _, pin, _ = pinned
    monkeypatch.setenv("GIT_DIR", str(root / ".git"))
    report = build_component_coverage([_component("villa/kept")])
    assert report["villa_commit"] == pin
    assert report["components"][0]["official_present"] is True


@pytest.mark.parametrize("breakage", ["broken gitfile", "empty .git", "no git"])
def test_an_unreadable_pin_falls_back_to_the_working_tree_and_says_so(
    pinned, monkeypatch, breakage
):
    """A git failure is not an absent component: the working tree answers, and the
    report says the pin was not read."""
    _, villa, _, _ = pinned
    if breakage == "no git":
        monkeypatch.setenv("PATH", "")
    else:
        shutil.rmtree(villa / ".git")
        if breakage == "broken gitfile":
            (villa / ".git").write_text("gitdir: /nonexistent\n")
        else:
            (villa / ".git").mkdir()

    report = build_component_coverage([_component("villa/kept")])
    assert report["components"][0]["official_present"] is True
    assert report["villa_commit"] is None
    assert report["source"] == f"the villa working tree ({report['pin_unread']})"
    reason = {
        "broken gitfile": "villa/.git does not open villa's own repository",
        "empty .git": "villa/.git does not open villa's own repository",
        "no git": "git is not installed",
    }[breakage]
    assert report["pin_unread"] == reason
    assert (
        f"read from the villa working tree, not the pin: the pinned tree could not be read ({reason})."
        in render_markdown(report)
    )


def test_a_deprecated_copy_is_named_beside_a_current_component(pinned):
    """ink-detection is in both places at the pin, and the recipes its prize use
    names are under deprecated/."""
    _, villa, _, git = pinned
    (villa / "old-tool").mkdir()
    (villa / "old-tool" / "f.txt").write_text("x")
    git(villa, "add", "old-tool")
    git(villa, "commit", "-q", "-m", "both")
    root = villa.parent
    pin = git(villa, "rev-parse", "HEAD")
    git(root, "update-index", "--cacheinfo", f"160000,{pin},villa")
    git(root, "commit", "-q", "-m", "bump")

    (row,) = build_component_coverage([_component("villa/old-tool")])["components"]
    assert row["coverage_status"] == "covered"
    assert row["deprecated_path"] == "villa/deprecated/old-tool"


def test_every_listed_local_hook_exists():
    """Six hooks pointed at paths that refactors in May and June 2026 had moved, so
    the handoff's regenerated report showed them missing for months."""
    from scripts.build_villa_component_coverage import COMPONENTS, REPO_ROOT

    missing = [
        hook
        for component in COMPONENTS
        for hook in component["local_hooks"]
        if not (REPO_ROOT / hook).exists()
    ]
    assert missing == []
