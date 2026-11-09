"""Dataset acquisition should select one annotation and plan every destination."""

import argparse
import io
import os

import pytest

from vesuvius_autoresearch.fibers import bench_cli
from vesuvius_autoresearch.fibers.dataset_fetch import MAX_LISTING_BYTES, FetchPlan

CUBE = "s1_00497_01497_03997_256"
ANNOTATION = "fibers_s1_00497z_01497y_03997x_256_v1.nml"


def listing_stub(monkeypatch, listing):
    urls = []

    def urlopen(url, **kwargs):
        assert kwargs["timeout"] == 60
        urls.append(url)
        return io.BytesIO(listing if url.endswith("nml/") else url.encode())

    monkeypatch.setattr(bench_cli.urllib.request, "urlopen", urlopen)
    return urls


def test_fetch_selects_latest_numeric_annotation_version(tmp_path, monkeypatch):
    listing = b"".join(
        f'<a href="fibers_s1_00497z_01497y_03997x_256_v{v}.nml">{v}</a>'.encode()
        for v in (1, 2, 10)
    )
    urls = listing_stub(monkeypatch, listing)
    assert bench_cli.cmd_fetch(argparse.Namespace(data_dir=tmp_path, cube=CUBE)) == 0
    assert (tmp_path / f"{CUBE}.nml").read_bytes().endswith(b"_v10.nml")
    assert len(urls) == 4


def test_fetch_checks_later_destinations_before_downloading(tmp_path, monkeypatch):
    urls = listing_stub(
        monkeypatch, b'<a href="fibers_s1_00497z_01497y_03997x_256_v1.nml">1</a>'
    )
    external = tmp_path / "external.tif"
    external.write_bytes(b"unrelated data")
    (tmp_path / f"{CUBE}_semantic.tif").symlink_to(external)
    with pytest.raises(ValueError, match="regular file"):
        bench_cli.cmd_fetch(argparse.Namespace(data_dir=tmp_path, cube=CUBE))
    assert len(urls) == 1
    assert not (tmp_path / f"{CUBE}.nml").exists()
    assert external.read_bytes() == b"unrelated data"


def existing_cube(root):
    paths = [
        root / f"{CUBE}{suffix}" for suffix in (".nml", "_image.tif", "_semantic.tif")
    ]
    for index, path in enumerate(paths):
        path.write_bytes(f"prior-{index}".encode())
        path.chmod(0o640)
    return paths


@pytest.mark.parametrize("reverse", [False, True])
def test_html_links_versions_aliases_and_order(reverse, tmp_path):
    links = [
        f"<a href='{ANNOTATION}'>one</a>",
        "<A HREF='fibers_s1a_00497z_01497y_03997x_256_v10.nml'>latest</A>",
        "<a href='fibers_s1_00497z_01497y_03997x_256_v2.nml'>two</a>",
        "<a href='fibers_s10_00497z_01497y_03997x_256_v00.nml'>scroll ten</a>",
        f"<a href='{ANNOTATION}'>duplicate</a>",
        "<!-- <a href='fibers_s1_00497z_01497y_03997x_256_v99.nml'>comment</a> -->",
        "<a href='../fibers_s1_00497z_01497y_03997x_256_v99.nml'>parent</a>",
        "<a href='https://elsewhere/fibers_s1_00497z_01497y_03997x_256_v99.nml'>absolute</a>",
    ]
    plan = FetchPlan.create("".join(reversed(links) if reverse else links), tmp_path)
    assert len(plan.downloads) == 6
    assert plan.downloads[0].relative_url.endswith(
        "s10_00497z_01497y_03997x_256_v00.nml"
    )
    assert plan.downloads[3].relative_url.endswith(
        "s1a_00497z_01497y_03997x_256_v10.nml"
    )
    assert not tmp_path.joinpath(f"{CUBE}.nml").exists()
    selected = FetchPlan.create("".join(links), tmp_path, CUBE)
    assert len(selected.downloads) == 3
    assert all("s10" not in entry.relative_url for entry in selected.downloads)


