# Pre-registration: does Studio give the same map, faster, without the windows that hold no CT?

**Written 2026-11-20, before Studio has been run with any window skipped.** Finding 132.

## The question

Studio is the slowest step of a band read. In finding 125 it took 4 h 24 min of PHerc. 0826's 8 h 48 min, with the
GPU busy throughout.

The winner's `inference.py`, run with the winner's command (`--stride 64 --blend hann`), runs the model on every
window of the canvas. A render's canvas is the rectangle around a flattened winding, and much of it has no CT.
Across ten of finding 125's windings (every seventh, w010 to w073), 35,501 of 78,259 windows (45.4%) have no CT in
their 128-pixel crop (the 96-pixel window and its 16 pixels of context each side).

Such a window writes only to its central 96 pixels, which have no CT either. The loop then sets every pixel without
CT to 0. So skipping these windows cannot change any pixel with CT, except through the GPU's rounding when a batch
holds other windows than before. **Does skipping them give the same map, and how much faster?**

## Reachability, checked before this was written

- **The code.** `studio_fast.py` holds the winner's loop line for line, using the winner's own `crop`, `hann96`
  and `load_model` from the checksummed file, with one change: with `--skip-empty`, windows whose crop has no CT
  are not run.
- **The tests**, on the CPU with a per-pixel stand-in for the network:
  - the copied loop's map equals the winner's file's map exactly, with the skip and without it;
  - with the skip, fewer windows are run and every pixel without CT is still 0.
- **The inputs and the reference maps are on this machine:**
  - PHerc. 211's 16-plane input (finding 123, SHA-256 `e7cdd509…`) and finding 123's map from it, made here with
    the winner's file and command;
  - finding 125's renders of PHerc. 0826's windings w062 and w065 (the first two of its inspection order), and
    finding 125's maps of them.
- **Not checked:** the GPU's rounding when batches differ, and the time saved.

## Procedure

`repro/first_letters/pherc0211_control/run_studio_fast.sh`, once, after finding 131 and before finding 129. Each step
runs only if the one before exited 0:

1. **check:** the weights, the winner's `inference.py` and PHerc. 211's input against their SHA-256 values.
2. **planes:** Studio's input for w062 and w065, rebuilt from finding 125's renders (`studio_e2e.py planes`, as
   finding 125 built it).
3. **runs:** on each of the three inputs, `studio_fast.py run` with the winner's command and batch size 32. First the
   full loop (`full`), then the loop with the skip (`skip`). Each run is timed from after the model has loaded.
4. **compare:** each map against its input's reference map, with finding 123's `compare`, over the pixels with CT.

## Registered measure and verdict

**The same map** means: against the reference, r ≥ 0.9999, p99 ≤ 0.002 and at least 99.95% of pixels on the same
side of 0.5. Finding 123's own run of the winner's command against the winner's published map, which differ by bf16
rounding, gave r 1.0, p99 0.000645 and 99.989%.

**Faster** means: the `skip` run takes at most 0.8 of the `full` run's time on each of w062 and w065.

| verdict | rule |
|---|---|
| `SKIP_ADOPTED` | every `skip` map is the same map, and the skip is faster |
| `SKIP_NOT_FASTER` | every `skip` map is the same map, and the skip is not faster |
| `SKIP_DIFFERS` | a `skip` map is not the same map |
| `DOES_NOT_RUN` | a step failed, or a `full` map is not the same map as its reference (the copied loop, or this machine, no longer gives the winner's file's map) |

**Described:** whether each map is identical to its reference over the CT, the windows counted and run, and every
run's seconds.

## Predictions, fixed now

1. **`SKIP_ADOPTED`, moderate-to-high confidence.** I expect the `full` maps identical to their references and the
   `skip` maps to differ by rounding at most.
2. The `skip` run takes about 0.55 to 0.65 of the `full` run's time on the band windings. 45% of the windows are
   skipped, but reading the input, the integral image and writing the map do not shrink.

## Consequences

- **`SKIP_ADOPTED`:** band reads registered after this run Studio through `studio_fast.py --skip-empty`. The
  winner's file, weights, command and batch size are otherwise unchanged. Findings 126 and 129 keep the winner's
  file, as registered.
- **Any other verdict:** band reads keep the winner's file.

## What the result cannot do

It is three inputs from two scrolls. The skip's argument holds for any input, but the GPU's rounding is measured
only on these.

## Cost

About 25 minutes of GPU time at up to about 15 GB, and about 1 GB of maps. Studio's input planes are deleted
afterwards. Studio's outputs are CC BY-NC 4.0, and PHerc. 0826 is eligible, so everything stays on this machine
and the report carries numbers.
