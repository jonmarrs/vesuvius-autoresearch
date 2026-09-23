"""set_cache_gb.sh bakes a render cache size into ONE work dir, with provenance.

The setting must live in the work dir (its wrapper and RENDER_IMAGE), not in the
environment at render time, so two arms of one study cannot silently differ.
"""

import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "repro" / "spiral_render"
SCRIPT = HERE / "set_cache_gb.sh"


def _workdir(tmp_path: Path) -> Path:
    w = tmp_path / "arm"
    shutil.copytree(HERE / "bin", w / "bin")
    (w / "RENDER_IMAGE").write_text("image=vc-render:local\nimage_id=sha256:x\n")
    return w


def run(*args):
    return subprocess.run(
        ["bash", str(SCRIPT), *map(str, args)], capture_output=True, text=True
    )


def test_bakes_the_flag_and_records_it(tmp_path):
    w = _workdir(tmp_path)
    r = run(w, 8)
    assert r.returncode == 0, r.stderr
    wrapper = (w / "bin" / "vc_render_tifxyz").read_text()
    assert '--scale-segmentation 4 --cache-gb 8 "$@"' in wrapper
    assert "cache_gb=8" in (w / "RENDER_IMAGE").read_text()
    # a broken wrapper would only fail hours into a render; it must still parse
    assert (
        subprocess.run(["sh", "-n", str(w / "bin" / "vc_render_tifxyz")]).returncode
        == 0
    )


def test_refuses_a_second_setting(tmp_path):
    w = _workdir(tmp_path)
    assert run(w, 8).returncode == 0
    r = run(w, 4)
    assert r.returncode != 0 and "already" in r.stderr
    assert "--cache-gb 4" not in (w / "bin" / "vc_render_tifxyz").read_text()


def test_refuses_a_non_integer(tmp_path):
    w = _workdir(tmp_path)
    r = run(w, "8GB")
    assert r.returncode != 0
    assert "--cache-gb" not in (w / "bin" / "vc_render_tifxyz").read_text()


def test_the_stock_wrapper_carries_no_cache_flag():
    """Default behaviour is unchanged: nothing is baked unless asked for."""
    assert "--cache-gb" not in (HERE / "bin" / "vc_render_tifxyz").read_text()
