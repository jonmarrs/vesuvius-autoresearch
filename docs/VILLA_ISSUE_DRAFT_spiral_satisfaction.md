# DRAFT (NOT POSTED) — villa issue: spiral satisfaction cannot detect a sheet switch

**Status: revised 2026-08-26 (second pass), NOT posted. HELD pending Jon's explicit approval.**
Do not post. Do not treat a later "continue" as authorization.

This supersedes the 2026-08-25 draft, which was written when the practical qualification
pointed the other way. The core claim is unchanged and has survived seven review cycles
untouched. What changed is everything around it.

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

## What changed since the last draft, and why the rewrite was needed

The last draft said nothing about how often the blindness matters in practice, because we had not
measured it. We since did, and the answer moved four times before settling. The final number
**contradicts** what an earlier version of our own report claimed. Specifically:

- the blindness holds under **both** villa configurations, and the mesh-gating one is the *more*
  permissive of the two — that strengthens the report and was not in the last draft;
- it holds across the theta=0 seam, and under warps built from real measured winding geometry;
- but under realistic patch noise the verdicts **do** diverge on a substantial minority of cases.
  The last draft implied the blindness was near-total in practice. It is not.

Including that qualification costs us the cleaner story and is the main reason to rewrite rather
than post the old text.

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

**How often this matters in practice.** The exactness above is for a patch lying on a winding. Real
patches carry surface noise, and once that noise is large enough the two verdicts do diverge. Our
estimate is that roughly **24 percent** of real patch windows carry enough scatter for the verdict to
differ. That number has moved several times as we found errors in our own chain, so it is worth
saying plainly what it rests on.

The chain is: measure the residual scatter of real traced patches, correct it for the attenuation
the estimator introduces, and compare against the scatter at which villa's verdict first flips. The
correction is the load-bearing step and it is large, roughly a factor of three, because a plane fit
over a small window absorbs much of the signal it is trying to measure. The correction depends on a
noise model, and that model is fitted to two correlation statistics of the real residual.

We tested the correction the only way available without a second ground truth, by measuring the same
windows with a second estimator that has a very different attenuation and a raw answer three times
smaller. If the correction model is right, both must agree afterwards. The result is that the noise
model we had originally published is decisively rejected, by a factor of 2.2, while the model our
data selects lands 27 percent apart rather than the 25 percent we had pre-registered as agreement,
which is inconclusive rather than confirming. So the correction is better constrained than it was,
and it is not confirmed.

Two caveats we would rather state than have found for us. When noise does cause the verdicts to
differ, that is the metric rejecting a noisy patch, not detecting a sheet switch; the blindness is
exact for clean patches, and real noise incidentally exposes a minority of displacements without the
metric ever testing for the thing that went wrong. And a reader who wants the frequency claim to be
load-bearing should treat it as the weakest part of this report. The exact result above needs none
of it.

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

1. **The frequency figure is now 24 percent and is stated with its provenance.** It has moved from
   6.8 to 30 to 24 percent as we found successive errors in our own chain, most recently a sampling
   bug that made a ten-patch statistic into a one-patch statistic. The paragraph is longer than a
   maintainer may want because it carries that history, and it says the cross-estimator test is
   inconclusive rather than confirming. The alternative is to state the exact result only and say
   nothing about frequency, which stays defensible and is cleaner.
2. **The reproduction points at one probe**, not the whole chain. The frequency discussion comes
   from a different and much longer pipeline. A reader who runs the command sees the periodicity
   result only. That is honest as written, but it means the weakest claim is the least reproducible
   one.
3. **Nothing here mentions the mesh-splicing config's practical consequence.** It gates what enters
   the output mesh, which is arguably the most concerning part, and the draft states the fact
   without drawing the inference. That restraint may be right for a first contact, or may be
   burying the lede.
