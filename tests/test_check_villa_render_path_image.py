"""The upstream monitor must see the sampler's build path, not only the Python trees.

It fired four times in one morning on lasagna commits while the change that
actually touched the voxel sampler (vc_render_tifxyz.cpp, via #1695 and #1828)
was invisible to it, because HOT_PATH is four Python files and the sampler is a
C++ binary compiled into a docker image from a separate pin.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "check_villa_render_path.py"
VILLA = REPO / "villa"
PIN = "be09a8503"


def _has(ref: str) -> bool:
    return (
        subprocess.run(
            [
                "git",
                "-C",
                str(VILLA),
                "rev-parse",
                "--verify",
                "-q",
                f"{ref}^{{commit}}",
            ],
            capture_output=True,
        ).returncode
        == 0
    )


@pytest.mark.skipif(
    not VILLA.exists() or not _has(PIN), reason="villa submodule / pin not present"
)
def test_image_path_changes_are_reported_separately():
    """Against the real range where #1695/#1828 landed, the sampler's path must
    surface, and it must NOT be folded into HOT PATH (a VILLA_REF bump cannot
    fix it -- only an image rebuild can)."""
    if not _has("origin/main"):
        pytest.skip("no origin/main in villa")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), PIN, "origin/main"],
        capture_output=True,
        text=True,
    )
    assert "IMAGE PATH CHANGED" in r.stdout, r.stdout
    assert "vc_render_tifxyz.cpp" in r.stdout
    assert "RENDER_IMAGE" in r.stdout, (
        "must point the reader at the right provenance file"
    )
    # the image path is a separate section, not smuggled into HOT PATH
    hot = (
        r.stdout.split("HOT PATH CHANGED")[1].split("\n\n")[0]
        if "HOT PATH CHANGED" in r.stdout
        else ""
    )
    assert "volume-cartographer" not in hot


def test_image_prefixes_cover_the_sampler_and_its_core():
    src = SCRIPT.read_text()
    for needle in (
        "volume-cartographer/apps/src/vc_render_tifxyz",
        "volume-cartographer/core/",
        "volume-cartographer/utils/",
    ):
        assert needle in src, f"IMAGE_PATH_PREFIXES lost {needle}"


def test_image_path_is_not_in_hot_path():
    """Keeping them separate is the point: HOT_PATH means 'bump VILLA_REF',
    IMAGE PATH means 'rebuild the image'. Conflating them misdirects the fix."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("cvrp", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert not any(p.startswith("volume-cartographer") for p in m.HOT_PATH)
