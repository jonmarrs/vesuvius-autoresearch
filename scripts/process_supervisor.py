"""Bounded lifecycle for commands whose workers share a new POSIX session."""

import os
import signal
import subprocess
import time


class ProcessSupervisor:
    def __init__(self, grace_seconds=5):
        self.active = None
        self.grace_seconds = grace_seconds

    def stop(self):
        """Terminate the whole group, including workers surviving their parent."""
        process = self.active
        if process is None:
            return
        self.active = None
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
