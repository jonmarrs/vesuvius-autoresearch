# Pre-registration: does villa's updated fitter change the ink our region yields?

**Written 2026-09-24 evening, before any upstream arm was fitted.** Written from
`docs/preregistration/TEMPLATE.md`. Decision code `scripts/analyse_upstream_fitter.py`, tests
`tests/test_analyse_upstream_fitter.py`, fit launcher `repro/spiral_fits/fit_upfit.sh`, chain
`repro/spiral_render/run_upstream_fitter_chain.sh`, tier entry `upfit_` → `upstream` in
`scripts/arm_tiers.py`. All are committed with this file.

## The question

Every current-tier number we publish, including those in the September filing, was fitted on villa
`be09a8503` (2026-09-12). Upstream has since landed two batches of fitter changes:

* the 09-14 series (#1782–#1793): flow-stage slabs, flow gradient conditioning, dt scheduling and a
  dt target cap, fiber supervision, B-spline Triton kernels;
* #1871 "Spiral simplification" (09-23), which removed dense-spacing, unverified patches, the
  influence anchor loss and checkpoint compatibility.

The filing now says plainly that nothing was re-measured on the new fitter. **Did the fitter change
the ink a fit reads, on our region, with everything after the fit held fixed?**

* **If yes,** our current-tier numbers describe superseded code a second time; the filing must say
  so, with the size.
* **If no** (within resolution), they carry over to the fitter villa ships today, and the filing
  can say that instead of hedging.

## Reachability — checked before designing

* **Tree:** `villa-spiral-upstream` = `git archive 75c79ac5f spiral-fitting lasagna vesuvius`, with
  `VILLA_SHA` recorded. Its own venv is built with `uv sync --frozen`, using
  `CXX=g++-13 CC=gcc-13` (as `repro/spiral_s1/README.md` documents). The only dependency change is the
  dropped `edt` pin.
* **Dataset:** ours has only `verified_patches`, so dropping unverified-patch support removes
  none of our inputs. All six config overrides the `curbase` fits use exist unchanged in upstream
  `config.py`.
* **Smoke** (200 steps, seed 1, output in the job's tmp dir, not in `spiral_out`):
  * It completed and wrote 240 winding dirs, range [10, 130).
  * It loaded the same inputs as `curbase`: 38,442 patches, and 59 / 2,173 / 5,413 absolute /
    relative / same-winding points.
  * It iterates at ~3.6 it/s, like the current tree. The first run spent ~10 min compiling Triton
    kernels; these are now cached.
* **Mesh compatibility:** upstream meshes have the same files (`x/y/z.tif`, `meta.json`), the same
  `meta.json` keys, float32 grids with the same row count, and ~94% valid, as a `curbase_s6` mesh.
  So the pinned render path can consume them unchanged.
* **Disclosed:** the smoke's `satisfied_area` at 200 steps was 16.2%. Our README records 16.149%
  for the current tree at a matched 200 steps. This was seen before registration. It is a
  200-step geometry value and says nothing about 30,000-step ink.

## The floor — measured, not inherited

The comparator is the six `curbase_s4..s9` arms from `reports/the_pooled_fit_only_floor.md`, which
were rendered deterministically on the same path. That report's pooled fit-only CV is
**0.0736 [0.051, 0.134]** (df 9).

**Resolution, computed now:** Welch 3 vs 6 at CV 0.0736 gives a 95% CI half-width of
t(df 4–7) × 0.0736 × √(1/3 + 1/6) = **±12.3% to ±14.4%**. The six baselines alone have CV **0.091**
(including `curbase_s6` at +21%). With that actual spread, and the upstream arms at CV 0.074, Welch df
≈ 5.0 gives **±14.5%**. **Only a fitter effect larger than ~15% can be detected.** The +67.6% from the last tree change would be; a few percent would not.

## Arms

| arm | work dir | what varies | held fixed | verified how |
|---|---|---|---|---|
| upfit_s1, upfit_s2, upfit_s3 | `detfit_up1`, `detfit_up2`, `detfit_up3` | fitter tree `75c79ac5f`; seeds 1–3 | dataset, z-ROI, overrides, 30,000 steps (default) | `FIT_TREE` file in each work dir; the gate refuses otherwise |
| curbase_s4..s9 (existing) | `detfit_s4`…`detfit_s9` | — | — | `VILLA_SHA`, `RENDER_IMAGE` checked by the same gate |

**Every arm is rendered on one path:**

* `VILLA_REF=be09a85035059fd83471b1632b5898c62f2c65b1`, with `VILLA_REF_EXPLICIT=1`.
* One `vc-render:local` image (`sha256:1f3a7985…`).
* `FLATTEN_DETERMINISTIC=1`, with the shim guard, and `INK_METRIC_SERIAL_FOLDS=1`.
* The scored windings w120–w129 only.

A test confirms that the six existing baselines already pass these render gates.

Seeds are not paired across trees: a code change re-draws every RNG stream.

## Predictions, fixed now

1. **NO DETECTED CHANGE, confidence low.**
   * For: none of the listed changes targets the outer windings or the ink objective, and the
     200-step geometry matched.
   * Against: the 09-14 series changes the optimiser's schedule, and the last tree change moved
     ink by +67.6%, which nobody predicted.
   * **No magnitude is predicted.**
2. **Upstream seed CV (df 2): no prediction.** It is reported with its interval only.

## Decision rule (`decide()` in `scripts/analyse_upstream_fitter.py`)

| outcome | verdict |
|---|---|
| any arm missing | refused (exception), no output |
| any gate fails: render tree ≠ `be09a8503`, images differ, flatten not deterministic, or `FIT_TREE` ≠ `75c79ac5f` | **INVALID**, no statistic reported |
| Welch 95% CI on (up − base)/base entirely > 0 | **FITTER CHANGED READING (+)** |
| CI entirely < 0 | **FITTER CHANGED READING (−)** |
| CI spans 0 | **NO DETECTED CHANGE**, reported as the interval, never as "no effect" |

**Descriptive, no verdict:** `satisfied_area_fraction` of the three upstream fits; the upstream seed
CV (df 2).

## What the result cannot do — computed before it arrives

* **It cannot say which upstream commit is responsible.** It measures ~20 commits as one change.
* **It says nothing about upstream's flatten, render sampler or scorer driver.** Those also changed
  (`lasagna/fit.py`, `vc_render_tifxyz.cpp`, `get_ink_metrics.py`) and are deliberately held at the
  pin. "Current villa end to end" is a different, larger study.
* **A NO DETECTED CHANGE bounds only effects beyond ~15%.** It cannot license "the numbers
  carry over exactly"; the filing may say only what the interval says.
* **Defaults count as part of "the fitter".** Upstream may have changed defaults for keys we do not
  override. That is part of what villa ships, not a confound to remove.

## Limits

* One region (s1, z 13056–18432), one dataset snapshot, one machine (1× 24 GB GPU).
* Three upstream fits against six baselines fitted 09-13 to 09-15 on the same hardware.

## Cost

Serial: fit ~2 h plus render and score ~2.5 h per arm, ≈ 13–14 h in total. No new data. Nothing else
may use the GPU meanwhile. The chain is launched with `setsid nohup … & disown` from installed copies
in `spiral_out/upstream_fitter_scripts/`, never from this worktree.

### Before launching

- [x] upstream tree provenance recorded (`villa-spiral-upstream/VILLA_SHA` = `75c79ac5f`)
- [x] smoke fit completed on it; mesh format compatible
- [x] baselines pass the render gates (test)
- [ ] rule, tests, launcher and chain committed; installed copies byte-identical
- [ ] shim activation line seen in the chain log for arm 1
