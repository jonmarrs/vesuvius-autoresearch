"""The #519 post-merge follow-ups to the checkpoint gate (Reviewer LOW-1..4, NIT-1..4).

- LOW-1: the audit runs under ``python -I`` with no package installed.
- LOW-2: scheme-like and fsspec ``::`` path strings are refused, and loaders get the absolute local path.
- LOW-3: every Lightning ``load_from_checkpoint(weights_only=False)`` is audited first.
- LOW-4: a pickle that BUILDs onto a class object (rewriting an allowlisted class) is refused.
- NIT-1: a record the reader lists but cannot read is REFUSED, not a traceback.
- NIT-2: a file object is audited from its current position, where torch.load reads it.
- NIT-3: the scripts load this checkout's gate by path, so another package of that name cannot replace it.
- NIT-4: the GP wrapper sets its cleanup trap before the copy and passes the checksum as arguments.
"""

from __future__ import annotations

import ast
import collections
import hashlib
import importlib
import importlib.util
import io
import os
import pickle
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"
AUDIT = CONTROL / "audit_pickle.py"
CHECKER = ROOT / "repro/first_letters/pherc343/check_ckpt_safe.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = _load("audit_pickle_519_followups", AUDIT)
checkpoints = importlib.import_module("vesuvius_autoresearch.core.checkpoint_tools")
refusal = importlib.import_module("vesuvius_autoresearch.core.checkpoint_refusal")
NON_ZIP = refusal.NON_ZIP_CHECKPOINT


def _zip_of(path: Path, data: bytes, name: str = "archive/data.pkl") -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("archive/version", b"3\n")
        archive.writestr("archive/byteorder", b"little")
        archive.writestr(name, data)
    path.write_bytes(buf.getvalue())


class _Touch:
    def __init__(self, marker: Path):
        self.marker = marker

    def __reduce__(self):
        return (os.system, (f"touch {self.marker}",))


def _run(args, **kwargs):
    env = kwargs.pop("env", None)
    base = {"PATH": os.environ.get("PATH", ""), "CUDA_VISIBLE_DEVICES": ""}
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={**base, **(env or {})},
        **kwargs,
    )


# --- LOW-1: python -I, no package -------------------------------------------------------------------------------


def test_the_audit_refuses_cleanly_under_isolated_python_without_the_package(tmp_path):
    # -S drops site-packages too, so no installed or editable copy of the package can be found.
    legacy = tmp_path / "legacy.pt"
    legacy.write_bytes(pickle.dumps({"w": 1}, protocol=2))
    result = _run([sys.executable, "-I", "-S", str(AUDIT), str(legacy)], cwd=tmp_path)
    assert "ModuleNotFoundError" not in result.stderr, result.stderr
    assert result.returncode == 1, result.stderr
    assert f"REFUSED: {legacy} {NON_ZIP}" in result.stderr


def test_the_audit_passes_a_state_dict_under_isolated_python(tmp_path):
    good = tmp_path / "good.pt"
    torch.save({"w": torch.zeros(2)}, good)
    result = _run([sys.executable, "-I", str(AUDIT), str(good)], cwd=tmp_path)
    assert result.returncode == 0, result.stderr


# --- NIT-3: another vesuvius_autoresearch on sys.path cannot supply the gate --------------------------------------


def _shadow_package(root: Path) -> Path:
    core = root / "vesuvius_autoresearch" / "core"
    core.mkdir(parents=True)
    (root / "vesuvius_autoresearch" / "__init__.py").write_text("")
    (core / "__init__.py").write_text("")
    (core / "checkpoint_refusal.py").write_text(
        'NON_ZIP_CHECKPOINT = "SHADOW SENTENCE"\n'
        "def require_zip_checkpoint(source):\n    return None\n"
    )
    return root


def test_a_regular_package_on_the_path_does_not_replace_the_audits_sentence(tmp_path):
    shadow = _shadow_package(tmp_path / "shadow")
    legacy = tmp_path / "legacy.pt"
    legacy.write_bytes(pickle.dumps({"w": 1}, protocol=2))
    result = _run(
        [sys.executable, str(AUDIT), str(legacy)],
        cwd=tmp_path,
        env={"PYTHONPATH": str(shadow)},
    )
    assert result.returncode == 1
    assert "SHADOW SENTENCE" not in result.stderr
    assert NON_ZIP in result.stderr


