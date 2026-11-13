"""Stat-only checks for observable overlap with the held-out CT volume.

A local path compares directory ancestry and inode identity. A remote address
is compared after normalization. Scheme and host case, a trailing dot on the
host, an ``http``/``https`` pair, a default port, backslashes, path parameters,
and repeated percent-encoding do not make the same volume look different.
``s3a`` and ``s3n`` are ``s3``. Query and fragment are ignored.

S3 does not resolve ``..``, so a key is inside the held-out volume when either
its resolved spelling or its once-decoded spelling with ``..`` left literal
overlaps. The bare bucket or host root contains every key of that address.

A small integer under any name, or any integer that is the whole key, is a
pyramid level of that parent. Leading zeros count (``01`` and ``00``).
``scroll/2024`` is not a level. Copies, crops, and a different host are not
proved independent.

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
    return None, (scheme, host, port, *_remote_paths(parts.path))


def _unescape(text):
    """Percent-decode until the text stops changing, at most eight times."""
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


def _is_integer(segment):
    return segment.isascii() and segment.isdigit() and segment != ""


def _pyramid_level(segments):
    """A resolution level of its parent.

    Any integer that is the whole key is a level of the bucket or host root,
    including ``100``. A smaller integer under any name is a level of that
    name (``vol/1``, ``surface_volume/2``, ``val.zarr.zip/1``). ``2024`` under
    a name is not.
    """
    leaf = segments[-1]
    if not _is_integer(leaf):
        return False
    if len(segments) == 1:
        return True
    return int(leaf) <= _MAX_PYRAMID_LEVEL


def _clean_segment(segment):
    segment = unicodedata.normalize("NFKC", segment).strip()
    if ";" in segment:
        segment = segment.split(";", 1)[0].strip()
    return segment


def _segments(path, *, repeated, resolve_dots):
    text = (_unescape(path) if repeated else unquote(path)).replace("\\", "/")
    segments = []
    for segment in text.split("/"):
        segment = _clean_segment(segment)
        if segment in ("", "."):
            continue
        if resolve_dots and segment == "..":
            if segments:
                segments.pop()
            continue
        segments.append(segment)
    return segments


def _fold_levels(segments):
    folded = list(segments)
    while folded and _pyramid_level(folded):
        folded.pop()
    return folded


def _remote_paths(path):
    """Literal once-decoded key, dot-resolved key, folded volume, and root flag.

    The literal key keeps ``..`` because S3 stores that segment. The resolved
    key is what the same characters mean after ``..`` is removed. Folding
    drops pyramid levels so sibling levels compare equal. ``is_root`` is the
    bare bucket or host, not a key that only became empty by resolving ``..``.
    """
    literal = _segments(path, repeated=False, resolve_dots=False)
    resolved = _segments(path, repeated=True, resolve_dots=True)
    is_root = not literal and ".." not in unquote(path)
    return (
        "/".join(literal),
        "/".join(resolved),
        "/".join(_fold_levels(resolved)),
        is_root,
    )


def _path_contains(parent, child):
    """True when ``child`` is strictly inside a non-empty ``parent``."""
    return bool(parent) and child.startswith(parent + "/")


def _pair_contains(left, right):
    return _path_contains(left, right) or _path_contains(right, left)


def _remote_overlap(left, right):
    """Same address, a nested key, a literal ``..`` key, or the bare root."""
    if left[:3] != right[:3]:
        return False
    literal_left, resolved_left, folded_left, root_left = left[3:]
    literal_right, resolved_right, folded_right, root_right = right[3:]
    if folded_left == folded_right:
        return True
    if _pair_contains(literal_left, literal_right):
        return True
    if _pair_contains(resolved_left, resolved_right):
        return True
    # The bare bucket contains every other key. A root *level* folds to the
    # same empty string and must not, by that, contain a different key.
    return bool(
        (root_left and resolved_right != "") or (root_right and resolved_left != "")
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
