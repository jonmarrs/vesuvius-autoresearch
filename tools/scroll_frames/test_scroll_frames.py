"""Tests for scroll-frames. Both regression tests below come from real bugs, not imagination."""

import pytest
from scroll_frames import Frame, collision, frames_for, parse_mesh_name, render

SEG = "20230702185753"
NAMES = [
    f"{SEG}-on-20260310170716-45.532um.tifxyz",
    f"{SEG}-on-20230205180739-7.91um.tifxyz",
    f"{SEG}-on-20260411134726-2.4um.tifxyz",
    f"{SEG}-on-20260608103018-1.129um.tifxyz",
]


def test_parses_scan_and_voxel_size_from_the_name():
    """Voxel size lives ONLY in the filename; meta.json does not carry it."""
    f = parse_mesh_name(f"{SEG}-on-20260411134726-2.4um.tifxyz")
    assert f.scan == "20260411134726" and f.um_per_voxel == 2.4


@pytest.mark.parametrize(
    "bad", ["notamesh", f"{SEG}.tifxyz", f"{SEG}-on-abc-2.4um.tifxyz"]
)
def test_non_conforming_names_are_skipped_not_guessed(bad):
    assert parse_mesh_name(bad) is None
    assert frames_for([bad]) == []


def test_frames_are_ordered_finest_first():
    assert [f.um_per_voxel for f in frames_for(NAMES)] == [1.129, 2.4, 7.91, 45.532]


def test_identical_declared_scale_with_differing_voxel_size_is_a_collision():
    metas = {n: {"scale": [0.05, 0.05]} for n in NAMES}
    c = collision(frames_for(NAMES, metas))
    assert c["collides"] and c["indistinguishable_metadata"]
    assert c["voxel_size_spread"] == pytest.approx(45.532 / 1.129)


def test_float32_and_float64_spellings_of_one_scale_still_collide():
    """REGRESSION. The catalog stores this field at both precisions, so the same value
    appears as 0.05 and 0.05000000074505806. Comparing exactly called those
    'distinguishable metadata' and reported no collision on the real bucket."""
    metas = {NAMES[0]: {"scale": [0.05, 0.05]}}
    metas.update({n: {"scale": [0.05000000074505806, 0.05]} for n in NAMES[1:]})
    assert collision(frames_for(NAMES, metas))["collides"]


def test_genuinely_different_scales_are_not_a_collision():
    """The check must discriminate: metadata that DOES distinguish frames is fine."""
    metas = {n: {"scale": [0.05 * (i + 1), 0.05]} for i, n in enumerate(NAMES)}
    assert not collision(frames_for(NAMES, metas))["collides"]


def test_a_single_frame_cannot_collide():
    assert not collision(frames_for(NAMES[:1]))["collides"]


def test_same_voxel_size_twice_is_not_flagged():
    names = [
        f"{SEG}-on-A1-2.4um.tifxyz".replace("A1", "20260411134726"),
        f"{SEG}-on-20260319133554-2.4um.tifxyz",
    ]
    metas = {n: {"scale": [0.05, 0.05]} for n in names}
    assert not collision(frames_for(names, metas))["collides"]


def test_render_states_that_the_ratio_is_not_a_transform():
    """The tool must not be readable as offering a conversion; that is the fudge-factor trap."""
    out = render("x/y", frames_for(NAMES, {n: {"scale": [0.05, 0.05]} for n in NAMES}))
    assert "not a transform" in out
    assert "COLLISION" in out


def test_meta_enrichment_is_optional():
    """Filenames alone must expose a collision, since meta.json may be unreadable."""
    assert collision(frames_for(NAMES))["voxel_size_spread"] > 40
