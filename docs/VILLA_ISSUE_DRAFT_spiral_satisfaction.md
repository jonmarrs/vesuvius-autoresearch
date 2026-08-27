# DRAFT (NOT POSTED) — villa issue: spiral satisfaction cannot detect a sheet switch

**Status: revised 2026-08-26 (fifth pass), NOT posted. HELD pending Jon's explicit approval.**
Do not post. Do not treat a later "continue" as authorization.

This supersedes the 2026-08-25 draft and the three earlier passes of 2026-08-26. The core claim is
unchanged and has now survived about ten review cycles untouched. The third pass removed the
frequency number on the strength of a result that turned out to be a bug in our own injection code;
that reason is withdrawn, and the number is back, with its provenance stated.

Target: a **new issue** on `ScrollPrize/villa`, not a PR. Modelled on the pattern that landed
issue #1522 (our only accepted contribution, against ten closed PRs): report a defect, ask for
nothing, propose the cheapest fix without demanding it, credit the prior art.

**Re-verified against upstream `main` on 2026-08-26**, not against our pin:

- `spiral-fitting/satisfaction_metrics.py`, now **1092 lines** (1052 yesterday, 714 at our pin —
  the file is under active development, so re-verify again on the day of posting)
- `metrics_config` still `0.45` / `6.0` / `0.95`; splicing override still `0.495` / `12.0` / `0.90`
- `winding_is_absolute` and `winding_annotation`: **0 occurrences** in that file
- `spiral-fitting/find_inconsistent_windings.py` still present
- no existing issue reports this

## What changed since the last pass

Realigned with the restructured report (`reports/spiral_satisfaction_winding_blindness.md`, commit
`68bf3b28`), which now separates what stands without a scatter model from an unfinished calibration.
The draft follows that split.

**Added: the real-geometry result**, which was the strongest evidence we had and was not in the
draft at all. villa's unmodified function on windows of published traced surfaces, with a
half-winding control that moves the score on 48 and 92 percent of windows while whole windings move
it on none. Until this the whole issue rested on an analytic spiral.

**Added: the two limits that come with it** — those windows are traced surfaces rather than
spiral-fit patches, and they are coarse enough that the smallest one available spans 0.89 of a
winding where the synthetic patch spans 0.16. Both are stated in the body rather than left for a
maintainer to discover.

**Removed as a headline: the frequency figure.** It is described, with its provenance and the fact
that we do not trust it, instead of being asserted. This is the second time it has come out and the
reasoning is different: last time it was removed because a check said it was biased high, and that
check turned out to be broken. This time it is demoted because the estimate has moved five times in
a day on our own defects and the machinery behind it is an unfinished calibration. The number is
still in the text; it is no longer the answer to "does this matter".

Constraints held, unchanged:

- **No ask.** No listing request, no prize mention, no link to our submission, no reference to our
  closed PRs.
- **Reports what the metric cannot detect**, not that any published fit is wrong. We have never run
  a real fit; no fitted spiral checkpoint is published.
- **Credits the machinery that already exists.**
- **Reproducible offline**, no GPU, no downloads, against villa's own unmodified function.
- House style: no em-dashes or en-dashes.

---

## Title

`spiral satisfaction metric cannot detect a sheet switch: a patch displaced by any whole number of windings scores identically to a correctly placed one`

## Body

**Summary.** `get_patch_satisfied_areas` decides whether a patch is satisfied by comparing it
against a target it derives from the patch's own position: it snaps the patch's median
shifted-radius to the nearest integer winding, then checks two residuals against that self-derived
target. Because the target moves with the patch, a patch sitting on the wrong wrap is scored against
the wrong wrap and passes. For a patch lying on a winding, displacing it by a whole winding changes
the satisfied-quad fraction by exactly zero.

This is the failure mode the 2026 open problems page lists fourth in its bottleneck table, "Meshes
can jump from one wrap to another", where the "what would help" column asks for conservative failure
detection.

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
`(0.44, 0.46]` and re-resolves identically five windings out, so it does not move with magnitude.
`0.45` is `metrics_config['satisfaction_radius_tolerance']`, so the acceptance half-width is the
tolerance itself in units of `dr_per_winding`.

