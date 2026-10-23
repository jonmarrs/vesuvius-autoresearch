"""Snapshot a public annotator folder for audit_fiber_reference_provenance.py.

python repro/fibers/fetch_reference_annotations.py https://dl.ash2txt.org/other/annotators/0139_fibers/ /tmp/ref0139

Writes annotations/ and download_manifest.json; refuses existing destinations.
The directory listing is captured once. A failed download prevents a success
manifest, so incomplete snapshots must not be used as a complete-folder audit.
Encoded filenames are decoded locally and quoted again for downloads. JSON
links outside the folder or with unsupported URLs are recorded as skipped.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import urlopen


class Listing(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = set()
        self.skipped_json_links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        try:
            parts = urlsplit(href)
            name = unquote(parts.path, errors="strict")
        except ValueError:
            if ".json" in href:
                self.skipped_json_links.append({"href": href, "reason": "invalid URL encoding"})
            return
        if not name.endswith(".json"):
            return
        if re.search(r"%(?![0-9a-fA-F]{2})", href):
            reason = "invalid percent escape"
        elif parts.scheme or parts.netloc or parts.query or parts.fragment:
            reason = "expected a relative filename without query or fragment"
        elif any(char in name for char in "/\\:") or any(
            ord(char) < 32 or ord(char) == 127 for char in href + name
        ):
            reason = "filename contains a path separator or unsupported character"
        else:
            self.names.add(name)
            return
        self.skipped_json_links.append({"href": href, "reason": reason})


def main():
    url, destination = sys.argv[1:]
    if not url.startswith("https://") or not url.endswith("/"):
        raise ValueError("expected an HTTPS directory URL ending with /")
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    annotations = root / "annotations"
    annotations.mkdir()
    with urlopen(url, timeout=60) as response:
        listing_bytes = response.read()
    (root / "index.html").write_bytes(listing_bytes)
    listing = Listing()
    listing.feed(listing_bytes.decode("utf-8"))
    if not listing.names:
        raise ValueError("listing contains no JSON annotations")

    def fetch(name):
        with urlopen(urljoin(url, quote(name, safe="")), timeout=60) as response:
            captured = response.read()
        # Validate the exact bytes saved, without rewriting the JSON.
        if json.loads(captured).get("type") != "vc3d_fiber":
            raise ValueError(f"{name}: expected vc3d_fiber")
        with (annotations / name).open("xb") as stream:
            stream.write(captured)
        return {"name": name, "bytes": len(captured), "sha256": hashlib.sha256(captured).hexdigest()}

    with ThreadPoolExecutor(max_workers=8) as pool:
        files = list(pool.map(fetch, sorted(listing.names)))
    manifest = {
        "source_url": url,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "index_sha256": hashlib.sha256(listing_bytes).hexdigest(),
        "files": files,
        "skipped_json_links": listing.skipped_json_links,
    }
    (root / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if listing.skipped_json_links:
        print(f"Downloaded {len(files)} JSON files; "
              f"skipped {len(listing.skipped_json_links)} listed JSON link(s); "
              "see download_manifest.json")
    else:
        print(f"Downloaded all {len(files)} listed JSON files ({sum(f['bytes'] for f in files)} bytes) from {url}")


if __name__ == "__main__":
    main()
