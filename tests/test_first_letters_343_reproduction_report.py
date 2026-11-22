"""reports/first_letters_343_reproduction.md (the First Letters kill test): every figure from its JSON record, the
verdict recomputed from the record's own checks, and what the strategy says about it."""

from __future__ import annotations

import json
import statistics
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "reports/first_letters_343_reproduction.json").read_text())
REPORT = " ".join(
    (ROOT / "reports/first_letters_343_reproduction.md").read_text().split()
)
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
PUB = D["image"]["pubstats"]
OWN = D["image"]["ownstats"]


def letter_ious(side):
    return [box["ink_shown_iou"] for box in side["comparison"]["letter_boxes"]]


def minutes(seconds):
    return f"{int(seconds // 60)} min {round(seconds % 60)} s"


def test_the_verdict_follows_from_the_recorded_checks():
    c = PUB["comparison"]
    reproduced = (
        D["mesh"]["all_match"]
        and D["render"]["check"]["decoded_voxels_identical_where_published"]
        and c["ink_shown_iou"] >= 0.99
        and c["abs_diff"]["max"] <= 8
    )
    assert reproduced and D["verdict"] == "REPRODUCED"
    assert "**Verdict `REPRODUCED`, for the part of the chain that was run.**" in REPORT
    assert f"(commit `{D['recipe']['commit'][:8]}`)" in REPORT
    assert D["recipe"]["repository"] in REPORT
    assert D["date"] in REPORT.split(")")[0] + ")"


def test_the_scope_is_stated_as_run():
    assert D["ink"]["jobs_run"] == len(D["ink"]["jobs"]) == 8
    assert {job["depth"] for job in D["ink"]["jobs"]} == {1}
    assert D["ink"]["full_recipe_jobs"] == 496 and "(496 GPU jobs)" in REPORT
    assert any(
        "spiral fit" in item for item in D["scope"]["taken_from_the_publication"]
    )
    assert any(
        "pooled over 31 depths" in item
        for item in D["scope"]["taken_from_the_publication"]
    )
    assert (
        "The step that produced the windings (spiral fit, snap, flatten) was not run"
        in REPORT
    )
    assert "Those statistics were copied from the published sidecar." in REPORT
    assert (
        "The test says nothing about whether the recipe finds text on an unread scroll."
        in REPORT
    )
    assert any("has not been read" in item for item in D["not_measured"])


def test_the_mesh_and_render_rows():
    files = D["mesh"]["files"]
    assert sorted(files) == ["meta.json", "x.tif", "y.tif", "z.tif"]
    assert all(f["match"] and f["ours"] == f["published"] for f in files.values())
    assert "| 4 of 4 identical |" in REPORT
    check = D["render"]["check"]
    assert all(layer["match"] for layer in check["area_layers_sha256"].values())
    assert list(check["area_layers_sha256"]) == ["34"]
    assert check["area_valid_mask_sha256"]["match"] and check["shape_matches"]
    fraction = check["area_valid_fraction"]
    assert fraction["ours"] == fraction["published"]
    assert f"both identical; valid fraction {fraction['ours']} on both sides" in REPORT
    tree = check["tree"]
    assert (
        tree["match"] is False and tree["ours"]["files"] == tree["published"]["files"]
    )
    assert (
        f"**differs**: {tree['ours']['files']:,} files on both sides, {tree['ours']['bytes']:,} bytes here against "
        f"{tree['published']['bytes']:,} published. Cause not identified"
    ) in REPORT


