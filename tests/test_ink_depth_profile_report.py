"""Finding 87's report quotes numbers; each must come from its saved artifact."""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPORT = (REPO / "reports" / "ink_depth_profile.md").read_text()
DATA = json.loads((REPO / "reports" / "ink_depth_profile.json").read_text())
FR47 = DATA["fragments"]["PHercParis2Fr47"]
FR143 = DATA["fragments"]["PHercParis2Fr143"]
BOTH = (FR47, FR143)


def _same(key):
    values = {json.dumps(f[key]) for f in BOTH}
    assert len(values) == 1, f"{key} differs between the fragments: {values}"
    return FR47[key]


def _of(share):
    return f"{share[0]} of {share[1]}"


def _auc(fragment, k):
    return fragment["per_slice"][k]["auc"]


def _row(fragment):
    aucs = [s["auc"] for s in fragment["per_slice"]]
    k, bright = fragment["strongest_contrast_slice"], fragment["brightest_slice"]
    layer = fragment["zarr_slice_0_is_layer"]
    seen = fragment["coverage"]["validation_contains"][str(k)]
    return (
        f"| {min(aucs):.4f}–{max(aucs):.4f} | zarr {k} (layer {k + layer}), "
        f"{_auc(fragment, k):.4f} | zarr {bright} (layer {bright + layer}) | {_of(seen)} |"
    )


def _quoted():
    depths = {f["shape"][0] for f in BOTH}
    assert len(depths) == 1, depths
    depth = depths.pop()
    layer0 = _same("zarr_slice_0_is_layer")
    band = _same("detector_band_in_zarr_slices")
    # The window geometry is shared; the per-slice shares name each fragment's
    # own slices, so only slice 16 is compared.
    shared = [
        {
            k: v if not k.endswith("_contains") else v["16"]
            for k, v in f["coverage"].items()
        }
        for f in BOTH
    ]
    assert shared[0] == shared[1], shared
    coverage = FR47["coverage"]
    rows = [m for f in BOTH for m in f["layer_mapping"]]
    first, last = coverage["validation_windows"]
    return {
        "depth": f"**{depth}** slices",
        "first layer": f"surface-volume **layer {layer0}**",
        "layer range": f"layers {layer0}–{layer0 + depth - 1}",
        "match": f"at most **{max(m['mean_abs_diff'] for m in rows):.3f}**",
        "next best": f"at least **{min(m['next_best_diff'] for m in rows):.3f}**",
        "band": f"zarr slices **{band}**",
        "detector files": (
            f"`layers/{DATA['detector_layers'][0]}.tif`–`{DATA['detector_layers'][1] - 1}.tif`"
        ),
        "read": f"**{coverage['read_slices']}** slices",
        "margin": f"plus a {DATA['depth_margin']}-slice margin",
        "z0": "z0 in {}–{}".format(*coverage["z0_values"]),
        "windows": f"[{first[0]}, {first[1]}) to [{last[0]}, {last[1]})",
        "val contains 16": f"**{_of(coverage['validation_contains']['16'])}**",
        "train contains 16": f"**{_of(coverage['training_contains']['16'])}**",
        "inside": (
            f"| {_of(coverage['validation_in_detector_band']['entirely_inside'])} "
            f"| {_of(coverage['training_in_detector_band']['entirely_inside'])} |"
        ),
        "fewest inside": (
            f"| {coverage['validation_in_detector_band']['min_slices_inside']} "
            f"| {coverage['training_in_detector_band']['min_slices_inside']} |"
        ),
        "samples": f"{FR47['sampled_pixels'][0]:,} of each",
        "Fr47 row": "| Fr47 (training) " + _row(FR47),
        "Fr143 row": "| Fr143 (validation) " + _row(FR143),
        "Fr143 slice 24": f"zarr 24 ({_auc(FR143, 24):.4f})",
        "commit": f"`{DATA['git_commit'][:8]}`",
    }


@pytest.mark.parametrize("name,text", sorted(_quoted().items()))
def test_report_quotes_the_artifact(name, text):
    assert text in REPORT, f"{name}: {text!r} not in the report"


def test_fr47_contrast_is_strongest_in_the_quoted_slices():
    strong = [s["zarr_slice"] for s in FR47["per_slice"] if s["auc"] <= 0.46]
    assert strong == list(range(17, 24))
    assert "strongest in zarr 17–23 (AUC at most 0.46" in REPORT


def test_quoted_share_of_windows_containing_fr143_slice_24():
    # From the window geometry the artifact records (z0 range, margin, num_layers).
    lo, hi = FR143["coverage"]["z0_values"]
    margin, layers = DATA["depth_margin"], DATA["num_layers"]
    starts = range(lo, hi + 1)
    hits = sum(z0 + margin <= 24 < z0 + margin + layers for z0 in starts)
    assert (
        f"zarr 24 ({_auc(FR143, 24):.4f}), which {hits} of {len(starts)} contain"
        in REPORT
    )


def test_both_fragments_sampled_the_quoted_count():
    assert all(f["sampled_pixels"] == [100_000, 100_000] for f in BOTH)


def test_config_band_is_the_detectors_band_in_zarr_slices():
    config = json.loads((REPO / "config.json").read_text())
    assert config["depth_band"] == _same("detector_band_in_zarr_slices")
    band = "z{}-{}".format(*config["depth_band"])
    assert f"`seeded-sample-400-v2+{band}`" in REPORT
