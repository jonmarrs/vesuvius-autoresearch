# Clearing our own published fiber baseline

Pre-registered contract: `docs/superpowers/specs/2026-07-31-fiber-tracer-beat-baseline-design.md`.
Primary metric is merge-penalized ERL against **each cube's own** connected-components floor.
Raw ERL, splits, merges and coverage are reported every time regardless of outcome. An ERLpen
gain accompanied by a rise in merges is a **failure**, not a win.

Dev cubes: `s1_00497_01497_03997_256`, `s1_00497_02497_02997_256`.
Held out until the final run: the three other Scroll-1 cubes.
Never used for any decision: `s5_03997_01497_03997_256`.

**Configurations tried so far: 7 parameter configurations (14 dev-cube tuning runs)**
(baseline; window 3/skip 0; window 3/skip 2; window 5/skip 0; window 3/skip 1 — see
Fix A below; NMS 2.0 alone; window 5/skip 0 + NMS 2.0 — see Fix B below — for the
per-configuration results). Each configuration is scored on both dev cubes, hence
2x runs per configuration.

## Baseline (reproduced 2026-07-31)

| cube | ERL | ERLpen | cc ERLpen | coverage | splits | merges | n inst |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | 26.60 | 23.16 | 37.13 | 0.623 | 1872 | 38 | 669 |
| s1_00497_02497_02997 | 45.77 | 33.58 | 64.27 | 0.704 | 2185 | 47 | 524 |

Stop reasons, cube 1: `high_curvature` 750 (46%), `collision` 455 (28%),
`low_response` 243 (15%), `out_of_bounds` 196 (12%).

Stop reasons, cube 2: `high_curvature` 664 (46%), `collision` 427 (30%),
`low_response` 160 (11%), `out_of_bounds` 157 (11%).

## Fix A: tangent smoothing

Ran the two required combinations (window 3 / skip 0, window 3 / skip 2) on both dev
cubes first. Neither cleared the cc-ERLpen floor on either cube, so per Step 4 we spent
the two-setting tuning budget on `(window 5, skip 0)` — does more smoothing alone scale
further? — and `(window 3, skip 1)` — does a smaller coast budget avoid the merge-rise
failure seen at skip 2? Both extra settings stayed inside the permitted
`--tangent-window {2,5}` / `--max-skip-steps {1,3}` menu; no other parameter changed.

| cube | window | skip | ERL | ERLpen | cc ERLpen | coverage | splits | merges | n inst |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | 1 | 0 (base) | 26.60 | 23.16 | 37.13 | 0.623 | 1872 | 38 | 669 |
| s1_00497_01497_03997 | 3 | 0 | 28.13 | 24.81 | 37.13 | 0.629 | 1890 | 37 | 673 |
| s1_00497_01497_03997 | 3 | 2 | 26.78 | 24.07 | 37.13 | 0.641 | 2048 | 41 | 711 |
| s1_00497_01497_03997 | 5 | 0 | 29.97 | 25.61 | 37.13 | 0.623 | 1847 | 28 | 678 |
| s1_00497_01497_03997 | 3 | 1 | 27.62 | 23.79 | 37.13 | 0.633 | 1953 | 40 | 706 |
| s1_00497_02497_02997 | 1 | 0 (base) | 45.77 | 33.58 | 64.27 | 0.704 | 2185 | 47 | 524 |
| s1_00497_02497_02997 | 3 | 0 | 45.19 | 35.54 | 64.27 | 0.699 | 2191 | 43 | 529 |
| s1_00497_02497_02997 | 3 | 2 | 46.75 | 32.98 | 64.27 | 0.708 | 2318 | 47 | 549 |
| s1_00497_02497_02997 | 5 | 0 | 45.47 | 35.84 | 64.27 | 0.697 | 2211 | 39 | 533 |
| s1_00497_02497_02997 | 3 | 1 | 47.20 | 34.40 | 64.27 | 0.706 | 2287 | 44 | 545 |

**Floor not cleared on either cube, in any configuration tried.** Best result per cube
(both at window 5 / skip 0, smoothing alone): cube 1 ERLpen 25.61 vs floor 37.13 (gap
11.5); cube 2 ERLpen 35.84 vs floor 64.27 (gap 28.4). Fix A narrows the gap by low
single digits; it does not come close to closing it.

**Which mechanism carried the change:** smoothing (`tangent_window`), not coasting
(`max_skip_steps`).

Comparing skip-nonzero rows against the unsmoothed baseline conflates the two
mechanisms, since window is also different. The clean isolation holds window fixed at
3 and varies only skip, i.e. window-3/skip-0 vs. window-3/skip-1 vs. window-3/skip-2 —
smoothing held constant, coasting turned on:

