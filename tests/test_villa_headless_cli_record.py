"""villa #2259's PR record must state what its captured evidence shows.

`docs/VILLA_DRAFT_headless_appimage_cli.md` is the record of an upstream
documentation PR. Its proof table, release and patch size were typed from
`reports/evidence/villa_headless_cli_2026-10-23.json` and the committed patch.
These tests read them back from those files.
"""

import json
import signal
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DRAFT = _REPO / "docs" / "VILLA_DRAFT_headless_appimage_cli.md"
_EVIDENCE = _REPO / "reports" / "evidence" / "villa_headless_cli_2026-10-23.json"
_PATCH = _REPO / "docs" / "villa_pr_headless_appimage_cli.patch"


def _results():
    return {r["name"]: r for r in json.loads(_EVIDENCE.read_text())["results"]}


def test_the_proof_table_is_the_captured_runs():
    r, draft = _results(), _DRAFT.read_text()
    direct = r["direct-render-help"]
    # a negative return code is the signal; the shell reports 128 + signal
    sig = signal.Signals(-direct["returncode"])
    assert direct["output"] == ""
    assert (
        f"| `./squashfs-root/usr/bin/vc_render_tifxyz --help` | {sig.name}; shell status "
        f"{128 + sig.value}; no output |"
    ) in draft
    for name, row in (
        ("apprun-render-help", "| `./squashfs-root/AppRun vc_render_tifxyz --help` |"),
        ("extract-and-run-help", "./VC3D.AppImage vc_render_tifxyz --help` |"),
    ):
        assert r[name]["returncode"] == 0, name
        assert r[name]["output"].startswith("vc_render_tifxyz: Render"), name
        assert f"{row} Help printed, exit 0 |" in draft, name
    trim = r["apprun-trim-usage"]
    assert trim["returncode"] == 1 and trim["output"].startswith("usage:")
    assert (
        "| `./squashfs-root/AppRun vc_tifxyz_trim` | Usage printed, expected exit 1 |"
        in draft
    )


def test_the_release_and_environment_are_the_evidence():
    e, draft = json.loads(_EVIDENCE.read_text()), _DRAFT.read_text()
    assert f"`{e['release']}`" in draft
    assert f"`{e['sha256']}`" in draft
    flat = " ".join(draft.split())  # rewrapping the record is harmless
    assert e["display_unset"] and "`DISPLAY` and `WAYLAND_DISPLAY` unset" in flat
    assert e["host"] == "Debian 13 x86_64" and "On Debian 13 x86_64" in draft


def test_the_patch_size_is_the_committed_patch():
    files, plus, minus = 0, 0, 0
    for chunk in _PATCH.read_text().split("diff --git ")[1:]:
        files += 1
        lines = chunk.split("\n@@", 1)[1].splitlines()
        plus += sum(x.startswith("+") and not x.startswith("+++") for x in lines)
        minus += sum(x.startswith("-") and not x.startswith("---") for x in lines)
    words = {1: "One", 2: "Two", 3: "Three"}
    assert (
        f"{words[files]} documentation files, +{plus}/-{minus} lines."
        in _DRAFT.read_text()
    )
