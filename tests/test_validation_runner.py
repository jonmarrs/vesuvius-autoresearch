"""The validation launcher must honor CLI intent and its own checkout."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import run_validation_tests as runner


@pytest.fixture
def launched(monkeypatch):
    calls = []

    def call(command, **kwargs):
        calls.append((command, kwargs))
        return 0

    monkeypatch.setattr(runner.subprocess, "call", call)
    return calls


def test_help_does_not_launch_pytest(monkeypatch, launched, capsys):
    monkeypatch.setattr(sys, "argv", ["validation", "--help"])
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert not launched
    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_unknown_option_is_rejected_before_launch(monkeypatch, launched):
    monkeypatch.setattr(sys, "argv", ["validation", "--typo"])
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert not launched
    assert exc.value.code == 2


def test_launch_uses_own_checkout_and_hides_cuda(tmp_path, monkeypatch, launched):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "3")
    monkeypatch.setattr(sys, "argv", ["validation"])
    try:
        status = runner.main()
    except SystemExit as exc:
        status = exc.code
    assert status == 0
    command, options = launched[0]
    assert command[:4] == [sys.executable, "-m", "pytest", "-q"]
    assert Path(options["cwd"]) == Path(runner.__file__).resolve().parents[1]
    assert options["env"]["CUDA_VISIBLE_DEVICES"] == ""
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "3"


@pytest.fixture
def registry(tmp_path, monkeypatch):
    root = tmp_path / "checkout with spaces"
    names = ["tests/test_zebra.py", "tests/test_alpha.py", "tests/test_middle.py"]
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    monkeypatch.setattr(runner, "REPO_ROOT", root)
    monkeypatch.setattr(runner, "VALIDATION_TESTS", names)
    return root, names


def test_overlapping_selections_keep_registry_order_once(registry, launched, capsys):
    _, names = registry
    assert runner.main(["--match", "*alpha*", "--match", "*test_*.py"]) == 0
    assert launched[0][0][4:] == names
    assert "Validation scope: 3/3 curated modules" in capsys.readouterr().out


def test_list_prints_only_selected_paths_and_launches_nothing(
    registry, launched, capsys
):
    assert runner.main(["--list", "--match", "*middle*", "--match", "*zebra*"]) == 0
    assert not launched
    assert capsys.readouterr().out.splitlines() == [registry[1][0], registry[1][2]]


def test_pytest_options_require_separator_and_preserve_argument_boundaries(
    registry, launched, capsys
):
    pytest_args = ["-k", "one or two", "--maxfail=1"]
    assert runner.main(["--match", "*alpha*", "--", *pytest_args]) == 0
    assert launched[0][0][4:] == [registry[1][1], *pytest_args]
    assert "Validation scope: 1/3 curated modules" in capsys.readouterr().out


@pytest.mark.parametrize(
    "arguments",
    [
        ["--match", "*alpha*", "--match", "*typo*"],
        ["--match", ""],
        ["-x"],
        ["--allow"],
        ["--list", "--", "-x"],
    ],
)
def test_bad_cli_intent_cannot_launch_a_different_suite(registry, launched, arguments):
    with pytest.raises(SystemExit) as exc:
        runner.main(arguments)
    assert exc.value.code == 2
    assert not launched


@pytest.mark.parametrize("visibility", [None, "", "2"])
def test_cuda_opt_in_preserves_inherited_visibility(
    registry, launched, monkeypatch, visibility
):
    if visibility is None:
        monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    else:
        monkeypatch.setenv("CUDA_VISIBLE_DEVICES", visibility)
    monkeypatch.setenv("VALIDATION_TEST_SENTINEL", "preserved")
    assert runner.main(["--allow-cuda"]) == 0
    env = launched[0][1]["env"]
    assert env.get("CUDA_VISIBLE_DEVICES") == visibility
    assert env["VALIDATION_TEST_SENTINEL"] == "preserved"
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == visibility


@pytest.mark.parametrize("broken", ["empty", "duplicate", "missing", "outside"])
def test_invalid_registry_stops_before_launch(registry, launched, monkeypatch, broken):
    root, names = registry
    if broken == "empty":
        monkeypatch.setattr(runner, "VALIDATION_TESTS", [])
    elif broken == "duplicate":
        monkeypatch.setattr(runner, "VALIDATION_TESTS", [names[0], names[0]])
    elif broken == "missing":
        (root / names[0]).unlink()
    else:
        outside = root.parent / "outside.py"
        outside.write_text("")
        (root / names[0]).unlink()
        (root / names[0]).symlink_to(outside)
    with pytest.raises(SystemExit) as exc:
        runner.main([])
    assert exc.value.code == 2
    assert not launched


@pytest.mark.parametrize(
    "child_status, expected", [(0, 0), (1, 1), (2, 2), (5, 5), (-2, 130), (-15, 143)]
)
def test_child_exit_status_is_preserved(registry, monkeypatch, child_status, expected):
    monkeypatch.setattr(runner.subprocess, "call", lambda *args, **kwargs: child_status)
    assert runner.main([]) == expected


@pytest.mark.parametrize(
    "error, status", [(OSError("cannot execute"), 1), (KeyboardInterrupt(), 130)]
)
def test_launch_failure_and_interrupt_are_concise(
    registry, monkeypatch, capsys, error, status
):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(runner.subprocess, "call", fail)
    assert runner.main([]) == status
    captured = capsys.readouterr()
    assert captured.err
    assert "Traceback" not in captured.err


@pytest.fixture
def cli_checkout(tmp_path):
    """Run the real launcher with a stdlib-only stand-in for the pytest child."""
    root = tmp_path / "other checkout with spaces"
    (root / "scripts").mkdir(parents=True)
    script = root / "scripts/run_validation_tests.py"
    shutil.copyfile(runner.__file__, script)
    for name in runner.VALIDATION_TESTS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    (root / "pytest.py").write_text(
        "import json, os, sys\n"
        "print(json.dumps({'cwd': os.getcwd(), 'args': sys.argv[1:], "
        "'cuda': os.environ.get('CUDA_VISIBLE_DEVICES'), 'python': sys.executable}))\n"
        "raise SystemExit(int(os.environ.get('VALIDATION_TEST_EXIT', '0')))\n"
    )
    # Either import would fail if listing or launching eagerly loaded ML modules.
    (root / "torch.py").write_text(
        "raise AssertionError('torch imported by launcher')\n"
    )
    elsewhere = tmp_path / "caller"
    elsewhere.mkdir()

    def run(*arguments, exit_code=0):
        return subprocess.run(
            [sys.executable, str(script), *arguments],
            cwd=elsewhere,
            env={
                **os.environ,
                "CUDA_VISIBLE_DEVICES": "5",
                "VALIDATION_TEST_EXIT": str(exit_code),
            },
            capture_output=True,
            text=True,
            timeout=30,
        )

    return root, run


@pytest.mark.parametrize("allow_cuda", [False, True])
def test_actual_cli_launches_in_its_own_checkout(cli_checkout, allow_cuda):
    root, run = cli_checkout
    args = ["--allow-cuda"] if allow_cuda else []
    result = run(
        *args, "--match", "*validation_runner*", "--", "-k", "one or two", exit_code=5
    )
    assert result.returncode == 5, result.stderr
    child = json.loads(result.stdout.splitlines()[-1])
    assert child["cwd"] == str(root)
    assert child["args"] == [
        "-q",
        "tests/test_validation_runner.py",
        "-k",
        "one or two",
    ]
    assert child["cuda"] == ("5" if allow_cuda else "")
    assert child["python"] == sys.executable


def test_actual_cli_listing_starts_no_child(cli_checkout):
    _, run = cli_checkout
    result = run("--list", "--match", "*validation_runner*")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "tests/test_validation_runner.py\n"
    assert not result.stderr