def test_same_version_with_distinct_annotation_names_is_ambiguous(
    tmp_path, monkeypatch
):
    listing = f"<a href='{ANNOTATION}'>a</a><a href='{ANNOTATION.replace('s1_', 's1a_')}'>b</a>".encode()
    urls = listing_stub(monkeypatch, listing)
    with pytest.raises(ValueError, match="ambiguous annotations"):
        bench_cli.cmd_fetch(argparse.Namespace(data_dir=tmp_path / "new", cube=CUBE))
    assert len(urls) == 1
    assert not (tmp_path / "new").exists()


def test_all_cube_plan_refuses_a_later_cube_before_any_transfer(tmp_path, monkeypatch):
    second = "s5_00497_01497_03997_256"
    (tmp_path / f"{second}_semantic.tif").mkdir()
    urls = listing_stub(
        monkeypatch,
        f"<a href='{ANNOTATION}'>1</a><a href='{ANNOTATION.replace('s1_', 's5_')}'>5</a>".encode(),
    )
    with pytest.raises(ValueError, match="regular file"):
        bench_cli.cmd_fetch(argparse.Namespace(data_dir=tmp_path, cube=None))
    assert len(urls) == 1
    assert not (tmp_path / f"{CUBE}.nml").exists()


def test_existing_downloads_cannot_alias_each_other(tmp_path, monkeypatch):
    paths = existing_cube(tmp_path)
    paths[1].unlink()
    os.link(paths[0], paths[1])
    urls = listing_stub(monkeypatch, f"<a href='{ANNOTATION}'>1</a>".encode())
    with pytest.raises(ValueError, match="artifact collision"):
        bench_cli.cmd_fetch(argparse.Namespace(data_dir=tmp_path, cube=CUBE))
    assert len(urls) == 1
    assert paths[0].read_bytes() == b"prior-0"


def test_refresh_replaces_existing_files_with_modes_preserved(tmp_path, monkeypatch):
    paths = existing_cube(tmp_path)
    urls = listing_stub(monkeypatch, f"<a href='{ANNOTATION}'>1</a>".encode())
    assert (
        bench_cli.main(
            ["--data-dir", str(tmp_path), "fetch", "--cube", CUBE, "--refresh"]
        )
        == 0
    )
    assert len(urls) == 4
    for path, url in zip(paths, urls[1:], strict=False):
        assert path.read_bytes() == url.encode()
        assert path.stat().st_mode & 0o777 == 0o640


def test_reuse_does_not_claim_existing_files_match_remote_sources(
    tmp_path, monkeypatch, capsys
):
    paths = existing_cube(tmp_path)
    before = [path.read_bytes() for path in paths]
    urls = listing_stub(monkeypatch, f"<a href='{ANNOTATION}'>1</a>".encode())
    assert bench_cli.main(["--data-dir", str(tmp_path), "fetch", "--cube", CUBE]) == 0
    assert len(urls) == 1
    assert [path.read_bytes() for path in paths] == before
    output = capsys.readouterr().out
    assert output.count("REUSE") == 3
    assert "source/content unverified" in output
    assert "--refresh" in output


@pytest.mark.parametrize("refresh", [False, True])
@pytest.mark.parametrize("exists", [False, True])
def test_dry_run_reads_only_listing_and_preserves_files(
    tmp_path, monkeypatch, capsys, refresh, exists
):
    root = tmp_path / "dataset"
    paths, before = [], []
    if exists:
        root.mkdir()
        paths = existing_cube(root)
        before = [path.read_bytes() for path in paths]
    urls = listing_stub(monkeypatch, f"<a href='{ANNOTATION}'>1</a>".encode())
    flags = ["--data-dir", str(root), "fetch", "--cube", CUBE, "--dry-run"]
    assert bench_cli.main([*flags, *(["--refresh"] if refresh else [])]) == 0
    assert len(urls) == 1
    assert root.exists() == exists
    assert [path.read_bytes() for path in paths] == before
    output = capsys.readouterr().out
    action = "REPLACE" if exists and refresh else "REUSE" if exists else "DOWNLOAD"
    assert output.count(action) == 3
    assert "dry run: no dataset files written" in output


