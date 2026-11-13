"""Stat-only checks for observable overlap with the held-out CT volume.

A local path compares directory ancestry and inode identity. A remote address
is compared after normalization. Scheme and host case, a trailing dot on the
host, an ``http``/``https`` pair, a default port, dot segments, backslashes,
path parameters, and repeated percent-encoding do not make the same volume
look different. ``s3a`` and ``s3n`` are ``s3``. Query and fragment are ignored.
One path inside another of the same host is the same volume, except that the
bare bucket or host root is only itself.

A small integer directly under a ``.zarr`` name, or the only segment of the
path, is a pyramid level of that parent. Leading zeros count (``01`` and
``00``). ``scroll/2024`` is not a level. Copies, crops, and a different host
are not proved independent.

The volume reader refuses every remote URI, so this comparison does not decide
a read that can run today. It is the spelling check a later remote reader
would already have to pass. This opens no arrays, changes no configuration,
and creates no filesystem entries.
"""

import os
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Schemes whose explicit default port is the same endpoint as no port.
_DEFAULT_PORTS = {"http": 80, "https": 443}
# A resolution level is a small integer. A year or other id is not.
_MAX_PYRAMID_LEVEL = 99


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
    host, port = _remote_authority(parts, scheme)
    # The same host and path over http and https is one object.
    if scheme in ("http", "https"):
        scheme = "http"
    return None, (scheme, host, port, _remote_path(parts.path))


def _unescape(text):
    """Percent-decode until the text stops changing, including ``%252F``."""
    for _ in range(8):
        decoded = unquote(text)
        if decoded == text:
            return text
        text = decoded
    return text


def _split_host_port(netloc):
    """Host and numeric port. A non-numeric port is ignored."""
    if netloc.startswith("["):
        end = netloc.find("]")
        if end == -1:
            return netloc, None
        host = netloc[1:end]
        rest = netloc[end + 1 :]
        if rest.startswith(":") and rest[1:].isdigit():
            return host, int(rest[1:])
        return host, None
    if netloc.count(":") == 1:
        host, port_text = netloc.rsplit(":", 1)
        if port_text.isdigit():
            return host, int(port_text)
        return host, None
    return netloc, None


def _remote_authority(parts, scheme):
    """Lowercased host, with a scheme's default port and a trailing dot removed."""
    netloc = parts.netloc
    if "@" in netloc:
        netloc = netloc.rsplit("@", 1)[-1]
    host, port = _split_host_port(_unescape(netloc))
    host = unicodedata.normalize("NFKC", host).lower().rstrip(".")
    if port == _DEFAULT_PORTS.get(scheme):
        port = None
    return host, port


def _small_level(segment):
    """``0``, ``00``, ``01``, or another integer up to the pyramid bound."""
    if not segment.isascii() or not segment.isdigit():
        return False
    return int(segment) <= _MAX_PYRAMID_LEVEL


def _zarr_level(segments):
    """A small integer directly under a ``.zarr`` name, or the whole path.

    ``val.zarr/01`` is level 1 of that volume. ``scroll/2024`` is a name.
    A lone ``1`` or ``2`` is a level of the bucket or host root.
    """
    if not _small_level(segments[-1]):
        return False
    if len(segments) == 1:
        return True
    return segments[-2].lower().endswith(".zarr")


def _remote_path(path):
    """Decode, resolve ``.`` and ``..``, and fold a real pyramid level.

    Decoding repeats, so ``%252F`` becomes a separator and ``%252E%252E``
    becomes ``..``. Backslashes are separators. A ``;`` parameter is not
    part of the key. The bare bucket or host root stays empty and is only
    itself. A key nested under another key of the same host is inside it.
    """
    segments = []
    for segment in _unescape(path).replace("\\", "/").split("/"):
        segment = unicodedata.normalize("NFKC", segment).strip()
        if ";" in segment:
            segment = segment.split(";", 1)[0].strip()
        if segment in ("", "."):
            continue
        if segment == "..":
            if segments:
                segments.pop()
            continue
        segments.append(segment)
    while segments and _zarr_level(segments):
        segments.pop()
    return "/".join(segments)


def _path_contains(parent, child):
    """True when ``child`` is strictly inside a non-empty ``parent``."""
    return bool(parent) and child.startswith(parent + "/")


def _remote_overlap(left, right):
    """Same normalized address, or one path inside the other."""
    if left[:3] != right[:3]:
        return False
    left_path, right_path = left[3], right[3]
    return (
        left_path == right_path
        or _path_contains(left_path, right_path)
        or _path_contains(right_path, left_path)
    )


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
    checkout. Symlinks, directory ancestry, the same normalized remote volume
    or a path nested inside it, and existing inode aliases are checked
    without reading CT.
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
