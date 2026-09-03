# Pre-registration: second look at the gap-expander ink question, n=6 per arm

> **⚠ PROVENANCE CORRECTED 2026-09-03.** This document names a single villa ref for its tooling.
> That is wrong: **fits ran on the `villa-spiral` WORKING TREE at `6847063f` (2026-08-26)** while
> **renders and scoring ran on its `origin/main` at `5479453a` (2026-08-30)**. Two refs, one
> pipeline. The measurements are unaffected -- every arm shares both refs -- but any claim here about
> which villa the code came from should be read against
> `reports/gap_expander_finding_is_stale_upstream_fixed_it.md`.

**Written 2026-09-02, before any of the five new fits is started.** This extends
`2026-09-02_gap_fix_ink_six_fits.md`, which returned `total_fg_pixels` **-9.25%, p = 0.0637** at 4
vs 3 and did not clear.

## The statistical problem this registration exists to handle

**Adding data to a non-significant result and re-testing at alpha = 0.05 is not a valid 5% test.**
Two looks at the same question, each at 0.05, spends roughly 8% type I error, and it is the single
most common way an honest-looking result is manufactured. Naming that now, before the fits, is the
point of this document.

**The fix, fixed now: Pocock-style alpha spending for two looks. The second look is tested at
alpha = 0.0294, not 0.05.** Look 1 has already been taken and reported at its own threshold, and its
verdict (not established) stands in the record whatever this returns.

## Arms

Six per arm, so **five new fits**:

* **BASE** +2: `seed05`, `seed06` (existing: `baseline01`, `seed02`, `seed03`, `seed04`)
* **GAP** +3: `gap133s4`, `gap133s5`, `gap133s6` (existing: `gap133`, `gap133s2`, `gap133s3`)

Config identical to their arm-mates, differing only in `optimizer_random_seed` (5, 6 for BASE;
4, 5, 6 for GAP) and, for GAP, `model_gap_expander_num_windings = 133`. Rendered on **w120-w129**,
tooling from `villa-spiral` at **5479453a** (NOT the submodule pin -- see
`repro/spiral_render/setup_workdir.sh`), serial-fold scoring, `--procs` at its default.

## Power, computed now from the OBSERVED spread

Look 1's `t = -2.565` at `sqrt(1/4 + 1/3)` implies a pooled relative CV of **0.0472** -- larger than
the 0.0421 assumed from the base-only floor, which is why look 1 fell short.

| n per arm | SE of rel diff | effect/SE at -9.25% |
|---:|---:|---:|
| 4 | 3.34% | 2.77 |
| 5 | 2.99% | 3.10 |
| **6** | **2.73%** | **3.39** |
| 7 | 2.52% | 3.67 |

At the stricter alpha = 0.0294 the requirement is about **3.05**, so **n = 6 per arm clears it with
margin and n = 5 only just**. Six is chosen for that reason and not because it is a round number.

**This assumes the effect is real and near -9.25%.** If the true effect is smaller, six per arm will
also fail to clear, and that outcome is a real answer rather than a reason for a third look.

## Decision rule, fixed now

Primary: `total_fg_pixels`, Welch two-sided, 6 vs 6, **alpha = 0.0294**.

| outcome | conclusion |
|---|---|
| p < 0.0294, negative | The fix **reduces** recovered ink on the windings it acts on. **Established.** Finding 13 resolves against the fix. |
| p < 0.0294, positive | The fix increases it. Established. |
| p >= 0.0294 | **Not established, and the question is CLOSED at this budget.** No third look without a new question, because a third look at 0.05 would spend ~11% type I error and I would be fishing. |

**No stopping early, no peeking.** The analysis runs once, when all twelve arms are scored. I will
not compute an interim result at 5 or 5.5 per arm, and the driver is arranged so a partial run
refuses rather than reports.

Complete separation is reported alongside as before and, as before, **never in place of** the Welch
test. At 6 vs 6 its null probability is 1/C(12,6) = **0.108%**.

Secondary metrics (`overall_fg_fraction`, `overall_line_score`, `overall_column_score`) are reported
with the same test and remain secondary; `col_gap_contrast` stays **retired** and is not re-tested.

## Prediction, fixed now

**p < 0.0294 with a negative difference**, i.e. the effect is real and this arm establishes it. Look
1's direction prediction was met and every one of the seven fits is consistent in direction, so this
is a genuine prediction rather than a hedge. If it misses, that is recorded as a miss and the
question closes.

## Cost

Five fits at ~2h, five outer renders at ~2.5h, five scorings at ~15min: **roughly 24 hours,
sequential**, because two renders cannot share this box. Renders run under
`repro/spiral_render/run_with_retry.sh`, since one render in six has been OOM-killed here.
