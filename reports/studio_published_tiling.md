Studio's published tiling is 2.4 times faster but not close enough to the winner's (r 0.94, 94.0% of pixels on the same side of 0.5), so band reads keep the winner's command (2026-11-20)

Finding 128. Studio was run with `inference.py`'s default tiling (windows every 96 pixels, their central 96 pixels
written without overlap) on the winner's own 16-plane input of PHerc. 211, and its map compared with finding 123's
map from the winner's command (`--stride 64 --blend hann`), over the winner's mask. Registered before Studio was run
with the published tiling on any input: `docs/preregistration/2026-11-20_studio_published_tiling.md` (commit
`eb9e10a5`). Record: `reports/studio_published_tiling.json`, which carries the run's `studio_tiling.json` and the seam
profile below (their SHA-256 values are in the record). Scripts as run: `repro/first_letters/pherc0211_control/`
(`run_studio_tiling.sh`, `studio_tiling.py`). The maps stay on this machine (CC BY-NC 4.0).

**Verdict `WINNERS_TILING_KEPT`**, not as predicted (I predicted `PUBLISHED_TILING_ADOPTED`, with moderate
confidence): both steps exited 0, but r = 0.9396 and 94.02% of pixels on the same side of 0.5, both short of the
0.98 lines.

## The registered numbers

| | value |
|---|---|
| pixels compared (the winner's mask) | 8,838,800 |
| **r, published tiling against the winner's** | **0.9396** (line 0.98) |
| **share of pixels on the same side of 0.5** | **0.9402** (line 0.98) |
| absolute difference: median, 99th percentile, largest | 0.0194, 0.3304, 0.7086 |
| mean probability: published tiling, winner's | 0.3361, 0.3352 |
| Studio's time on this input: published tiling, winner's (finding 123) | 31 s, 75 s |

The second prediction (about 30 to 40 s) held: 2.4 times faster.

## Described after the verdict

Deciding nothing, and not registered: `studio_tiling.py seams`, the mean absolute difference over the mask by
position within the published tiling's 96-pixel windows.

| | on the windows' edges (first and last pixel) | in their middle (pixels 32 to 63) |
|---|---|---|
| along columns | 0.0649 | 0.0384 |
| along rows | 0.0681 | 0.0368 |

The two maps differ most on the windows' edges, 1.7 to 1.9 times as much as in their middle, so the published
tiling leaves seams. They also differ in the middle, where each pixel takes one window's prediction instead of an
average of about two. As the registration said, ink near the threshold switches side: 6% of pixels do.

## What this does to the campaign

The registered consequence: later reads keep the winner's command. Findings 125 to 127 used it already. Studio
stays the slowest step of a band read: in finding 125 it took 4 h 24 min of 8 h 48 min. A setting between the two
(a coarser stride with blending, for example) was not tested; it would need its own registration.

## What this does not show

1. **That the published tiling reads letters worse.** The winner's map is the reference, so this measures distance
   from it, not legibility.
2. **Other inputs.** It is one input of one scroll.

## What it cost

| step | wall time |
|---|---|
| checksums | 2 s |
| Studio, published tiling (at most 14,481 MiB of GPU memory) | 31 s |
| comparison (the record was written 2 s after the map) | about 2 s |
