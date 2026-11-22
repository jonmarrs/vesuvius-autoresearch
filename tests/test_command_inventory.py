"""Command discovery must not import targets, start work or probe a GPU."""

import builtins
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import list_commands as cli
from vesuvius_autoresearch.core import command_inventory as catalog

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "configs/command_inventory.json"


def test_declared_entrypoints_and_guides_exist_and_module_prefixes_match():
    inventory, source = catalog.read_inventory(INVENTORY)
    assert source["sha256"] == hashlib.sha256(INVENTORY.read_bytes()).hexdigest()
    for row in inventory["commands"]:
        assert (ROOT / row["source"]).is_file(), row["id"]
        assert (ROOT / row["guide"]).is_file(), row["id"]
    by_id = {row["id"]: row for row in inventory["commands"]}
    assert (
        by_id["production-predict"]["stack"] == "torch"
    )  # even --dry-run imports Torch
    assert by_id["scroll-frames"]["stack"] != "stdlib"  # live CLI needs s3fs
    assert by_id["fiber-filter"]["layout"] == "wheel-or-checkout"
    assert by_id["loop-start"]["effects"] == "state"


def test_selection_preserves_inventory_order_and_refuses_unknown_or_empty_matches():
    inventory, _ = catalog.read_inventory(INVENTORY)
    selected = catalog.select_commands(inventory, stack="stdlib")
    assert selected == [
        row for row in inventory["commands"] if row["stack"] == "stdlib"
    ]
    for args in (
        {"command": "missing"},
        {"stack": "gpu"},
        {"command": "regional-predict", "stack": "stdlib"},
    ):
        with pytest.raises(ValueError):
            catalog.select_commands(inventory, **args)


