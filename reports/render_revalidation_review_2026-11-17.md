# Renderer-v2 compatibility: one registered PHerc1667 crop

**PASS: maximum center-plane NCC 0.78897 against the released surface volume**,
above the fixed 0.60 gate. This is compatibility on one 128 × 128 interior crop,
not ink accuracy, an independently selected held-out test or whole-scroll
validation. All 16,384 pixels have support across all 26 rendered layers.

The [registration](../docs/preregistration/2026-11-17_renderer_v2_1667_compatibility.md),
[machine plan](../configs/studies/render_1667_v2_2026-11-17.json) and tested
[runner](../repro/sota_data/revalidate_render_1667_v2.py) were committed as
`f56123604bf1e2d6fc9194d4f79e0be4ae878ff7` at 15:18:32 UTC, before payload
acquisition and scoring. The receipt was published at 15:20:02 UTC. Only source
metadata was inspected before registration. The [complete review JSON](render_revalidation_review_2026-11-17.json)
contains the receipt, exact command, selected source hashes, object digests,
runtime, tests and limitations.

## Result

PHerc1667 w011 geometry, raw CT and released surface volume declare the same
scan frame. The fixed geometry crop is y=736, x=112, height=128, width=128;
the reference crop is y=920, x=140, height=160, width=160. Geometry scale,
array dimensions and uint8 volume types matched the fixed design. Normals use
a one-pixel halo. The scored plane is offset zero before byte quantization.

| Released depth | Center-plane NCC |
| --- | --- |
| 50 | 0.70949820 |
| 52 | **0.78896658** |
| 54 | 0.77788526 |
| 56 | 0.69077989 |
| 58 | 0.56360600 |

The maximum over these five depths was fixed by the registration. All five
scores are retained at full precision in JSON; display rounding did not decide
the gate. Geometry validity and full-depth support are both 100%; depth-clamped
fraction is zero. The real crop therefore does not test exclusion at a clipped
boundary; the synthetic sampler regression does.

One live attempt captured **82 source objects, 175,582,829 bytes**: three metadata
objects, three geometry TIFFs, 72 raw chunks and four reference chunks. This
fits the fixed 192 MiB total budget. Original bytes and arrays remain outside
Git. Missing chunks, redirects, incomplete downloads, changed captures and
changed source/plan identities refuse publication. HTTPS hashes identify the
retrieved objects and are not independently published upstream checksums.

An offline replay with network access disabled at the transport reproduced the
layers, support mask and resized references **bit for bit**, plus identical
sampling statistics and comparison results. An independent NumPy `corrcoef`
calculation agrees with all five NCCs within 1e-14. This replay is the same
measurement's reproducibility check, not a new independent scientific sample.

## Engineering and verification

The old comparison scripts and their historical reports are unchanged. The new
runner uses the current sampler's full-depth support mask, a fixed source design
and captured source bytes. The chunk reader accepts an optional explicit
transport; its default S3 path and numerical behavior remain unchanged.
No checkpoint, training input, model setting or promotion policy was changed.

The synthetic integration selection passed **121 tests**: 23 revalidation
contracts, 80 surface contracts and 18 renderer checks. Registry, file-mode,
preserved-source and document/claim checks gave **171 passed, 1 skipped**;
the skip needs absent local arm artifacts. Counts overlap. Mypy passes on
**1037 files**, maintained Ruff and changed-file formatting pass, and the
unchanged lock resolves **258 packages**. CPU smoke gave **8 passed, 3 skipped,
0 failed**; its skips need a checkpoint or training data.

The historical whole-segment and depth tables retain their original scope.
This result does not rerun them, validate OBJ auto-scale, establish independent
scan registration, measure GPU memory or resolve the separate confidence-analysis
rerun. Those limits remain in the [audit](../docs/REPOSITORY_AUDIT.md#items-for-owner-review).
