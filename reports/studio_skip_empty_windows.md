Studio gives the same map in 0.58 to 0.59 of the time when it skips the windows that hold no CT (2026-11-21)

Finding 132. `studio_fast.py` runs the winner's `inference.py` loop line for line, with one change: with
`--skip-empty`, windows whose 128-pixel crop holds no CT are not run. Each of three inputs was read twice with the
winner's command (`--stride 64 --blend hann`, batch size 32), once in full and once with the skip. Each map was then
compared with its reference over the pixels with CT. The inputs were PHerc. 211's 16-plane input (finding 123) and
finding 125's PHerc. 0826 windings w062 and w065. Registered before any window was skipped:
`docs/preregistration/2026-11-20_studio_skip_empty_windows.md` (commit `9b99cf7e`). Record:
`reports/studio_skip_empty_windows.json`, from the run's `studio_fast.json` and gates. Scripts as run:
`repro/first_letters/pherc0211_control/` (`run_studio_fast.sh`, `studio_fast.py`).

PHerc. 0826 is eligible, so its maps stay on this machine and this report carries numbers only.

**Verdict `SKIP_ADOPTED`**, as predicted, by the registered table. Every step exited 0. Every `full` map is
identical to its reference over the CT, every `skip` map is the same map by the registered lines, and the skip ran
in 0.5918 and 0.5781 of the full loop's time on w062 and w065 (line: at most 0.8).

## The registered numbers

Each map against its reference, over the pixels with CT (lines: r at least 0.9999, p99 of the absolute difference
at most 0.002, at least 99.95% of pixels on the same side of 0.5):

| input | run | pixels | r | p99 | largest difference | same side | identical |
|---|---|---|---|---|---|---|---|
| PHerc. 211 | full | 8,838,800 | 1.0 | 0.0 | 0.0 | 1.0 | yes |
| PHerc. 211 | skip | 8,838,800 | 1.0 | 0.0 | 2.1e-05 | 1.0 | no |
| w062 | full | 25,692,200 | 1.0 | 0.0 | 0.0 | 1.0 | yes |
| w062 | skip | 25,692,200 | 1.0 | 0.0 | 0.000497 | 1.0 | no |
| w065 | full | 27,095,588 | 1.0 | 0.0 | 0.0 | 1.0 | yes |
| w065 | skip | 27,095,588 | 1.0 | 0.0 | 0.00075 | 1.0 | no |

The skip changes some pixels by at most 0.00075, the GPU's rounding when a batch holds other windows than before.
No pixel crosses 0.5.

| input | windows | run with the skip | full, seconds | skip, seconds | skip over full |
|---|---|---|---|---|---|
| PHerc. 211 | 2,784 | 2,523 | 62.5 | 57.3 | 0.9168 |
| w062 | 11,842 | 6,994 | 267.5 | 158.3 | 0.5918 |
| w065 | 13,002 | 7,411 | 290.8 | 168.1 | 0.5781 |

Seconds are from after the model loaded. The faster rule counts w062 and w065 only. PHerc. 211's input is the
winner's surface, nearly all CT, so the skip leaves it little to save.

**Predictions.** (1) `SKIP_ADOPTED`, moderate-to-high confidence, with the `full` maps identical and the `skip`
maps differing by rounding at most: held. (2) The skip takes about 0.55 to 0.65 of the full loop's time on the band
windings: held (0.5918 and 0.5781). The time falls less than the windows do (to 0.5906 and 0.57 of them), because
reading the input and writing the map do not shrink.

## What it cost

18 min 6 s in all (registered: about 25 minutes). GPU memory peaked at 14,936 MiB in use by all processes
(registered: up to about 15 GB).

## What this does to the campaign

The registered consequence of `SKIP_ADOPTED`: **band reads registered after this run Studio through
`studio_fast.py --skip-empty`.** The winner's file, weights, command and batch size are otherwise unchanged.
Finding 133 (PHerc. 0800) reads this record when it starts (`run_after_controls.sh`) and sets
`STUDIO_SKIP_EMPTY=1`. Findings 126 and 129 kept, or keep, the winner's file, as registered.

On finding 126's band, Studio took 6 h 45 min. At these windings' ratio that would have been about 4 hours.

## What this does not show

1. **That every input gives the same map.** The argument that a skipped window cannot change a pixel with CT holds
   for any input. The GPU's rounding was measured only on these three.
2. **The saving on another band.** It depends on how much of each canvas has no CT. Finding 125's windings had 45.4%
   of their windows empty; these two had 40.9% and 43%.