def test_listing_never_imports_targets_or_starts_a_child(monkeypatch, capsys):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"numpy", "torch", "cupy", "napari", "webknossos"}:
            pytest.fail(f"catalog imported a runtime: {name}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    for name in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(
            subprocess, name, lambda *a, **k: pytest.fail("catalog started a command")
        )
    assert cli.main(["--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["readiness"] == "not_checked"
    assert any(row["id"] == "loop-start" for row in result["commands"])


def test_cli_discovery_from_another_directory_without_site_packages_or_writes(tmp_path):
    # A small checkout copy also exposes accidental pyc/output writes.
    for name in (
        "scripts/list_commands.py",
        "configs/command_inventory.json",
        "src/vesuvius_autoresearch/core/__init__.py",
        "src/vesuvius_autoresearch/core/command_inventory.py",
        "src/vesuvius_autoresearch/core/file_capture.py",
    ):
        path = tmp_path / "checkout" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())

    def tree():
        return {
            str(p.relative_to(tmp_path)): p.read_bytes()
            for p in tmp_path.rglob("*")
            if p.is_file()
        }

    before = tree()
    env = dict(os.environ, PYTHONPATH="", CUDA_VISIBLE_DEVICES="")
    run = subprocess.run(
        [
            sys.executable,
            "-S",
            str(tmp_path / "checkout/scripts/list_commands.py"),
            "--command",
            "proofreader-check",
            "--json",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result["commands"][0]["id"] == "proofreader-check"
    assert result["commands"][0]["villa"] == "required"
    assert result["readiness"] == "not_checked"
    assert tree() == before


@pytest.mark.parametrize(
    "case",
    [
        "version",
        "duplicate_id",
        "bad_stack",
        "bad_layout",
        "source_traversal",
        "mismatched_module",
        "shell_injection",
        "multiline",
        "missing_field",
    ],
)
def test_malformed_inventory_refuses_metadata_instead_of_falling_back(tmp_path, case):
    value = json.loads(INVENTORY.read_text())
    row = value["commands"][0]
    if case == "version":
        value["schema_version"] = True
    elif case == "duplicate_id":
        value["commands"].append(row.copy())
    elif case == "bad_stack":
        row["stack"] = "auto"
    elif case == "bad_layout":
        row["layout"] = "wheel"
    elif case == "source_traversal":
        row["source"] = "../scripts/list_commands.py"
    elif case == "mismatched_module":
        row.update(kind="module", argv=["python", "-m", "scripts.other"])
    elif case == "shell_injection":
        row["argv"] = ["python", "-c", "print('executed')"]
    elif case == "multiline":
        row["summary"] = "one\nsecond command"
    else:
        row.pop("guide")
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        catalog.read_inventory(path)


def test_inventory_size_and_duplicate_json_keys_are_refused(tmp_path):
    path = tmp_path / "inventory.json"
    path.write_bytes(b"x" * (catalog.MAX_INVENTORY_BYTES + 1))
    with pytest.raises(ValueError, match="exceeds"):
        catalog.read_inventory(path)
    path.write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(ValueError, match="duplicate"):
        catalog.read_inventory(path)


def test_report_identity_uses_the_parsed_capture_even_if_file_changes(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "inventory.json"
    raw = INVENTORY.read_bytes()
    path.write_bytes(raw)
    original = catalog.capture_bytes

    def captured(source, limit):
        result = original(source, limit)
        path.write_text("changed after capture")
        return result

    monkeypatch.setattr(catalog, "capture_bytes", captured)
    assert cli.main(["--inventory", str(path), "--command", "commands", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["commands"][0]["id"] == "commands"
    assert report["inventory_source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert (
        report["inventory_source"]["sha256"]
        != hashlib.sha256(path.read_bytes()).hexdigest()
    )


def test_cli_unknown_command_returns_a_concise_nonzero_error(capsys):
    assert cli.main(["--command", "does-not-exist"]) == 2
    assert "unknown command ID" in capsys.readouterr().err


def _row(**fields):
    return lambda value: value["commands"][0].update(fields)


def _top(**fields):
    return lambda value: value.update(fields)


_TOP = "unsupported command inventory"
_META = "nonempty single-line strings"
_CLASS = "invalid command boundary classification"
_PREFIX = "invalid command prefix/guide"
_SOURCE = "command prefix does not match its declared source"
_WHEEL = "packaged command must be a runtime module"
_PACKAGED = "src/vesuvius_autoresearch/core/command_inventory.py"


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        pytest.param(lambda value: list(value), _TOP, id="top_level_list"),
        pytest.param(_top(notes="x"), _TOP, id="extra_top_key"),
        pytest.param(_top(schema_version=2), _TOP, id="schema_2"),
        pytest.param(_top(scope="  "), _TOP, id="blank_scope"),
        pytest.param(_top(stacks=list(catalog.STACKS)), _TOP, id="stacks_list"),
        pytest.param(
            lambda value: value["stacks"].update(cuda="GPU"), _TOP, id="extra_stack"
        ),
        pytest.param(
            lambda value: value["stacks"].update(gui=""), _TOP, id="blank_stack"
        ),
        pytest.param(
            lambda value: value.update(
                commands={row["id"]: row for row in value["commands"]}
            ),
            _TOP,
            id="commands_dict",
        ),
        pytest.param(_top(commands=[]), _TOP, id="no_commands"),
        pytest.param(
            lambda value: value.update(
                commands=[dict(value["commands"][0], id=f"c{i}") for i in range(101)]
            ),
            _TOP,
            id="too_many_commands",
        ),
        pytest.param(_row(extra="x"), "invalid command inventory fields", id="field"),
        pytest.param(_row(summary="   "), _META, id="blank_summary"),
        pytest.param(_row(summary="one\x7f"), _META, id="delete_char"),
        pytest.param(_row(summary=5), _META, id="numeric_summary"),
        pytest.param(_row(needs=""), _META, id="blank_needs"),
        pytest.param(_row(summary="one\x85second"), _META, id="next_line"),
        pytest.param(_row(summary="one\x9bsecond"), _META, id="c1_control"),
        pytest.param(_row(summary="one second"), _META, id="line_separator"),
        pytest.param(_row(argv=["python", "x "]), _PREFIX, id="paragraph_sep"),
        pytest.param(_row(id="1commands"), "invalid or duplicate command ID", id="id"),
        pytest.param(_row(villa="maybe"), _CLASS, id="villa"),
        pytest.param(_row(effects="network"), _CLASS, id="effects"),
        pytest.param(_row(argv="pythonx"), _PREFIX, id="argv_string"),
        pytest.param(_row(argv=["python"]), _PREFIX, id="argv_short"),
        pytest.param(
            _row(argv=["python", "scripts/list_commands.py", *["--json"] * 15]),
            _PREFIX,
            id="argv_long",
        ),
        pytest.param(
            _row(argv=["python", "scripts/list_commands.py", ""]),
            _PREFIX,
            id="argv_blank",
        ),
        pytest.param(_row(guide="docs/COMMANDS.txt"), _PREFIX, id="guide_suffix"),
        pytest.param(_row(guide="docs/COMMAND NOTES.md"), _PREFIX, id="guide_space"),
        pytest.param(_row(guide="docs/../COMMANDS.md"), _PREFIX, id="guide_parent"),
        pytest.param(_row(guide="./docs/COMMANDS.md"), _PREFIX, id="guide_dot"),
        pytest.param(_row(guide="/docs/COMMANDS.md"), _PREFIX, id="guide_absolute"),
        pytest.param(
            _row(source="scripts/run.sh", argv=["python", "scripts/run.sh"]),
            _SOURCE,
            id="script_not_py",
        ),
        pytest.param(
            _row(kind="shell", source="scripts/run.sh", argv=["bash", "scripts/x.sh"]),
            _SOURCE,
            id="shell_other_script",
        ),
        pytest.param(
            _row(
                kind="shell", source="scripts/run.py", argv=["bash", "scripts/run.py"]
            ),
            _SOURCE,
            id="shell_not_sh",
        ),
        pytest.param(
            _row(
                kind="module", source="src/listing.py", argv=["python", "-m", "listing"]
            ),
            _SOURCE,
            id="module_without_package",
        ),
        pytest.param(
            _row(
                kind="module",
                source="scripts/list_commands.py",
                argv=["python", "-c", "scripts.list_commands"],
            ),
            _SOURCE,
            id="module_without_dash_m",
        ),
        pytest.param(_row(kind="binary"), _SOURCE, id="unknown_kind"),
        pytest.param(_row(layout="wheel-or-checkout"), _WHEEL, id="wheel_script"),
        pytest.param(
            _row(
                layout="wheel-or-checkout",
                source=_PACKAGED,
                argv=["python", _PACKAGED],
            ),
            _WHEEL,
            id="wheel_script_in_package",
        ),
        pytest.param(
            _row(
                layout="wheel-or-checkout",
                kind="module",
                source="src/other/tool.py",
                argv=["python", "-m", "other.tool"],
            ),
            _WHEEL,
            id="wheel_other_package",
        ),
    ],
)
def test_each_inventory_rule_refuses_its_own_edit(tmp_path, edit, message):
    value = json.loads(INVENTORY.read_text())
    replaced = edit(value)
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(value if replaced is None else replaced))
    with pytest.raises(ValueError, match=message):
        catalog.read_inventory(path)


def test_the_inventory_source_names_the_resolved_file_and_its_parsed_bytes():
    _, source = catalog.read_inventory(INVENTORY)
    raw = INVENTORY.read_bytes()
    assert source == {
        "path": str(INVENTORY.resolve()),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def test_an_unknown_stack_is_named_as_unknown():
    inventory, _ = catalog.read_inventory(INVENTORY)
    with pytest.raises(ValueError, match="unknown stack: gpu"):
        catalog.select_commands(inventory, stack="gpu")