def test_a_regular_package_on_the_path_does_not_replace_the_checkers_zip_gate(tmp_path):
    shadow = _shadow_package(tmp_path / "shadow")
    legacy = tmp_path / "legacy.pt"
    # A legacy tensor pickle loads under weights_only=True, so only the zip gate refuses it.
    torch.save({"w": torch.zeros(1)}, legacy, _use_new_zipfile_serialization=False)
    result = _run(
        [sys.executable, str(CHECKER), str(legacy)],
        cwd=tmp_path,
        env={"PYTHONPATH": str(shadow)},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.startswith("NOT_WEIGHTS_ONLY legacy.pt"), result.stdout
    assert "convert it offline to zip" in result.stdout


# --- LOW-2: scheme-like and chained paths ------------------------------------------------------------------------

URL_LIKE = [
    "data:application/octet-stream;base64,UEsDBA==",
    "file:w.pt",
    "s3:bucket/w.pt",
    "hf://scrollprize/w.pt",
    "http:w.pt",
    "simplecache::w.pt",
    "memory::w.pt",
    "sub/simplecache::w.pt",
]


@pytest.mark.parametrize("name", URL_LIKE)
def test_a_path_fsspec_would_read_as_a_url_is_refused_even_when_a_file_has_that_name(
    tmp_path, monkeypatch, name
):
    monkeypatch.chdir(tmp_path)
    local = tmp_path / name
    try:
        local.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"w": torch.zeros(1)}, local)
    except (
        OSError
    ):  # a name the filesystem cannot hold: the refusal must not depend on it
        pass
    with pytest.raises(ValueError, match="refusing a checkpoint URL"):
        refusal.require_zip_checkpoint(name)
    with pytest.raises(ValueError, match="refusing a checkpoint URL"):
        checkpoints.load_checkpoint(name, weights_only=True)
    with pytest.raises(ValueError, match="refusing a checkpoint URL"):
        checkpoints.require_audited_checkpoint(Path(name))
    with pytest.raises(ValueError, match="refusing a checkpoint URL"):
        refusal.local_checkpoint_path(name)


def test_a_local_name_with_a_colon_after_a_slash_still_loads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "run1").mkdir()
    torch.save({"w": torch.zeros(1)}, tmp_path / "run1" / "w:1.pt")
    loaded = checkpoints.load_checkpoint("run1/w:1.pt", weights_only=True)
    assert tuple(loaded["w"].shape) == (1,)
    assert refusal.local_checkpoint_path("run1/w:1.pt") == str(
        tmp_path / "run1" / "w:1.pt"
    )


# --- LOW-3: the Lightning sites ----------------------------------------------------------------------------------

LIGHTNING_SITES = [
    "repro/sota_data/gt_finetune.py",
    "scripts/detector_depth_ablation.py",
    "scripts/detector_on_full_v2_sample.py",
    "scripts/detector_on_loop_sample.py",
    "scripts/detector_random_window_control.py",
    "src/vesuvius_autoresearch/detector/infer.py",
]


def _calls(tree: ast.AST) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            names.append(
                func.attr
                if isinstance(func, ast.Attribute)
                else getattr(func, "id", "")
            )
    return names


@pytest.mark.parametrize("relative", LIGHTNING_SITES)
def test_each_lightning_site_loads_through_the_audited_helper(relative):
    calls = _calls(ast.parse((ROOT / relative).read_text()))
    assert "load_lightning_checkpoint" in calls, relative
    assert "load_from_checkpoint" not in calls, relative
    assert "require_zip_checkpoint" not in calls, relative


class _FakeLightning:
    loads: list = []

    @classmethod
    def load_from_checkpoint(cls, path, **kwargs):
        cls.loads.append((path, kwargs))
        return "model"


def test_the_lightning_helper_audits_before_lightning_unpickles(tmp_path):
    marker = tmp_path / "ran"
    evil = tmp_path / "evil.ckpt"
    torch.save({"state_dict": {}, "hook": _Touch(marker)}, evil)
    _FakeLightning.loads = []
    with pytest.raises(ValueError, match="posix.system"):
        checkpoints.load_lightning_checkpoint(_FakeLightning, evil, cfg=None)
    assert _FakeLightning.loads == [] and not marker.exists()


def test_the_lightning_helper_hands_lightning_the_audited_absolute_path(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    model = torch.nn.Linear(2, 2)
    optimizer = torch.optim.AdamW(model.parameters())
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, 10)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "sched": scheduler,
            "dd": collections.defaultdict(dict),
        },
        tmp_path / "good.ckpt",
    )
    _FakeLightning.loads = []
    assert (
        checkpoints.load_lightning_checkpoint(_FakeLightning, "good.ckpt", cfg=1)
        == "model"
    )
    assert _FakeLightning.loads == [
        (str(tmp_path / "good.ckpt"), {"cfg": 1, "weights_only": False})
    ]
    with pytest.raises(ValueError, match="refusing a checkpoint URL"):
        checkpoints.load_lightning_checkpoint(_FakeLightning, "simplecache::good.ckpt")
    assert len(_FakeLightning.loads) == 1


