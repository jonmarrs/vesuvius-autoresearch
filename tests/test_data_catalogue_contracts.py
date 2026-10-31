"""Local catalogues must not imply readiness or silently inspect arbitrary images."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts import generate_manifest as inventory, generate_training_atlas as atlas

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt

    before = set(plt.get_fignums())
    monkeypatch.chdir(tmp_path)
    (tmp_path / "local_data").mkdir()
    yield tmp_path
    for number in set(plt.get_fignums()).difference(before):
        plt.close(number)


def _broken_png_chunk(shape):
    """A PNG whose image data continues in a chunk of type NUL: Pillow raises
    SyntaxError, not OSError, while decoding it."""
    import io
    import struct
    import zlib

    buffer = io.BytesIO()
    Image.fromarray(np.full(shape, 255, np.uint8)).save(buffer, "PNG")
    data = buffer.getvalue()
    start = data.index(b"IDAT") - 4
    (length,) = struct.unpack(">I", data[start : start + 4])
    payload = data[start + 8 : start + 8 + length]

    def chunk(kind, body):
        crc = struct.pack(">I", zlib.crc32(kind + body))
        return struct.pack(">I", len(body)) + kind + body + crc

    half = len(payload) // 2
    return (
        data[:start]
        + chunk(b"IDAT", payload[:half])
        + chunk(b"\0\0\0\0", payload[half:])
        + data[start + 12 + length :]
    )


def fragment(root, name="fragment", *, labels=None, mask=None):
    directory = root / "local_data" / name
    directory.mkdir()
    Image.fromarray(
        np.asarray(labels if labels is not None else np.ones((4, 6)) * 255, np.uint8)
    ).save(directory / "inklabels.png")
    if mask is not None:
        Image.fromarray(np.asarray(mask, np.uint8)).save(directory / "mask.png")
    return directory


def test_single_fragment_atlas_runs_without_axes_shape_crash(workspace):
    fragment(workspace, mask=np.ones((4, 6)) * 255)
    atlas.generate_atlas()


def test_rgb_is_not_binary_ink_ground_truth(workspace):
    fragment(workspace, "rgb1", labels=np.zeros((4, 6, 3)))
    fragment(workspace, "rgb2", labels=np.zeros((4, 6, 3)))
    with pytest.raises(ValueError, match="binary|grayscale"):
        atlas.generate_atlas()


def test_mask_presence_does_not_prove_shape_agreement(workspace):
    fragment(workspace, "bad", mask=np.ones((3, 6)) * 255)
    fragment(workspace, "good", mask=np.ones((4, 6)) * 255)
    with pytest.raises(ValueError, match="shape"):
        atlas.generate_atlas()


def test_directory_size_does_not_follow_symlink_cycles(workspace):
    root = workspace / "local_data"
    (root / "payload").write_bytes(b"data")
    (root / "loop").symlink_to(root, target_is_directory=True)
    assert inventory.get_dir_size(root) == 4


def test_directory_size_does_not_count_external_symlink_targets(workspace):
    root = workspace / "local_data"
    (root / "payload").write_bytes(b"data")
    external = workspace / "external"
    external.write_bytes(b"outside" * 10)
    (root / "alias").symlink_to(external)
    assert inventory.get_dir_size(root) == 4


def test_inventory_does_not_infer_readiness_or_fixed_sizes_from_names(workspace):
    directory = workspace / "local_data" / "Scroll_2_div_10_1GB"
    directory.mkdir()
    with (directory / "sparse").open("wb") as stream:
        stream.truncate(101 * 1024**2)
    inventory.generate()
    text = "\n".join(path.read_text() for path in workspace.rglob("*.md"))
    assert "Ready" not in text
    assert "~63GB" not in text
    assert "11x 1GB" not in text


def test_inventory_does_not_overwrite_existing_report(workspace):
    previous = workspace / "local_data_manifest.md"
    previous.write_text("previous report")
    inventory.generate()
    assert previous.read_text() == "previous report"


def test_missing_inventory_root_is_cli_failure(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/generate_manifest.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not (tmp_path / "reports").exists()


def read_report(output, name):
    import json

    return json.loads((output / name).read_text(encoding="utf-8"))


def assert_artifacts(output, report):
    import hashlib

    for name, expected in report["artifacts"].items():
        data = (output / name).read_bytes()
        assert len(data) == expected["bytes"]
        assert hashlib.sha256(data).hexdigest() == expected["sha256"]


def test_inventory_covers_small_root_nested_sparse_and_link_entries(workspace):
    import os

    root = workspace / "local_data"
    (root / "plain").write_bytes(b"abc")
    (root / "nested").mkdir()
    (root / "nested" / "small").write_bytes(b"12345")
    with (root / "nested" / "sparse").open("wb") as stream:
        stream.truncate(10_000)
    os.link(root / "plain", root / "hardlink")
    (root / "loop").symlink_to(root)
    (root / "broken").symlink_to(root / "absent")
    os.mkfifo(root / "pipe")
    output = inventory.generate(root, workspace / "inventory")
    report = read_report(output, "inventory.json")
    assert report["totals"] == {
        "entries": 8,
        "regular_files": 4,
        "apparent_bytes": 10_011,
        "directories": 1,
        "symlinks_not_followed": 2,
        "special_files_not_read": 1,
    }
    assert report["content_hashed"] is False
    assert "not assessed" in report["scope"]
    assert len(report["source"]["entries"]) == 8
    assert [row["name"] for row in report["top_level"]] == [
        "broken",
        "hardlink",
        "loop",
        "nested",
        "pipe",
        "plain",
    ]
    assert_artifacts(output, report)


def test_empty_inventory_is_an_explicit_zero_observation(workspace):
    report = read_report(inventory.generate(), "inventory.json")
    assert report["totals"]["entries"] == 0
    assert report["totals"]["apparent_bytes"] == 0
    assert report["top_level"] == []


def test_inventory_escapes_names_in_markdown(workspace):
    (workspace / "local_data" / ("a|<b>" + chr(96) + "*_\nname")).write_bytes(b"abc")
    output = inventory.generate()
    text = (output / "inventory.md").read_text()
    assert "a&#124;&lt;b&gt;&#96;&#42;&#95;&#92;nname" in text
    assert "<b>" not in text


@pytest.mark.parametrize(
    "api,kwargs",
    [
        (inventory.generate, {"max_entries": 1}),
        (atlas.generate_atlas, {"max_entries": 1}),
    ],
)
def test_entry_limit_fails_before_publication(workspace, api, kwargs):
    fragment(workspace, "a")
    fragment(workspace, "b")
    with pytest.raises(ValueError, match="budget"):
        api(output=workspace / "output", **kwargs)
    assert not (workspace / "output").exists()
    assert not (workspace / "reports").exists()


def test_inventory_depth_budget_does_not_publish_partial_totals(workspace):
    (workspace / "local_data" / "a" / "b").mkdir(parents=True)
    with pytest.raises(ValueError, match="max_depth"):
        inventory.generate(output=workspace / "output", max_depth=1)
    assert not (workspace / "output").exists()


@pytest.mark.parametrize(
    "api,parameter,maximum",
    [
        (inventory.generate, "max_entries", 100_000),
        (inventory.generate, "max_depth", 32),
        (atlas.generate_atlas, "limit", 24),
        (atlas.generate_atlas, "max_pixels", 4096**2),
        (atlas.generate_atlas, "max_entries", 4096),
    ],
)
@pytest.mark.parametrize(
    "bad", [0, -1, True, np.bool_(True), 1.5, float("nan"), float("inf"), "bad", None]
)
def test_numeric_limits_reject_invalid_values(workspace, api, parameter, maximum, bad):
    with pytest.raises(ValueError):
        api(**{parameter: bad})
    assert not (workspace / "reports").exists()


@pytest.mark.parametrize(
    "api,parameter,maximum",
    [
        (inventory.generate, "max_entries", 100_000),
        (inventory.generate, "max_depth", 32),
        (atlas.generate_atlas, "limit", 24),
        (atlas.generate_atlas, "max_pixels", 4096**2),
        (atlas.generate_atlas, "max_entries", 4096),
    ],
)
def test_limits_have_hard_upper_bounds(workspace, api, parameter, maximum):
    with pytest.raises(ValueError, match="exceed"):
        api(**{parameter: maximum + 1})


@pytest.mark.parametrize("api", [inventory.generate, atlas.generate_atlas])
@pytest.mark.parametrize("kind", ["file", "link", "missing"])
def test_root_must_be_a_real_directory(workspace, api, kind):
    root = workspace / "root"
    if kind == "file":
        root.write_text("source")
    elif kind == "link":
        root.symlink_to(workspace / "local_data")
    with pytest.raises(ValueError, match="root"):
        api(root, workspace / "output")
    assert not (workspace / "output").exists()


@pytest.mark.parametrize("api", [inventory.generate, atlas.generate_atlas])
@pytest.mark.parametrize(
    "kind", ["directory", "file", "link", "broken_link", "inside", "ancestor"]
)
def test_output_must_be_new_and_disjoint(workspace, api, kind):
    root = workspace / "local_data"
    fragment(workspace)
    output = workspace / "output"
    if kind == "directory":
        output.mkdir()
        (output / "marker").write_text("preserve")
    elif kind == "file":
        output.write_text("preserve")
    elif kind == "link":
        output.symlink_to(root)
    elif kind == "broken_link":
        output.symlink_to(workspace / "missing")
    elif kind == "inside":
        output = root / "new"
    else:
        output = workspace
    before = (root / "fragment" / "inklabels.png").read_bytes()
    with pytest.raises(ValueError, match="exists|overlap"):
        api(root, output)
    assert (root / "fragment" / "inklabels.png").read_bytes() == before
    if kind == "directory":
        assert (output / "marker").read_text() == "preserve"
    if kind == "file":
        assert output.read_text() == "preserve"
    if kind == "broken_link":
        assert output.is_symlink()
    if kind == "inside":
        assert not output.exists()


def test_atlas_exact_counts_hashes_and_optional_masks(workspace):
    import hashlib
    import json
    import xml.etree.ElementTree as ET

    labels = np.array([[0, 1, 1], [1, 0, 1]], dtype=np.uint8)
    mask = np.array([[1, 0, 1], [1, 1, 0]], dtype=np.uint8)
    directory = fragment(workspace, "a", labels=labels, mask=mask)
    fragment(workspace, "b", labels=labels * 255)
    output = atlas.generate_atlas(output=workspace / "atlas")
    report = read_report(output, "atlas.json")
    first, second = report["fragments"]
    assert first["shape_yx"] == [2, 3]
    assert first["ink_pixels"] == second["ink_pixels"] == 4
    assert first["mask_pixels"] == 4
    assert first["ink_inside_mask"] == first["ink_outside_mask"] == 2
    assert first["mask_status"] == "binary_shape_checked"
    assert second["mask_status"] == "absent"
    assert second["mask"] is second["ink_inside_mask"] is None
    assert (
        first["labels"]["sha256"]
        == hashlib.sha256((directory / "inklabels.png").read_bytes()).hexdigest()
    )
    assert (
        first["mask"]["sha256"]
        == hashlib.sha256((directory / "mask.png").read_bytes()).hexdigest()
    )
    assert "CT registration" in report["scope"] and "not assessed" in report["scope"]
    with Image.open(output / "atlas.png") as image:
        assert list(image.size) == report["canvas_wh"] == [2250, 750]
        description = json.loads(image.info["Description"])
        assert description["fragments"][0]["labels"] == first["labels"]["sha256"]
    svg = ET.parse(output / "atlas.svg").getroot()
    assert (
        json.loads(svg.find(".//{http://purl.org/dc/elements/1.1/}description").text)
        == description
    )
    assert_artifacts(output, report)


def test_equivalent_binary_encodings_have_identical_previews(workspace):
    from scripts.data_catalogue import fragment_snapshot

    labels = np.array([[0, 1, 0], [1, 1, 0]], dtype=np.uint8)
    fragment(workspace, "a", labels=labels)
    fragment(workspace, "b", labels=labels * 255)
    root = workspace / "local_data"
    a, b = fragment_snapshot(root)["entries"]
    record_a, preview_a = atlas.inspect_fragment(root, a, 24)
    record_b, preview_b = atlas.inspect_fragment(root, b, 24)
    assert np.array_equal(preview_a, preview_b)
    assert set(np.unique(preview_a)) == {0, 255}
    assert record_a["ink_pixels"] == record_b["ink_pixels"] == 3


def test_zero_ink_is_reported_without_readiness_claim(workspace):
    fragment(workspace, labels=np.zeros((4, 6)))
    report = read_report(atlas.generate_atlas(), "atlas.json")
    assert report["fragments"][0]["ink_pixels"] == 0
    assert "not assessed" in report["scope"]


def test_selection_is_bounded_explicit_and_does_not_follow_directory_links(workspace):
    fragment(workspace, "a")
    fragment(workspace, "z", labels=np.ones((4, 6, 3)))
    (workspace / "local_data" / "alias").symlink_to(workspace / "local_data" / "a")
    (workspace / "local_data" / "inklabels.png").write_text("root file")
    report = read_report(atlas.generate_atlas(limit=1), "atlas.json")
    assert [item["name"] for item in report["fragments"]] == ["a"]
    assert report["selection"]["candidate_count"] == 2
    assert report["selection"]["uninspected_candidates"] == 1


@pytest.mark.parametrize(
    "values",
    [
        [[0, 2], [0, 0]],
        [[0, 1], [255, 0]],
    ],
)
@pytest.mark.parametrize("name", ["inklabels.png", "mask.png"])
def test_binary_validation_applies_to_both_sources(workspace, values, name):
    directory = fragment(workspace)
    Image.fromarray(np.tile(np.asarray(values, np.uint8), (2, 3))).save(
        directory / name
    )
    with pytest.raises(ValueError, match="binary"):
        atlas.generate_atlas()
    assert not (workspace / "reports").exists()


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "P", "I;16"])
def test_atlas_rejects_ambiguous_image_modes(workspace, mode):
    directory = fragment(workspace)
    Image.new(mode, (6, 4)).save(directory / "inklabels.png")
    with pytest.raises(ValueError, match="binary|grayscale"):
        atlas.generate_atlas()


@pytest.mark.parametrize("name", ["inklabels.png", "mask.png"])
@pytest.mark.parametrize(
    "kind", ["corrupt", "broken_chunk", "jpeg", "directory", "link", "broken_link"]
)
def test_bad_selected_sources_fail_instead_of_silent_skips(workspace, name, kind):
    directory = fragment(workspace, mask=np.ones((4, 6)))
    path = directory / name
    path.unlink()
    if kind == "corrupt":
        path.write_bytes(b"not an image")
    elif kind == "broken_chunk":
        path.write_bytes(_broken_png_chunk((4, 6)))
    elif kind == "jpeg":
        Image.new("L", (6, 4)).save(path, format="JPEG")
    elif kind == "directory":
        path.mkdir()
    else:
        target = workspace / "source.png"
        if kind == "link":
            Image.new("L", (6, 4)).save(target)
        path.symlink_to(target)
    with pytest.raises((ValueError, OSError)):
        atlas.generate_atlas(output=workspace / "output")
    assert not (workspace / "output").exists()


def test_empty_mask_is_not_positive_support(workspace):
    fragment(workspace, mask=np.zeros((4, 6)))
    with pytest.raises(ValueError, match="positive"):
        atlas.generate_atlas()


def test_png_pixel_budget_applies_before_decode(workspace, monkeypatch):
    directory = fragment(workspace)
    Image.new("L", (20, 30)).save(directory / "inklabels.png")
    original = Image.Image.load

    def guard(image, *args, **kwargs):
        if image.size == (20, 30):
            pytest.fail("oversized source decoded before pixel budget")
        return original(image, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "load", guard)
    with pytest.raises(ValueError, match="max_pixels"):
        atlas.generate_atlas(max_pixels=500)


def test_png_byte_budget_applies_before_open(workspace, monkeypatch):
    from scripts import data_catalogue

    fragment(workspace)
    monkeypatch.setattr(data_catalogue, "MAX_IMAGE_BYTES", 8)
    monkeypatch.setattr(
        Image, "open", lambda *args, **kwargs: pytest.fail("oversized source opened")
    )
    with pytest.raises(ValueError, match="bytes"):
        atlas.generate_atlas()


def test_pillow_safety_limit_is_preserved(workspace, monkeypatch):
    fragment(workspace)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(ValueError, match="safety"):
        atlas.generate_atlas()
    assert Image.MAX_IMAGE_PIXELS == 10


def test_empty_atlas_is_cli_failure(workspace):
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/generate_training_atlas.py")],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not (workspace / "reports").exists()


@pytest.mark.parametrize(
    "api,module",
    [
        (inventory.generate, inventory),
        (atlas.generate_atlas, atlas),
    ],
)
def test_json_failure_rolls_back_bundle(workspace, monkeypatch, api, module):
    fragment(workspace)

    def fail(*args, **kwargs):
        raise OSError("injected JSON failure")

    monkeypatch.setattr(module, "write_verified_json", fail)
    with pytest.raises(OSError, match="injected"):
        api(output=workspace / "output")
    assert not (workspace / "output").exists()
    assert not list(workspace.glob(".output-*"))


def test_second_image_failure_rolls_back_pair(workspace, monkeypatch):
    fragment(workspace)
    original = atlas.Figure.savefig

    def fail_svg(figure, filename, *args, **kwargs):
        if str(filename).endswith(".svg"):
            raise OSError("injected SVG failure")
        return original(figure, filename, *args, **kwargs)

    monkeypatch.setattr(atlas.Figure, "savefig", fail_svg)
    with pytest.raises(OSError, match="injected"):
        atlas.generate_atlas(output=workspace / "output")
    assert not (workspace / "output").exists()
    assert not list(workspace.glob(".output-*"))


@pytest.mark.parametrize(
    "api,module",
    [
        (inventory.generate, inventory),
        (atlas.generate_atlas, atlas),
    ],
)
def test_listing_change_during_processing_rolls_back(
    workspace, monkeypatch, api, module
):
    directory = fragment(workspace)
    original = module.write_verified_json

    def mutate(*args, **kwargs):
        original(*args, **kwargs)
        (directory / "unexpected").write_text("changed")

    monkeypatch.setattr(module, "write_verified_json", mutate)
    with pytest.raises(ValueError, match="changed"):
        api(output=workspace / "output")
    assert not (workspace / "output").exists()


def test_png_hash_detects_same_metadata_content_changes(workspace, monkeypatch):
    import os

    directory = fragment(workspace)
    path = directory / "inklabels.png"
    before = path.stat()
    original = atlas.write_verified_json

    def mutate(*args, **kwargs):
        original(*args, **kwargs)
        data = bytearray(path.read_bytes())
        data[-1] ^= 1
        path.write_bytes(data)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))

    monkeypatch.setattr(atlas, "write_verified_json", mutate)
    with pytest.raises(ValueError, match="PNG source changed"):
        atlas.generate_atlas(output=workspace / "output")
    assert not (workspace / "output").exists()


def test_missing_mask_appearing_during_processing_is_detected(workspace, monkeypatch):
    directory = fragment(workspace)
    original = atlas.write_verified_json

    def mutate(*args, **kwargs):
        original(*args, **kwargs)
        Image.new("L", (6, 4), 255).save(directory / "mask.png")

    monkeypatch.setattr(atlas, "write_verified_json", mutate)
    with pytest.raises(ValueError, match="changed"):
        atlas.generate_atlas(output=workspace / "output")
    assert not (workspace / "output").exists()


@pytest.mark.parametrize(
    "api,module",
    [
        (inventory.generate, inventory),
        (atlas.generate_atlas, atlas),
    ],
)
def test_destination_appearing_during_processing_is_preserved(
    workspace, monkeypatch, api, module
):
    fragment(workspace)
    output = workspace / "output"
    original = module.write_verified_json

    def appear(*args, **kwargs):
        original(*args, **kwargs)
        output.mkdir()
        (output / "marker").write_text("other writer")

    monkeypatch.setattr(module, "write_verified_json", appear)
    with pytest.raises(ValueError, match="appeared"):
        api(output=output)
    assert (output / "marker").read_text() == "other writer"
    assert not (output / "atlas.png").exists()
    assert not list(workspace.glob(".output-*"))


def test_rendering_preserves_global_figures_style_and_canvas(workspace):
    import matplotlib
    import matplotlib.pyplot as plt

    fragment(workspace, name="$not_math$\nwrapped")
    with matplotlib.rc_context({"savefig.bbox": "tight", "axes.facecolor": "red"}):
        before = dict(matplotlib.rcParams)
        figure = plt.figure()
        managed = plt.get_fignums()
        try:
            output = atlas.generate_atlas()
            assert dict(matplotlib.rcParams) == before
            assert plt.get_fignums() == managed
            with Image.open(output / "atlas.png") as image:
                assert image.size == (2250, 750)
        finally:
            plt.close(figure)


@pytest.mark.parametrize(
    "script,filename",
    [
        ("generate_manifest.py", "inventory.json"),
        ("generate_training_atlas.py", "atlas.json"),
    ],
)
def test_cli_with_absolute_paths_works_outside_checkout(workspace, script, filename):
    fragment(workspace)
    root = workspace / "local_data"
    before = (root / "fragment" / "inklabels.png").read_bytes()
    command = [
        sys.executable,
        str(REPO / "scripts" / script),
        "--root",
        str(root),
        "--out",
        str(workspace / "output"),
    ]
    result = subprocess.run(command, cwd="/tmp", capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (workspace / "output" / filename).exists()
    assert (root / "fragment" / "inklabels.png").read_bytes() == before
    second = subprocess.run(command, cwd="/tmp", capture_output=True, text=True)
    assert second.returncode != 0
    assert "exists" in second.stderr


@pytest.mark.parametrize(
    "script,option",
    [
        ("generate_manifest.py", "--max-entries"),
        ("generate_training_atlas.py", "--limit"),
    ],
)
def test_invalid_cli_limits_do_not_publish(workspace, script, option):
    fragment(workspace)
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / script), option, "0"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not (workspace / "reports").exists()


def test_inventory_entry_limit_counts_nested_entries(workspace):
    root = workspace / "local_data"
    (root / "a").mkdir()
    (root / "b").mkdir()
    (root / "a" / "payload").write_text("a")
    (root / "b" / "payload").write_text("b")
    output = inventory.generate(output=workspace / "exact", max_entries=4, max_depth=1)
    assert read_report(output, "inventory.json")["totals"]["entries"] == 4
    with pytest.raises(ValueError, match="budget"):
        inventory.generate(output=workspace / "limited", max_entries=3)
    assert not (workspace / "limited").exists()


def test_inventory_read_error_is_not_a_partial_success(workspace, monkeypatch):
    from scripts import data_catalogue

    (workspace / "local_data" / "a").mkdir()
    original = data_catalogue.os.scandir

    def fail_nested(path):
        if Path(path).name == "a":
            raise PermissionError("injected inaccessible directory")
        return original(path)

    monkeypatch.setattr(data_catalogue.os, "scandir", fail_nested)
    with pytest.raises(PermissionError, match="injected"):
        inventory.generate(output=workspace / "output")
    assert not (workspace / "output").exists()


def test_bilevel_png_is_normalized_and_thumbnail_is_bounded(workspace):
    from scripts.data_catalogue import fragment_snapshot

    directory = fragment(workspace)
    with Image.new("1", (1024, 256), 1) as image:
        image.save(directory / "inklabels.png")
    root = workspace / "local_data"
    entry = fragment_snapshot(root)["entries"][0]
    record, preview = atlas.inspect_fragment(root, entry, 1024 * 256)
    assert record["shape_yx"] == [256, 1024]
    assert record["ink_pixels"] == 1024 * 256
    assert preview.shape == (128, 512)
    assert (preview == 255).all()


def test_changed_source_during_capture_is_rejected(workspace, monkeypatch):
    from scripts import data_catalogue

    directory = fragment(workspace)
    original = data_catalogue.signature
    calls = 0

    def changed(path):
        nonlocal calls
        result = original(path)
        if Path(path).name == "inklabels.png":
            calls += 1
            if calls >= 2:
                return {**result, "mtime_ns": result["mtime_ns"] + 1}
        return result

    monkeypatch.setattr(data_catalogue, "signature", changed)
    with pytest.raises(ValueError, match="changed while reading"):
        data_catalogue.captured_binary_png(directory / "inklabels.png", max_pixels=24)


@pytest.mark.parametrize(
    "long_name",
    [
        "z_" + "long_fragment_name_" * 10,
        "z " + "a" * 24 + " " + "b" * 24 + " " + "c" * 20,
    ],
)
def test_long_caption_does_not_overlap_other_panel_images(
    workspace, monkeypatch, long_name
):
    names = [str(index) for index in range(6)] + [long_name]
    for index, name in enumerate(names):
        shape = (384, 64) if index == 3 else (128, 256)
        fragment(workspace, name, labels=np.ones(shape))
    original = atlas.Figure.savefig

    def check_bounds(figure, filename, *args, **kwargs):
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        title = figure.axes[6].title.get_window_extent(renderer)
        assert not title.overlaps(figure.axes[3].get_window_extent(renderer))
        return original(figure, filename, *args, **kwargs)

    monkeypatch.setattr(atlas.Figure, "savefig", check_bounds)
    output = atlas.generate_atlas()
    report = read_report(output, "atlas.json")
    assert report["fragments"][-1]["name"] == names[-1]
