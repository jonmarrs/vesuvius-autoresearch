"""A folder snapshot must not silently omit URL-encoded annotation filenames."""

import hashlib
import io
import json

import pytest

from repro.fibers import fetch_reference_annotations as fetcher
from scripts.audit_fiber_reference_provenance import audit_folder


def download(tmp_path, monkeypatch, links):
    captured = b'{"type": "vc3d_fiber", "control_points": []}\n'
    requested = []
    listing = ''.join(f'<a href="{href}">annotation</a>' for href in links).encode()

    def open_url(url, **kwargs):
        requested.append(url)
        return io.BytesIO(listing if url.endswith("/") else captured)

    root = tmp_path / "snapshot"
    monkeypatch.setattr(fetcher, "urlopen", open_url)
    monkeypatch.setattr(fetcher.sys, "argv", ["fetch", "https://example.org/fibers/", str(root)])
    fetcher.main()
    return root, json.loads((root / "download_manifest.json").read_bytes()), requested, captured


@pytest.mark.parametrize("href, name", [
    ("fiber%20one.json", "fiber one.json"),
    ("fibr%C3%A9.json", "fibré.json"),
    ("fiber%2520.json", "fiber%20.json"),
])
def test_encoded_filename_is_downloaded_and_bound_to_the_audit(tmp_path, monkeypatch, href, name):
    root, manifest, requested, captured = download(tmp_path, monkeypatch, [href])
    assert requested == ["https://example.org/fibers/", f"https://example.org/fibers/{href}"]
    assert (root / "annotations" / name).read_bytes() == captured
    assert manifest["files"] == [{
        "name": name, "bytes": len(captured), "sha256": hashlib.sha256(captured).hexdigest()}]
    assert manifest["files"] == audit_folder(root / "annotations")["inputs"]
    assert manifest["skipped_json_links"] == []


@pytest.mark.parametrize("unsafe", [
    "../outside.json", "%2E%2E%2Foutside.json", "%2foutside.json", "bad%5Cname.json",
    "https://elsewhere.example/outside.json", "fiber.json?download=1", "fiber.json#part",
    "bad%ZZ.json", "bad%FF.json", "bad%00.json", "bad%0A.json",
    "/other/annotators/outside.json", "c%3Ad.json", "file:outside.json", "bad%7F.json",
])
def test_skipped_json_links_are_recorded_without_claiming_a_complete_download(
    tmp_path, monkeypatch, capsys, unsafe
):
    root, manifest, requested, _ = download(tmp_path, monkeypatch, ["fiber.json", unsafe])
    assert requested == ["https://example.org/fibers/", "https://example.org/fibers/fiber.json"]
    assert [row["href"] for row in manifest["skipped_json_links"]] == [unsafe]
    assert manifest["skipped_json_links"][0]["reason"]
    output = capsys.readouterr().out
    assert "skipped 1 listed JSON link" in output and "Downloaded all" not in output
    assert sorted(p.name for p in (root / "annotations").iterdir()) == ["fiber.json"]


def test_duplicate_encoded_and_plain_links_refer_to_one_local_file(tmp_path, monkeypatch):
    root, manifest, requested, _ = download(tmp_path, monkeypatch, ["f%69ber.json", "fiber.json"])
    assert [row["name"] for row in manifest["files"]] == ["fiber.json"]
    assert requested == ["https://example.org/fibers/", "https://example.org/fibers/fiber.json"]


def test_anchor_without_an_href_is_ignored():
    listing = fetcher.Listing()
    listing.feed('<a href>empty</a><a>absent</a>')
    assert listing.names == set()


def test_only_anchors_are_listed_files():
    # a page's own <link> or <script> is not a file in the folder
    listing = fetcher.Listing()
    listing.feed('<link rel="alternate" href="index.json"><script src="app.json"></script>'
                 '<a href="fiber.json">fiber</a>')
    assert listing.names == {"fiber.json"} and listing.skipped_json_links == []