# --- LOW-4: BUILD on a class -------------------------------------------------------------------------------------

_SCHED = b"ctorch.optim.lr_scheduler\nCosineAnnealingLR\n"
_STATE = b"N}X\x04\x00\x00\x00stepccollections\ndefaultdict\ns\x86"
BUILD_ON_CLASS_PICKLES = {
    "global": b"\x80\x02" + _SCHED + _STATE + b"b.",
    "memo": b"\x80\x02" + _SCHED + b"q\x000h\x00" + _STATE + b"b.",
    "stack_global": (
        b"\x80\x04\x8c\x18torch.optim.lr_scheduler\x94\x8c\x11CosineAnnealingLR\x94\x93\x94"
        + _STATE
        + b"b."
    ),
    "in_a_dict": b"\x80\x02}X\x01\x00\x00\x00k" + _SCHED + _STATE + b"bs.",
}


@pytest.mark.parametrize("kind", sorted(BUILD_ON_CLASS_PICKLES))
def test_a_build_on_a_class_is_refused(tmp_path, kind):
    data = BUILD_ON_CLASS_PICKLES[kind]
    names, refused = audit.imported(data)
    assert "torch.optim.lr_scheduler.CosineAnnealingLR" in names
    assert audit.BUILD_ON_CLASS in refused, (kind, refused)
    path = tmp_path / "patch.pt"
    _zip_of(path, data)
    result = audit.audit(path, set(checkpoints.CHECKPOINT_CLASS_ALLOW))
    assert result["outside_allowlist"] == [] and result["passes"] is False


def test_real_checkpoints_with_allowlisted_instances_still_pass(tmp_path):
    model = torch.nn.Linear(2, 2)
    optimizer = torch.optim.AdamW(model.parameters())
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, 10)
    # Stepped, so the optimizer carries per-parameter state as a trained checkpoint does.
    model(torch.ones(1, 2)).sum().backward()
    optimizer.step()
    scheduler.step()
    path = tmp_path / "full.pt"
    torch.save(
        {
            "state_dict": model.state_dict(),
            "optimizer": optimizer,
            "scheduler": scheduler,
            "dd": collections.defaultdict(dict, {"a": {}}),
            "optimizer_state": optimizer.state_dict(),
            "scheduler_state": scheduler.state_dict(),
        },
        path,
    )
    result = audit.audit(path, set(checkpoints.CHECKPOINT_CLASS_ALLOW))
    assert result["passes"], result
    for protocol in (2, 4, 5):
        names, refused = audit.imported(
            pickle.dumps(
                {"dd": collections.defaultdict(dict), "t": (1, [2], {3: 4})},
                protocol=protocol,
            )
        )
        assert refused == [], (protocol, refused)


# --- NIT-1: get_record failures ----------------------------------------------------------------------------------