| cube | comparison | ERLpen | merges |
| --- | --- | --- | --- |
| cube 1 | skip 0 -> skip 1 (window 3 fixed) | 24.81 -> 23.79 (-1.02) | 37 -> 40 (+3) |
| cube 1 | skip 0 -> skip 2 (window 3 fixed) | 24.81 -> 24.07 (-0.74) | 37 -> 41 (+4) |
| cube 2 | skip 0 -> skip 1 (window 3 fixed) | 35.54 -> 34.40 (-1.14) | 43 -> 44 (+1) |
| cube 2 | skip 0 -> skip 2 (window 3 fixed) | 35.54 -> 32.98 (-2.56) | 43 -> 47 (+4) |

At fixed window, adding coasting **regresses ERLpen and raises merges in all four
cases, on both cubes, at both tested skip budgets.** This is a materially stronger and
cleaner result than a baseline-relative comparison gives, because it isolates coasting
from smoothing entirely: coasting on top of smoothing is not a wash, it is consistently
worse than smoothing alone.

Every skip-0 row (window 3 and window 5) improved ERLpen on both cubes over baseline
while merges fell or held (cube 1: 38 -> 37 -> 28; cube 2: 47 -> 43 -> 39) — a gain on
ERLpen and merges specifically, and the mechanism responsible for every ERLpen/merges
gain reported in this section. It is not a gain on every metric: on cube 2 both skip-0
rows have raw ERL below baseline (45.19 and 45.47 vs. 45.77), coverage below baseline
(0.699 and 0.697 vs. 0.704), and splits above baseline (2191 and 2211 vs. 2185). Scoped
to ERLpen-and-merges, not "pure gain, no penalty" across the board.

The baseline-relative view is messier and worth stating precisely rather than
summarizing away: two of the four skip-nonzero rows trip the pre-registered
failure condition against the unsmoothed baseline (cube 1, skip 1 and skip 2 both) —
merges rise while ERLpen still ticks up, because the baseline comparison includes both
mechanisms and smoothing's contribution is muddying a coasting-driven merge increase.
But one skip-nonzero row, cube 2 / window 3 / skip 1, is a genuine **PASS** against
baseline in isolation (ERLpen 33.58 -> 34.40, merges 47 -> 44 both improve) — it is not
a failure and not a wash, it is the same *kind* of result as the smoothing-only gains,
just smaller, because on that cube the smoothing benefit outweighs the coasting cost at
that specific budget. That row does not change the same-window verdict above (window-3/
skip-0 -> skip-1 on cube 2 is still a regression, 35.54 -> 34.40, merges 43 -> 44); it
means smoothing is carrying that row too, partially offset by coasting, not that
coasting is contributing positively.

Net picture: smoothing is the only mechanism that produces a same-window, isolated gain
anywhere in this data. Coasting, isolated the same way, is a regression on both metrics
in all four tested cases. The reviewer's read from Task 2 (coasting steps along a frozen
direction and can't absorb a turn) is consistent with this: it does not add real
connectivity, it just suppresses a stop long enough to occasionally paper over a bad
segment, at the price of wrong-instance merges and (per the same-window comparison)
a net ERLpen cost on top of what smoothing alone already achieves.

Stop reasons after each run:

- s1_00497_01497_03997, window 3 / skip 0: `high_curvature` 813, `collision` 457,
  `low_response` 222, `out_of_bounds` 188.
- s1_00497_01497_03997, window 3 / skip 2: `high_curvature` 512, `collision` 511,
  `low_response` 401, `out_of_bounds` 220.
- s1_00497_01497_03997, window 5 / skip 0: `high_curvature` 876, `collision` 431,
  `low_response` 209, `out_of_bounds` 188.
- s1_00497_01497_03997, window 3 / skip 1: `high_curvature` 658, `collision` 501,
  `low_response` 314, `out_of_bounds` 209.
- s1_00497_02497_02997, window 3 / skip 0: `high_curvature` 684, `collision` 422,
  `low_response` 164, `out_of_bounds` 152.
- s1_00497_02497_02997, window 3 / skip 2: `high_curvature` 381, `collision` 436,
  `low_response` 336, `out_of_bounds` 183.
- s1_00497_02497_02997, window 5 / skip 0: `high_curvature` 738, `collision` 427,
  `low_response` 144, `out_of_bounds` 145.
- s1_00497_02497_02997, window 3 / skip 1: `high_curvature` 530, `collision` 422,
  `low_response` 236, `out_of_bounds` 174.

Coasting visibly does what it was built to do -- `high_curvature` stops drop sharply
every time `max_skip_steps > 0` is set (e.g. cube 1: 813 -> 512 at skip 2, 813 -> 658 at
skip 1) -- but those suppressed stops mostly reappear as `low_response` or `collision`
stops a few steps later rather than turning into extra legitimate length, which is why
ERL barely moves and merges go up on cube 1.

