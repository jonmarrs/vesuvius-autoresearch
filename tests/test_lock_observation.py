"""Status must observe kernel ownership without reserving or releasing a lock."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import loop_control

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not Path("/proc/locks").exists(), reason="Linux /proc lock observation"
)


@pytest.fixture
def holder(tmp_path):
    processes = []

    def start(contents=b"999999999\n", *, name="run_autoresearch_loop.py", cwd=None):
        script = tmp_path / name
        script.write_text(
            "import fcntl,sys,time\n"
            "lock=open(sys.argv[1], 'wb')\n"
            "fcntl.lockf(lock, fcntl.LOCK_EX)\n"
            "lock.write(bytes.fromhex(sys.argv[2])); lock.flush()\n"
            "print('ready', flush=True)\n"
            "time.sleep(60)\n"
        )
        process = subprocess.Popen(
            [
                sys.executable,
                str(script),
                str(tmp_path / "autoresearch.lock"),
                contents.hex(),
            ],
            cwd=cwd or tmp_path,
            stdout=subprocess.PIPE,
            text=True,
        )
        processes.append(process)
        assert process.stdout is not None
        assert process.stdout.readline() == "ready\n"
        return process

    yield start
    for process in processes:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)
        if process.stdout is not None:
            process.stdout.close()


@pytest.mark.parametrize("contents", [b"", b"x", b"\xff", b"999999999\n"])
def test_kernel_owner_is_visible_despite_missing_or_stale_pid_text(
    tmp_path, holder, contents
):
    process = holder(contents)
    lock = tmp_path / "autoresearch.lock"
    before = lock.read_bytes(), lock.stat().st_mtime_ns
    assert loop_control.running_pid(tmp_path) == process.pid
    assert (lock.read_bytes(), lock.stat().st_mtime_ns) == before
    assert loop_control.main(["status", "--repo", str(tmp_path)]) == 0


def test_idle_inspection_never_opens_or_reserves_the_lock(tmp_path, monkeypatch):
    lock = tmp_path / "autoresearch.lock"
    lock.write_bytes(b"old PID text")
    original = Path.open

    def no_lock_open(path, *args, **kwargs):
        assert path != lock, "status must not open the research lock file"
        return original(path, *args, **kwargs)

    def no_acquisition(*args, **kwargs):
        raise AssertionError("status must not acquire the research lock")

    monkeypatch.setattr(Path, "open", no_lock_open)
    monkeypatch.setattr(loop_control.fcntl, "lockf", no_acquisition)
    assert loop_control.running_pid(tmp_path) is None


def test_owner_is_found_where_stat_reports_another_device(
    tmp_path, holder, monkeypatch
):
    """/proc/locks names the file system's own device; stat() reports a btrfs
    subvolume's, or an overlayfs layer's (layers on several file systems). A
    status that matched stat()'s device read such a loop as idle, and stop left
    it running. Simulated by shifting the device stat() gives for the lock."""
    process = holder()
    lock = tmp_path / "autoresearch.lock"
    real = lock.stat()
    real_stat, real_fstat, real_open = Path.stat, os.fstat, os.open

    def as_a_subvolume(result):
        if (result.st_dev, result.st_ino) != (real.st_dev, real.st_ino):
            return result
        fields = list(result[:10])
        fields[2] = os.makedev(os.major(real.st_dev), os.minor(real.st_dev) + 1)
        return os.stat_result(fields)

    def no_io_open(file, flags, *args, **kwargs):
        if Path(file) == lock:
            assert flags & os.O_PATH, "status must not open the lock for I/O"
        return real_open(file, flags, *args, **kwargs)

    monkeypatch.setattr(
        Path, "stat", lambda self, **kw: as_a_subvolume(real_stat(self, **kw))
    )
    monkeypatch.setattr(os, "fstat", lambda fd: as_a_subvolume(real_fstat(fd)))
    monkeypatch.setattr(os, "open", no_io_open)
    assert lock.stat().st_dev != real.st_dev
    assert loop_control.running_pid(tmp_path) == process.pid
    assert loop_control.main(["status", "--repo", str(tmp_path)]) == 0


def test_inspection_in_owner_process_does_not_release_its_lock(tmp_path):
    script = tmp_path / "run_autoresearch_loop.py"
    script.write_text(
        "import os,subprocess,sys\n"
        "from pathlib import Path\n"
        "from scripts.loop_control import acquire_lock,running_pid\n"
        "lock=acquire_lock('autoresearch.lock')\n"
        "assert running_pid(Path.cwd()) == os.getpid()\n"
        "probe=subprocess.run([sys.executable,'-c',\n"
        ' \'import fcntl; f=open("autoresearch.lock","a+"); '
        "fcntl.lockf(f,fcntl.LOCK_EX|fcntl.LOCK_NB)'],capture_output=True)\n"
        "assert probe.returncode != 0, 'status released the owner lock'\n"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("foreign", ["command", "checkout"])
def test_kernel_owner_still_requires_expected_command_and_checkout(
    tmp_path, holder, foreign, capsys
):
    elsewhere = tmp_path / "other"
    elsewhere.mkdir()
    process = holder(
        str(os.getpid()).encode(),
        name="unrelated.py" if foreign == "command" else "run_autoresearch_loop.py",
        cwd=elsewhere if foreign == "checkout" else tmp_path,
    )
    assert loop_control.main(["stop", "--repo", str(tmp_path), "--timeout", "0"]) == 2
    assert "does not identify this checkout's loop" in capsys.readouterr().err
    assert process.poll() is None


def test_symlink_lock_uses_target_inode(tmp_path, holder):
    target = tmp_path / "actual.lock"
    target.touch()
    (tmp_path / "autoresearch.lock").symlink_to(target)
    process = holder()
    assert loop_control.running_pid(tmp_path) == process.pid


def test_stale_live_pid_cannot_redirect_stop(tmp_path, holder):
    script = tmp_path / "promote_loop_candidate.py"
    script.write_text("import time\nprint('ready',flush=True)\ntime.sleep(60)\n")
    other = subprocess.Popen(
        [sys.executable, str(script)], cwd=tmp_path, stdout=subprocess.PIPE, text=True
    )
    try:
        assert other.stdout is not None and other.stdout.readline() == "ready\n"
        owner = holder(str(other.pid).encode())
        assert loop_control.running_pid(tmp_path) == owner.pid
        assert (
            loop_control.main(["stop", "--repo", str(tmp_path), "--timeout", "2"]) == 0
        )
        assert owner.wait(timeout=2) == -signal.SIGTERM
        assert other.poll() is None
    finally:
        other.kill()
        other.wait(timeout=2)
        if other.stdout is not None:
            other.stdout.close()


def test_workspace_json_reports_real_owner_without_changing_files(tmp_path, holder):
    for name in ("train", "val"):
        (tmp_path / name / "surface_volume.zarr").mkdir(parents=True)
        (tmp_path / name / "inklabels.png").write_bytes(b"not decoded")
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "uris": ["train/surface_volume.zarr"],
                "val_uri": "val/surface_volume.zarr",
                "unlabeled_uris": [],
            }
        )
    )
    process = holder()

    def snapshot():
        return {
            path.relative_to(tmp_path): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in tmp_path.rglob("*")
            if path.is_file()
        }

    before = snapshot()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/workspace_status.py"),
            "--repo",
            str(tmp_path),
            "--json",
        ],
        cwd=tmp_path.parent,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["process"]["pid"] == process.pid
    assert report["process"]["state"] == "running"
    assert report["training_readiness"] == "not_checked"
    assert snapshot() == before


def test_missing_kernel_observation_is_unknown_not_idle(tmp_path, monkeypatch, capsys):
    (tmp_path / "autoresearch.lock").touch()
    original = Path.read_text

    def unavailable(path, *args, **kwargs):
        if path == Path("/proc/locks"):
            raise PermissionError("lock-owner records unavailable")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unavailable)
    assert loop_control.main(["status", "--repo", str(tmp_path)]) == 2
    assert "records unavailable" in capsys.readouterr().err


def test_lock_path_replaced_during_observation_fails_closed(
    tmp_path, holder, monkeypatch
):
    holder()
    lock = tmp_path / "autoresearch.lock"
    original = Path.read_text

    def replace_lock(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path == Path("/proc/locks"):
            replacement = tmp_path / "replacement"
            replacement.touch()
            replacement.replace(lock)
        return result

    monkeypatch.setattr(Path, "read_text", replace_lock)
    with pytest.raises(RuntimeError, match="path changed during inspection"):
        loop_control.running_pid(tmp_path)


def test_queued_requests_are_not_treated_as_owners(tmp_path, holder, monkeypatch):
    process = holder()
    records = Path("/proc/locks").read_text()
    owner = next(row for row in records.splitlines() if f" {process.pid} " in row)
    queued = owner.replace("POSIX", "-> POSIX").replace(
        f" {process.pid} ", " 999999999 "
    )
    original = Path.read_text

    def with_waiter(path, *args, **kwargs):
        if path == Path("/proc/locks"):
            return records + "\n" + queued + "\n"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", with_waiter)
    assert loop_control.running_pid(tmp_path) == process.pid


def test_other_lock_protocol_is_unknown(tmp_path):
    path = tmp_path / "run_autoresearch_loop.py"
    path.write_text(
        "import fcntl,time\n"
        "lock=open('autoresearch.lock','w')\n"
        "fcntl.flock(lock,fcntl.LOCK_EX)\n"
        "print('ready',flush=True)\n"
        "time.sleep(60)\n"
    )
    process = subprocess.Popen(
        [sys.executable, str(path)], cwd=tmp_path, stdout=subprocess.PIPE, text=True
    )
    try:
        assert process.stdout is not None and process.stdout.readline() == "ready\n"
        with pytest.raises(RuntimeError, match="unsupported owner or lock type"):
            loop_control.running_pid(tmp_path)
    finally:
        process.kill()
        process.wait(timeout=2)
        if process.stdout is not None:
            process.stdout.close()