def test_a_record_cut_at_a_nul_is_refused_not_raised(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("archive/version", b"3\n")
        archive.writestr("archive/byteorder", b"little")
        archive.writestr("archive/data.pklZ", pickle.dumps({"w": 1}, protocol=2))
    path = tmp_path / "nul.pt"
    # The reader lists "data.pkl" (cut at the NUL) and then cannot find it by that name.
    path.write_bytes(buf.getvalue().replace(b"data.pklZ", b"data.pkl\x00"))
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert result["message"] == audit.NON_ZIP_CHECKPOINT
    with pytest.raises(ValueError, match="convert it offline to zip"):
        checkpoints.load_checkpoint(path, weights_only=False)


def test_any_get_record_error_is_refused(tmp_path, monkeypatch):
    path = tmp_path / "w.pt"
    torch.save({"w": torch.zeros(1)}, path)
    real = torch._C.PyTorchFileReader

    class Reader:
        def __init__(self, name):
            self._inner = real(name)

        def get_all_records(self):
            return self._inner.get_all_records()

        def get_record(self, name):
            raise RuntimeError("synthetic get_record failure")

    monkeypatch.setattr(torch._C, "PyTorchFileReader", Reader)
    result = audit.audit(path, set())
    assert result["passes"] is False and result["message"] == audit.NON_ZIP_CHECKPOINT


# --- NIT-2: buffers are audited from where torch reads them -----------------------------------------------------


def _zip_bytes(value) -> bytes:
    buf = io.BytesIO()
    torch.save(value, buf)
    return buf.getvalue()


def test_a_buffer_is_audited_from_its_current_position(tmp_path):
    prefix = b"J" * 100
    buf = io.BytesIO(prefix + _zip_bytes({"w": torch.zeros(3)}))
    buf.seek(len(prefix))
    loaded = checkpoints.load_checkpoint(buf, weights_only=False)
    assert tuple(loaded["w"].shape) == (3,)


def test_a_malicious_zip_after_a_benign_one_is_refused_where_torch_would_read_it(
    tmp_path,
):
    marker = tmp_path / "ran"
    benign = _zip_bytes({"w": torch.zeros(1)})
    buf = io.BytesIO(benign + _zip_bytes(_Touch(marker)))
    buf.seek(len(benign))
    with pytest.raises(ValueError, match="posix.system"):
        checkpoints.load_checkpoint(buf, weights_only=False)
    assert buf.tell() == len(benign) and not marker.exists()


def test_the_audit_copy_restores_the_buffer_position():
    buf = io.BytesIO(b"abcdef")
    buf.seek(2)
    path, temporary = checkpoints._audit_path(buf)
    try:
        assert path.read_bytes() == b"cdef" and buf.tell() == 2
    finally:
        os.unlink(temporary)


# --- NIT-4: the GP wrapper ---------------------------------------------------------------------------------------


def _wrapper_tree(tmp_path: Path, run_dir: Path, cp_body: str | None = None):
    """The wrapper in a throwaway checkout layout, with stub env, interpreter and weights."""
    root = tmp_path / "repo"
    here = root / "repro/first_letters/pherc0211_control"
    here.mkdir(parents=True)
    weights = tmp_path / "gp" / "timesformer_weights.ckpt"
    weights.parent.mkdir()
    weights.write_bytes(b"stub weights")
    digest = hashlib.sha256(b"stub weights").hexdigest()
    text = (CONTROL / "run_gp_timesformer.sh").read_text()
    pinned = "93f56e569e1f4c66b71112c41985b64445b5245ff1fb610e44f495c2a0aee36f"
    assert f"CK_SHA256={pinned}" in text
    (here / "run_gp_timesformer.sh").write_text(
        text.replace(pinned, digest)
    )  # a test-only pin
    (here / "env.sh").write_text(
        f"C={_sh_quote(str(run_dir))}\n"
        "WINNER=$C/inputs/winner\nSEG_NAME=v9\nSEG=$WINNER/v9\nRENDER=$C/work/render\nMAPS=$C/work/maps\n"
        'mkdir -p "$C/work" "$C/logs"\n'
        'control_gate() { mkdir -p "$C/work/gate"; echo "$2" > "$C/work/gate/$1"; }\n'
    )
    (root / "villa/deprecated/ink-detection").mkdir(parents=True)
    (root / "villa/deprecated/ink-detection/inference_timesformer.py").write_text("")
    (weights.parent / ".venv-gp/bin").mkdir(parents=True)
    pygp = weights.parent / ".venv-gp/bin/python"
    pygp.write_text("#!/bin/sh\nexit 0\n")
    pygp.chmod(0o755)
    (run_dir / "work/render/0").mkdir(parents=True)
    (run_dir / "work/maps_reader_v3/v9").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pyw = bin_dir / "pyw"
    pyw.write_text("#!/bin/sh\nexit 3\n")  # the audit step stops the run here
    pyw.chmod(0o755)
    if cp_body is not None:
        fake_cp = bin_dir / "cp"
        fake_cp.write_text("#!/bin/bash\n" + cp_body)
        fake_cp.chmod(0o755)
    env = {
        "GP_DIR": str(weights.parent),
        "PYW": str(pyw),
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
    }
    return here / "run_gp_timesformer.sh", env


def _sh_quote(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


@pytest.mark.skipif(
    shutil.which("sha256sum") is None, reason="needs coreutils sha256sum"
)
def test_the_checksum_step_survives_a_quote_in_the_run_directory(tmp_path):
    run_dir = tmp_path / "o'brien run"
    script, env = _wrapper_tree(tmp_path, run_dir)
    result = _run(["bash", str(script)], env=env)
    gate = run_dir / "work/gate"
    assert (gate / "gp_checksum").read_text().strip() == "0", (
        result.stdout + result.stderr
    )
    assert (gate / "gp_audit").read_text().strip() == "3"
    assert list((run_dir / "work/tmp").glob("gpck.*")) == []


def test_an_interrupt_during_the_copy_leaves_no_copy_behind(tmp_path):
    run_dir = tmp_path / "run"
    # cp writes part of the copy, then the wrapper is terminated mid-copy.
    script, env = _wrapper_tree(
        tmp_path,
        run_dir,
        cp_body='printf partial > "${@: -1}"\nkill -TERM "$PPID"\nsleep 5\n',
    )
    result = _run(["bash", str(script)], env=env)
    assert result.returncode != 0
    assert not (run_dir / "work/gate/gp_checksum").exists()
    assert list((run_dir / "work/tmp").glob("gpck.*")) == [], result.stderr
