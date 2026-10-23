"""Snapshot a public annotator folder for audit_fiber_reference_provenance.py.

python repro/fibers/fetch_reference_annotations.py https://dl.ash2txt.org/other/annotators/0139_fibers/ /tmp/ref0139

Writes annotations/ and download_manifest.json; refuses existing destinations.
The directory listing is captured once. A failed download prevents a success
manifest, so incomplete snapshots must not be used as a complete-folder audit.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import urljoin
from urllib.request import urlopen


class Listing(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = set()

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href", "")
        if (tag == "a" and href.endswith(".json") and "/" not in href
                and "\\" not in href and ":" not in href and "%" not in href):
            self.names.add(href)


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
        with urlopen(urljoin(url, name), timeout=60) as response:
            captured = response.read()
        # Validate the exact bytes saved, without rewriting the JSON.
        if json.loads(captured).get("type") != "vc3d_fiber":
            raise ValueError(f"{name}: expected vc3d_fiber")
        (annotations / name).write_bytes(captured)
        return {"name": name, "bytes": len(captured), "sha256": hashlib.sha256(captured).hexdigest()}

    with ThreadPoolExecutor(max_workers=8) as pool:
        files = list(pool.map(fetch, sorted(listing.names)))
    manifest = {
        "source_url": url,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "index_sha256": hashlib.sha256(listing_bytes).hexdigest(),
        "files": files,
    }
    (root / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Downloaded all {len(files)} listed JSON files ({sum(f['bytes'] for f in files)} bytes) from {url}")


if __name__ == "__main__":
    main()
