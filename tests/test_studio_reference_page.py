"""The Studio reference page draws known-letter maps as the band pages draw theirs: same encoding, turned into reading
orientation, thumbnails at one eighth with a 1 cm bar, and studio_band's numbers over the rendered area."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rp = _load("reference_page_under_test", BAND / "reference_page.py")


def _render(path: Path, rendered: np.ndarray) -> Path:
    import zarr

    data = np.zeros((66, *rendered.shape), np.uint8)
    data[33] = np.where(rendered, 100, 0)
    zarr.open(str(path), mode="w").create_dataset(
        "0", data=data, chunks=(66, *rendered.shape)
    )
    return path


def _panel(tmp_path, key="0211_w035", flip_ud=False, flip_lr=True):
    h, w = 760, 1140  # two by three tiles of 380
    rendered = np.zeros((h, w), bool)
    rendered[:, :760] = True  # the right third was not rendered: its tile is not scored
    prob = np.zeros((h, w), np.float32)
    prob[:380, :380] = 0.8  # the top-left tile is all ink
    np.save(tmp_path / f"{key}.npy", prob)
    render = _render(tmp_path / f"{key}_66.zarr", rendered)
    return rp.Panel(
        key,
        "PHerc. 211",
        "Studio",
        tmp_path / f"{key}.npy",
        render,
        flip_ud,
        flip_lr,
        9.362,
    )


def test_a_panel_is_turned_into_reading_orientation_and_scored_on_its_rendered_area(
    tmp_path,
):
    import cv2

    out = tmp_path / "page"
    path = rp.build(out, [_panel(tmp_path)])
    n = json.loads((out / "reference.json").read_text())["panels"]["0211_w035"]
    assert n["tiles_scored"] == 4 and n["largest_tile_ink_share"] == 1.0
    assert n["ink_share"] == 0.25  # one tile of ink over four rendered tiles
    image = cv2.imread(str(out / "images" / "0211_w035.png"), cv2.IMREAD_GRAYSCALE)
    assert image.shape == (760, 1140)
    assert (
        image[0, -1] == 204 and image[0, 0] == 0
    )  # mirrored: the ink is now top right (0.8 x 255)
    thumb = cv2.imread(str(out / "thumbs" / "0211_w035.png"), cv2.IMREAD_GRAYSCALE)
    assert thumb.shape == (95, 142)
    assert n["bar_px_on_thumbnail"] == 134  # 1 cm at 9.362 um, at one eighth
    assert (thumb[84:87, 6:140] == 255).all()  # the bar, bottom left
    assert (
        "0211_w035" in path.read_text()
        and "planes in reverse order" in path.read_text()
    )


def test_upside_down_flips_rows(tmp_path):
    import cv2

    out = tmp_path / "page"
    rp.build(out, [_panel(tmp_path, flip_ud=True, flip_lr=False)])
    image = cv2.imread(str(out / "images" / "0211_w035.png"), cv2.IMREAD_GRAYSCALE)
    assert image[-1, 0] == 204 and image[0, 0] == 0


def test_a_map_that_does_not_fit_its_render_is_refused(tmp_path):
    p = _panel(tmp_path)
    np.save(p.studio_map, np.zeros((10, 10), np.float32))
    try:
        rp.build(tmp_path / "page", [p])
    except SystemExit as e:
        assert "its render" in str(e)
    else:
        raise AssertionError("a map of the wrong shape was drawn")


def test_the_letter_sizes_and_band_links_are_on_the_page(tmp_path):
    sizes = tmp_path / "sizes.csv"
    sizes.write_text("id,height_mm\n1,2.0\n2,3.0\n3,5.0\n")
    letters = rp.letter_heights(sizes)
    assert letters == {"letters": 3, "median_mm": 3.0, "min_mm": 2.0, "max_mm": 5.0}
    page = rp.build(
        tmp_path / "page",
        [_panel(tmp_path)],
        letters,
        [("PHerc. 0826", "a/index.html")],
    ).read_text()
    assert "2.0 to 5.0 mm tall (median 3.0 mm)" in page
    assert "about 320 pixels at full resolution and 40 on a thumbnail" in page
    assert "<a href='../a/index.html'>PHerc. 0826</a>" in page


def _custom(
    tmp_path,
    key,
    prob,
    rendered,
    flip_ud=False,
    flip_lr=False,
    voxel_um=9.362,
    what="Studio",
):
    np.save(tmp_path / f"{key}.npy", np.asarray(prob, np.float32))
    return rp.Panel(key, "PHerc. 211", what, tmp_path / f"{key}.npy", _render(tmp_path / f"{key}_66.zarr", rendered),
                    flip_ud, flip_lr, voxel_um)  # fmt: skip


def _drawn(tmp_path, panel):
    import cv2

    out = tmp_path / "page"
    rp.build(out, [panel])
    record = json.loads((out / "reference.json").read_text())["panels"][panel.key]
    image = cv2.imread(str(out / "images" / f"{panel.key}.png"), cv2.IMREAD_GRAYSCALE)
    thumb = cv2.imread(str(out / "thumbs" / f"{panel.key}.png"), cv2.IMREAD_GRAYSCALE)
    return record, image, thumb, (out / "index.html").read_text()


def test_a_panel_with_nothing_rendered_has_no_ink_share_and_no_tile(tmp_path):
    record = _drawn(
        tmp_path,
        _custom(
            tmp_path, "empty", np.full((760, 760), 0.9), np.zeros((760, 760), bool)
        ),
    )[0]
    assert (record["rendered_pixels"], record["ink_share"]) == (0, None)
    assert (record["tiles_scored"], record["largest_tile_ink_share"]) == (0, None)


def test_the_image_rounds_and_clips_the_probability_and_ink_starts_at_exactly_half(
    tmp_path,
):
    prob = np.zeros((760, 760))
    prob[:380, :380] = 0.5  # 127.5, rounded to 128; and ink
    prob[700, 700], prob[700, 701] = 1.5, -0.2
    record, image, _, _ = _drawn(
        tmp_path, _custom(tmp_path, "edges", prob, np.ones((760, 760), bool))
    )
    assert (image[0, 0], image[700, 700], image[700, 701]) == (128, 255, 0)
    assert record["ink_share"] == 0.25 and record["largest_tile_ink_share"] == 1.0


@pytest.mark.parametrize(
    ("shape", "voxel_um", "bar_rows"),
    [
        (
            (760, 1140),
            8.9,
            None,
        ),  # a 140-pixel bar does not fit 142 columns with its margins
        ((88, 1140), 9.362, None),  # an 11-row thumbnail has no room for it
        ((96, 1140), 9.362, (1, 4)),  # a 12-row thumbnail has
    ],
)
def test_the_bar_is_drawn_only_where_it_fits(tmp_path, shape, voxel_um, bar_rows):
    panel = _custom(
        tmp_path, "bar", np.zeros(shape), np.ones(shape, bool), voxel_um=voxel_um
    )
    thumb = _drawn(tmp_path, panel)[2]
    drawn = np.argwhere(thumb == 255)
    if bar_rows is None:
        assert drawn.size == 0
    else:
        assert sorted(set(drawn[:, 0])) == list(range(*bar_rows))
        assert (drawn[:, 1].min(), drawn[:, 1].max()) == (6, 139)


def test_a_map_narrower_than_eight_pixels_still_has_a_thumbnail(tmp_path):
    thumb = _drawn(
        tmp_path, _custom(tmp_path, "narrow", np.zeros((16, 4)), np.ones((16, 4), bool))
    )[2]
    assert thumb.shape == (2, 1)


def test_the_letter_heights_median_is_rounded_to_hundredths(tmp_path):
    sizes = tmp_path / "sizes.csv"
    sizes.write_text("id,height_mm\n1,1.0\n2,1.333\n")
    assert rp.letter_heights(sizes) == {
        "letters": 2,
        "median_mm": 1.17,
        "min_mm": 1.0,
        "max_mm": 1.333,
    }


@pytest.mark.parametrize(
    ("flip_ud", "flip_lr", "shown"),
    [
        (False, False, "(unturned)"),
        (True, False, "(upside down)"),
        (True, True, "(mirrored, upside down)"),
    ],
)
def test_the_record_and_the_page_name_each_panels_turn_and_escape_its_text(
    tmp_path, flip_ud, flip_lr, shown
):
    panel = _custom(tmp_path, "turn", np.zeros((40, 40)), np.ones((40, 40), bool), flip_ud, flip_lr,
                    voxel_um=7.91, what="planes <reversed>")  # fmt: skip
    record, _, _, page = _drawn(tmp_path, panel)
    assert (record["flip_ud"], record["flip_lr"], record["voxel_um"]) == (
        flip_ud,
        flip_lr,
        7.91,
    )
    assert f"turn</a> {shown}<br>planes &lt;reversed&gt;</td>" in page
    assert "Band pages" not in page and "Letter size" not in page  # neither given


def test_the_default_panels_are_211s_four_windings_and_343s_surface_each_with_its_reversed_planes(
    tmp_path, monkeypatch
):
    fl = tmp_path / "fl"
    reference = fl / "pherc343_repro/work/studio_343/reference"
    reference.mkdir(parents=True)
    (reference / "concat_w047-w048_R5B2_z9500-11000.json").write_text(
        json.dumps(
            {"orientation": {"flip_ud": False, "flip_lr": True}, "voxel_size_um": 7.91}
        )
    )
    band = fl / "pherc0211_band_z7650"
    calls = []
    monkeypatch.setattr(rp.band_index, "axis", lambda path: ("axis", path))
    monkeypatch.setattr(
        rp.analysis, "load_tifxyz", lambda path: (("xyz", path), "valid")
    )

    def orientation(xyz, valid, umbilicus, top_to_bottom, left_handed):
        calls.append((xyz, valid, umbilicus, top_to_bottom, left_handed))
        return {"flip_ud": True, "flip_lr": False}

    monkeypatch.setattr(rp.band_index, "orientation", orientation)
    panels = rp.default_panels(fl)
    axis = ("axis", band / "dataset/umbilicus.json")
    assert calls == [
        (
            ("xyz", band / f"work/final_e2e/{w}.tifxyz"),
            "valid",
            axis,
            True,
            False,
        )  # top to bottom, right-handed
        for w in ("w033", "w034", "w035", "w036")
    ]
    maps = fl / "pherc0211_control/work/studio_e2e/maps"
    expected = []
    for w in ("w033", "w034", "w035", "w036"):
        for suffix in ("", "_reversed"):
            expected.append((f"0211_{w}{suffix}", maps / f"{w}{suffix}.npy", band / f"work/render_e2e/{w}_66.zarr",
                             True, False, 9.362))  # fmt: skip
    work = fl / "pherc343_repro/work"
    for stem in ("forward", "reversed"):
        expected.append((f"0343_{stem}", work / f"studio_343/maps/{stem}.npy",
                         work / "concat_w047-w048_R5B2_z9500-11000_66.zarr", False, True, 7.91))  # fmt: skip
    assert [
        (p.key, p.studio_map, p.render, p.flip_ud, p.flip_lr, p.voxel_um)
        for p in panels
    ] == expected


def test_main_reads_the_letter_sizes_and_links_only_the_band_pages_that_exist_under_the_given_root(
    tmp_path, monkeypatch
):
    fl = tmp_path / "fl"
    reference = fl / "pherc343_repro/work/studio_343/reference"
    reference.mkdir(parents=True)
    (reference / "concat_w047-w048_R5B2_z9500-11000_letter_sizes.csv").write_text(
        "id,height_mm\n1,2.5\n"
    )
    label, path = rp.BAND_PAGES[1]
    (fl / path).parent.mkdir(parents=True)
    (fl / path).write_text("")
    got = {}
    monkeypatch.setattr(rp, "default_panels", lambda root: [("panels of", root)])

    def build(out, panels, letters, pages):
        got.update(out=out, panels=panels, letters=letters, pages=pages)
        return out / "index.html"

    monkeypatch.setattr(rp, "build", build)
    assert rp.main([str(tmp_path / "page"), "--fl-root", str(fl)]) == 0
    assert got == {
        "out": tmp_path / "page",
        "panels": [("panels of", fl)],
        "letters": {"letters": 1, "median_mm": 2.5, "min_mm": 2.5, "max_mm": 2.5},
        "pages": [(label, path)],
    }
