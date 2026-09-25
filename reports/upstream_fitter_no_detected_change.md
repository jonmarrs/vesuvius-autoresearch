# villa's updated fitter: no detected change in the ink we read (+4.8%, CI [−7.5%, +17.2%])

**2026-09-25.** Result of `docs/preregistration/2026-09-24_upstream_fitter.md`, decided by
`scripts/analyse_upstream_fitter.py`. The rule and tests were committed at `2cb28f84` before any
upstream arm was fitted. Verdict JSON: `reports/upstream_fitter_verdict.json`.

## Result

Three fits on villa `75c79ac5f` were compared with the six `curbase_s4..s9` fits on `be09a8503`.
`75c79ac5f` is the fitter after the 09-14 series and #1871 "Spiral simplification". Every arm was
flattened, rendered and scored on one pinned path: villa `be09a8503`, image `sha256:1f3a7985…`,
deterministic flatten, scored windings w120–w129.

| arm | `total_fg_pixels` | `satisfied_area_fraction` |
|---|---:|---:|
| detfit_up1 (upfit_s1) | 3,279,498 | 0.8465 |
| detfit_up2 (upfit_s2) | 3,360,916 | 0.8518 |
| detfit_up3 (upfit_s3) | 3,012,138 | 0.8504 |
| **upstream mean** | **3,217,517** | |
| curbase_s4..s9 mean | 3,069,469 | 0.8457–0.8543 (range) |

**VERDICT: NO DETECTED CHANGE.**

> upstream vs current: **+4.82%, 95% CI [−7.51%, +17.15%]** (Welch, df 6.1)

**All four gates passed:**

* every render tree is `be09a8503`;
* one render image across all nine arms;
* every flatten is deterministic, and the shim line was seen for each upstream render (`GUARD_OK` ×3);
* every upstream `FIT_TREE` is `75c79ac5f`.

**The prediction was NO DETECTED CHANGE, at low confidence.** It held. Its reasoning is weak
evidence, since a null was the likelier outcome of an under-powered design anyway.

## Checks run before writing

* **Content, not just labels.** For all three arms, the 10 scored windings in the work dir are
  byte-identical (md5 of `x/y/z.tif`) to the upstream fit's own output. The gates check provenance
  files; this checks that the meshes behind them are the claimed ones.
* **The baseline outlier.** `curbase_s6` sits +21% above the rest of its group. Without it the
  estimate is **+8.46%, CI [−3.84%, +20.75%]** (df 3.3). It still spans zero, so the verdict does not
  rest on that fit. Both point estimates are positive; neither interval excludes zero.

## What it means

* **The current-tier numbers were not overturned by the new fitter, within ±15%.** At registration
  the resolution was ±14.5%, and the realised interval is 24.7 points wide. A fitter effect of the
  size of the last tree change (+67.6%) is excluded. A gain of up to ~17%, or a loss of up to ~8%,
  is not.
* **Geometry is indistinguishable too** (descriptive). Upstream `satisfied_area_fraction`
  (0.8465–0.8518) sits inside the baselines' range (0.8457–0.8543).
* **The filing may now say this** in place of "not re-measured", quoting the interval and not "no
  change".

## Side observation (not registered)

The upstream fitter iterates at **~2.5–2.6 it/s against 3.7–4.1 it/s** for `be09a8503`, on the same
GPU with nothing else running. A 30,000-step upstream fit took 3 h 05 min wall time (arms 2 and 3, from the chain log). At the old
rate, 30,000 steps take ~2 h 10 min; that figure is estimated from the rate, not measured. The first run
also spent ~10 min compiling Triton kernels (now cached). The cause was not investigated.

## What this cannot say

* **It cannot say which upstream commit did what.** About twenty commits are measured as one change.
* **It says nothing about upstream's flatten, render sampler or scorer driver.** All three changed
  and were deliberately held at the pin.
* **It cannot say the numbers carry over exactly.** Effects under ~15% are not resolved.
* **One region, one dataset snapshot, three upstream seeds.** The upstream CV (0.057, df 2) is
  descriptive only.
