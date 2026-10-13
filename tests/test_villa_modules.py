"""Pinned villa leaf modules load by path, independent of import order and cwd.

Before this, villa's TTA was imported after prepending villa/vesuvius/src to
sys.path: following an earlier `import vesuvius` it silently returned the older
installed snapshot, and preceding one it replaced `vesuvius` for the whole process.
The lasagna uint8 warp prepended the relative path "villa/lasagna", which resolved
only from the repository root; elsewhere its failure was caught and flattening was
silently skipped.
"""

from __future__ import annotations

import ast
import sys
import types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from importlib.machinery import SourceFileLoader
from pathlib import Path
from threading import Event

import pytest

from vesuvius_autoresearch.core import villa_modules
from vesuvius_autoresearch.core.villa_modules import load_villa_leaf, non_leaf_imports

REPO = Path(__file__).resolve().parents[1]
PINNED_LEAVES = (
    "vesuvius/src/vesuvius/models/run/tta.py",  # villa_inference._load_villa_tta
    "lasagna/grid_sample_3d_u8.py",  # VesuviusLabeledDataset lasagna uint8 warp
)


def _tree(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


@pytest.fixture
def installed_vesuvius(monkeypatch):
    """An already-imported `vesuvius` package that is not the pinned one."""
    fake = types.ModuleType("vesuvius")
    fake.__path__ = []
    monkeypatch.setitem(sys.modules, "vesuvius", fake)
    return fake


def test_leaf_loads_from_its_file_without_touching_import_state(
    tmp_path, installed_vesuvius
):
    root = _tree(
        tmp_path / "villa", {"pkg/run/tta.py": "import math\nWHO = 'pinned'\n"}
    )
    path_before = list(sys.path)
    module = load_villa_leaf("pkg/run/tta.py", villa_root=root)
    assert module.WHO == "pinned"
    assert Path(module.__file__) == (root / "pkg/run/tta.py").resolve()
    assert sys.path == path_before
    assert sys.modules["vesuvius"] is installed_vesuvius


def test_leaf_executes_once_per_process(tmp_path):
    log = tmp_path / "executions"
    root = _tree(
        tmp_path / "villa",
        {"leaf.py": f"with open({str(log)!r}, 'a') as f:\n    f.write('x')\n"},
    )
    assert load_villa_leaf("leaf.py", villa_root=root) is load_villa_leaf(
        "leaf.py", villa_root=root
    )
    assert log.read_text() == "x"


@pytest.mark.parametrize(
    "source",
    [
        "from . import blending\n",
        "from .blending import blend\n",
        "from vesuvius.models import build\n",
        "import vesuvius.data\n",
        "import blending\n",  # a sibling file, absolute
        "def f():\n    from blending import blend\n",  # nested imports count too
    ],
)
def test_a_module_that_imports_outside_its_file_is_refused(tmp_path, source):
    root = _tree(tmp_path / "villa", {"run/tta.py": source, "run/blending.py": ""})
    before = set(sys.modules)
    with pytest.raises(ImportError, match="leaf"):
        load_villa_leaf("run/tta.py", villa_root=root)
    assert set(sys.modules) == before


def test_a_failed_execution_is_not_cached(tmp_path):
    root = _tree(tmp_path / "villa", {"leaf.py": "raise RuntimeError('boom')\n"})
    before = set(sys.modules)
    with pytest.raises(RuntimeError, match="boom"):
        load_villa_leaf("leaf.py", villa_root=root)
    assert set(sys.modules) == before


@pytest.mark.parametrize("first_fails", [False, True])
def test_concurrent_callers_wait_for_module_initialization(
    tmp_path, monkeypatch, first_fails
):
    root = _tree(tmp_path / "villa", {"leaf.py": "READY = 'complete'\n"})
    initializing, release, second_started = Event(), Event(), Event()
    execute = SourceFileLoader.exec_module
    attempts = []

    def paused_execution(loader, module):
        if Path(loader.path) == root / "leaf.py":
            attempts.append(module)
            if len(attempts) == 1:
                initializing.set()
                assert release.wait(5), "test did not release the initializer"
                if first_fails:
                    raise RuntimeError("first initializer failed")
        return execute(loader, module)

    def second_call():
        second_started.set()
        return load_villa_leaf("leaf.py", villa_root=root)

    monkeypatch.setattr(SourceFileLoader, "exec_module", paused_execution)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(load_villa_leaf, "leaf.py", villa_root=root)
        try:
            assert initializing.wait(5)
            second = pool.submit(second_call)
            assert second_started.wait(5)
            with pytest.raises(FutureTimeout):
                second.result(timeout=0.2)
        finally:
            release.set()
        if first_fails:
            with pytest.raises(RuntimeError, match="first initializer failed"):
                first.result(timeout=5)
            assert second.result(timeout=5).READY == "complete"
            assert len(attempts) == 2
        else:
            assert first.result(timeout=5) is second.result(timeout=5)
            assert len(attempts) == 1
        assert second.result(timeout=5).READY == "complete"


def test_a_slow_module_does_not_block_a_different_module(tmp_path, monkeypatch):
    root = _tree(
        tmp_path / "villa", {"slow.py": "READY = 1\n", "other.py": "READY = 2\n"}
    )
    initializing, release = Event(), Event()
    execute = SourceFileLoader.exec_module

    def paused_execution(loader, module):
        if Path(loader.path) == root / "slow.py":
            initializing.set()
            assert release.wait(5)
        return execute(loader, module)

    monkeypatch.setattr(SourceFileLoader, "exec_module", paused_execution)
    with ThreadPoolExecutor(max_workers=2) as pool:
        slow = pool.submit(load_villa_leaf, "slow.py", villa_root=root)
        try:
            assert initializing.wait(5)
            other = pool.submit(load_villa_leaf, "other.py", villa_root=root)
            assert other.result(timeout=2).READY == 2
        finally:
            release.set()
        assert slow.result(timeout=5).READY == 1


def test_a_missing_file_names_the_submodule_step(tmp_path):
    with pytest.raises(FileNotFoundError, match="git submodule update --init villa"):
        load_villa_leaf("lasagna/absent.py", villa_root=tmp_path)


@pytest.mark.parametrize("relative", PINNED_LEAVES)
def test_files_loaded_as_leaves_are_still_leaves_at_this_pin(relative):
    """A villa bump that gives these files sibling imports fails here, on CPU,
    instead of inside a GPU training run."""
    path = villa_modules.VILLA_ROOT / relative
    if not path.is_file():
        pytest.skip("villa submodule not checked out")
    assert non_leaf_imports(path) == []


def test_package_code_puts_no_relative_path_on_sys_path():
    """A relative sys.path entry resolves against the process cwd, not the repo."""
    offenders = []
    for path in sorted((REPO / "src").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"insert", "append"}
                and ast.unparse(node.func.value) == "sys.path"
                and any(
                    isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                    for arg in node.args
                )
            ):
                offenders.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert not offenders, offenders


