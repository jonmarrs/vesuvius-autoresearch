"""Missing originals are explicit skips, or failures when selected strictly."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from research_prerequisites import STUDY_PATHS, git_environment

ROOT = Path(__file__).resolve().parents[1]


def test_git_hook_selectors_cannot_redirect_temporary_repository_operations(
    monkeypatch,
):
    monkeypatch.setenv("GIT_DIR", "/other/repository/.git")
    monkeypatch.setenv("GIT_INDEX_FILE", "/other/repository/index")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "never")
    env = git_environment()
    assert "GIT_DIR" not in env and "GIT_INDEX_FILE" not in env
    assert env["GIT_CONFIG_COUNT"] == "1" and env["GIT_CONFIG_VALUE_0"] == "never"
    assert env["GIT_NO_LAZY_FETCH"] == "1"


def run_checks(tmp_path, source, *options, provision=()):
    root = tmp_path / "checkout"
    tests = root / "tests"
    tests.mkdir(parents=True)
    for name in ("conftest.py", "research_prerequisites.py"):
        shutil.copy2(ROOT / "tests" / name, tests / name)
    shutil.copy2(ROOT / "pyproject.toml", root / "pyproject.toml")
    (tests / "test_cases.py").write_text(source)
    for name in provision:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"deliberately invalid scientific payload")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "-rs", "--tb=short", *options],
        cwd=root,
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONPATH": ""},
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout + result.stderr


@pytest.mark.parametrize("strict", [False, True])
def test_missing_data_skips_or_fails_without_running_the_assertion(tmp_path, strict):
    code, output = run_checks(
        tmp_path,
        'import pytest\n@pytest.mark.research_input("spiral_rays")\ndef test_claim():\n    raise AssertionError("CLAIM RAN")\n',
        *(["--require-research-inputs"] if strict else []),
    )
    assert code == (1 if strict else 0), output
    assert "missing original study input" in output
    assert "CLAIM RAN" not in output
    assert ("1 error" if strict else "1 skipped") in output


def test_strict_mode_only_requires_selected_checks(tmp_path):
    code, output = run_checks(
        tmp_path,
        'import pytest\n@pytest.mark.research_input("spiral_patches")\ndef test_claim():\n    assert False\ndef test_control():\n    pass\n',
        "--require-research-inputs",
        "-k",
        "control",
    )
    assert code == 0 and "1 passed" in output, output


def test_present_but_invalid_data_does_not_skip_or_approve_the_claim(tmp_path):
    code, output = run_checks(
        tmp_path,
        'import pytest\n@pytest.mark.research_input("spiral_patches")\ndef test_claim():\n    raise AssertionError("INVALID PAYLOAD MUST FAIL")\n',
        "--require-research-inputs",
        provision=STUDY_PATHS["spiral_patches"],
    )
    assert code == 1 and "1 failed" in output, output
    assert "INVALID PAYLOAD MUST FAIL" in output and "skipped" not in output


def test_multiple_requirements_are_combined(tmp_path):
    code, output = run_checks(
        tmp_path,
        'import pytest\n@pytest.mark.research_input("spiral_patches")\n@pytest.mark.research_input("spiral_rays")\ndef test_claim():\n    pass\n',
        "--require-research-inputs",
        provision=STUDY_PATHS["spiral_patches"],
    )
    assert code == 1 and "spiral_winding_model_phercparis4" in output, output


@pytest.mark.parametrize(
    "declaration",
    [
        'research_input("typo")',
        "research_input()",
        'villa_history("HEAD")',
        "villa_history()",
    ],
)
def test_bad_declarations_fail_instead_of_becoming_skips(tmp_path, declaration):
    code, output = run_checks(
        tmp_path,
        f"import pytest\n@pytest.mark.{declaration}\ndef test_claim():\n    pass\n",
    )
    assert code == 1 and "research prerequisite check failed" in output, output
    assert "skipped" not in output


@pytest.mark.parametrize("strict", [False, True])
def test_an_absent_villa_checkout_is_not_the_parent_repository(tmp_path, strict):
    # git -C villa could resolve a hash in the parent. That must not satisfy
    # a history requirement belonging to the independent Villa repository.
    root = tmp_path / "checkout"
    (root / "villa").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True, env=git_environment())
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "parent",
        ],
        check=True,
        env=git_environment(),
    )
    ref = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, env=git_environment()
    ).strip()
    code, output = run_checks(
        tmp_path,
        f'import pytest\n@pytest.mark.villa_history("{ref}")\ndef test_claim():\n    pass\n',
        *(["--require-research-inputs"] if strict else []),
    )
    assert code == (1 if strict else 0), output
    assert "own initialized checkout" in output


def test_valid_history_runs_the_assertion_with_lazy_fetch_disabled(tmp_path):
    root = tmp_path / "checkout"
    villa = root / "villa"
    subprocess.run(["git", "init", "-q", str(villa)], check=True, env=git_environment())
    subprocess.run(
        [
            "git",
            "-C",
            str(villa),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "Villa fixture",
        ],
        check=True,
        env=git_environment(),
    )
    ref = subprocess.check_output(
        ["git", "-C", str(villa), "rev-parse", "HEAD"], text=True, env=git_environment()
    ).strip()
    code, output = run_checks(
        tmp_path,
        f'import os, pytest\n@pytest.mark.villa_history("{ref}")\ndef test_claim():\n    assert os.environ["GIT_NO_LAZY_FETCH"] == "1"\n',
        "--require-research-inputs",
    )
    assert code == 0 and "1 passed" in output, output


@pytest.mark.parametrize("strict", [False, True])
def test_missing_commit_is_named_in_an_initialized_villa_checkout(tmp_path, strict):
    villa = tmp_path / "checkout/villa"
    subprocess.run(["git", "init", "-q", str(villa)], check=True, env=git_environment())
    code, output = run_checks(
        tmp_path,
        'import pytest\n@pytest.mark.villa_history("deadbeef")\ndef test_claim():\n    pass\n',
        *(["--require-research-inputs"] if strict else []),
    )
    assert code == (1 if strict else 0), output
    assert "missing Villa commit: deadbeef" in output


def test_missing_source_blob_after_valid_commit_preflight_is_a_failure(tmp_path):
    root = tmp_path / "checkout"
    villa = root / "villa"
    subprocess.run(["git", "init", "-q", str(villa)], check=True, env=git_environment())
    subprocess.run(
        [
            "git",
            "-C",
            str(villa),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "incomplete history fixture",
        ],
        check=True,
        env=git_environment(),
    )
    ref = subprocess.check_output(
        ["git", "-C", str(villa), "rev-parse", "HEAD"], text=True, env=git_environment()
    ).strip()
    preserved = root / "repro/villa_preserved/ink_detection"
    preserved.mkdir(parents=True)
    (preserved / "missing.py").write_bytes(b"preserved source must be compared")
    source = (
        (ROOT / "tests/test_villa_preserved.py")
        .read_text()
        .replace('PIN = "ced62390e"', f'PIN = "{ref}"')
    )
    code, output = run_checks(
        tmp_path, source, "--require-research-inputs", "-k", "every_preserved_file"
    )
    assert code == 1 and "historical source blob unavailable" in output, output
    assert "1 failed" in output and "skipped" not in output


@pytest.mark.parametrize("strict", [False, True])
def test_hex_named_branch_cannot_substitute_for_a_commit_prefix(tmp_path, strict):
    villa = tmp_path / "checkout/villa"
    env = git_environment()
    subprocess.run(["git", "init", "-q", str(villa)], check=True, env=env)
    subprocess.run(
        [
            "git",
            "-C",
            str(villa),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "unrelated commit",
        ],
        check=True,
        env=env,
    )
    actual = subprocess.check_output(
        ["git", "-C", str(villa), "rev-parse", "HEAD"], text=True, env=env
    ).strip()
    assert not actual.startswith("deadbeef")
    subprocess.run(["git", "-C", str(villa), "branch", "deadbeef"], check=True, env=env)
    code, output = run_checks(
        tmp_path,
        'import pytest\n@pytest.mark.villa_history("deadbeef")\ndef test_claim():\n    raise AssertionError("WRONG SOURCE RAN")\n',
        *(["--require-research-inputs"] if strict else []),
    )
    assert code == (1 if strict else 0), output
    assert "missing Villa commit: deadbeef" in output
    assert "WRONG SOURCE RAN" not in output
