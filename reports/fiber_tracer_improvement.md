# Clearing our own published fiber baseline

Pre-registered contract: `docs/superpowers/specs/2026-07-31-fiber-tracer-beat-baseline-design.md`.
Primary metric is merge-penalized ERL against **each cube's own** connected-components floor.
Raw ERL, splits, merges and coverage are reported every time regardless of outcome. An ERLpen
gain accompanied by a rise in merges is a **failure**, not a win.

Dev cubes: `s1_00497_01497_03997_256`, `s1_00497_02497_02997_256`.
Held out until the final run: the three other Scroll-1 cubes.
Never used for any decision: `s5_03997_01497_03997_256`.

**Configurations tried so far: 5** (baseline; window 3/skip 0; window 3/skip 2;
window 5/skip 0; window 3/skip 1 — see Fix A below for the per-configuration results).

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
while merges fell or held (cube 1: 38 -> 37 -> 28; cube 2: 47 -> 43 -> 39) — pure gain,
no penalty, and the mechanism responsible for every gain reported in this section.

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

**Configurations tried so far: 5** (baseline; window 3/skip 0; window 3/skip 2;
window 5/skip 0; window 3/skip 1).