**Merge check (pre-registered):**

- s1_00497_01497_03997 (window 3 / skip 0): merges 38 -> 37. ERLpen improved
  (23.16 -> 24.81). **PASS** (merges did not rise).
- s1_00497_01497_03997 (window 3 / skip 2): merges 38 -> 41. ERLpen improved
  (23.16 -> 24.07). **FAIL** -- ERLpen gain accompanied by more merges, exactly the
  pre-registered failure condition. Reported as a failure, not a win.
- s1_00497_01497_03997 (window 5 / skip 0): merges 38 -> 28. ERLpen improved
  (23.16 -> 25.61). **PASS**.
- s1_00497_01497_03997 (window 3 / skip 1): merges 38 -> 40. ERLpen improved
  (23.16 -> 23.79). **FAIL** -- same failure condition as skip 2, at a smaller coast
  budget; coasting is unsafe on this cube at any tested non-zero skip value.
- s1_00497_02497_02997 (window 3 / skip 0): merges 47 -> 43. ERLpen improved
  (33.58 -> 35.54). **PASS**.
- s1_00497_02497_02997 (window 3 / skip 2): merges 47 -> 47. ERLpen worsened
  (33.58 -> 32.98). **PASS** (not a failure -- ERLpen did not improve, so the
  improve-while-merges-rise condition does not apply; this row is simply a loss for
  Fix A on this cube).
- s1_00497_02497_02997 (window 5 / skip 0): merges 47 -> 39. ERLpen improved
  (33.58 -> 35.84). **PASS**.
- s1_00497_02497_02997 (window 3 / skip 1): merges 47 -> 44. ERLpen improved
  (33.58 -> 34.40). **PASS**.

Net: 2 of 8 rows trip the pre-registered failure condition, both on cube 1, both
involving `max_skip_steps > 0`. Smoothing alone never fails the check on either cube.
This is not presented as a win where it failed -- the cube 1 / skip >= 1 rows are
recorded as failures per the contract, independent of the small ERLpen numbers involved.

**Bottom line:** the cc-ERLpen floor is not cleared on either dev cube by any of the
five configurations tried. Smoothing alone is a small, safe, real gain (+1.65 to
+2.45 ERLpen across the four skip-0 rows on the two cubes, merges flat-to-down) but
nowhere near enough to beat the connected-components floor. Coasting, isolated from
smoothing via the same-window comparison above, is a net regression on both ERLpen and
merges in all four tested cases and is additionally unsafe (against the unsmoothed
baseline) on cube 1 at every tested budget. Fix A as specified does not beat baseline in
the sense that matters for this contract; per the brief, this is reported as the honest
result and the work proceeds to Task 4.

**Configurations tried so far: 5 parameter configurations (10 dev-cube runs)**
(baseline; window 3/skip 0; window 3/skip 2; window 5/skip 0; window 3/skip 1).

## Fix B: seed NMS, and both fixes together

Ran the two required configurations from the brief on both dev cubes: NMS alone
(`--seed-nms-radius 2.0`, window/skip at published baseline) and NMS combined with the
best smoothing setting Task 3 found (`--tangent-window 5 --max-skip-steps 0
--seed-nms-radius 2.0`). No additional tuning was performed; this is exactly the 4-run
menu specified, nothing more.

| cube | window | skip | nms | ERL | ERLpen | cc ERLpen | coverage | splits | merges | n inst | collisions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | 1 | 0 | 0.0 (base) | 26.60 | 23.16 | 37.13 | 0.623 | 1872 | 38 | 669 | 455 |
| s1_00497_01497_03997 | 1 | 0 | 2.0 | 26.43 | 22.93 | 37.13 | 0.621 | 1863 | 38 | 658 | 438 |
| s1_00497_01497_03997 | 5 | 0 | 2.0 | 29.76 | 25.35 | 37.13 | 0.624 | 1839 | 28 | 661 | 414 |
| s1_00497_02497_02997 | 1 | 0 | 0.0 (base) | 45.77 | 33.58 | 64.27 | 0.704 | 2185 | 47 | 524 | 427 |
| s1_00497_02497_02997 | 1 | 0 | 2.0 | 45.59 | 33.32 | 64.27 | 0.699 | 2153 | 49 | 513 | 399 |
| s1_00497_02497_02997 | 5 | 0 | 2.0 | 45.62 | 35.87 | 64.27 | 0.693 | 2179 | 38 | 523 | 403 |

Stop reasons after each new run:

- s1_00497_01497_03997, NMS alone (window 1 / skip 0 / nms 2.0): `high_curvature` 738,
  `collision` 438, `low_response` 240, `out_of_bounds` 196.
- s1_00497_01497_03997, combined (window 5 / skip 0 / nms 2.0): `high_curvature` 853,
  `collision` 414, `low_response` 207, `out_of_bounds` 188.
