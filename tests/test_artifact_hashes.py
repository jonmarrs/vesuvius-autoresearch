"""CPU artifact operations must not depend on checkpoint reconstruction."""

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.artifact_hashes import sha256_file

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("payload", [b"", b"known content", b"x" * (1024 * 1024 + 17)])
def test_hash_matches_sha256_across_read_boundaries(tmp_path, payload):
    source = tmp_path / "source.bin"
    source.write_bytes(payload)
    assert sha256_file(source) == hashlib.sha256(payload).hexdigest()


def test_missing_source_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path / "missing")


def test_checkpoint_export_preserves_the_old_hash_api():
    from scripts import export_for_production

    assert export_for_production.sha256_file is sha256_file


def test_cpu_reports_and_mask_preparation_do_not_import_torch(tmp_path):
    # A fresh interpreter makes transitive imports observable, even after other
    # tests have imported PyTorch. Reject the dependency, rather than timing it.
    code = """
import importlib.abc
import sys
from pathlib import Path
class NoTorch(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'torch' or fullname.startswith('torch.'):
            raise ImportError('CPU artifact operation imported torch')
sys.meta_path.insert(0, NoTorch())
from scripts import cross_scroll_validation, spatial_split_mask
import numpy as np
from PIL import Image
root = Path(sys.argv[1])
source = root / 'mask.png'
Image.fromarray(np.full((8,8), 255, dtype=np.uint8)).save(source)
assert cross_scroll_validation.sha256_file(source)
result = spatial_split_mask.prepare_split(source, root/'split', buffer=0)
assert result['source_positive_pixels'] == 64
assert 'torch' not in sys.modules
"""
    run = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 0, run.stderr