def test_the_ink_map_and_image_rows():
    match = PUB["comparison"]["ink_map_sha256_match"]
    assert match == {
        "dnative": True,
        "hecate": True,
        "ink9-42": False,
        "ink9-43": False,
    }
    assert "dense_native and Hecate identical; ink_9um seeds 42 and 43 differ" in REPORT
    whole = PUB["whole_png"]
    h, w = whole["shape_hw"]
    share = 100 * whole["differing_pixels"] / whole["pixels"]
    assert (
        f"| pixels of the whole {w} × {h} PNG | {whole['differing_pixels']:,} of {whole['pixels']:,} differ "
        f"({share:.3f}%), by at most {whole['max_abs_diff']} of 255 |"
    ) in REPORT
    assert f"{100 - share:.2f}% of its pixels are identical" in REPORT
    assert f"none differs by more than {whole['max_abs_diff']} of 255" in REPORT
    ph, pw = PUB["comparison"]["panel_hw"]
    ious = letter_ious(PUB)
    assert (
        f"| Image, data panel only ({pw} × {ph}) | ink drawn on both / on either | IoU "
        f"{PUB['comparison']['ink_shown_iou']}; in each of the {len(ious)} letter boxes at least {min(ious)} |"
    ) in REPORT


def test_the_rerun_and_the_shift_control():
    maps = D["rerun_same_model"]["maps"]
    assert D["rerun_same_model"]["model"] == "hybrid_3d2d-seed42"
    assert maps["_reverse"]["max"] == maps["forward"]["max"] == 1
    assert (
        f"differ on {100 * maps['_reverse']['differing_fraction']:.3f}% of pixels (reading side; "
        f"{100 * maps['forward']['differing_fraction']:.3f}% on the other side), never by more than one grey level"
    ) in REPORT
    shifted = PUB["comparison"]["control_ours_shifted"]
    iou = [shifted[k]["ink_shown_iou"] for k in ("16px", "64px", "256px")]
    r = [shifted[k]["ink_tint_pearson_r"] for k in ("16px", "64px", "256px")]
    assert (
        f"gives IoU {iou[0]:.3f} at 16 px, {iou[1]:.3f} at 64 px and {iou[2]:.3f} at 256 px "
        f"(tint correlation {r[0]:.3f}, {r[1]:.3f}, {r[2]:.3f})"
    ) in REPORT


def test_the_statistics_table():
    p, o = PUB["comparison"], OWN["comparison"]
    shown = p["ink_shown_fraction"]
    assert (
        f"| ink drawn, share of the panel (published {shown['published']}) | {shown['ours']} | "
        f"{o['ink_shown_fraction']['ours']} |"
    ) in REPORT
    assert (
        f"| IoU of drawn ink with the published image | {p['ink_shown_iou']} | {o['ink_shown_iou']} |"
        in REPORT
    )
    assert (
        f"| tint correlation with the published image | {p['ink_tint_pearson_r']:.3f} | "
        f"{o['ink_tint_pearson_r']:.3f} |"
    ) in REPORT
    a, b = letter_ious(PUB), letter_ious(OWN)
    assert (
        f"| letter boxes: lowest / median IoU | {min(a)} / {statistics.median(a):.3f} | "
        f"{min(b):.3f} / {statistics.median(b):.3f} |"
    ) in REPORT
    norm = o["normalisation"]
    assert all(
        m["ours"]["mean"] > m["published"]["mean"]
        and m["ours"]["sd"] > m["published"]["sd"]
        for m in norm.values()
    )
    hecate = norm["hecate"]
    assert (
        f"(Hecate: mean {hecate['ours']['mean']:.3f} against {hecate['published']['mean']:.3f})"
        in REPORT
    )
    assert o["ensemble_stretch"]["ours"]["source"].startswith("these maps")
    assert p["ensemble_stretch"]["ours"] == p["ensemble_stretch"]["published"]


