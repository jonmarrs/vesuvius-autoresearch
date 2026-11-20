# Pre-registration: is Studio's published tiling close enough to the winner's to read bands 2.25 times faster?

**Written 2026-11-20, before Studio has been run with its published tiling on any input.** Finding 128.

## The question

Findings 123 to 127 run Studio with the winner's submission command: `--stride 64 --blend hann`, windows every 64
pixels, Hann-weighted and averaged. `inference.py`'s default is Studio's published tiling: windows every 96 pixels,
whose central 96 pixels are written without overlap. That needs (96/64)² = 2.25 times fewer windows.

The GPU is the limit. It runs at 87 to 100% throughout finding 125's Studio stage, which takes about 7 to 10 s per
megapixel. That band has 2,327 megapixels, so its Studio stage takes about five hours. **Does the published tiling
give the same map, so that later blind band reads can use it?**

## Reachability, checked before this was written

- The input is the winner's own 16-plane input of PHerc. 211, 8,838,800 pixels inside the winner's mask, as finding
  123 checked against its SHA-256.
- The reference is finding 123's map from that input with the winner's command: r 1.0 against the winner's
  published map, 75 s.
- Finding 123's environment, weights and `inference.py`; `--batch-size 32` as before.

## Procedure

`repro/first_letters/pherc0211_control/run_studio_tiling.sh`, once, after finding 127:

1. **check:** the SHA-256 values of the weights, the planes and `inference.py`.
2. **infer:** `inference.py` with the published tiling (no `--stride`, no `--blend`) and `--batch-size 32`, timed.
3. **compare:** `studio_tiling.py`, over the winner's mask, with finding 123's `compare`. It reports r, the
   distribution of absolute differences, and the share of pixels on the same side of 0.5.

## Decision rule, fixed now

| verdict | rule | consequence |
|---|---|---|
| `PUBLISHED_TILING_ADOPTED` | r ≥ 0.98 and at least 98% of pixels on the same side of 0.5 | blind band reads registered after this use the published tiling |
| `WINNERS_TILING_KEPT` | otherwise | later reads keep the winner's command |
| `DOES_NOT_RUN` | a step failed | as `WINNERS_TILING_KEPT` |

Findings 125 to 127 are registered with the winner's command and keep it whatever this shows.

## Predictions, fixed now

1. `PUBLISHED_TILING_ADOPTED`, moderate confidence. The two tilings differ only at the edges of each window's
   central 96 pixels. Against: without blending, each pixel takes one window's prediction instead of an average of
   about two, so ink near the threshold could switch side.
2. About 30 to 40 s against 75 s. The model load is a fixed cost, so the saving is below 2.25 times here.

## What the result cannot do

It is one input of one scroll, where the winner's map is the reference. Tile seams that agree with the winner's map
at r 0.98 could still be visible. The owner reads the images, so any seams are disclosed in the band report.

## Cost

About a minute of GPU time. Nothing is uploaded; the map stays on this machine (CC BY-NC 4.0).