@pytest.mark.parametrize(
    "bad", ["missing", "invalid", "empty_listing", "large_listing"]
)
def test_bad_request_or_listing_does_not_create_destination(tmp_path, monkeypatch, bad):
    root = tmp_path / "new"
    listing = f"<a href='{ANNOTATION}'>1</a>".encode()
    if bad == "empty_listing":
        listing = b"<html>no annotation links</html>"
    elif bad == "large_listing":
        listing = b"x" * (MAX_LISTING_BYTES + 1)
    urls = listing_stub(monkeypatch, listing)
    cube = (
        "../bad" if bad == "invalid" else "s9_1_2_3_256" if bad == "missing" else None
    )
    with pytest.raises(ValueError):
        bench_cli.cmd_fetch(argparse.Namespace(data_dir=root, cube=cube))
    assert len(urls) == (0 if bad == "invalid" else 1)
    assert not root.exists()


@pytest.mark.parametrize("failure", ["empty", "short", "bad_length", "interrupted"])
def test_failed_refresh_preserves_previous_file(tmp_path, monkeypatch, failure):
    paths = existing_cube(tmp_path)
    before = [path.read_bytes() for path in paths]

    class Response(io.BytesIO):
        headers = {"Content-Length": "bad" if failure == "bad_length" else "100"}

        def read(self, *args):
            if failure == "interrupted" and self.tell():
                raise OSError("interrupted transfer")
            return super().read(*args)

    def urlopen(url, **kwargs):
        if url.endswith("nml/"):
            return io.BytesIO(f"<a href='{ANNOTATION}'>1</a>".encode())
        return Response(b"" if failure == "empty" else b"partial")

    monkeypatch.setattr(bench_cli.urllib.request, "urlopen", urlopen)
    with pytest.raises((ValueError, OSError)):
        bench_cli.main(
            ["--data-dir", str(tmp_path), "fetch", "--cube", CUBE, "--refresh"]
        )
    assert [path.read_bytes() for path in paths] == before
    assert sorted(tmp_path.iterdir()) == sorted(paths)


def test_transfer_rechecks_all_destinations_before_publication(tmp_path, monkeypatch):
    paths = existing_cube(tmp_path)

    class Replaced(io.BytesIO):
        def read(self, *args):
            result = super().read(*args)
            if result:
                paths[2].unlink()
                paths[2].symlink_to(paths[1])
            return result

    monkeypatch.setattr(
        bench_cli.urllib.request,
        "urlopen",
        lambda url, **kwargs: io.BytesIO(f"<a href='{ANNOTATION}'>1</a>".encode())
        if url.endswith("nml/")
        else Replaced(b"new"),
    )
    with pytest.raises(ValueError, match="artifact collision|regular file"):
        bench_cli.main(
            ["--data-dir", str(tmp_path), "fetch", "--cube", CUBE, "--refresh"]
        )
    assert paths[0].read_bytes() == b"prior-0"
    assert paths[1].read_bytes() == b"prior-1"
    assert not list(tmp_path.glob(".*.nml.*"))


def test_incomplete_listing_cannot_publish_a_partial_cube_selection(
    tmp_path, monkeypatch
):
    content = f"<a href='{ANNOTATION}'>1</a>".encode()

    class Listing(io.BytesIO):
        headers = {"Content-Length": str(len(content) + 100)}

    calls = []

    def urlopen(url, **kwargs):
        calls.append(url)
        return Listing(content) if url.endswith("nml/") else io.BytesIO(b"payload")

    monkeypatch.setattr(bench_cli.urllib.request, "urlopen", urlopen)
    root = tmp_path / "new"
    with pytest.raises(ValueError, match="incomplete dataset listing"):
        bench_cli.cmd_fetch(argparse.Namespace(data_dir=root, cube=None))
    assert len(calls) == 1
    assert not root.exists()
