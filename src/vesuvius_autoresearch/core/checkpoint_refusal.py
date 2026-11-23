"""The checkpoint-gate sentences, defined once.

A path is a torch zip only when it is a local file whose first bytes are the
zip local-file signature. A missing file and a URL are refused here; the
pickle audit then refuses a zip whose members or offsets are ambiguous.
"""

import os

# Shared by the audit, the loaders, and the two scripts that still unpickle
# with weights_only=False. Do not copy this sentence.
NON_ZIP_CHECKPOINT = (
    "refusing a non-zip checkpoint; convert it offline to zip before loading"
)
MISSING_CHECKPOINT = "refusing a missing checkpoint"
URL_CHECKPOINT = (
    "refusing a checkpoint URL; copy it offline to a zip file before loading"
)

_ZIP_LOCAL = b"PK\x03\x04"


def _text(source):
    if isinstance(source, str):
        return source
    if isinstance(source, os.PathLike):
        return os.fspath(source)
    return None


def read_signature(source) -> bytes:
    """The leading bytes of a path or a seekable buffer.

    A missing file and any path containing ``://`` raise. They are not left
    for a later loader: Lightning accepts a URL, and a missing path used to
    skip this gate.
    """
    text = _text(source)
    if text is not None and "://" in text:
        raise ValueError(URL_CHECKPOINT)
    if text is not None:
        try:
            with open(text, "rb") as handle:
                return handle.read(len(_ZIP_LOCAL))
        except FileNotFoundError:
            raise ValueError(MISSING_CHECKPOINT) from None
    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source[: len(_ZIP_LOCAL)])
    position = source.tell()
    try:
        return source.read(len(_ZIP_LOCAL))
    finally:
        source.seek(position)


def require_zip_checkpoint(source) -> None:
    """Refuse anything torch would not read as a zip archive."""
    if read_signature(source) != _ZIP_LOCAL:
        raise ValueError(NON_ZIP_CHECKPOINT)
