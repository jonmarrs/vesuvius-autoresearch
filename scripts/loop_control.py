"""Control research work registered in this checkout's lock, without process-name scans."""

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
                raise RuntimeError(
                    "loop lock is held but contains no valid PID"
                ) from None
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
                Path(os.fsdecode(arg)).name
                in {
                    "run_autoresearch_loop.py",
                    "f1_noise_probe.py",
                    "scripts.f1_noise_probe",
                    "ablate_scroll_augmentations.py",
                    "scripts.ablate_scroll_augmentations",
                    "reevaluate_best_model.py",
                    "scripts.reevaluate_best_model",
                }
                for arg in args
                if arg
            ):
                raise RuntimeError(
                    "lock PID does not identify this checkout's loop"
                ) from None
            return pid
    return None


# The training scripts run in this checkout under a supervisor, each in a
# session of its own: the loop's train.py and the ablation's cell. Run here,
# both write run_result.json, and train.py the loop's files as well.
RUN_SCRIPTS = ("scripts/training/train.py", "scripts/train_with_new_augs.py")


def _stat_fields(pid):
    """/proc/<pid>/stat after the command name: [state, ppid, ...]."""
    with open(f"/proc/{pid}/stat") as f:
        return f.read().rsplit(")", 1)[1].split()


def _process_age(pid):
    """Seconds since pid started; None if unknown."""
    try:
        start = int(_stat_fields(pid)[19])
        with open("/proc/uptime") as f:
            uptime = float(f.read().split()[0])
        return uptime - start / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError):
        return None


def unsupervised_runs(repo, supervisor=None):
    """Training runs going in this checkout that no live supervisor owns, as
    (PID, age in seconds or None, whether a supervisor started it).

    A supervisor starts each run in a session of its own, so when the loop or
    the ablation is killed without its handler running (SIGKILL; a closed
    terminal), its run goes on, with no timeout: it can still write
    run_result.json and, for train.py, replace best_model.pt. A run started
    here by hand writes the same files. A run is an interpreter (python, uv)
    working in this checkout with one of RUN_SCRIPTS among its arguments, by
    path; an editor or pager open on the file is not one. A run whose session
    leader is a child of supervisor (the lock holder's PID) is that holder's
    own and is skipped. Supervisor-started runs are session leaders with a
    config_temp* config. A run's own processes (uv run's python child, with
    the same arguments) are part of it, not runs of their own. A run whose
    session leader is gone (uv killed alone) is listed as not started by a
    supervisor: what started it can no longer be told. Linux /proc only."""
    if not os.path.isdir("/proc"):
        return []
    repo = os.path.realpath(repo)
    scripts = {os.path.join(repo, name) for name in RUN_SCRIPTS}
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) == os.getpid():
            continue
        pid = int(entry)
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                args = [os.fsdecode(a) for a in f.read().split(b"\0") if a]
            cwd = os.path.realpath(f"/proc/{pid}/cwd")
            session = os.getsid(pid)
            parent = int(_stat_fields(pid)[1])
        except (OSError, ValueError, IndexError):
            continue  # gone, or another user's process
        try:
            leader_parent = int(_stat_fields(session)[1])
        except (OSError, ValueError, IndexError):
            leader_parent = None  # the session leader is gone
        if cwd != repo or not args:
            continue
        if supervisor is not None and leader_parent == supervisor:
            continue
        program = os.path.basename(args[0])
        if not (program.startswith("python") or program == "uv"):
            continue
        if not any(os.path.realpath(os.path.join(cwd, a)) in scripts for a in args[1:]):
            continue
        started = session == pid and any(
            os.path.basename(a).startswith("config_temp") for a in args
        )
        found.append((pid, _process_age(pid), started, parent))
    runs = {pid for pid, _, _, _ in found}
    return sorted(
        (pid, age, started) for pid, age, started, parent in found if parent not in runs
    )


def describe_run(pid, age, started):
    what = "started by a loop or ablation" if started else "started by hand"
    when = f", running {age / 60:.0f} min" if age is not None else ""
    return f"PID {pid} ({what}{when})"


def stop_unsupervised_runs(repo, timeout):
    """Stop the groups of runs a dead supervisor left; name, not stop, runs
    started by hand. Returns whether every stopped run has ended."""
    runs = unsupervised_runs(repo)
    leaders = [pid for pid, _, started in runs if started]
    for pid, age, started in runs:
        verb = "stopping" if started else "not stopping"
        print(
            f"Unsupervised training run in this checkout, {verb}: "
            f"{describe_run(pid, age, started)}."
        )
    for pid in leaders:
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(started for _, _, started in unsupervised_runs(repo)):
            return True
        time.sleep(0.1)
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "stop"])
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    if args.action == "stop":
        (repo / ".loop_paused").touch()
    try:
        pid = running_pid(repo)
        if args.action == "status":
            if pid is not None:
                print(f"Autoresearch work is running (PID {pid}).")
            # Shown, but not "running": the loop's start decides about them.
            for run in unsupervised_runs(repo, supervisor=pid):
                print(
                    f"Unsupervised training run in this checkout: {describe_run(*run)}."
                )
            return 0 if pid is not None else 1
        if pid is not None:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + args.timeout
            while running_pid(repo) == pid:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"loop PID {pid} did not stop within {args.timeout:g}s; "
                        "watchdog remains paused"
                    )
                time.sleep(0.1)
        # What a killed loop or ablation left going, which no handler stopped.
        if not stop_unsupervised_runs(repo, args.timeout):
            raise RuntimeError(
                f"an unsupervised training run did not stop within {args.timeout:g}s; "
                "watchdog remains paused"
            )
        print(
            "Autoresearch work stopped. Watchdog paused."
            if pid is not None
            else "No autoresearch work running. Watchdog paused."
        )
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"loop control: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
