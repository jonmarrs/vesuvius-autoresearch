# Pre-registration: does villa's updated Python render stage change the ink score of fixed meshes?

**Written 2026-09-25, before any arm was rendered.** Decision code `scripts/analyse_upstream_render_path.py`;
tests `tests/test_analyse_upstream_render_path.py`; chain
`repro/spiral_render/run_upstream_render_path_chain.sh`. All are committed with this file.

## The question

`reports/upstream_fitter_no_detected_change.md` held everything after the fit at the pin. But upstream
also changed the post-fit stages:

* `lasagna/fit.py`, the flatten;
* `spiral-fitting/tifxyz.py`, mesh I/O;
* `spiral-fitting/get_ink_metrics.py`, the scoring driver;
* 76 other executable files under the render trees (`scripts/check_villa_render_path.py
  be09a8503 75c79ac5f`).

**For identical meshes, does the `75c79ac5f` Python stage produce a different `total_fg_pixels`?**

* **If yes,** absolute ink numbers are stage-specific. A villa user on current code gets a different
  count from ours for the same surface, and any cross-version comparison needs a render-stage term.
* **If no,** the upstream-fitter result extends to "villa as it runs today", minus the sampler (see
  below).

## Scope, and what is deliberately NOT varied

* **The C++ sampler is held.** Our image (`sha256:1f3a7985…`) rebuilds only `vc_tifxyz2obj` and
  `vc_obj_uv_lift`. `vc_render_tifxyz` comes from villa's published `:edge` runtime image. Upstream's
  sampler-source changes reach a render only through a new published image, not through villa's
  tree. That is a separate question, and it is not asked here.
* **The venv is held:** `villa-spiral`'s. It was checked identical to the upstream lock in the
  versions that matter (Python 3.14.3, torch 2.11.0+cu128, numpy 2.5.2). If upstream code needs a
  package the venv lacks, the render fails loudly and the study stops.

## Reachability, checked before registering

`setup_workdir.sh` with `VILLA_REF=75c79ac5f` extracts the three trees, and `serial_folds.patch`
applies cleanly to upstream's `get_ink_metrics.py`. This was dry-run into a scratch dir.

## Arms

All use the `upfit_s1` meshes, windings w120–w129, which are byte-identical to `detfit_up1`'s.

| arm | Python stage | role |
|---|---|---|
| `rpath_up_a` | `75c79ac5f` | measurement |
| `rpath_up_b` | `75c79ac5f` | determinism check on the new code |
| `rpath_pin_a` | `be09a8503` | same-day environment check |
| `detfit_up1` (exists) | `be09a8503` | reference, 3,279,498 |

**Every arm uses:** one image, `FLATTEN_DETERMINISTIC=1` and `INK_METRIC_SERIAL_FOLDS=1`, run
serially.

**The shim guard now requires a NEW shim line per arm.** The older chains grepped the log tail,
which back-to-back render-only arms could satisfy with the previous arm's line. The pooled chain was
checked: every one of its six arms logged its own three shim lines, so nothing slipped through there.

**Why the upstream stage is rendered twice.** The shim sets `warn_only=True`. An op without a
deterministic kernel in new code would therefore run stochastically without failing, so determinism
on `75c79ac5f` must be measured, not assumed.

## Decision rule (`decide()`)

| condition | verdict |
|---|---|
| any arm missing | refused |
| wrong tree, different image, or non-deterministic flatten on any arm | **INVALID** |
| `rpath_pin_a` differs from `detfit_up1` by > 0.01% | **INVALID** (environment drifted; nothing attributable) |
| the upstream repeats agree within 0.01%, and \|effect\| < 0.5% | **RENDER PATH INERT (within 0.5%)** |
| the upstream repeats agree within 0.01%, and \|effect\| ≥ 0.5% | **RENDER PATH CHANGES INK** (effect reported) |
| the upstream repeats differ by d > 0.01%, and \|effect\| > max(0.5%, 3d) | **RENDER PATH CHANGES INK (upstream stage nondeterministic)** |
| the upstream repeats differ, otherwise | **NOT RESOLVED (upstream stage nondeterministic)** |

The effect is mean(upstream) / mean(pinned) − 1. The 0.01% tolerance comes from the measured pinned
deterministic floor (0.0014%). The 0.5% inertness bound is small next to the 7% fit-only floor that
all fit comparisons carry.

## Predictions, fixed now

1. **The pinned re-render reproduces `detfit_up1`.** Confidence high.
2. **The upstream stage is deterministic.** Confidence moderate: `lasagna/fit.py` changed by an
   unknown amount.
3. **Effect: withheld.** The last render-path change (`d8c5f488a` → `be09a8503`, 678 lines) was
   suspected of +4.3% and never cleanly resolved. There is no basis for a direction.

## What the result cannot do

* **One fit, one region.** A render-stage effect could depend on the surface. A single arm measures
  its size on one surface, exactly, and cannot establish generality.
* **It says nothing about the sampler** in a newer published image.
* **It cannot attribute an effect to a file** among the ~80 changed.

## Cost

Three renders, ~1 h 45 min each (deterministic flatten), ≈ 5.5 h serial on the GPU. Run from
installed copies in `spiral_out/upstream_render_path_scripts/`, launched with `setsid nohup`.
