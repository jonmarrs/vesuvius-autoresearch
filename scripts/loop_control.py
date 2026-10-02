"""Control the loop registered in this checkout's lock, without process-name scans."""

import argparse
import fcntl
import os
import signal
import sys
import time
from pathlib import Path


def acquire_lock(path):
    # Never truncate before acquiring: a second launcher must not erase the PID
    # of the loop that already owns the lock.
    stream = open(path, "a+")
    try:
        fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stream.seek(0)
        stream.truncate()
        stream.write(f"{os.getpid()}\n")
        stream.flush()
    except BaseException:
        stream.close()
        raise
    return stream


def running_pid(repo):
    path = repo / "autoresearch.lock"
    if not path.exists():
        return None
    with path.open("r+") as stream:
        try:
            fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            value = stream.read().strip()
            if not value.isdigit() or int(value) <= 1:
                raise RuntimeError("loop lock is held but contains no valid PID")
            pid = int(value)
            # Also verify checkout and script so foreign metadata cannot target
            # another job. /proc is available on the supported Linux GPU hosts.
            try:
                proc = Path(f"/proc/{pid}")
                args = proc.joinpath("cmdline").read_bytes().split(b"\0")
                if not any(args):
                    return None  # exiting/zombie process; there is nothing to signal
                cwd = proc.joinpath("cwd").resolve(strict=True)
            except FileNotFoundError:
                return None
            if cwd != repo.resolve() or not any(
                Path(os.fsdecode(arg)).name == "run_autoresearch_loop.py"
                for arg in args if arg
            ):
                raise RuntimeError("lock PID does not identify this checkout's loop")
            return pid
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "stop"])
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    if args.action == "stop":
        (repo / ".loop_paused").touch()
    try:
        pid = running_pid(repo)
        if args.action == "status":
            if pid is not None:
                print(f"Autoresearch loop is running (PID {pid}).")
            return 0 if pid is not None else 1
        if pid is None:
            print("No autoresearch loop running. Watchdog paused.")
            return 0
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if running_pid(repo) != pid:
                print("Autoresearch loop stopped. Watchdog paused.")
                return 0
            time.sleep(0.1)
        raise RuntimeError(f"loop PID {pid} did not stop within {args.timeout:g}s; watchdog remains paused")
    except (OSError, RuntimeError) as exc:
        print(f"loop control: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