- s1_00497_02497_02997, NMS alone (window 1 / skip 0 / nms 2.0): `high_curvature` 662,
  `collision` 399, `low_response` 158, `out_of_bounds` 157.
- s1_00497_02497_02997, combined (window 5 / skip 0 / nms 2.0): `high_curvature` 733,
  `collision` 403, `low_response` 142, `out_of_bounds` 146.

**Did Fix B move collisions?** Cube 1: 455 -> 438 with NMS alone (-17, -3.7%), -> 414
with NMS + smoothing combined (-41 vs baseline, -9.0%, though part of that further drop
is smoothing changing walk geometry, not NMS itself). Cube 2: 427 -> 399 with NMS alone
(-28, -6.6%), -> 403 combined (-24 vs baseline, -5.6%). The change is small in both
cases -- single-digit percentage reductions, not the kind of move you'd expect if
duplicate seeds were a major source of collisions. This matches the brief's prediction:
the seed loop already skips candidates that land in already-claimed territory before a
walk ever starts, so most of the 400+ collisions per cube are walks that start from a
legitimate, non-duplicate seed and then drift into a *neighbouring* fiber's claimed
territory partway through the walk. Seed NMS can only remove redundant seed points; it
has no mechanism to stop an already-running walk from wandering into someone else's
territory, which is where the bulk of these collisions originate. The default
`seed_stride=2` also limits how many candidates NMS ever sees, but not spatially: `trace.py`
sorts seed candidates by response and keeps every 2nd one (`cand[order][::2]`), which halves
the candidate set globally rather than thinning out nearby seeds specifically, so it is not a
spatial resampling radius. Fix B is targeting a minority contributor to the collision count,
not the dominant one.

**Merge check (pre-registered):**

- s1_00497_01497_03997, NMS alone: merges 38 -> 38 (unchanged). ERLpen 23.16 -> 22.93
  (worsened, not improved). The automatic-failure condition (ERLpen improving while
  merges rise) does not apply because ERLpen did not improve. **PASS** by the letter of
  the contract, but this row is a plain loss for the tracer -- ERLpen is down and merges
  are flat, so NMS alone provides no benefit on this cube.
- s1_00497_01497_03997, combined: merges 38 -> 28 (fell). ERLpen 23.16 -> 25.35
  (improved). **PASS**, and a real gain (fewer merges, higher ERLpen) -- this row is
  carried by the smoothing component (window 5 / skip 0 alone already reached ERLpen
  25.61 / merges 28 in Fix A); NMS on top moves ERLpen from 25.61 to 25.35, i.e. slightly
  *worse* than smoothing alone at identical merges (28), so NMS is not adding value here,
  it is marginally subtracting it.
- s1_00497_02497_02997, NMS alone: merges 47 -> 49 (**rose**). ERLpen 33.58 -> 33.32
  (worsened, not improved). Because ERLpen did not improve, this does not trip the
  literal automatic-failure wording -- but flagging it directly per the instruction to
  check merges first: this is a straight double regression, worse on both the primary
  metric and the merge count, and it is the only row where merges rose. NMS alone is a
  net negative on this cube.
- s1_00497_02497_02997, combined: merges 47 -> 38 (fell). ERLpen 33.58 -> 35.87
  (improved). **PASS**, a real gain -- again essentially the smoothing-alone result from
  Fix A (ERLpen 35.84 / merges 39) with NMS moving it a negligible amount further
  (35.84 -> 35.87, merges 39 -> 38). The combined row is indistinguishable from smoothing
  alone within measurement noise.

**Did merges rise anywhere?** Yes -- s1_00497_02497_02997, NMS alone: 47 -> 49. It is
the only row of the four where merges increased, and it happened on the row where NMS
was not paired with smoothing. It does not trigger the automatic-failure clause because
ERLpen simultaneously worsened rather than improved on that same row, but it is recorded
here plainly as required, not folded into a "PASS" without comment.

**Floor check:** neither cube clears its floor in any of the four new configurations.
Cube 1 combined: ERLpen 25.35 vs floor 37.13 (gap 11.78). Cube 2 combined: ERLpen 35.87
vs floor 64.27 (gap 28.40). Both gaps are essentially unchanged from Fix A's best
smoothing-only numbers (25.61 and 35.84 respectively) -- NMS contributes at most a few
hundredths of an ERLpen point on top of smoothing, well inside run-to-run noise, and on
cube 1 it is very slightly negative.