**It holds under the configuration that gates the output mesh, which is the more permissive of the
two.** All of the above is under the default `metrics_config`. The second call site, inside
`save_mesh`, overrides all three thresholds to `0.495` / `12.0` / `0.90` and decides which patches
are spliced into the output mesh. Under that configuration the whole-winding delta is still exactly
zero, and the acceptance edge moves outward to `(0.49, 0.499]`. So the path with downstream
consequences rejects a narrower strip around the midpoint than the reporting path does.

It also holds across the theta = 0 seam, where the branch-offset unwrap is exercised, and under
radial warps interpolated from the inter-winding spacings actually measured along rays in the
published PHercParis4 `winding_model` export.

**Confirmed on real traced geometry, not only on an analytic spiral.** The numbers above come from
a synthetic patch. Scoring the same unmodified function on windows taken from published traced
surfaces, translated into the umbilicus-centred frame, gives the same answer, and a control shows
the test could have come out otherwise:

| displacement | 2x4-cell windows (n=60) | 12x16-cell windows (n=36) |
|---|---|---|
| 0.5 windings (control) | max change 1.0000, 48 percent of windows | 0.1576, 92 percent |
| 1.0 windings | 0.0000, none | 0.0000, none |
| 2.0 windings | 0.0000, none | 0.0000, none |
| 5.5 windings (control) | 1.0000, 48 percent | 0.1636, 92 percent |

A half winding moves the score on half to nearly all real windows, so the construction plainly can
move it. Whole and double windings move it on none, by exactly zero, and that holds at each window's
own best-fit spacing rather than at a shared constant.

Two things about those windows are worth stating rather than leaving for a reader to find. They are
windows of traced surfaces, not spiral-fit patches, because no fitted spiral checkpoint is published
under `dl.ash2txt.org/datasets/spiral_datasets/`. And they are coarse: traced surfaces step about 20
voxels per grid cell, so the smallest window with any quads spans about 0.89 of a winding radially,
where the synthetic patch spans 0.16. No window the published data can form resembles the synthetic
patch on that axis, which is a limit on what can be checked with what is public, and it is also why
larger real windows are never satisfied at any spacing: a window spanning nine windings contains
points belonging to nine different windings.

**The annotations that would fix this already exist and are already load-bearing elsewhere.**
`get_patch_abs_winding_loss` selects point collections on `metadata.winding_is_absolute` and pins
each annotated point's shifted radius to `winding_annotation * dr_per_winding`. So absolute winding
truth is present in the inputs and drives the fit. Neither `winding_is_absolute` nor
`winding_annotation` appears anywhere in `satisfaction_metrics.py`. The truth is consumed by the fit
and never used to score it.

`find_inconsistent_windings.py` already does the harder half of the work: it derives a patch's
expected absolute winding by direct votes from attached absolute anchors plus a backwards BFS over
relative-winding edges. It is a standalone debug tool, run one `--patch-id` at a time and outside the
fit loop, so nothing in the scored path benefits from it today.

**How often this matters in practice: we cannot give you a defensible number.** The exactness above
is for a patch lying on a winding. Real patches carry surface noise, and once that noise is large
enough the two verdicts do diverge, so the blindness is not total in practice.

We built the machinery to estimate the rate and we do not trust its output. The estimate needs the
residual scatter of real patches corrected for the attenuation the estimator introduces, and that
correction is large, roughly a factor of three, and depends on a fitted noise model. Our figure has
taken five values in a single day, and every move came from a defect we found in our own code rather
than from new evidence: an attenuation fitted under one noise field and compared against a threshold
measured under another; a correlation target that turned out to be a one-patch statistic because a
loop broke out of the wrong level; a transplant that injected an empty field for half its donors.
Three of those were written down before we caught them. The current figure is about 24 percent, the
attenuation behind it is better constrained than it was but is not confirmed, and one of the
arguments we had used to support it has been withdrawn outright.

Publishing that as a headline would be claiming more than we have. What we can say without any of
that machinery: the blindness is exact for a patch lying on a winding, real noise incidentally
exposes some minority of displacements, and in those cases the metric is rejecting a noisy patch
rather than detecting a sheet switch. It never tests for the thing that went wrong. Everything else
in this report needs no noise model at all.

