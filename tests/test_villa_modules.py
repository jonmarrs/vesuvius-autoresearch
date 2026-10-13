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


def _contract_checking_kernel(tmp_path, device):
    # Mirrors the TORCH_CHECKs in villa's grid_sample_3d_u8_kernel.cu; on the CPU
    # only the device checks are left out.
    on = "x.is_cuda" if device == "cuda" else "True"
    return _tree(
        tmp_path / "villa",
        {
            "lasagna/grid_sample_3d_u8.py": (
                "import torch\n"
                "CALLS = []\n"
                f"def on_device(x): return {on}\n"
                "def grid_sample_3d_u8(vol, grid, offset, inv_scale):\n"
                "    assert on_device(vol) and vol.dtype == torch.uint8, 'volume must be CUDA uint8'\n"
                "    assert vol.dim() == 4, 'volume must be (C, Z, Y, X)'\n"
                "    assert vol.is_contiguous(), 'volume must be contiguous'\n"
                "    assert on_device(grid) and grid.dtype == torch.float32, 'grid must be CUDA float32'\n"
                "    assert grid.dim() == 4 and grid.shape[3] == 3, 'grid must be (D, H, W, 3)'\n"
                "    assert on_device(offset) and offset.numel() == 3, 'offset must be CUDA (3,)'\n"
                "    assert on_device(inv_scale) and inv_scale.numel() == 3, 'inv_scale must be CUDA (3,)'\n"
                "    CALLS.append((tuple(vol.shape), tuple(grid.shape)))\n"
                "    return vol + 1\n"
            )
        },
    )


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_lasagna_uint8_warp_runs_outside_the_repository_root(
    tmp_path, monkeypatch, device
):
    """The call meets the kernel's contract, and loads it by absolute path. On the
    CPU the loader's device refusal is bypassed so the rest of the path is covered."""
    torch = pytest.importorskip("torch")
    from vesuvius_autoresearch.core import vesuvius_loader

    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("villa's uint8 kernel takes CUDA tensors")
    if device == "cpu":
        monkeypatch.setattr(
            vesuvius_loader, "_lasagna_unavailable_reason", lambda p: None
        )
    root = _contract_checking_kernel(tmp_path, device)
    monkeypatch.setattr(villa_modules, "VILLA_ROOT", root)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    # A non-contiguous view, as a sliced volume read can produce.
    patch = torch.zeros((5, 8, 16), dtype=torch.uint8, device=device)[:, :, ::2]
    path_before = list(sys.path)

    warped = _lasagna_dataset()._apply_lasagna_flattening(patch)

    assert torch.equal(warped, patch + 1), "warp skipped: flattening silently disabled"
    assert load_villa_leaf("lasagna/grid_sample_3d_u8.py", villa_root=root).CALLS == [
        ((1, 5, 8, 8), (5, 8, 8, 3))
    ]
    assert sys.path == path_before


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize(
    ("dtype", "reason"),
    [
        ("uint8", "takes CUDA tensors; this patch is on cpu"),
        ("int32", "no lasagna warp for torch.int32 patches"),
        ("float16", "no lasagna warp for torch.float16 patches"),
        ("bfloat16", "no lasagna warp for torch.bfloat16 patches"),
    ],
)
def test_a_patch_the_warp_cannot_take_is_refused_before_any_work(
    tmp_path, monkeypatch, strict, dtype, reason
):
    """The loader reads uint8 patches on the CPU, which villa's kernel refuses, and
    uint16 volumes as int32, which no path warps; half precision fails mid-warp. The refusal names the reason (not
    the JIT compile failure the uint8 path used to hit first), and nothing is
    computed or loaded for it."""
    torch = pytest.importorskip("torch")
    from vesuvius_autoresearch.core import vesuvius_loader

    loaded = []
    monkeypatch.setattr(
        villa_modules, "load_villa_leaf", lambda *a, **k: loaded.append(a)
    )
    monkeypatch.setattr(
        torch.nn.functional, "softmax", lambda *a, **k: pytest.fail("surface computed")
    )
    monkeypatch.setattr(vesuvius_loader, "_WARNING_COUNTS", defaultdict(int))
    dataset = _lasagna_dataset()
    dataset.strict_reads = strict
    patch = torch.full((5, 8, 8), 7, dtype=getattr(torch, dtype))

    if strict:
        with pytest.raises(RuntimeError, match=reason):
            dataset._apply_lasagna_flattening(patch)
    else:
        assert dataset._apply_lasagna_flattening(patch) is patch
        assert vesuvius_loader.warning_counts() == {"lasagna_warp_failed": 1}
    assert loaded == []
