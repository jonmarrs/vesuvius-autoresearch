"""The permission bits of a file published by rename.

``tempfile.mkstemp`` and ``NamedTemporaryFile`` create their file 0600. A file
written under a temporary name and renamed into place as it is can be read by
its owner alone, where ``open()`` would have given it 0666 less the umask.
"""

from __future__ import annotations

import os
import stat


def current_umask() -> int:
    """The process's umask, read without changing it where Linux reports it:
    os.umask can only be read by setting it, which a thread creating a file
    meanwhile (a loader's) would see."""
    try:
        with open("/proc/self/status") as status:
            for line in status:
                if line.startswith("Umask:"):
                    return int(line.split()[1], 8)
    except (OSError, ValueError, IndexError):
        pass
    umask = os.umask(0o022)
    os.umask(umask)
    return umask


def replacement_mode(path) -> int:
    """The permission bits a file written over ``path`` should have: those of
    the file it replaces, else what open() would give a new file (0666 less
    the umask). mkstemp creates its file 0600."""
    try:
        return stat.S_IMODE(os.stat(path).st_mode)
    except FileNotFoundError:
        return 0o666 & ~current_umask()
