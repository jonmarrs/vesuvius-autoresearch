# DRAFT (NOT POSTED) — villa issue: spiral satisfaction cannot detect a sheet switch

**Status: revised 2026-08-26 (third pass), NOT posted. HELD pending Jon's explicit approval.**
Do not post. Do not treat a later "continue" as authorization.

This supersedes the 2026-08-25 draft and both earlier passes of 2026-08-26. The core claim is
unchanged and has now survived about ten review cycles untouched. Everything around it has moved
again, and this pass **removes the frequency number entirely** rather than publishing a fourth
value for it.

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

## What changed since the last pass, and why the frequency number is gone

Everything structural is unchanged and is what the issue actually reports:

- the blindness holds under **both** villa configurations, and the mesh-gating one is the *more*
  permissive of the two;
- it holds across the theta = 0 seam, and under warps built from real measured winding geometry;
- under realistic patch noise the verdicts **do** diverge on some fraction of cases, so the
  blindness is not total in practice.

What changed is that we stopped claiming to know that fraction. It has moved 6.8 → 30 → 24 percent
across three revisions, each caused by a defect we found in our own chain, and the latest check says
the remaining estimate is biased high by an unknown amount: when we inject a perturbation shaped
like a real patch residual rather than the fitted noise model, roughly three quarters of test cases
never diverge the verdict at **any** amplitude, while the fitted model diverges 2.3 times as many.
The framework that produces the 24 percent assumes a divergence threshold exists; for realistically
shaped noise it usually does not, so the framework cannot be transported and cannot be repaired into
a corrected figure.

Publishing a fourth number, knowing it is biased and not knowing by how much, would be worse than
saying that plainly. So the body now states the structure of the practical question and says we
cannot put a defensible figure on it. That costs us the tidiest answer to "does this ever matter",
and it is the honest state of our evidence.

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

**How often this matters in practice, and why we are not giving a number.** The exactness above is
for a patch lying on a winding. Real patches carry surface noise, and once that noise is large enough
the two verdicts do diverge, so the blindness is not total in practice. We tried repeatedly to
quantify how often and we are not able to.

The approach was: measure the residual scatter of real traced patches, correct it for the attenuation
the estimator introduces, and compare against the scatter at which villa's verdict first flips. Three
things went wrong with it, and the third is not fixable by more care.

The correction is the load-bearing step and it is large, roughly a factor of three, because a plane
fit over a small window absorbs much of the signal it is measuring. It depends on a noise model
fitted to correlation statistics of the real residual, and our first published version of that
statistic came from a single patch rather than from all of them, which moved the answer. Correcting
that was straightforward. Testing the correction with a second estimator of very different
attenuation was informative but only partly: it decisively rejects the noise model we had originally
published, and it neither confirms nor rejects the one our data selects.

The part that is not repairable is this. When we inject a perturbation shaped like an actual patch
residual, instead of the fitted noise model, roughly three quarters of our test cases never diverge
the two verdicts at any amplitude we can apply, and extending the amplitude range thirty-fold changes
that not at all. The fitted model diverges the verdict on 2.3 times as many cases. The whole
framework presumes that a divergence threshold exists and asks how often real noise reaches it; for
realistically shaped noise there is usually no such threshold. So our remaining estimate is biased
high by an amount we cannot determine, and we would rather say that than publish it.

What we can say without any of that machinery: the blindness is **exact** for a patch lying on a
winding, real noise incidentally exposes some minority of displacements, and in those cases the
metric is rejecting a noisy patch rather than detecting a sheet switch. It never tests for the thing
that went wrong. The rest of this report needs no noise model at all.

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
- [ ] Jon reads and approves the body verbatim

## Notes for the reviewer of this draft

Three judgement calls worth challenging:

1. **The frequency number is gone rather than revised a fourth time.** The alternative is to publish
   ~24 percent with the caveat that it is biased high by an unknown amount. That would answer a
   maintainer's likely first question, "does this ever matter", with something concrete. It is out
   because a number we know to be biased, in the direction that makes our finding look more
   important, is exactly the kind of claim this project has had to retract repeatedly. The cost is
   real: the issue is less quotable without it.

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
| 2026-08-26 | dropped | real-residual-shaped noise usually produces no divergence threshold at all |
