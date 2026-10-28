"""Staged replacement of the legacy JSON/TSV worklist pair; serialize writers."""

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from vesuvius_autoresearch.core.file_modes import replacement_mode


@dataclass
class StagedFile:
    output: Path
    workspace: Path
    published: bool = False


def publish_pair(outputs, render, verify):
    """Prepare both files before touching prior outputs; roll back caught errors.

    Readers must also serialize with publication: two paths cannot change in one
    filesystem operation. Preserve backups if rollback itself fails.
    """
    entries: list[StagedFile] = []
    preserve = False
    try:
        for output in map(Path, outputs):
            output.parent.mkdir(parents=True, exist_ok=True)
            workspace = Path(
                tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent)
            )
            entries.append(StagedFile(output, workspace))
        render(*(entry.workspace / "new" for entry in entries))
        verify()
        for entry in entries:
            output, workspace = entry.output, entry.workspace
            os.chmod(workspace / "new", replacement_mode(output))
        try:
            for entry in entries:
                output, workspace = entry.output, entry.workspace
                if output.exists() or output.is_symlink():
                    output.rename(workspace / "previous")
                # Record intent before rename: an interrupt may arrive after
                # the filesystem mutation but before Python regains control.
                entry.published = True
                (workspace / "new").rename(output)
        except BaseException as exc:
            # Keep backups if rollback itself is interrupted.
            preserve = True
            failures = []
            for entry in reversed(entries):
                try:
                    previous = entry.workspace / "previous"
                    if previous.exists() or previous.is_symlink():
                        previous.replace(entry.output)
                    elif entry.published:
                        entry.output.unlink(missing_ok=True)
                except OSError as rollback_error:
                    failures.append(str(rollback_error))
            if failures:
                raise RuntimeError(
                    "worklist rollback failed; recover retained files in "
                    + ", ".join(str(entry.workspace) for entry in entries)
                ) from exc
            preserve = False
            raise
    finally:
        if not preserve:
            for entry in entries:
                shutil.rmtree(entry.workspace, ignore_errors=True)