def test_the_costs():
    render, ink = D["render"], D["ink"]
    assert (
        render["exit"] == 0
        and ink["exit"] == 0
        and all(job["exit"] == 0 for job in ink["jobs"])
    )
    assert (
        f"| {minutes(render['wall_seconds'])} | {render['threads']} threads, {render['cache_gb']} GB chunk cache"
        in REPORT
    )
    assert (
        f"container capped at {render['container_memory_cap'].rstrip('g')} GB" in REPORT
    )
    assert f"{render['ct_bytes_cached'] / 1e9:.2f} GB of CT streamed" in REPORT
    total = sum(ink["wall_seconds"].values())
    assert f"| {minutes(total)} | one villa job and one Hecate job at a time" in REPORT
    assert f"peak GPU memory {ink['gpu']['peak_memory_mib']:,} MiB" in REPORT

    def span(name):
        s = [job["seconds"] for job in ink["jobs"] if job["model"].startswith(name)]
        return f"{min(s)}–{max(s)} s"

    assert (
        f"dense_native {span('dnative')}, ink_9um {span('hybrid_3d2d')}, Hecate {span('hecate')}"
        in REPORT
    )
    assert (
        f"the full sweep is 31 × {total:,} s, about {31 * total / 3600:.0f} hours"
        in REPORT
    )
    loop = D["training_loop"]
    assert f"{loop['stopped'][11:16]} to {loop['started'][11:16]} PST" in REPORT


def test_the_strategy_reports_the_kill_test_as_passed():
    assert "reports/first_letters_343_reproduction.md" in STRATEGY
    assert "not yet run here" not in STRATEGY
    assert "waits for the owner's decision on pausing the training loop" not in STRATEGY
    whole = PUB["whole_png"]
    share = 100 * whole["differing_pixels"] / whole["pixels"]
    assert f"{100 - share:.2f}% of the published image's pixels" in STRATEGY
    # The mesh step was not part of the kill test; finding 110 ran it on 2026-11-12.
    assert "reports/first_letters_343_mesh_step.md" in STRATEGY


def test_the_host_the_jobs_and_the_render_shape_are_the_record_s():
    host, jobs, render = D["host"], D["ink"]["jobs"], D["render"]
    assert (
        f"Host: {host['cpu_cores']} cores, {host['ram_gb']} GB of RAM, one RTX 4090."
        in REPORT
    )
    assert host["gpu"].startswith("RTX 4090")
    models = {job["model"] for job in jobs}
    assert len(models) == 4 and len(jobs) == 2 * len(models)
    assert {job["render"] for job in jobs} == {"plain", "padded"}
    assert {job["depth"] for job in jobs} == {1}
    assert (
        f"| Ink, {len(jobs)} jobs ({len(models)} models × plain and padded render, depth +1) |"
        in REPORT
    )
    layers, height, width = render["check"]["shape"]
    assert f"| Render, {layers} layers of {height} × {width} |" in REPORT
    assert f"| {layers}-layer render |" in REPORT
    source = render["renderer_source"]
    assert "75c79ac5f" in source and "identical to 41701aa" in source
    assert (
        "our source build of villa `75c79ac5f`, whose `volume-cartographer` tree is identical to `41701aa`"
        in REPORT
    )


def test_the_strategy_s_costs_and_dates_are_the_record_s():
    render, ink, loop = D["render"], D["ink"], D["training_loop"]
    total = sum(ink["wall_seconds"].values())
    assert ink["jobs_run"] == 8
    assert (
        f"({render['wall_seconds'] / 60:.0f} minutes, and {total / 60:.0f} minutes for the eight jobs of one depth, "
        f"at a peak of {ink['gpu']['peak_memory_mib']:,} MiB of GPU memory)" in STRATEGY
    )
    stopped, started = (
        datetime.fromisoformat(loop[key]) for key in ("stopped", "started")
    )
    paused = int((started - stopped).total_seconds() // 60)
    assert f"The kill test stopped it for {paused} minutes." in STRATEGY
    day = date.fromisoformat(D["date"])
    on = f"on {day:%B} {day.day}"
    for sentence in (
        f"The kill test passed {on} for the chain from the published windings",
        f"Passed {on} from the published windings onward",
        f"The kill test ran {on};",
        f"Answered {on}: yes.",
    ):
        assert sentence in STRATEGY
