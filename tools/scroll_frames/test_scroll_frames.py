"""Tests for scroll-frames. Both regression tests below come from real bugs, not imagination."""

import json

import pytest
import scroll_frames
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
    "bad",
    [
        "notamesh",
        f"{SEG}.tifxyz",
        f"{SEG}-on-abc-2.4um.tifxyz",
        # A voxel size that is not a positive number raised, or divided by zero.
        f"{SEG}-on-20260411134726-1.2.3um.tifxyz",
        f"{SEG}-on-20260411134726-.um.tifxyz",
        f"{SEG}-on-20260411134726-0um.tifxyz",
    ],
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


def test_render_without_any_readable_scale_says_so():
    """REGRESSION. With no meta.json read, render indexed an empty list of declared scales."""
    out = render("x/y", frames_for(NAMES))
    assert "COLLISION" in out and "no meta.json could be read for a scale" in out
    assert "declare scale" not in out


def test_render_with_some_scales_unread_does_not_say_all():
    metas = {n: {"scale": [0.05, 0.05]} for n in NAMES[:2]}
    out = render("x/y", frames_for(NAMES, metas))
    assert "2 of 4 meshes declare a scale, all 0.05" in out and "all 4" not in out
    assert collision(frames_for(NAMES, metas))["n_declaring_scale"] == 2


def _run(monkeypatch, capsys, argv, fetched):
    def fetch(segment):
        if isinstance(fetched, Exception):
            raise fetched
        return fetched

    monkeypatch.setattr(scroll_frames, "_fetch", fetch)
    code = scroll_frames.main(argv)
    return code, capsys.readouterr()


def test_main_exits_1_on_a_collision_and_0_without(monkeypatch, capsys):
    metas = {n: {"scale": [0.05, 0.05]} for n in NAMES}
    code, out = _run(monkeypatch, capsys, ["list", "P/s"], (NAMES, metas))
    assert code == 1 and "COLLISION" in out.out
    code, _ = _run(monkeypatch, capsys, ["list", "P/s"], (NAMES[:1], {}))
    assert code == 0


def test_main_json_reports_the_frames_and_the_collision(monkeypatch, capsys):
    metas = {n: {"scale": [0.05, 0.05]} for n in NAMES}
    code, out = _run(monkeypatch, capsys, ["list", "P/s", "--json"], (NAMES, metas))
    report = json.loads(out.out)
    assert code == 1 and report["collision"]["n_declaring_scale"] == 4
    assert [f["um_per_voxel"] for f in report["frames"]] == [1.129, 2.4, 7.91, 45.532]


@pytest.mark.parametrize(
    "failure", [ImportError("no s3fs"), FileNotFoundError("no such segment")]
)
def test_a_failed_lookup_exits_2_not_1(monkeypatch, capsys, failure):
    """REGRESSION. 1 means a collision, and an uncaught error exited 1 too."""
    code, out = _run(monkeypatch, capsys, ["list", "P/s"], failure)
    assert code == 2 and "scrollframes:" in out.err and out.out == ""


def test_a_segment_without_its_scroll_exits_2(monkeypatch, capsys):
    """REGRESSION. It raised SystemExit with a message, which exits 1: a collision."""
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, capsys, ["list", SEG], (NAMES, {}))
    assert exc.value.code == 2
