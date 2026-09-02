# Pre-registration: what is the seed-noise floor on the OUTER windings?

**Written 2026-09-01, before any of the three renders.** Only one outer-winding render exists
(`baseline01`, from `reports/gap_fix_outer_windings_still_not_established.md`), so no spread is
measurable yet.

## Why this has to be measured

Every noise floor this project quotes was measured on **w010-w019**:

| quantity | CV across 4 seeds | different-fit floor (2*CV) |
|---|---:|---:|
| `total_fg_pixels` | 0.1086 | 21.7% |
| `overall_line_score` | 0.0342 | 6.8% |
| `overall_column_score` | 0.1343 | 26.9% |

Yesterday's arm judged two **outer-winding** numbers against those floors: `total_fg_pixels` at
-11.03% was called uninterpretable, and `overall_column_score` at -46.57% was recorded as a
post-hoc observation that would clear its floor. Both judgements **transfer a floor across regions**,
which is an assumption and was disclosed as a limit rather than defended.

There is positive reason to doubt the transfer. The outer ten windings have about half the inner
ten's ink density (0.508% against ~0.93%), they are where duplicate coverage concentrates, and
column detection reports median column widths of 256-278px against the 850px it looks for. A region
that different has no claim on the same noise.

**Nothing new needs fitting.** All four honest seeds already carry w120-w129 meshes.

## Arms

Render and score **w120-w129** for `seed02`, `seed03`, `seed04`. `baseline01` (seed 1) is already
done and is reused unchanged. n = 4, matching the inner-winding measurement exactly.

Identical tooling to both arms of the previous report: spiral-fitting extracted at villa
**`5479453a`** (corrected 2026-09-02; this document first said `c935851c3`, which is the *submodule*
pin and not what renders run from -- `setup_workdir.sh` extracts from the separate `villa-spiral`
checkout, whose `origin/main` is 5479453a and does not even contain `c935851c3`. The arms are
unaffected: every arm in this work used 5479453a, which is what comparability depends on), the
LASAGNA path,
`INK_METRIC_SERIAL_FOLDS=1`, scoring from `data/ink_scorer_venv`.

## Predictions, fixed now

1. **All four render non-blank** (`p95 > 0` on the five full tiles). A blank strip voids that arm.
2. **The outer CV of `total_fg_pixels` will be HIGHER than the inner 0.1086.** Stated as a directional
   prediction so it can be wrong: the outer region carries half the ink density on a slightly larger
   canvas, so the same absolute jitter is a larger relative one. If it comes back lower, the
   prediction is recorded as a miss.
3. No prediction on `line` or `column` CV. I have been wrong three times about what an observable
   does, and twice more this week about where one acts.

## Decision rule, fixed now

Let `F_outer = 2 * CV_outer` be the different-fit floor measured out there.

**For the gap-expander ink result (-11.03% on `total_fg_pixels`):**

* `F_outer > 11.03%`: the reported conclusion stands unchanged, and is now grounded in the right
  region instead of a transferred floor.
* `F_outer <= 11.03%`: **the -11.03% clears the floor and the conclusion REVERSES** — the gap fix
  would then have a measured negative ink effect on the windings it acts on. I commit now to
  reporting that as a reversal of yesterday's report, prominently, rather than as a refinement.

**For the column observation (-46.57%):**

* `2*CV_outer(column) > 46.57%`: the post-hoc observation dies and is retired, not carried forward.
* `2*CV_outer(column) <= 46.57%`: it survives as a *candidate* only. It was still not pre-registered
  for that arm, so surviving here licenses a properly registered arm, not a claim.

**A CV from n=4 is itself uncertain, so the floor is an interval and the verdict is taken from the
interval.** The 95% interval on a CV at n=4 spans **0.57x to 3.73x** the point estimate. A
comparison counts as resolved only when the **whole** floor interval sits on one side of the
observation; if the interval straddles it, the answer is UNRESOLVED at n=4 and is reported as such
rather than as whichever side the point estimate fell on. The three branches above are therefore
read against `[2*CV_lo, 2*CV_hi]`, not against `2*CV` alone.

*Revision, recorded: the first draft of this rule used a cruder "within a factor of two of the
observation" band. It was replaced while the renders were still running and **before any of their
numbers existed**, because the band made STANDS almost unreachable — a floor twice the observation
is a comfortable pass, not a tie. The interval version is implemented in
`scripts/analyse_outer_floor.py`, also written before the data.*

## Which arms may be pooled, fixed now

The four arms above and **nothing else**. `scripts/analyse_outer_floor.py` refuses any tag outside
`(baseline01, seed02, seed03, seed04)`, refuses a duplicate, and applies the same 0.01
`satisfied_area` quality gate `analyse_seed_spread.py` uses, naming any fit it drops.

The trap being closed is specific. `gap133` is a **config** arm, and pooling it would put a config
effect inside a seed floor. That widens the floor, and a wider floor is precisely what leaves my
published conclusion STANDING, so the error would fail in the flattering direction. Quality alone
would not catch it: gap133's `satisfied_area` is 0.0082 from baseline01's, **inside** the 0.01 band.
Hence an allowlist on top of the gate. Added while seed02 was still rendering, before any of the
three arms produced a number.

## What this cannot do

It measures seed noise within one config, on one dataset, one ROI, one winding decade. It says
nothing about whether the gap fix helps ink; it only fixes the yardstick that question is judged
against. The six-fit arm remains the only thing that answers that.

## Cost

Three renders at about 2h05m each plus three scorings at about 15 minutes, roughly 7 hours, no new
fits. Sequential because `vc_render_tifxyz` peaks at 26GB on a 32GB box.
