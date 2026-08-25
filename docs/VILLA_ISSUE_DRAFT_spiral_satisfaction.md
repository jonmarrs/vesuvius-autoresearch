# DRAFT (NOT POSTED) — villa issue: spiral satisfaction cannot detect a sheet switch

**Status: drafted 2026-08-25, NOT posted. HELD 2026-08-25 — Jon reviewed the body and
judged it not ready.** Do not post. Do not treat a later "continue" as authorization; this
needs an explicit fresh decision after the open engineering below lands.

Known-open engineering that bears on this draft:
  - the splicing configuration (0.495 / 12.0 / 0.90) is what gates the output mesh, and every
    number in the body is for the reporting configuration (0.45 / 6.0 / 0.95). "You measured
    the config that prints, not the one that gates the mesh" is the strongest available
    objection and it is not yet answered.
  - the theta=0 seam is still unexercised.
  - no real fit has ever been run.

Target: a **new issue** on `ScrollPrize/villa`, not a PR. Modelled on the pattern that landed
issue #1522 (our only accepted contribution, against ten closed PRs): report a real defect,
ask for nothing, propose the cheapest fix without demanding it, credit the prior art.

**Everything re-verified against upstream `main` on 2026-08-25 before drafting**, not taken
from our own pin or our own reports. Our submodule is pinned at `ced62390e`, which predates
PR #1548 (2026-08-21), so the old `volume-cartographer/scripts/spiral/` paths now 404 and are
NOT used here. Verified on live main:

- file is at `spiral-fitting/satisfaction_metrics.py`, now 1052 lines (was 714 at our pin)
- `metrics_config` still `0.45` / `6.0` / `0.95`; the splicing overrides `0.495` / `12.0` /
  `0.90` now live in the same file
- `winding_is_absolute` and `winding_annotation`: **0 occurrences** in that file
- snap-to-nearest present in **both** code paths, `get_patch_satisfied_areas` and the newer
  `evaluate_patch_satisfaction_packed`
- no absolute / expected / annotated winding comparison anywhere in the file
- `spiral-fitting/find_inconsistent_windings.py` still present, 5 references to
  `winding_is_absolute`

Constraints held deliberately:

- **No ask.** No listing request, no prize mention, no link to our submission, no reference to
  our closed PRs.
- **Reports what the metric cannot detect**, not that any published fit is wrong. We have never
  run a real fit; no fitted spiral checkpoint is published.
- **Credits the machinery that already exists.** `find_inconsistent_windings.py` already
  propagates the annotations. The gap is that the scored metric does not consult it.
- **Reproducible offline**, no GPU, no downloads, against villa's own unmodified function.
- House style: no em-dashes or en-dashes.

---

## Title

`spiral satisfaction metric cannot detect a sheet switch: a patch displaced by any whole number of windings scores identically to a correctly placed one`

## Body

**Summary.** `get_patch_satisfied_areas` decides whether a patch is satisfied by comparing it
against a target it derives from the patch's own position: it snaps the patch's median
shifted-radius to the nearest integer winding, then checks two residuals against that
self-derived target. Because the target moves with the patch, a patch sitting on the wrong wrap
is scored against the wrong wrap and passes. Displacing a patch by a whole winding changes the
satisfied-quad fraction by exactly zero.

This is the failure mode the 2026 open problems page lists fourth in its bottleneck table,
"Meshes can jump from one wrap to another", where the "what would help" column asks for
conservative failure detection.

**The blindness is periodic, not a one-winding special case.** What decides acceptance is the
displacement's distance from the nearest integer winding, not its magnitude. Measured against
villa's own unmodified function on an analytic spiral, at `dr = 12.81` voxels:

| displacement (windings) | distance from nearest winding | verdict |
|---|---|---|
| 0.5 | 0.5000 | rejected |
| 1.0 | 0.0000 | satisfied |
| 5.5 | 0.5000 | rejected |
| 23.8006 | 0.1994 | **satisfied** |

A patch displaced by 23.8006 windings, roughly 305 voxels at that spacing, is scored satisfied,
while one displaced by half a winding is rejected. The acceptance edge is bracketed at
`(0.44, 0.46]` and re-resolves identically five windings out (`5.44` satisfied, `5.46`
rejected), so it does not move with magnitude. That leaves a rejected strip of roughly 8 to 12
percent of each inter-winding period; the rest of the period is accepted.

`0.45` is `metrics_config['satisfaction_radius_tolerance']`, so the acceptance half-width is
the tolerance itself, in units of `dr_per_winding`. The measurement is consistent with the
constant rather than with an empirical accident.

**The annotations that would fix this already exist and are already load-bearing elsewhere.**
`get_patch_abs_winding_loss` selects point collections on `metadata.winding_is_absolute` and
pins each annotated point's shifted radius to `winding_annotation * dr_per_winding`. So absolute
winding truth is present in the inputs and drives the fit. Neither `winding_is_absolute` nor
`winding_annotation` appears anywhere in `satisfaction_metrics.py`. The truth is consumed by the
fit and never used to score it.

`find_inconsistent_windings.py` already does the harder half of the work: it derives a patch's
expected absolute winding by direct votes from attached absolute anchors plus a backwards BFS
over relative-winding edges. It is a standalone debug tool, run one `--patch-id` at a time and
outside the fit loop, so nothing in the scored path benefits from it today.

**Scope, stated plainly.** This says nothing about how often real fits actually misplace a patch
by a winding, and it is not a claim that any published fit is wrong. It is a statement about
what the metric can and cannot detect. Every number above was measured on synthetic patches
scored by villa's real unmodified function. We did not run a fit, because no fitted spiral
checkpoint is published under `dl.ash2txt.org/datasets/spiral_datasets/`.

The `12.81` voxel spacing is not invented either: it is the median inter-winding gap measured
across 25,283,382 adjacent-winding gaps in the published PHercParis4 `winding_model/` crossing
export, whose per-shard medians run 11.32 to 16.74. The same measurement puts villa's 6.0 voxel
scan tolerance at about 47 percent of the real winding spacing.

**A smaller thing that follows.** Under combined patch scatter and a nonlinear scan-to-spiral
map, we found exactly one configuration in a 25 cell sweep where the patch-level verdict does
differ between the correctly placed and displaced patch, at a delta of `-0.018182`. It is worth
noting only because it is smaller than that sweep's worst-case delta of `-0.042424`: what
decides whether the verdict changes is proximity to the `satisfied_patch_quad_fraction`
threshold, not the size of the delta, so a worst-case delta does not bound the verdict.

**Cheapest fix first.** For patches reachable from an absolute-winding annotation, compare the
snapped target winding against the annotation-derived expectation and report the disagreement
alongside the existing satisfaction figure. That is a report-only change: it adds a signal
without altering what the metric accepts, and the propagation logic already exists in
`find_inconsistent_windings.py`. A stricter version, failing such patches outright, would be a
behaviour change and is not what this issue asks for.

**Reproduction.** Offline, no GPU, no downloads, against villa's unmodified function:

```
git clone https://github.com/jonmarrs/vesuvius-autoresearch
cd vesuvius-autoresearch
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_untested_cells.py
```

Full write-up, including the limits and the corrections we made to our own earlier claims, is
in `reports/spiral_satisfaction_winding_blindness.md` in that repository.

---

## Pre-post checklist

- [ ] Re-verify the four upstream facts again on the day of posting (paths move; PR #1548 moved
      this file four days before this draft)
- [ ] Confirm no newer issue already reports this
- [ ] Confirm the reproduction command runs clean from a fresh clone
- [ ] Jon reads and approves the body verbatim
