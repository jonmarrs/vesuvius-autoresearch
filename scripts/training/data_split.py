"""Stat-only checks for observable overlap with the held-out CT volume.

A local path compares directory ancestry and inode identity. A remote address
compares its spelling: the same address, the level-zero spelling, or a path
inside that address. Copies, crops, and remote URLs that differ in host,
query, or fragment are not proved independent. This opens no arrays, changes
no configuration, and creates no filesystem entries.
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlsplit


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
    # Preserve query, fragment and authority. A child path of the same address
    # is inside the held-out volume; a pyramid level is one such child. A
    # different host, query or fragment cannot be proved the same object from
    # the spelling, so it is left unverified. The level-zero array and the
    # volume group are the same spelling the volume loader accepts.
    path = parts.path.rstrip("/")
    if path.endswith("/0"):
        path = path[:-2]
    return None, (parts.scheme, parts.netloc, path, parts.query, parts.fragment)


def _path_contains(parent, child):
    """True when ``child`` is a path strictly inside ``parent``.

    An empty parent is the bucket or host root, so every key is inside it.
    The boundary is a slash: ``val.zarr`` does not contain ``val.zarr-other``.
    """
    if parent == "":
        return child.startswith("/")
    return child.startswith(parent + "/")


def _remote_overlap(left, right):
    """Same remote address, or one path inside the other."""
    if left == right:
        return True
    if left[:2] != right[:2] or left[3:] != right[3:]:
        return False
    return _path_contains(left[2], right[2]) or _path_contains(right[2], left[2])


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
    checkout. Symlinks, directory ancestry, a remote path inside the same
    address, and existing inode aliases are checked without reading CT.
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
