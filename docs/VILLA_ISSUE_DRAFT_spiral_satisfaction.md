# DRAFT (NOT POSTED) — villa issue: spiral satisfaction cannot detect a sheet switch

**Status: revised 2026-08-27 (seventh pass), NOT posted. HELD pending Jon's explicit approval.**
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

**The frequency paragraph is cut**, on Jon's instruction. 294 words out; the body is back to about
1,330 from 1,630. Nothing else depended on it, which was the argument for cutting it.

What survives of it is two sentences moved into Scope, because dropping the number should not leave
a reader thinking the blindness is unconditional: it is exact for a patch lying on a winding, real
noise makes the verdicts diverge on some cases, and when that happens the metric is rejecting a
noisy patch rather than detecting a sheet switch. No figure is given, and the draft says we could
not produce one we trust.

Scope also had to be corrected rather than just trimmed. It claimed every number above was measured
on synthetic patches, which stopped being true when the real-geometry table went in two passes ago.

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

**Scope, stated plainly.** This says nothing about how often real spiral fits actually misplace a
patch by a winding, and it is not a claim that any published fit is wrong. It is a statement about
what the metric can and cannot detect. The numbers above come from synthetic patches and from
windows of published traced surfaces, all scored by villa's real unmodified function. We did not run
a fit, because no fitted spiral checkpoint is published under
`dl.ash2txt.org/datasets/spiral_datasets/`.

One qualification the exactness above deserves: it is exact for a patch lying on a winding. Real
patches carry surface noise, and with enough of it the two verdicts do diverge, so the blindness is
not total in practice. We tried to estimate how often and could not do it to our own satisfaction,
so we are not putting a figure on it here. When noise does cause a divergence, note what is
happening: the metric is rejecting a noisy patch, not detecting a sheet switch. It never tests for
the thing that went wrong.

The `12.81` voxel spacing is measured, not assumed: it is the median inter-winding gap across
25,283,382 adjacent-winding gaps in the published `winding_model` crossing export, whose per-shard
medians run 11.32 to 16.74. That puts villa's 6.0 voxel scan tolerance at about 47 percent of the
real winding spacing.

**Cheapest fix first, and it is about thirty lines.** For patches reachable from an absolute-winding
annotation, compare the snapped target winding against the annotation-derived expectation and report
the disagreement alongside the existing satisfaction figure. That is a report-only change: it adds a
signal without altering what the metric accepts, and the propagation logic already exists in
`find_inconsistent_windings.py`.

We implemented it rather than only proposing it. The left column below is scored by
`get_patch_satisfied_areas` itself, unmodified:

| case | satisfied fraction | the check |
|---|---|---|
| correctly placed | 1.000000 | agrees |
| displaced one whole winding | 1.000000 | disagrees by +1 |
| displaced two whole windings | 1.000000 | disagrees by +2 |
| displaced 23 whole windings | 1.000000 | disagrees by +23 |
| correctly placed, 2.0 voxel scatter | 1.000000 | agrees |
| displaced one winding, 2.0 voxel scatter | 1.000000 | disagrees by +1 |

The satisfied fraction is identical across every row, spread `0.00e+00`. The check separates them
without looking at the patch's shape, because it adds nothing about the patch's geometry: the
snapped winding comes from the patch, the expected winding has to come from an annotation, and the
check is only the comparison between the two. The scatter rows matter as much as the displaced ones,
since a check that fired on noise would be unusable.

One implementation detail, because getting it wrong produces phantom reports. Reproduce the snap as
villa's own arithmetic rather than as a rounding call. Swept over 120,060 medians the two disagree
52 times, always at an exact half-winding tie, and villa's direction at a tie is decided by whether
`median % dr` lands just below or just above `dr / 2` in floating point rather than by any rule.
Measure zero on real data, but a detector that disagreed with the metric at the boundary would
report a disagreement the metric does not have.

What we cannot show is whether this is useful in practice. It has never been run against a real
annotated patch, because no fitted spiral checkpoint is published. Whether annotations reach enough
patches to make the signal worth printing is a question for someone with the fit. A stricter
version, failing such patches outright, would be a behaviour change and is not what this issue asks
for.

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
- [ ] Add the fix demonstration to the reproduction block. It runs offline with no downloads
      (`scripts/winding_disagreement_check.py`), so unlike the real-geometry table there is no
      reason for it to be unreproducible, and a maintainer is more likely to try a fix than a
      defect.
- [ ] Jon reads and approves the body verbatim

## Notes for the reviewer of this draft

Three judgement calls worth challenging:

1. **The frequency figure is gone from the body entirely**, and the revision table below now records
   six values for it across two days, ending in deletion. What remains is two sentences in Scope
   saying the blindness is not total in practice and that we have no figure we trust. A maintainer
   asking "does this ever matter" gets an honest non-answer rather than a number. If that reads as
   too thin, the alternative is to restore one sentence naming the order of magnitude, but every
   version of that sentence we have written has had to be retracted.

2. **The reproduction points at one probe**, not the whole chain. That probe covers the exact,
   surrogate-free result, which is now the only quantitative claim in the body, so the match between
   what is claimed and what is reproducible is better than in earlier drafts. The discarded
   frequency work is not reproducible from the one command, and is no longer relied on.

3. **The body is now about 1,600 words**, up from roughly 1,100, and most of the growth is the
   real-geometry table and the fix demonstration. Both earn their place, but a first contact this
   long may get skimmed, and the two things a maintainer most needs to see are the periodicity table
   and the fix. If it wants cutting, the frequency paragraph and the splicing-config paragraph are
   the two that can go without losing the argument.

4. **Nothing here mentions the mesh-splicing config's practical consequence.** It gates what enters
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
| 2026-08-27 | cut from the body | Jon's call. Two sentences survive in Scope: the blindness is not total in practice, and we have no figure we trust |
| 2026-08-26 | 24%, demoted | not a new defect: the report was restructured, and the whole scatter-model chain moved to an appendix marked unfinished. The figure stays in the text and stops being the answer to "does this matter" |
