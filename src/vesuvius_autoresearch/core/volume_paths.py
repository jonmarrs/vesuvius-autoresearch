"""Stat-only local/remote volume identities shared by split and depth checks."""

import os
from pathlib import Path
from urllib.parse import unquote, urlsplit


def volume_location(uri, base, *, resolve_local=True):
    """Classify one identifier without opening arrays or contacting a server.

    Existing paths win over URL parsing, matching FastVesuviusVolume. Remote
    identities retain authority, query and fragment and recognize root/level 0.
    Keep a lexical local path when deriving annotations beside a volume symlink.
    """
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError("volume identifiers must be nonempty strings")
    base = Path(base)
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
    path = parts.path.rstrip("/")
    if path.endswith("/0"):
        path = path[:-2]
    return None, (parts.scheme, parts.netloc, path, parts.query, parts.fragment)