**Bottom line:** Fix B is a null result. Seed NMS at radius 2.0 produces a small,
single-digit-percentage reduction in collisions on both cubes (as predicted, since it
can only remove redundant seeds, not stop drifting walks), no meaningful movement in
ERLpen beyond what smoothing alone already achieved, and on cube 2 in isolation it is a
net regression on both ERLpen and merges. Combined with smoothing, the two rows that
pass the merge check are carried entirely by the smoothing component identified in Fix
A; NMS adds nothing distinguishable from noise on top of it. Neither cube comes close to
its connected-components floor with any configuration tried in this task or the last.

**Configurations tried so far: 7 parameter configurations (14 dev-cube runs)**
(baseline; window 3/skip 0; window 3/skip 2; window 5/skip 0; window 3/skip 1;
NMS 2.0 alone; window 5/skip 0 + NMS 2.0). Each configuration is scored on both dev
cubes, hence 2x runs per configuration (5 configurations / 10 runs after Fix A, +2
configurations / +4 runs from Fix B = 7 configurations / 14 runs total).

## Task 6: the frozen configuration, held-out cubes scored once

**Configuration, decided before this section's runs and not changed afterward:**

```
--tangent-window 5 --max-skip-steps 0 --seed-nms-radius 0.0
```

All other tracer parameters at the published defaults (`--relink` on, `--seed-percentile
85.0`, `--continue-threshold 0.5`, `--min-length 15.0`, `--max-angle 25.0`,
`--claim-radius 3.5`, `--relink-gap 10.0`, `--relink-angle 30.0`, `--tolerance 2.0`).

Why each part, decided from dev-cube evidence and not renegotiated here:

- `tangent_window=5`: the best smoothing setting on both dev cubes in Fix A (ERLpen
  25.61 and 35.84 — the best smoothing-only numbers per cube. Cube 1's 25.61 is the
  best figure found anywhere in this work; cube 2 reached 35.87 in Fix B with seed NMS
  enabled, a 0.03 difference that did not justify shipping a mechanism measured null).
- `max_skip_steps=0`: coasting was falsified in Fix A. Isolated from smoothing (fixed
  window, skip on vs. off), it regressed ERLpen and raised merges in all four tested
  cases, on both cubes, at both tested skip budgets. It does not ship.
- `seed_nms_radius=0.0`: NMS was a null result in Fix B. It moved collisions only
  455 -> 438 (cube 1) and 427 -> 399 (cube 2), single-digit percentage reductions, and
  combined with smoothing the ERLpen was indistinguishable from smoothing alone --
  actually slightly worse on cube 1 (25.35 vs 25.61). Shipping a mechanism measured to
  do nothing would be dishonest packaging, so NMS is off.

**After this point no parameter changes.** All six cubes below -- both dev cubes and
all four cubes never used to make a tuning decision -- are scored once, at this
configuration, and reported whatever the result.

### Commands and full output

```
$ uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube s1_00497_01497_03997_256 \
    --tangent-window 5 --max-skip-steps 0 --seed-nms-radius 0.0
cube=s1_00497_01497_03997_256  gt_fibers=87  tolerance=2.0  trace=18s  stops={'low_response': 209, 'high_curvature': 876, 'out_of_bounds': 188, 'collision': 431}
row                                    ERL  ERLpen    cov  splits  merges   ninst
---------------------------------------------------------------------------------
tracer                               29.97   25.61  0.623    1847      28     678
floor: connected components         197.11   37.13  0.918     265      66     299

$ uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube s1_00497_02497_02997_256 \
    --tangent-window 5 --max-skip-steps 0 --seed-nms-radius 0.0
cube=s1_00497_02497_02997_256  gt_fibers=109  tolerance=2.0  trace=15s  stops={'low_response': 144, 'high_curvature': 738, 'out_of_bounds': 145, 'collision': 427}
row                                    ERL  ERLpen    cov  splits  merges   ninst
---------------------------------------------------------------------------------
tracer                               45.47   35.84  0.697    2211      39     533
floor: connected components         207.49   64.27  0.932     224      63     214

$ uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube s1_00997_02497_02997_256 \
    --tangent-window 5 --max-skip-steps 0 --seed-nms-radius 0.0
cube=s1_00997_02497_02997_256  gt_fibers=128  tolerance=2.0  trace=12s  stops={'low_response': 159, 'high_curvature': 672, 'out_of_bounds': 145, 'collision': 396}
row                                    ERL  ERLpen    cov  splits  merges   ninst
---------------------------------------------------------------------------------
tracer                               38.44   33.00  0.602    2044      34     524
floor: connected components         195.82   56.45  0.823     317      66     220

$ uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube s1_08997_02997_02497_256 \
    --tangent-window 5 --max-skip-steps 0 --seed-nms-radius 0.0
cube=s1_08997_02997_02497_256  gt_fibers=105  tolerance=2.0  trace=13s  stops={'low_response': 204, 'high_curvature': 646, 'out_of_bounds': 151, 'collision': 425}
row                                    ERL  ERLpen    cov  splits  merges   ninst
---------------------------------------------------------------------------------
tracer                               33.62   31.04  0.667    2571      12     549
floor: connected components         186.52  106.14  0.900     334      46     290

$ uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube s1_10997_02997_02997_256 \
    --tangent-window 5 --max-skip-steps 0 --seed-nms-radius 0.0
cube=s1_10997_02997_02997_256  gt_fibers=91  tolerance=2.0  trace=13s  stops={'low_response': 109, 'high_curvature': 634, 'out_of_bounds': 194, 'collision': 434, 'invalid_direction': 1}
row                                    ERL  ERLpen    cov  splits  merges   ninst
---------------------------------------------------------------------------------
tracer                               36.64   36.19  0.618    1579       6     508
floor: connected components         194.14   57.67  0.855     203      57     148

$ uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube s5_03997_01497_03997_256 \
    --tangent-window 5 --max-skip-steps 0 --seed-nms-radius 0.0
cube=s5_03997_01497_03997_256  gt_fibers=68  tolerance=2.0  trace=12s  stops={'high_curvature': 526, 'low_response': 174, 'out_of_bounds': 177, 'collision': 291}
row                                    ERL  ERLpen    cov  splits  merges   ninst
---------------------------------------------------------------------------------
tracer                               31.57   31.18  0.620    1209       5     495
floor: connected components         182.22   51.10  0.867     201      39     267
```

