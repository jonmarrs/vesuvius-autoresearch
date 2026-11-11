"""Stat-only checks for observable overlap with the held-out CT volume.

This cannot establish independence of copies, crops, or different remote URLs.
It opens no arrays, changes no configuration, and creates no filesystem entries.
"""

from pathlib import Path
from urllib.parse import unquote, urlsplit


def _location(uri, base):
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError("volume identifiers must be nonempty strings")
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
        return (base / path).resolve(), None
    # Preserve query/fragment and authority: different remote addresses cannot
    # be proved independent here. Only recognize identical addresses and the
    # root/level-zero spelling used by the volume loader.
    path = parts.path.rstrip("/")
    if path.endswith("/0"):
        path = path[:-2]
    return None, (parts.scheme, parts.netloc, path, parts.query, parts.fragment)


def _overlap(first, second):
    left, remote_left = first
    right, remote_right = second
    if left is None or right is None:
        return remote_left is not None and remote_left == remote_right
    if left == right or left in right.parents or right in left.parents:
        return True
    try:
        return left.samefile(right)
    except FileNotFoundError:
        # Missing inputs are checked by the caller; this is overlap preflight.
        return False


def local_volume_path(uri, *, base_dir=None):
    """Resolve an observable local identifier; remote identifiers return None."""
    base = Path.cwd() if base_dir is None else Path(base_dir)
    return _location(uri, base)[0]


def validate_training_split(config, *, base_dir=None):
    """Refuse labeled/active UA-MT inputs that observably overlap val_uri.

    Relative paths use the actual training CWD, or the explicitly inspected
    checkout. Symlinks, directory ancestry and existing inode aliases are checked
    without reading CT. Disabled UA-MT inputs are not used and are not inspected.
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
