# villa's updated Python render stage is inert on fixed meshes (+0.0005%)

**2026-09-25.** Result of `docs/preregistration/2026-09-25_upstream_render_path.md`, decided by
`scripts/analyse_upstream_render_path.py`. The rule and tests were committed at `ac51063e` before any arm
rendered. Verdict JSON: `reports/upstream_render_path_verdict.json`.

## Result: RENDER PATH INERT (within 0.5%)

The `upfit_s1` meshes (w120–w129) were rendered on two Python stages. The image, venv and
deterministic flatten were identical throughout.

| arm | Python stage | `total_fg_pixels` |
|---|---|---:|
| `rpath_up_a` | `75c79ac5f` | 3,279,537 |
| `rpath_up_b` | `75c79ac5f` | 3,279,545 |
| `rpath_pin_a` | `be09a8503` (today) | 3,279,548 |
| `detfit_up1` | `be09a8503` (09-25 00:11) | 3,279,498 |

* **Effect** (mean upstream / mean pinned − 1): **+0.0005%**, about 18 pixels of 3.28 M.
* **Upstream repeatability:** 0.0002% (8 px). The new stage is deterministic under the shim.
* **Pinned same-day reproduction:** 0.0015% (50 px). This matches the 0.0014% floor measured
  earlier, so the environment has not drifted.

**The registered predictions were:**

* the pinned re-render reproduces: **hit**;
* the upstream stage is deterministic: **hit**;
* the effect: withheld.

## Checked before writing: the arms really ran different code on the same surface

* **Different code.** The render-stage files extracted into each work dir hash differently between
  the stages:
  * `lasagna/fit.py`: 78 diff lines;
  * `spiral-fitting/tifxyz.py`: 26;
  * `spiral-fitting/get_ink_metrics.py`: 1;
  * 10 files under `lasagna/` differ in total.

  Within each stage, the arms' files are identical. So "inert" means this code change does not move
  the score. It does not mean the same code ran twice.
* **Same surface.** The concatenated `x/y/z.tif` of all 30 scored-winding grids hash identically
  (`0b45f2de…`) in all four work dirs.

## What it means, together with finding 62

* **The fitter change** (finding 62): +4.82% [−7.51%, +17.15%], no detected change at ±15%.
* **The Python render-stage change** (this report): exactly inert, +0.0005% on this surface.

So **villa's tree at `75c79ac5f`, end to end on the Python side, does not detectably change what
our region reads.** Our current-tier numbers carry over to it within the fitter comparison's ±15%.
The render stage contributes nothing measurable to that bound.

## What it cannot say

* **One surface.** On one fit, the effect is measured exactly. A render-stage change could still
  matter on a different surface, but nothing here suggests one.
* **The C++ sampler is not covered.** `vc_render_tifxyz` comes from villa's published `:edge`
  runtime image, which was held fixed. Upstream's sampler-source changes reach users only through a
  new published image.
* **It cannot attribute anything to individual files**, and there is nothing to attribute.
