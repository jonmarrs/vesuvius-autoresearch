"""Bounded lifecycle for commands whose workers share a new POSIX session."""

import os
import signal
import subprocess
import time


class ProcessSupervisor:
    def __init__(self, grace_seconds=5):
        self.active = None
        self.stopping = None
        self.grace_seconds = grace_seconds

    def stop(self):
        """Terminate the whole group, including workers surviving their parent.

        A signal handler can call this while a stop is under way: a second stop
        during the first one's grace period, or a stop during run()'s own
        clean-up. That call kills the group at once and waits for its leader,
        because the caller acts on the run's files next (the loop settles
        best_model.pt). It used to return at once with the group still alive,
        and the handler's exit then cut the first stop short before its SIGKILL.
        If the wait is interrupted, the group is killed before the exception
        propagates."""
        if self.active is None and self.stopping is not None:
            self._kill(self.stopping)
            return
        process = self.active
        if process is None:
            return
        self.active = None
        self.stopping = process
        try:
            # start_new_session makes the child's PID the group ID. Do not look up
            # its current group: the leader can exit while its workers remain alive.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                process.wait(timeout=self.grace_seconds)
                return
            deadline = time.monotonic() + self.grace_seconds
            while time.monotonic() < deadline:
                process.poll()  # reap the leader before checking the group
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.05)
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=max(self.grace_seconds, 1))
        except BaseException:
            self._kill(process)
            raise
        finally:
            self.stopping = None

    def _kill(self, process):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            # Bounded: an interrupted wait in the same thread may still hold the
            # process's wait lock, and then this one times out instead.
            process.wait(timeout=max(self.grace_seconds, 1))
        except subprocess.TimeoutExpired:
            pass

    def run(self, command, *, timeout, check=False, **kwargs):
        if self.active is not None:
            raise RuntimeError("a supervised process is already running")
        process = subprocess.Popen(command, start_new_session=True, **kwargs)
        self.active = process
        try:
            returncode = process.wait(timeout=timeout)
            if check and returncode:
                raise subprocess.CalledProcessError(returncode, command)
            return subprocess.CompletedProcess(command, returncode)
        finally:
            # Also cleans up descendants after a successful or failed leader exit.
            try:
                self.stop()
            finally:
                self.active = None