Six commands, six runs, no retries, no parameter deviations from the frozen configuration
written above. `s1_00497_01497_03997_256` and `s1_00497_02497_02997_256` reproduce Fix A's
window-5/skip-0 numbers exactly (29.97/25.61 and 45.47/35.84), which is expected: the frozen
configuration is not new for those two cubes, only for the four that had never been scored
under it before.

### Final result (frozen configuration, held-out cubes scored once)

Configuration: tangent_window=5, max_skip_steps=0, seed_nms_radius=0.0, all other parameters
at the published defaults. **Configurations tried in total: 7** parameter configurations
(unchanged from the Fix A / Fix B banner above). This task added **zero new configurations** --
it reruns the configuration Fix A already selected (window 5 / skip 0 / NMS 0, i.e. smoothing
alone) on the four cubes that had never been scored under it, plus the two dev cubes for
completeness. Run count: 14 dev-cube tuning runs (Fix A + Fix B) + 6 frozen-configuration runs
in this task (2 of which reproduce prior dev-cube numbers exactly, 4 of which are genuinely new
held-out/cross-scroll evaluations) = 20 runs total across the whole study, 7 distinct
configurations.

| cube | role | ERL | cc ERL | ERLpen | cc ERLpen | beat floor? | coverage | splits | merges |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | dev | 29.97 | 197.11 | 25.61 | 37.13 | no | 0.623 | 1847 | 28 |
| s1_00497_02497_02997 | dev | 45.47 | 207.49 | 35.84 | 64.27 | no | 0.697 | 2211 | 39 |
| s1_00997_02497_02997 | held out | 38.44 | 195.82 | 33.00 | 56.45 | no | 0.602 | 2044 | 34 |
| s1_08997_02997_02497 | held out | 33.62 | 186.52 | 31.04 | 106.14 | no | 0.667 | 2571 | 12 |
| s1_10997_02997_02997 | held out | 36.64 | 194.14 | 36.19 | 57.67 | no | 0.618 | 1579 | 6 |
| s5_03997_01497_03997 | never touched | 31.57 | 182.22 | 31.18 | 51.10 | no | 0.620 | 1209 | 5 |

Neither metric is cleared on any cube. The floor is not close on any cube: the smallest
ERLpen gap is 11.52 (dev cube 1) and the largest is 75.10 (`s1_08997_02997_02497`); the
smallest raw-ERL gap is 150.65 and the largest is 167.14. Connected components wins raw ERL
by 4.56x-6.58x and merge-penalized ERL by 1.45x-3.42x, with no cube going the other way.

### Verdict: did not clear

**Form 3 of the pre-registered options (Step 4): the frozen configuration did not clear the
connected-components floor, on either metric, on any of the six cubes.** This is published
in the same style as this project's other negatives (Fix A, Fix B, the 128^3-vs-full-cube
retraction): the numbers as measured, and the likely reason.

Likely reason, consistent with the causal story built across Fix A/B: the tracer's limiting
factor is not local direction noise (what smoothing fixes) or duplicate seeding (what NMS
targets) but **walks drifting into a neighbouring fiber's claimed territory and getting cut
off by collisions long before they reach the fiber's true extent** -- `collision` is the
single largest or second-largest stop reason on every cube in this run (raw counts 291-434
across the six cubes: 431, 427, 396, 425, 434, 291 for
`s1_00497_01497_03997`/`s1_00497_02497_02997`/`s1_00997_02497_02997`/`s1_08997_02997_02497`/
`s1_10997_02997_02997`/`s5_03997_01497_03997` respectively), and connected components has no
such mechanism to cut a trace short at all, which is most of why its ERL is 4.6-6.6x higher
regardless of the penalty.

