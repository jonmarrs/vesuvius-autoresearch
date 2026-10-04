# villa #1818's smooth surface interpolation moves ink locally by up to ±20%; its default is inert

> **Correction of scope, 2026-10-03 (finding 72).** The ±20% per window below did **not** replicate at
> that size in villa's own scoring pipeline. On 8 labelled segment meshes, with one p95 normalisation
> per strip as `render_ink` does, smooth moved the count by a median of 1.3% per window (range −9% to
> +7%), and its agreement with villa's ink labels not at all. **Per-crop p95 normalisation is NOT the
> reason (tested 2026-10-03):** re-scoring these windows with one shared p95 per mode leaves median |Δ|
> at 4.7% (range −17.5% to +21.1%; `reports/shared_p95_rescore.json`, prereg
> `docs/preregistration/2026-10-03_shared_p95_normalisation.md`, prediction FAILED). Measured instead:
> this spiral flat's grid cells are ~80 voxels (~10 output px); the segment meshes' are ~20 (~2.5 px).
> Smooth and linear differ only inside cells, so cell size is the leading candidate. Quote this
> report's numbers only for its own surface type. See `reports/scorer_vs_labels_surface_interpolation.md`.

**2026-10-02.** Result of `docs/preregistration/2026-10-02_surface_interpolation_windows.md` (committed
`1cb2f0d6` before any window rendered; procedural amendment `6acd1295` before any window scored), plus
one post-hoc control, labelled as such. Data: `reports/interp_smoke.json`, `reports/interp_windows.json`,
`reports/interp_scorer_stability.json`.

## 1. The default is inert, measured

villa #1818 (2026-09-30) added `vc_render_tifxyz --surface-interpolation {linear,smooth}`, default
`linear`. `render_ink.py` does not pass the flag. On one crop of `detfit_up1`'s saved flat, sampled
exactly as `render_ink.py` samples it, three renders are **byte-identical on all 5 slices**:
* the source build before #1818 (`75c79ac5f`);
* the build after it (`f637f3b35`, which also contains #1905, #1831 and #1848);
* the PR #1905 head's full render of the same window.

So nothing that landed between those commits changes the sampled stack at the default. The loop's
numbers are unaffected by #1818. The code reading agrees: the linear path is a refactor with
identical arithmetic.

## 2. `smooth` re-places ink; my prediction failed

Eight full-height windows (2048 × 4460 px, about 18% of the strip), chosen on surface coverage alone.
Each was rendered by `vc-render:sampler-f637f3b35` at the default and with `smooth`, then strip-built
and scored like `render_ink.py` + `get_ink_metrics.py`:

| window x | linear fg | smooth fg | Δ fg | Δ line score |
|---:|---:|---:|---:|---:|
| 37376 | 99,289 | 104,106 | +4.85% | −0.007 |
| 40007 | 158,147 | 161,501 | +2.12% | −0.018 |
| 48782 | 83,842 | 81,132 | −3.23% | +0.009 |
| 56021 | 86,339 | 87,820 | +1.72% | −0.001 |
| 65308 | 29,541 | 31,292 | +5.93% | −0.067 |
| 74083 | 219,232 | 207,240 | −5.47% | −0.069 |
| 77226 | 45,739 | 53,795 | **+17.61%** | −0.086 |
| 83953 | 73,556 | 58,693 | **−20.21%** | −0.007 |
| **pooled** | 795,685 | 785,579 | **−1.27%** | median −0.013 |

* **Prediction 1, "|Δ fg| < 1% in every window": FAILED.** Not one window is under 1%; the median
  |Δ| is 5.2%. The one-crop smoke (−0.09%) was not representative.
* **Prediction 2, "line score: no consistent direction": held as registered** (7 negative, 1
  positive; the rule was "not all 8 of one sign"). It is still 7 of 8.

## 3. The swings are not scorer instability (post-hoc control)

Was the crop-level score just this jumpy? On the two extreme windows and one moderate one, I scored
the **linear** composite with three meaningless changes:
* a second JPEG pass;
* ±1 grey level on a random 8% of pixels (the fraction smooth changes, at the smallest size);
* a 1-pixel shift.

| window | smooth | JPEG | ±1 noise | 1-px shift |
|---:|---:|---:|---:|---:|
| 77226 | +17.61% | +0.64% | +0.07% | +1.39% |
| 83953 | −20.21% | +0.01% | +0.36% | +2.82% |
| 56021 | +1.72% | +0.25% | +0.57% | +1.49% |

Meaningless changes move fg by **≤ 2.8%**. Smooth moves the two extreme windows by **7–20×** that.
Window 56021's +1.72% is **within** the control range, so not every window's effect is resolved.
The line score moves by ≤ 0.014 under the controls and by −0.086 under smooth at 77226.

## 4. What it is not

* **Not coverage.** Smooth renders 0.2–0.5% more valid pixels in every window, far too little.
* **Not the strip normalisation.** p95 rises by 0–6.7% under smooth, and windows with similar p95
  shifts go in opposite directions (77226: p95 +6.5%, fg +17.6%; 83953: p95 +1.9%, fg −20.2%).
* **Most plausibly geometry.** Smooth changes the sampled positions and normals between grid
  vertices. The scorer is known to be sensitive to sub-voxel surface changes: a 4-voxel radial shift
  costs ink in both directions, and ink placement reproduces only at r ≈ 0.70 across seeds. A large
  local move with a small net (−1.3%) is that signature. This is inferred, not isolated here.

## 5. What it means

* **For villa's loop:** the default changes nothing. Anyone who renders with `smooth`, or a future
  default flip, shifts per-region ink by up to ±20% and, on this surface, the total by about −1%.
  **Never compare runs rendered in different modes.** The render log prints `Surface interpolation:
  smooth (bicubic)` only in smooth mode, so a mixed comparison is detectable from files a run
  already leaves. inkdelta now checks for it (0.5.0).
* **For reading:** there is no sign that smooth reads text better. Line regularity falls slightly in
  7 of 8 windows. Without ground truth, nothing here says which rendering is more faithful. It says
  that they differ locally, by a lot.

## Limits

* One surface, one region (PHercParis4), one scorer; 8 windows ≈ 18% of the strip. The pooled −1.27%
  is a window sum, not a full-strip render, and crop scoring normalises per window, not per strip.
* The control is post hoc and covers 3 of the 8 windows.
* No full-strip study was run. Pre-registered as unwarranted if both predictions held. One failed,
  but the actionable conclusion (do not mix modes; total ≈ −1%) does not need it.
* Nothing posted to villa.

## Post-hoc audit (2026-10-04, villa-independent code review merged as PR #2)

A code review (`docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-03.md`) hardened this study's scripts. It found:
* the smoke comparison truncated incomplete slice sets;
* the window analysis did not check the saved window list;
* a selector failure could be swallowed;
* **the registered per-window surface check ran once per chain**, not "before each window" as the
  pre-registration said.

That last one is a deviation from the registered method. It is disclosed here and has no effect: the
surface is a static file, its md5 (`bfd9ef809c27930d553b778adc209dd9`) was verified at chain start, and
nothing writes to it. **Re-analysis with the hardened scripts reproduces every window exactly**:
* identical linear and smooth counts and Δ in all 8 windows;
* identical predictions-held;
* the only change is a new summary field, `n_fg_undefined = 0`.
