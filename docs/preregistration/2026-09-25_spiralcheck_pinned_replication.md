# Pre-registration: does any spiralcheck metric track ink within config on the pinned tier?

**Written 2026-09-25, before spiralcheck was run on any pinned-tier fit.** Decision code
`scripts/analyse_spiralcheck_pinned_replication.py`; tests `tests/test_spiralcheck_pinned_replication.py`.
Both are committed with this file.

## The question

`reports/spiralcheck_is_not_discriminating_here.md` (Q3) found no within-config relation between
spiralcheck's metrics and ink on 12 current-tier fits. At df 8, though, only **|r| ≥ 0.750** could
register, so that null excludes almost nothing.

The pinned tier (villa-spiral `6847063f`) has **24 scored fits in six configs**. That is independent
data: different fits, a different code tier, and ink measured on different renders. At df 17 the
critical value falls to **|r| ≥ 0.561**.

* **If a metric tracks ink here,** the current-tier null was a power failure and spiralcheck has
  reading-relevant signal.
* **If none does,** the null holds on a second tier at a tighter bound.

## Reachability and instrument, checked before registering

* **Fits:** all 24 fitted dirs exist, with their scored windings w120–w129 `_spliced`. The gate
  checks byte identity to each `outer_<tag>` work dir at collection time.
* **Render code:** these arms predate `VILLA_SHA`/`RENDER_IMAGE` records, so their provenance was
  checked by content. The render-path files in all 24 work dirs (`lasagna/fit.py`,
  `lasagna/fit_data.py`, `vesuvius/.../tifxyz/reader.py`, `spiral-fitting/get_ink_metrics.py`) hash
  **identically (1 distinct hash / 24)**.
* **Render image:** all 24 were scored between **2026-09-01 23:08 and 09-07 10:47**. That is after
  the only `vc-render:local` image on the machine was built (08-30 21:47), and it has not been
  rebuilt since.
* **Flatten:** stock (stochastic). This adds ~3% render noise to ink. That is noise in y, which
  weakens a correlation and cannot create one.

## Design

**Groups** (config → fits):

* `baseline`: baseline01, seed02–06
* `gap133`: gap133, gap133s2–s6
* `boot090`: s1–s3
* `rand090`: s1–s3
* `strip090`: s1–s3
* `nosame`: s1–s3

**Ink:** `outer_<tag>/ink_metric/metrics.json` → `total_fg_pixels`.

**Metrics:** the same four, from spiralcheck `intrinsic` (commit `d1b50e29`, default thresholds, our
umbilicus) on a symlinked subset of the fit's scored windings. The functions are imported from the
first study's script, not re-implemented.

**Gates:** each subset is run twice and the runs must match; meshes must be byte-identical to the
work dir; all 24 must be present. Any failure gives **INVALID**.

**Rule, per metric:** Pearson r of metric vs ink, both config-centred, df 17, Bonferroni α 0.0125.

| outcome | verdict |
|---|---|
| p < 0.0125 | TRACKS INK (+/−) |
| otherwise | NO DETECTED RELATION |
| constant, or no within-config variation | UNINFORMATIVE |

**Headline:**

| condition | headline |
|---|---|
| any metric tracks ink | **READING-RELEVANT ON PINNED** |
| all four uninformative | **UNINFORMATIVE** |
| otherwise | **NO DETECTED RELATION** |

## Prediction, fixed now

**NO DETECTED RELATION on all four. Confidence moderate.** The current-tier correlations were
|r| ≤ 0.29 once one outlier was removed. Geometry has not transmitted to ink in any of our studies.

## What the result cannot do

* **A null here still excludes only |r| ≥ 0.56**, and only on this region.
* **A positive finding would be on superseded code.** It would need the current tier to confirm it,
  and the current tier has already failed to. Such a result would be reported as a
  tier-disagreement, not a validation.
* **This is not a test of config separation** (Q2). The pinned configs differ in patch sets, which
  spiralcheck's pitch sees trivially.

## Cost

CPU only: 24 fits × 2 runs × ~4 s ≈ 3 min. Nothing new is fitted, rendered or scored.