*Correction (post-review):* an earlier version of this paragraph stated the range as
"396-434", which silently dropped the cross-scroll cube's 291 and understated the true
spread by 105 events. As a **share of that cube's own stops**, though, the picture does not
change: collision is 291/1168 = 24.9% of all stops on the cross-scroll cube, fractionally below
the 25.3%-31.6% band the other five cubes occupy (25.3%, 29.4%, 28.9%, 29.8%, 31.6%) -- by 0.4
points, the smallest of the six shares but not a different regime -- "roughly
a quarter to a third of all stops" still holds and collision is still the second-largest stop
reason on every cube including this one. The lower *raw* count on the cross-scroll cube tracks
that cube having the fewest ground-truth fibers (68, vs. 87-128 elsewhere) and the fewest total
stops of the six (1168, vs. 1372-1704 elsewhere), not a qualitatively different collision
dynamic. The causal argument (collisions, not curvature-sensitivity or duplicate seeding, are
what caps the tracer) is unchanged by the correction; only the absolute-count range was wrong.

Fixing the underlying problem would need a different kind of change (e.g. a claim policy that
can recover from a wrong-fiber excursion, or a walk that reconsiders instead of stopping) than
anything tried in this study; smoothing and seed NMS were the two changes budgeted for this
work and neither reaches into that failure mode.

### Did the dev-cube gain generalize?

Comparing each cube's frozen-configuration ERLpen against its own `tracer_strict_relink`
baseline (the same row `reports/fiber_benchmark_all_cubes.json` publishes, recorded before
this work began):

| cube | role | ERL base→frozen | ΔERL | ERLpen base→frozen | ΔERLpen | coverage base→frozen | Δcoverage | splits base→frozen | Δsplits | merges base→frozen | Δmerges |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | dev | 26.60 → 29.97 | +3.37 | 23.16 → 25.61 | +2.45 | 0.623 → 0.623 | 0.0000 | 1872 → 1847 | -25 | 38 → 28 | -10 |
| s1_00497_02497_02997 | dev | 45.77 → 45.47 | -0.30 | 33.58 → 35.84 | +2.26 | 0.7038 → 0.697 | -0.0068 | 2185 → 2211 | +26 | 47 → 39 | -8 |
| s1_00997_02497_02997 | held out | 36.32 → 38.44 | +2.12 | 29.84 → 33.00 | +3.16 | 0.6054 → 0.602 | -0.0034 | 2034 → 2044 | +10 | 45 → 34 | -11 |
| s1_08997_02997_02497 | held out | 34.14 → 33.62 | -0.52 | 30.76 → 31.04 | +0.28 | 0.671 → 0.667 | -0.0040 | 2529 → 2571 | +42 | 15 → 12 | -3 |
| s1_10997_02997_02997 | held out | 37.43 → 36.64 | -0.79 | 34.22 → 36.19 | +1.97 | 0.6161 → 0.618 | +0.0019 | 1568 → 1579 | +11 | 14 → 6 | -8 |
| s5_03997_01497_03997 | never touched | 31.54 → 31.57 | +0.03 | 25.41 → 31.18 | +5.77 | 0.6233 → 0.620 | -0.0033 | 1196 → 1209 | +13 | 13 → 5 | -8 |

All four contract metrics against their baselines, per cube, per the reporting requirement in
the header of this document. **The ERLpen gain is predominantly a merge-reduction effect, not
a run-length effect.** Raw ERL fell on three of six cubes -- including a dev cube
(`s1_00497_02497_02997`, -0.30) -- and is essentially flat on a fourth (the cross-scroll cube,
+0.03); it rose meaningfully on only two cubes. Splits, which measure fragmentation directly,
rose on five of six cubes (only the dev cube that set `tangent_window` improves on splits, and
even there by only -25 against 1872). Coverage fell on four of six. ERLpen goes up mainly
because the merge penalty is now being applied to fewer merges on an otherwise similarly (or
more) fragmented set of runs -- the tracer is tracing about the same distance per run, and in
several cases a shorter one, while merging less.

