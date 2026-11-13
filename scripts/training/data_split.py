"""Stat-only checks for observable overlap with the held-out CT volume.

A local path compares directory ancestry and inode identity. A remote address
is compared after normalization: scheme and host case, a default port, dot
segments, and percent-encoding do not make the same volume look different.
``s3a`` and ``s3n`` are ``s3``. Query and fragment are ignored. Trailing
integer segments are pyramid levels of the parent, so sibling levels are the
same volume. A path of only those segments is a level of the bucket or host
root; an integer name cannot be told from a level without opening the store.
Copies, crops, and a different host are not proved independent.

The volume reader refuses every remote URI, so this comparison does not decide
a read that can run today. It is the spelling check a later remote reader
would already have to pass. This opens no arrays, changes no configuration,
and creates no filesystem entries.
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Schemes whose explicit default port is the same endpoint as no port.
_DEFAULT_PORTS = {"http": 80, "https": 443}


def _location(uri, base, *, resolve_local=True):
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError("volume identifiers must be nonempty strings")
    # Match FastVesuviusVolume: an existing path wins over URL interpretation.
    # POSIX names may contain colons or even look like a remote URI.
    candidate = base / uri
    if os.path.exists(candidate):
        return (candidate.resolve() if resolve_local else candidate), None
    parts = urlsplit(uri)
    if not parts.scheme or (
        parts.scheme == "file" and parts.netloc in ("", "localhost")
    ):
        if parts.scheme == "file":
            if parts.query or parts.fragment:
                raise ValueError("local file URIs cannot have a query or fragment")
            path = unquote(parts.path)
        else:
            path = uri
        local = base / path
        return (local.resolve() if resolve_local else local), None
    # Query and fragment are not part of the volume. A signed URL and a bare
    # URL of the same scheme, host, and path are the same spelling.
    scheme = parts.scheme.lower()
    if scheme in ("s3a", "s3n"):
        scheme = "s3"
    return None, (scheme, *_remote_authority(parts, scheme), _remote_path(parts.path))


def _remote_authority(parts, scheme):
    """Lowercased host, with a scheme's default port removed."""
    try:
        host = parts.hostname or ""
        port = parts.port
    except ValueError:
        return parts.netloc.lower(), None
    if port == _DEFAULT_PORTS.get(scheme):
        port = None
    return host, port


def _integer_level(segment):
    """A pyramid level segment: ``0`` or a decimal integer without a leading zero."""
    if not segment.isascii() or not segment.isdigit():
        return False
    return segment == "0" or not segment.startswith("0")


def _remote_path(path):
    """Decode, resolve ``.`` and ``..``, and fold a trailing pyramid level.

    Percent-decoding runs first, so ``%2F`` is a separator and ``%2E%2E`` is
    ``..``. A bucket or host root stays empty and is only itself: it is not a
    parent of every key. Trailing integer segments are resolution levels of
    the parent, so ``volume/1`` and ``volume/2`` are that volume. A non-level
    key under the same prefix, such as ``volume/labels``, is not.
    """
    segments = []
    for segment in unquote(path).split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if segments:
                segments.pop()
            continue
        segments.append(segment)
    while segments and _integer_level(segments[-1]):
        segments.pop()
    return "/".join(segments)


def _remote_overlap(left, right):
    """Same normalized scheme, host, port, and volume path."""
    return left == right


def _overlap(first, second):
    left, remote_left = first
    right, remote_right = second
    if left is None or right is None:
        return (
            remote_left is not None
            and remote_right is not None
            and _remote_overlap(remote_left, remote_right)
        )
    if left == right or left in right.parents or right in left.parents:
        return True
    try:
        return left.samefile(right)
    except FileNotFoundError:
        # Missing inputs are checked by the caller; this is overlap preflight.
        return False


def local_volume_path(uri, *, base_dir=None, resolve=True):
    """Return a local path, or None for remote identifiers.

    Keep the visible path with resolve=False when deriving annotation paths:
    training selects labels beside the URI, not beside its symlink target.
    """
    base = Path.cwd() if base_dir is None else Path(base_dir)
    return _location(uri, base, resolve_local=resolve)[0]


def validate_training_split(config, *, base_dir=None):
    """Refuse labeled/active UA-MT inputs that observably overlap val_uri.

    Relative paths use the actual training CWD, or the explicitly inspected
    checkout. Symlinks, directory ancestry, the same normalized remote volume,
    and existing inode aliases are checked without reading CT.
    Disabled UA-MT inputs are not used and are not inspected.
    Callers keep inputs/writers stable; this is a snapshot, not a lock or proof
    that physically overlapping/copied study regions have been excluded.
    """
    base = Path.cwd() if base_dir is None else Path(base_dir)
    validation = _location(config.val_uri, base)
    if not isinstance(config.uris, list) or not config.uris:
        raise ValueError("uris must be a nonempty list of volume identifiers")
    pools = [("training", config.uris)]
    if config.use_uamt:
        if config.unlabeled_uris is not None and not isinstance(
            config.unlabeled_uris, list
        ):
            raise ValueError("unlabeled_uris must be a list of volume identifiers")
        pools.append(("unlabeled", config.unlabeled_uris or []))
    for role, uris in pools:
        for index, uri in enumerate(uris):
            if _overlap(_location(uri, base), validation):
                raise ValueError(
                    f"{role}[{index}] overlaps val_uri; choose independent training and validation volumes"
                )