**Scope, stated plainly.** This says nothing about how often real spiral fits actually misplace a
patch by a winding, and it is not a claim that any published fit is wrong. It is a statement about
what the metric can and cannot detect. Every number above was measured on synthetic patches scored by
villa's real unmodified function. We did not run a fit, because no fitted spiral checkpoint is
published under `dl.ash2txt.org/datasets/spiral_datasets/`.

The `12.81` voxel spacing is measured, not assumed: it is the median inter-winding gap across
25,283,382 adjacent-winding gaps in the published `winding_model` crossing export, whose per-shard
medians run 11.32 to 16.74. That puts villa's 6.0 voxel scan tolerance at about 47 percent of the
real winding spacing.

**Cheapest fix first.** For patches reachable from an absolute-winding annotation, compare the
snapped target winding against the annotation-derived expectation and report the disagreement
alongside the existing satisfaction figure. That is a report-only change: it adds a signal without
altering what the metric accepts, and the propagation logic already exists in
`find_inconsistent_windings.py`. A stricter version, failing such patches outright, would be a
behaviour change and is not what this issue asks for.

**Reproduction.** Offline, no GPU, no downloads, against villa's unmodified function:

```
git clone https://github.com/jonmarrs/vesuvius-autoresearch
cd vesuvius-autoresearch
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_untested_cells.py
```

Full write-up, including the limits and the corrections we made to our own earlier claims, is in
`reports/spiral_satisfaction_winding_blindness.md` in that repository.

---

## Pre-post checklist

- [ ] Re-verify the upstream facts again on the day of posting. The file grew 714 to 1052 to 1092
      lines over three days and its directory moved once; treat any path here as stale until checked.
- [ ] Confirm no newer issue reports this
- [ ] Confirm the reproduction command runs clean from a fresh clone
- [ ] Decide whether the real-geometry table needs its own reproduction command. It currently has
      none: the single command reproduces the analytic result only, and the real-geometry work needs
      the `verified_patches` data, which is a download rather than an offline run.
- [ ] Jon reads and approves the body verbatim

## Notes for the reviewer of this draft

Three judgement calls worth challenging:

1. **The frequency figure is present but demoted, rather than either asserted or deleted.** A
   maintainer's first question will be "does this ever matter", so saying nothing is unsatisfying;
   asserting a number that has moved five times in a day on our own defects would be worse. The
   middle course, describing the estimate and why we distrust it, risks reading as hedging. If you
   want it gone entirely, the body loses one paragraph and nothing else depends on it.

2. **The reproduction points at one probe**, not the whole chain. That probe covers the exact,
   surrogate-free result, which is now the only quantitative claim in the body, so the match between
   what is claimed and what is reproducible is better than in earlier drafts. The discarded
   frequency work is not reproducible from the one command, and is no longer relied on.

3. **Nothing here mentions the mesh-splicing config's practical consequence.** It gates what enters
   the output mesh, which is arguably the most concerning part, and the draft states the fact without
   drawing the inference. That restraint may be right for a first contact, or may be burying the
   lede.

## Revision history of the frequency claim, for the reviewer only

Not for the issue body. Kept because the sequence is the reason the number was dropped.

| date | figure | what changed it |
|---|---|---|
| 2026-08-25 | (none) | not yet measured |
| 2026-08-26 | 6.8% | first estimate; compared quantities measured under two different noise models |
| 2026-08-26 | 30% | both sides recomputed under one model |
| 2026-08-26 | 24% | the correlation target was a one-patch statistic, not a ten-patch one |
| 2026-08-26 | dropped | real-residual-shaped noise appeared to produce no divergence threshold |
| 2026-08-26 | 24% | that check was broken: half the donors injected an all-zero field. Repaired, real-residual noise diverges the verdict as often as the fitted model (53% vs 54%) |
| 2026-08-26 | 24%, demoted | not a new defect: the report was restructured, and the whole scatter-model chain moved to an appendix marked unfinished. The figure stays in the text and stops being the answer to "does this matter" |