Dev-cube mean gain: +2.36 ERLpen. Held-out (three Scroll-1 cubes) mean gain: +1.80 ERLpen --
smaller than dev on average, but not vanished, and the held-out range (+0.28 to +3.16) spans
both below and above the dev numbers. One held-out cube, `s1_08997_02997_02497`, is close to
a wash (+0.28) -- on that cube the gain nearly disappeared, and it is also the cube with by
far the largest cc-ERLpen floor (106.14), so its 75.10-point gap dwarfs a fraction-of-a-point
gain either way. The other two held-out cubes show gains comparable to or larger than the dev
cubes. **Verdict on generalization: directionally consistent on the primary metric (ERLpen up,
merges down, on all six cubes, no exceptions) but not uniform in size, and not directionally
consistent on the other three contract metrics** -- raw ERL fell or was flat on four of six
cubes and splits rose on five of six, per the table and mechanism note above. On ERLpen alone,
it is not the case that the gain simply survived at dev-cube magnitude, nor is it the case that
it vanished; it ranged 20x in size (+0.28 to +5.77) across cubes never distinguished by any
other property in this study, which means the "dev gain" was never a single stable number to
begin with. In every case the gain is smaller than the remaining floor gap, by a factor ranging
roughly 3x to 270x across the six cubes (smallest on the cross-scroll cube, largest on
`s1_08997_02997_02497`), so this variance does not change the outcome.

Merges fell on every one of the six cubes (38->28, 47->39, 45->34, 15->12, 14->6, 13->5). The
*average* proportional reduction is larger on the four cubes not used to pick the
configuration (-24%, -20%, -57%, -62%; mean -41%) than on the two dev cubes that set it
(-26%, -17%; mean -22%) -- but this is not true cube-for-cube: the smallest held-out
reduction, -20% on `s1_08997_02997_02497`, is a smaller proportional drop than the larger of
the two dev reductions, -26% on `s1_00497_01497_03997`. The six raw counts are shown above;
read the four-cube figure as an average tendency, not a uniform per-cube ordering. The
pre-registered merge check (ERLpen improving while merges rise = automatic failure) is never
tripped anywhere in this table -- every row is a **PASS** by that check, consistently.

### The cross-scroll cube, on its own line

`s5_03997_01497_03997_256` (Scroll 5) is the cleanest generalization number in the whole
study on the primary metric: it informed no tuning decision at any point, in either Fix A or
Fix B, and was first run under the frozen configuration in this task. ERLpen improved from
25.41 (baseline) to 31.18 (frozen configuration), a **+5.77 gain -- the single largest ERLpen
gain of any cube in this study**, with merges falling from 13 to 5 (-62%).

That headline number needs the same mechanism disclosure as the rest of the study, and this
is the cube it matters most for, since it is the study's best-protected number and the one
most likely to be quoted on its own. Raw ERL on this cube barely moved at all: 31.54 -> 31.57,
a +0.03 change, and splits *rose* by 13 (1196 -> 1209). The tracer is not tracing this cube's
fibers any farther than the baseline tracer did; it is producing a very slightly more
fragmented set of runs and getting credited for the merge count dropping from 13 to 5. The
+5.77 is essentially all merge-count effect, not run-length effect -- the same pattern as the
other five cubes, just with the largest ERLpen swing because this cube's baseline merge count
(13) had the most room to fall in percentage terms.

That the largest, most consistent-looking ERLpen gain shows up on the one cube that never fed
a decision is still a useful sanity check that the configuration is not overfit to the two dev
cubes on the primary metric -- but the gap to that same cube's own connected-components floor
is still 19.92 ERLpen points (31.18 vs 51.10) and 150.65 raw-ERL points (31.57 vs 182.22), the
second-smallest ERLpen gap of the six but still nowhere near closed. Cross-scroll transfer of
the *ERLpen improvement* looks fine; cross-scroll transfer of raw tracing length does not
happen on this cube, and cross-scroll transfer to *beating the floor* does not happen anywhere,
because no configuration tried anywhere in this study gets within an order of magnitude of
doing that.

### Bottom line

The frozen configuration (tangent_window=5, max_skip_steps=0, seed_nms_radius=0.0) is a
small, safe, real improvement over the published baseline tracer **on the primary metric** --
ERLpen up and merges down on all six cubes with no exceptions, including the never-touched
cross-scroll cube -- and it **does not come close to beating connected components on either
metric, on any cube**. The gain is not evenly a gain: raw ERL fell or was essentially flat on
four of six cubes and splits rose on five of six (see "Did the dev-cube gain generalize?"
above), so most of the ERLpen improvement is the merge penalty being applied to fewer merges
rather than the tracer tracing farther. The smallest remaining ERLpen gap is 11.52 points (dev
cube 1) and the largest is 75.10 (`s1_08997_02997_02497`); the smallest raw-ERL gap is 150.65
points. This is the final, frozen-configuration result against the pre-registered contract. No
further tuning follows.

**Configurations tried in total: 7 parameter configurations, 20 runs** (14 dev-cube tuning
runs across Fix A and Fix B, plus 6 frozen-configuration runs in this task -- 2 of which
reproduce dev-cube numbers already counted above, 4 of which are new held-out/cross-scroll
evaluations of the configuration already selected before this task began).