# --- call sites (they import torch) --------------------------------------------


def test_villa_tta_is_the_pinned_file_whatever_was_imported_first(
    tmp_path, monkeypatch, installed_vesuvius
):
    pytest.importorskip("torch")
    from vesuvius_autoresearch.core import villa_inference

    root = _tree(
        tmp_path / "villa",
        {
            villa_inference._VILLA_TTA: "def infer_with_tta(*a, **k):\n    return 'pinned'\n"
        },
    )
    monkeypatch.setattr(villa_modules, "VILLA_ROOT", root)
    path_before = list(sys.path)
    assert villa_inference._load_villa_tta()() == "pinned"
    assert sys.path == path_before
    assert sys.modules["vesuvius"] is installed_vesuvius


def _lasagna_dataset():
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    dataset = VesuviusLabeledDataset.__new__(VesuviusLabeledDataset)
    dataset.use_lasagna = True
    dataset.volume = types.SimpleNamespace(uri="synthetic")
    return dataset


def _contract_checking_kernel(tmp_path):
    # Mirrors the TORCH_CHECKs in villa's grid_sample_3d_u8_kernel.cu.
    return _tree(
        tmp_path / "villa",
        {
            "lasagna/grid_sample_3d_u8.py": (
                "CALLS = []\n"
                "def grid_sample_3d_u8(vol, grid, offset, inv_scale):\n"
                "    assert vol.is_cuda and vol.dim() == 4, 'volume must be CUDA (C, Z, Y, X)'\n"
                "    assert grid.is_cuda and grid.dim() == 4 and grid.shape[3] == 3, 'grid must be CUDA (D, H, W, 3)'\n"
                "    assert offset.is_cuda and inv_scale.is_cuda\n"
                "    CALLS.append((tuple(vol.shape), tuple(grid.shape)))\n"
                "    return vol + 1\n"
            )
        },
    )


def test_lasagna_uint8_warp_runs_outside_the_repository_root(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("villa's uint8 kernel takes CUDA tensors")
    root = _contract_checking_kernel(tmp_path)
    monkeypatch.setattr(villa_modules, "VILLA_ROOT", root)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    patch = torch.zeros((5, 8, 8), dtype=torch.uint8, device="cuda")
    path_before = list(sys.path)

    warped = _lasagna_dataset()._apply_lasagna_flattening(patch)

    assert torch.equal(warped, patch + 1), "warp skipped: flattening silently disabled"
    assert load_villa_leaf("lasagna/grid_sample_3d_u8.py", villa_root=root).CALLS == [
        ((1, 5, 8, 8), (5, 8, 8, 3))
    ]
    assert sys.path == path_before


@pytest.mark.parametrize("strict", [False, True])
def test_a_cpu_uint8_patch_is_refused_before_the_kernel_loads(
    tmp_path, monkeypatch, strict
):
    """The loader reads uint8 patches on the CPU. The kernel cannot take them, so the
    refusal names that, rather than the JIT compile failure it used to hit first."""
    torch = pytest.importorskip("torch")
    from vesuvius_autoresearch.core import vesuvius_loader

    loaded = []
    monkeypatch.setattr(
        villa_modules, "load_villa_leaf", lambda *a, **k: loaded.append(a)
    )
    monkeypatch.setattr(vesuvius_loader, "_WARNING_COUNTS", defaultdict(int))
    dataset = _lasagna_dataset()
    dataset.strict_reads = strict
    patch = torch.full((5, 8, 8), 7, dtype=torch.uint8)

    if strict:
        with pytest.raises(
            RuntimeError, match="takes CUDA tensors; this patch is on cpu"
        ):
            dataset._apply_lasagna_flattening(patch)
    else:
        assert dataset._apply_lasagna_flattening(patch) is patch
        assert vesuvius_loader.warning_counts() == {"lasagna_warp_failed": 1}
    assert loaded == []
