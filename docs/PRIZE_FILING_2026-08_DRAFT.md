# DRAFT (NOT FILED): August 2026 Progress Prize submission

**Status: drafted 2026-08-18, NOT filed.** Jon files it himself, via
https://docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform
(the Progress Prize form linked from https://scrollprize.org/prizes; the
`forms.gle/xoF5C3QsYutKP97x7` address used in July is stale and no longer appears on that
page). Nothing in this document has been sent, posted, or
submitted.

House style throughout: no em-dashes or en-dashes as punctuation (Jon's call, 2026-07-29).

Short per-field answers for the form live in `PRIZE_FILING_2026-08_FORM_ANSWERS.md`. This
file is the long writeup that goes into the single main field.

<!-- ============================================================================
     PASTE BOUNDARY. Everything ABOVE this line is internal metadata and must NOT
     be pasted into the form. Copy from the "Corrections to our July 2026
     submission" heading below through the end of the file.
     ============================================================================ -->

---

## Corrections to our July 2026 submission, stated first

We filed in July on 2026-07-29. Two of that submission's central claims were wrong. We found
both ourselves after filing, published the retractions, and are opening this month's entry
with them rather than leaving the record standing. There has been no separate outreach to
organisers about it; the same reviewers see this, which is where a correction belongs.

**1. Our "everything reads at chance on held-out ground truth" result was our own bug, and it
reverses.** Our registration code applied a single hardcoded surface-volume shape, belonging
to one segment, to every segment. On the held-out flagship (`20231210121321`) that scaled the
region crop wrongly and emitted a ground-truth label displaced and stretched about 1766
level-0 voxels out of place. Everything scored against it looked like chance.

Re-registered and re-scored, same segment, same models, `scrollgt score` semantics:

| model (held-out `20231210121321`) | as filed | corrected | AP-lift | exposure to this segment |
|---|---|---|---|---|
| released canon prediction | roc_auc 0.5632 | **0.7526** | 2.15 | none |
| our 1-scroll student (arm A) | 0.5626 | **0.7716** | 2.67 | **used it as its best-epoch selection set** |
| our 2-scroll student (arm B) | 0.5531 | **0.7305** | 2.34 | none |
| our 3-scroll student (arm C) | 0.5576 | **0.7462** | 2.44 | none |
| legacy detector, our near-chance reference | 0.5006 | 0.5176 | 1.01 | none |

Read the exposure column before the arm A row. Arm A is the only model above the canon
teacher here, and it is the one row whose margin is selection-optimistic, because this
segment picked its checkpoint. ScrollGT's own leaderboard marks it "selection-set only". We
do not claim a student that beats the released canon prediction; the two fully clean arms sit
at 0.7305 and 0.7462, at or just below the teacher's 0.7526.

The reference row is the legacy detector, not a constructed all-positive predictor: a true
all-positive predictor scores ROC-AUC exactly 0.5 by construction and would not move under
re-registration. This one moved from 0.5006 to 0.5176, which is what a weak model does.

The models were reading held-out ink the whole time. Our benchmark was measuring its own
misalignment. Teacher-enrichment on the same convention went 1.68 to 6.01.

**2. Our GT fine-tuning negative is retracted, because it was measured on a displaced label.**
A **second copy** of the same hardcoded constant, in a different module (`gt_register.py`),
fed that experiment's training data. On one of its training segments (`20231005123336`) the
assumed surface-volume shape was 50600x36400 against a true 34880x97280: an error of 167% in
x and the wrong aspect entirely. That model trained on badly misplaced labels, so its result
measured nothing.

**Two retractions, neither of which flattered us.** One raised our own numbers: the held-out
result went from chance to genuine held-out generalization. The other removed a negative we
can no longer test: the fine-tune claim was a claim against a lever, and retracting it
reopens that lever nominally rather than usefully, since Finding 5 shows the experiment is
now unanswerable for want of registered training data.

**Both original objections were correct.** `erdpx` closed villa PR
[#1280](https://github.com/ScrollPrize/villa/pull/1280) on 2026-08-06 saying the registration
example did not show the alignment working. We checked instead of assuming a listing-policy
rejection. The objection was right, and for a worse reason than presentation: our only visual
evidence painted registered GT opaquely over a thresholded model prediction, which is
structurally incapable of demonstrating alignment.

**Also retracted from July: the renderer's novelty claim.** We wrote that our surface renderer
makes the bucket's mesh-only segments readable "for the first time." That is false. villa
already ships `vc_obj2tifxyz` and `vc_render_tifxyz`, which cover both of our input paths and
are more capable. The honest remaining differences are that ours is pure Python with no C++
build and emits detector-format output directly. That is convenience, not capability, and it
is not offered as a headline this month.

Public record: the `#robots` correction was posted 2026-08-14 as a thread reply under our
2026-07-29 announcement, and the ScrollGT and vesuvius-autoresearch repos carry the
retractions inline at every affected passage.

Full detail and reproduction:
[registration_offset_2026-08-07.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registration_offset_2026-08-07.md)

---

**Primary submission artifacts (open-source, MIT):**
- https://github.com/jonmarrs/scrollgt : the held-out ground-truth evaluation layer, now with
  its registration gated on placement and its pixel family honestly narrowed
- https://github.com/jonmarrs/placement-check : the ten-line check that would have caught our
  own bug, published standalone so nobody else ships it
- https://github.com/jonmarrs/scroll-frames : the mesh coordinate-frame collision checker
  behind villa issue [#1522](https://github.com/ScrollPrize/villa/issues/1522)

**Methodology / source repo:** https://github.com/jonmarrs/vesuvius-autoresearch (MIT)

---

## Title

**We audited our own benchmark in public and it got more honest.**

## TL;DR (60-second version)

1. **We broke our own headline result and published the break.** A hardcoded level-0 shape
   displaced our held-out ground truth by about 1766 voxels. Fixed, the "everything reads at
   chance" finding inverts: the canon teacher reads that segment at ROC-AUC 0.753 and our
   clean students at 0.731 to 0.746, against our legacy detector, a near-chance reference, at
   0.518. A second copy of
   the same constant, found a week later, voided our GT fine-tuning negative too.
2. **Every retraction ships with the guard that prevents its recurrence.** Placement is now a
   gate rather than a diagnostic (`placement_peak`: agreement must peak at zero shift, not
   merely have a tight residual). Placement is enforced on the training path, not only on the
   evaluation path. Retirement lives in one shared module. Shipped metadata is pinned key by
   key. One command refuses to run because it would overwrite the retraction it lives under.
3. **ScrollGT's fiber family grew from six cubes to eleven, cross-scroll from one to six**,
   with a rule that aggregation across size classes raises instead of returning a mean,
   because ERL is a length statistic.
4. **Two axes measured to a ceiling rather than assumed.** The registered-pixel family is
   n=1 and the candidate pool is exhausted upstream. The column family is n=1 and a
   pre-registered attempt to add a second target came back BLOCKED, falsifying a premise of
   our own spec.
5. **Community engagement, which is new this month:** a `#robots` post on fiber-metric
   gaming, and villa issue [#1522](https://github.com/ScrollPrize/villa/issues/1522),
   reporting a catalog-wide metadata defect that costs anyone bridging between two meshes of
   one segment.
6. **Two small tools were extracted so the checks travel** rather than staying inside our
   pipeline: `placement-check` (2026-08-15) and `scroll-frames` (2026-08-18), both MIT, both
   installable standalone.

We still do not claim an independent letter-reading capability, and we still lose to
connected components on fiber tracing. Both are stated below.

## Summary

The prize rewards the best open-source submission that makes the collection easier to read.
An evaluation layer that reports the wrong number makes the collection harder to read, not
easier, and in July ours did exactly that for anyone who scored against it. This month's
work is the correction of that, done in public, plus the engineering that keeps it from
happening again.

Three things are worth pulling out of it.

**The corrections were found by us, published by us, and made our own numbers better.** We
told the community that beating ROC-AUC 0.60 on our held-out target "would be news." Several
already-published models were over that bar the whole time, ours included. We retracted that
publicly and asked anyone who had scored before 2026-08-07 to re-pull and re-score.

**Each retraction is paired with a guard in code.** The guards are enumerated below, and each
one names the specific failure it prevents. Every one of them is a test in the suite, run
locally, rather than a note in a document; the ScrollGT ones additionally run in CI on every
push.

**The pattern behind the bug was named and is now the thing being defended against.** Three
separate times, an instrument fired correctly and we attributed the failure to the data
instead of to our own code:

- the alignment gate failed at teacher-enrichment 1.68 on the held-out target. We called the
  teacher weak and built a teacher-free gate to get past it. It reads 6.01 on the fixed
  pipeline.
- a fourth region was withheld because enrichment sat near 1 for all four orientation
  candidates, which we read as a chance-quality teacher. It reads 4.88 on the fixed pipeline.
- we cited an 8-voxel correspondence residual as evidence of correct placement. A residual
  measures scatter, not position. It sat at 8 voxels while the label was 1766 voxels out.

The common shape is not carelessness about measurement. It is explaining away an instrument
that disagrees with us. The instruments were right every time.

## What is being released

### 1. ScrollGT, with its registration gated on placement (headline)

https://github.com/jonmarrs/scrollgt

The held-out human-ground-truth evaluation layer, materially changed this month:

- **Registration is gated on placement.** `register.placement_peak` scans agreement over pure
  translations on a common interior crop (never `np.roll`, whose wraparound would contaminate
  the score) and requires the peak to sit within 48 level-2 px of zero shift. The threshold is
  derived from the measured cross-scan floor, not reverse-engineered from our data, and it
  catches the bug that produced the retraction nine times over.
- **Every scorecard reports placement, not just the residual.** Each target publishes its
  **resolution limit** as a spec rather than a footnote: about 0.31 mm on the held-out target.
  Features closer together than that cannot be scored reliably, and all absolute scores are
  mild lower bounds.
- **Both `20230702185753` pixel targets are now non-scoring** and `scrollgt score` refuses
  them. Local placement error on that segment reaches roughly 1.9x the 512 micron prize
  analysis window, so within a single window a model could be scored against ground truth
  from a different part of the sheet. Their published rows are retained as a train-region
  contrast, explicitly marked a record rather than a leaderboard
  (`--allow-non-scoring` reproduces them).
- **This leaves one scoreable pixel target, not three.** That is a real reduction in what we
  offer relative to July, and we would rather state it than let the earlier framing stand.
- **The fiber family went from six cubes to eleven** and cross-scroll coverage from one cube
  to six. Details below.
- The column and fiber families are unaffected by the registration bug: different ground
  truth, no registration bridge.

### 2. placement-check (new tool)

https://github.com/jonmarrs/placement-check

The check whose absence let the bug ship, extracted so that nobody else has to learn it the
way we did. One function, numpy only, exits non-zero so it can gate a pipeline.

```
peak at (dy=31, dx=-8), offset 32.0 px; dice 0.5901 at zero, 0.6878 at peak
  agreement improves +0.0977 when shifted, which it should not for a correctly placed label
FAIL: offset 32.0 px exceeds 8 px
```

The argument it encodes in one line: **a registration is correct only if agreement peaks at
zero shift.** Our benchmark reported a median correspondence residual of 8 voxels while the
label sat 1766 voxels out. Both numbers were true. A residual measures how much individual
correspondences scatter; it says nothing about where the result ends up.

`tests/test_placement_impl_parity.py` in the methodology repo compares the published tool
against the implementation we actually run (deliberately two implementations: the published
one is numpy-only so it is trivial to adopt, ours uses the OpenCV already in our environment)
and asserts the **answers** match. If it fails, the tool we advertise is not the tool we run.

### 3. scroll-frames (new tool) and villa issue #1522

https://github.com/jonmarrs/scroll-frames

For a segment with more than one `.tifxyz`, `meta.json` gives no way to tell which scan frame
a mesh's coordinates are in. Every mesh declares the same `"scale"`, correct in each file
taken alone, while the underlying voxel sizes differ by up to 40x. The voxel size appears
nowhere in `meta.json`; it is recoverable only from the directory name.

Measured across the open bucket on 2026-08-18 (47 scroll prefixes, anonymous S3):

| | count |
|---|---|
| segments with a `mesh/` directory | 311 |
| of those, carrying more than one `.tifxyz` | 257 |
| of those, whose meshes all declare the same `scale` while voxel sizes differ | **204** |

Voxel-size spread across the 257 multi-frame segments: median 8.3x, maximum 40.33x.

Reported to villa as issue
[#1522](https://github.com/ScrollPrize/villa/issues/1522), filed 2026-08-18. It reports the
defect, credits the prior art that correctly certifies this corpus clean on a different axis
(`scroll-data-audit`, `tifxyz-repair`: every file here is internally valid; the gap is between
files), proposes the cheapest fix first, and asks for nothing.

### 4. The detector and distillation stack, carried forward

`vesuvius_autoresearch.detector` (the 2023 Grand-Prize TimeSformer recipe productionized as a
tested subpackage with a one-command `reproduce`), the community metric contract
(`detector/metrics.py`: threshold-swept F1 primary, AP-prevalence-lift as the anti-gaming
gate, ROC-AUC secondary), the SOTA open-data tooling, and the distillation pipeline whose
students are the corrected held-out rows above. Unchanged in substance this month except that
their held-out numbers are now right.

### 5. Community engagement (new this month)

July's submission scored nothing on the community-use criterion, correctly: we had published
tools and nobody had used them, and we had not put a result in front of anyone in a form they
could act on. This month:

- **`#robots`, 2026-08-18: "Coverage and precision cannot rank a fiber tracer."** A top-level
  post, deliberately titled with the falsifiable claim rather than with our project name,
  because in a channel people scan for work relevant to their own, a project name tells a
  fiber-tracing reader nothing about whether to open it. It carries the four-labelling floor
  table, the ERL size-class trap, and the fact that connected components beats our own tracer
  on every cube. Every number in it was re-verified against the shipped data on 2026-08-17
  before drafting rather than taken from notes. Verbatim record:
  [`docs/DISCORD_POSTED_robots_2026-08-18.md`](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/DISCORD_POSTED_robots_2026-08-18.md).
- **`#robots`, 2026-08-14: the correction.** Posted as a thread reply under our 2026-07-29
  announcement, telling readers that if they scored against the ScrollGT pixel targets before
  2026-08-07 their number was wrong and probably too low, and asking them to re-pull and
  re-score. That post is the reason the corrected numbers reached the people who could have
  been misled by the originals.
- **villa issue [#1522](https://github.com/ScrollPrize/villa/issues/1522), filed 2026-08-18.**
  The mesh coordinate-frame defect above. A defect report with no ask attached: no listing
  request, no link to a prize submission.

## Where each criterion is evidenced

**Released early.** Public repository dates, all MIT, all installable now:
[ScrollGT](https://github.com/jonmarrs/scrollgt) **2026-07-11**,
[placement-check](https://github.com/jonmarrs/placement-check) **2026-08-15**,
[scroll-frames](https://github.com/jonmarrs/scroll-frames) **2026-08-18**. ScrollGT has been
public for five weeks and carries its own retraction and correction history in the repo, so
what a reader sees is the record rather than a cleaned-up snapshot. The two extracted tools
are recent; scroll-frames is same-day as this filing, and we would rather say so than round it
up.

**Gets used.** This is our weakest criterion and we will not dress it up. **No external
adoption is yet demonstrated.** The `#robots` top-level post and villa issue #1522 are both
dated 2026-08-18, the same day as this filing, and neither has a response yet. They are
outbound contributions, not evidence of use. The one piece of engagement with a prior audience
is the 2026-08-14 correction reply, and its content is that our earlier published numbers were
wrong. In July we scored nothing here; this month we have put falsifiable claims and a defect
report in front of people, and whether that turns into use is not ours to assert.

**Solves a real problem.** No human ground truth is aligned to the SOTA geometry in the open
bucket, so "my model reads ink" and "my model reproduces another model" are not separable
outside the core team; ScrollGT supplies registered held-out ground truth that separates them,
and its scorecards ship the placement and resolution caveats alongside the number.
placement-check is the ten-line check whose absence produced our own retraction, extracted so
the next person bridging old labels onto re-flattened geometry does not repeat it.
scroll-frames and villa issue #1522 address a defect affecting 204 segments in the open
bucket, where `meta.json` cannot tell you which scan frame a mesh's coordinates are in.

**Well documented.** Each ScrollGT target publishes its resolution limit as a spec rather than
a footnote, and its `meta.json` records the enrichment figure that establishes a shared
coordinate frame. `baselines/BASELINES.md` carries every baseline row including our own
negatives and our withdrawn 2026-07 values. `CONTRIBUTING.md` documents the submit-a-row flow.
The reproduction commands in the block at the end of this document are the same ones we run.
Every retraction in this submission links to the report that establishes it and to the probe
that reproduces it.

## Findings

### Finding 1: the registration bug, root cause and blast radius

`repro/sota_data/register_run.py:26` held `LEVEL0_SHAPE = (50600, 36400)`, a single
module-level constant applied to every segment. It is `20230702185753`'s level-0 surface
volume shape. `20231210121321`'s is `(51000, 39980)`.

`_region_in_mesh()` maps the level-2 region into mesh coordinates through that shape, so with
the wrong constant **both the crop origin and the crop width** scale wrongly. The emitted
label is translated *and* stretched: x by +9.8%, y by +0.79%. That is why a translation-only
correction only reached Dice 0.53; a pure shift cannot undo a stretch. Undoing the mapping
analytically moves the agreement peak from (76, 435) level-2 px to (23, -9), which is zero
within noise.

Blame was arbitrated rather than assumed: the canon prediction tifs are exactly the level-0
surface volume shapes, so the teacher crop is correct and the registered GT was the misplaced
artifact.

**Why our own cross-segment sanity check could not catch it.** July's filing explicitly ruled
out a registration artifact: *"the same registration quality let the good-teacher segment
score 0.70, so the near-chance number is real."* That inference was doubly wrong. The offsets
are per-segment, so one segment scoring well says nothing about the other. And the segment
used as the reassuring reference is the one segment the bug could not affect, because the
hardcoded constant was its own geometry. It vouched for nothing.

**The second copy, found 2026-08-14.** Fixing `register_run.py` was not enough.
`gt_register.py` carried its own hardcoded `LEVEL0_SHAPE = (50600, 36400)`, applied to every
segment, and it survived the original fix because nobody grepped for other copies. It fed the
GT fine-tune's training data. Note the shape of `20231005123336`: 34880x97280 is *wide*, where
20230702185753 is *tall*. The assumed shape was not merely wrong, it was the wrong aspect.

The lesson generalises past this constant: **when a bug is caused by a hardcoded value, grep
for other copies before calling it fixed.**

### Finding 2: the guards now in code

Each guard names the failure it prevents, and each is a test rather than a note in a
document. Six of the seven live in the methodology repo and run locally with
`CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/ -q`; that repo has no CI workflow, so
"run locally" is the honest description. The seventh, `tests/test_fiber_meta_keys.py`, lives
in ScrollGT, which does run its suite in CI on every push and pull request.

| guard | the specific failure it prevents |
|---|---|
| `register.placement_peak`, enforced in every gate mode at 48 level-2 px | A label with a tight correspondence residual shipping while bodily displaced. Residual measures scatter; this measures position. It is the check that was missing, and the bug it would have caught sits 9x above its threshold. |
| Placement enforced on the **training** path (`gt_register.gt_prep_fragment`) | The evaluation path being gated while the training path was not, which is how the fine-tune came to train on displaced labels. A region whose placement cannot be checked (no teacher crop on disk) is now **dropped**, not passed; `allow_unverified_placement=True` overrides but records `placement_verified: False` so the gap stays visible downstream. |
| `repro/sota_data/retirement.py`, one stdlib-only module | Retirement existing only in the availability probe while `gt_prep_fragment`, the function that actually decides what enters training, knew nothing about it. The retired segment came back `passed: True`. A constant duplicated across two files is also the exact shape of the bug that started all of this. |
| `LEVEL0_SHAPES` with a `level0_shape(seg)` accessor that **raises** rather than guessing | Silent fallback to a default shape. Three regression tests: one greps the package for any reappearing `LEVEL0_SHAPE = (...)` literal outside its home, one pins that `gt_register` uses the shared accessor, one fails if two segments share a shape (the copy-paste signature). |
| `tests/test_fiber_meta_keys.py`, frozen key sets compared by **equality**, not `issubset` | The exporter silently deleting shipped metadata. It has done so twice: once dropping five `convention_check` fields (the empirical proof that skeleton and mask share a coordinate frame), once about to delete `mask.generated` from all eleven public targets. Both times the *presence* of a key was never asserted anywhere. An added key is a deliberate schema change and has to come here and say so. |
| `repro.sota_data.gt_finetune score` raises on entry | This command overwrites its report markdown and JSON wholesale, and the 2026-07 checkpoints are still on disk. It was one invocation away from erasing the retraction banner and the `superseded` block that are now the entire content of those two files, and re-emitting the retracted claim. Re-scoring would not rehabilitate anything either: a model fine-tuned on displaced labels yields a fresh void number. |
| `tests/test_placement_impl_parity.py` | The published tool drifting from the implementation we run. Two implementations of one check is the shape of the bug that started all of this; the difference here is that these are *allowed* to differ in code, so the test compares answers instead of source. |

Retirement is deliberately segment-level rather than region-level, because the measured problem
is segment-wide: both regions of `20230702185753` are poorly placed (46.6 px and 53.3 px) while
`20231210121321` is 3 to 4 times tighter. Retiring one region and keeping its sibling would
misrepresent it.

### Finding 3: the residual offset is a floor, not a pending bug

After the constant was fixed, a smaller placement error remained: about 32 level-2 px (roughly
130 level-0 voxels, 0.31 mm) held-out. Two candidate fixes were tested and **falsified**:

- Sampling both the 7.91 micron and 2.4 micron flattenings on a common normalised UV lattice
  (83,668 paired points) and fitting a global similarity leaves a median residual of **2137
  voxels, 4.6% of the surface's 46,474-voxel extent**. They are independent flattenings of the
  same physical surface; same-UV sampling is not a valid bridge.
- Carrying points into the old-scan frame with an unpaired 3D similarity (PCA plus trimmed ICP,
  4.03M vs 381k points) fits a plausible scale but leaves a median residual of **81 old-scan
  voxels**, against the existing obj bridge's **7.95**. Routing through it would be worse than
  what we have.

The residual is broad rather than bimodal (5% / 50% / 99% quantiles: 7.4 / 64.4 / 452.5
old-scan voxels; only 32% of points within 25 voxels), which is what genuinely different
surfaces look like, not a fixable extent mismatch. The 2023 and 2026 segmentations of this
sheet are materially different surfaces.

So it is published as **each target's resolution limit** rather than carried as an open bug.
The offset field is also **non-rigid**: measured per 768 px tile, `20230702185753` has
sd 26.8 (dy) / 33.0 (dx) with the worst tile near 102 px, and a fitted plane leaves residual
scatter essentially equal to the raw scatter. A single global placement figure is therefore
optimistic, and per-target scatter is now published alongside the global peak.

The honest tension is worth naming: relaxing a gate because our data fails it is exactly the
move that produced the July retraction. What makes this different is that the floor was
measured independently, before the threshold was picked, and the threshold was **not** raised
to accommodate the target that clears it by only 1.4 px. A test fails if that margin is
eroded.

### Finding 4: fiber targets, six cubes to eleven, and a size-class rule

The fiber connectivity family expanded from six cubes to **eleven**: eight at 256 cubed and
three at 512 cubed, tolerance 2.0 voxels, every row scored against the identical `fiber_hz_vt`
mask shipped with each target. Cross-scroll coverage went from **one cube to six**. No cube in
the expansion failed to export; all eleven ship ground truth, a reference mask, and
oracle/floor scores.

Each target's `meta.json` records how many times more often a ground-truth skeleton node lands
on the scoring mask than chance density predicts, which is what establishes a shared
coordinate frame. Across the original six that sat at 13.6x to 16.4x; across all eleven it
spans **9.9x to 21.5x**. Wider, but every target still many times chance, so the expansion did
not introduce one with a silently broken registration.

**ERL does not compare across cube sizes, and is never averaged across them.** ERL is expected
run length in voxels: a 512 cubed cube admits fibers up to twice as long per axis, so its ERL
runs roughly double for purely geometric reasons. The measured oracles make this unambiguous:

| size class | oracle ERL range |
|---|---|
| 256 cubed (n=8) | 222.06 to 261.63 |
| 512 cubed (n=3) | 497.52 to 513.32 |

`aggregate_fiber_scores` **raises** on a mixed size-class input rather than silently producing
a misleading mean, and the published tables are split the same way, each with its own oracle
row so the ceiling sits beside the scores.

**What that costs the cross-scroll axis, stated plainly.** Six cross-scroll cubes are not six
comparable cross-scroll points. Per class the split is 5 primary plus 3 cross-scroll at 256
cubed, and **0 primary plus 3 cross-scroll at 512 cubed**. Since scores are never compared
across classes, the three 512 cubed cross-scroll cubes have no same-scroll counterpart in their
own class to transfer from. The usable same-versus-cross comparison is n=3 against n=5, inside
the 256 cubed class only. Closing that needs 512 cubed Scroll-1 cubes, which the villa dataset
does not currently offer.

**What the floors establish, and why both metrics are required.** On
`s1_00497_01497_03997`, four completely different labellings score identical coverage (0.9177)
and identical precision (0.2194), because both are properties of the shared fiber mask rather
than of the instance labelling:

| labelling | ERL | ERLpen | coverage | precision |
|---|---|---|---|---|
| oracle (disclosed) | 258.27 | 239.46 | 1.0000 | 1.0000 |
| one instance for everything | 199.18 | **0.00** | 0.9177 | 0.2194 |
| connected components | 197.11 | 37.13 | 0.9177 | 0.2194 |
| one instance per voxel | 0.94 | 0.94 | 0.9177 | 0.2194 |
| 50 random instances | 0.98 | **0.00** | 0.9177 | 0.2194 |

A benchmark reporting coverage and precision alone cannot distinguish a correct tracer from
`numpy.random`. Raw ERL alone is gameable too: labelling everything once scores 199.18 against
an oracle's 258.27, within 23%, while its merge-penalized ERL is exactly 0.00. So both ERL and
the merge count are required, and `scrollgt score-fibers` never prints one without the other.
ScrollGT's `tests/test_fiber_gaming.py` pins this, and it runs in CI on every push.

**Our own tracer loses to connected components on both metrics, on every cube it has been
scored against.** The tracer finds the fibers (coverage 0.605 to 0.704 of ground-truth length
is claimed by something) but cannot hold one identity along them, so its runs are short and ERL
is low. An earlier reading that the tracer was marginally ahead on the penalized metric came
from a 128 cubed sub-volume and does not survive at full-cube scale; it should not be cited.

### Finding 5: two ceilings, measured rather than assumed

**The registered-pixel family is n=1 and the pool is exhausted upstream.** Surveyed
2026-08-15 with a committed, re-runnable probe. Six Scroll-1 segments carry a 2023 hand ink
label:

| segment | hand label | in open data | placement | usable |
|---|---|---|---|---|
| `20230702185753` y4000_x2500 | yes | yes | 46.6 px | no, retired non-scoring |
| `20230702185753` y7000_x4000 | yes | yes | 53.3 px | no, fails the 48 px gate |
| `20231005123336` y4000_x2500 | yes | yes | 57.5 px (+/-1 px) | no, fails the gate |
| `20231005123336` y7000_x4000 | yes | yes | drops at prep | no, periodicity 0.556, ink 0.0005 |
| `20231210121321` y4000_x2500 | yes | yes | 32.0 px | **passes, spent as held-out eval** |
| `20230820203112` | yes | **no** | n/a | no SOTA geometry exists |
| `20230826170124` | yes | **no** | n/a | no SOTA geometry exists |
| `20230903193206` | yes | **no** | n/a | no SOTA geometry exists |

Two blockers bind independently. Registration quality accounts for two segments and is the
cross-scan floor above, closed as irreducible. Data availability accounts for three more,
which are absent from the open data entirely: there is nothing to place a label onto. **A
perfect registration would not unblock this**, and neither would compute. One segment cannot
be both the training set and the held-out test.

The consequence for users is stated in ScrollGT's README rather than buried: a single-target
pixel family cannot separate model quality from segment idiosyncrasy. Any score is a score on
one sheet. The README previously said `20231210121321` was "currently" the only target we
would stand behind, which implies the family grows with more effort on our side. It does not;
that word has been dropped.

Two unblock paths exist, both upstream and both necessary rather than sufficient: re-flatten
one of the three labelled-but-absent segments, or hand-label one of the eight published
2023-era segments that carry no label (all eight confirmed on 2026-08-15 to resolve
`surface-volumes/`). A fresh segment still has to place well enough to score.

**The consequence for the GT fine-tune experiment is that it is unanswerable as posed, not
that it failed.** That distinction matters. Replacing a false negative with a stronger
negative pointing the same direction would repeat the original error with more confidence. The
honest replacement is narrower: the experiment cannot be run, and here is precisely which
resource is missing. Its original premise is void independently, since it quoted arm C at
ROC-AUC 0.558 as the bar to beat, and that figure now reads about 0.746.

**The column family is n=1, and a pre-registered attempt to add a second target came back
BLOCKED, falsifying a premise of our own spec.** On 2026-08-17 we attempted to transfer the
published PHerc 1667 22-column reading onto a second flattening (`w011_flatboi`) of what our
spec described as the same material. Result: **0 of 22 columns clear all four gates**, against
a pre-registered floor of 5. The stop condition fired, no target shipped, and no ScrollGT files
were touched.

The interesting part is why. Our spec's premise was wrong: `merged_v4`, the existing target's
flattening, is a whole-scroll merge across multiple windings, while `w011_flatboi` is **one
winding** inside that merge. They do not cover the same material. Both segment names contain
the substring `w011`, which is what made them look like one winding differently flattened.

The measurement that establishes it, independent of that inference:

- Every one of the 22 columns' mapped `dst_gx0` is exactly 5, and every `dst_gx1` falls in a
  narrow 590 to 661 range, regardless of which source column produced it. Twenty-two source
  boxes spanning 30097 grid px all land in the same ~650 px window of the destination.
- Median 3D correspondence residual runs 185.4 / 2203.8 / 2990.7 voxels (min / median / max),
  falling near-monotonically from column 1 to column 22 exactly as the scroll's spiral geometry
  predicts. The best column, at 185.4 voxels (about 0.44 mm), is roughly **23x** this project's
  own accepted correspondence quality of 7.95 voxels. It is the least-bad case, not a plausible
  pass.
- The teacher-free periodicity gate computed for all 22 columns (0.026 to 0.245 against a
  `> 0.5` gate) and failed everywhere. We flag explicitly that this null carries less weight
  than the other two, because that function was designed for near-binary ink masks and is being
  applied here to raw CT grayscale, where its `> 127` binarization has no relationship to ink.
  Corroborating, not decisive on its own.

The report also records that `coverage: 1.000` for every column was a construction artifact of
running with `max_residual=None` as the plan specified, so the coverage floor did not
discriminate anything in this run, and says so rather than presenting it as a passed gate. And
it names the two-second check (read both meshes' `meta.json` bounding boxes) that would have
reached the same answer before the run.

## Honest limitations (stated plainly)

- **We caught our own escalation gate contradicting itself, and the version that governs is
  not cleared.** Our strategy document carried two gates for the capped First-Letters swing.
  The older one read "held-out ROC > 0.65 or clearly legible letterforms." The governing one,
  re-derived on 2026-08-16 after the correction, is to beat the canon teacher (0.7526) on the
  held-out target by more than the selection caveat. **On the corrected numbers the two gave
  opposite answers, and they sat side by side saying opposite things until 2026-08-18, when we
  found it and reconciled it** (commit `4e722eea`): arms B and C at 0.7305 and 0.7462 clear
  the old gate and do not clear the governing one. The second gate had been added without
  grepping for the first, which is the same enumeration failure described in Finding 1. A
  strategy document that answers "escalate?" both ways is worse than either answer, so the
  older bullet is now marked superseded rather than deleted. The old gate was also never
  testable on its own terms: it was written for rendered Scroll-3 data, and Scroll 3 ships no
  human ground truth, so no ROC can be computed there at all. On the Scroll-1 substitute the
  pixel family is n=1, so one number cannot separate model quality from one sheet's
  idiosyncrasy, and the only model above the teacher there (arm A, 0.7716 vs 0.7526) used that
  segment as its best-epoch selection set, so its margin is selection-optimistic. **The swing
  stays capped.**
- **We do not claim an independent letter-reading capability.** The corrected held-out numbers
  show genuine generalization, and they show our students landing at or just below the teacher
  they were distilled from. That is faithful distillation of a teacher that reads, not evidence
  of a model that reads better. On PHerc 1667 columns, our own arm C and legacy detector sit at
  the noise floor (0.575 and 0.592 against a noise realization of 0.585) and both maps are
  texture without letterforms.
- **Our fiber tracer loses to connected components on every cube it has been scored against**,
  on raw ERL and on merge-penalized ERL. The tracer rows exist for six of the eleven cubes; the
  five added by this expansion ship ground truth, mask and oracle/floor scores, and their
  tracer columns are marked with a dash rather than guessed at.
- **Placement verification is relative, not absolute.** `placement_peak` measures where
  agreement between a registered label and a model prediction is maximised. It localises
  disagreement between two artifacts rather than establishing truth about where the ink is.
  This is a caveat on every placement figure we publish, the 32.0 px pass as much as the 57.5
  px failure, and it is not a reason to discount any one inconvenient number.
- **The pixel targets' resolution limit is about 0.31 mm held-out**, and all absolute scores
  are mild lower bounds. Features closer together than that cannot be scored reliably.
- **The column family's single target is not an independence test.** It rests on the
  eight-papyrologist consensus reading (Angelotti et al., CC BY-NC 4.0), and its scoring
  contract measures consistency with that reading, never letter accuracy. The geometry oracle
  row (1.0000) is trivially reachable by reading the public `columns.json`, which is why column
  scores are necessary rather than sufficient evidence and every submitted row must include its
  prediction map.
- **Our own published numbers still need checking.** On 2026-08-18, preparing villa issue
  #1522, we re-verified `scroll-frames`'s README against the live bucket and one of its four
  figures did not reproduce: a claimed median frame spread of 7x, stated with no denominator,
  is 8.29x across the 257 multi-frame segments. It was corrected before the issue linked to it,
  and the correction says the earlier number did not reproduce rather than quietly swapping it.
  Also corrected this month: a placement figure of 55.1 px published in our own 08-07 report
  was a hand-run measurement no committed path reproduced; re-run from committed code it is
  57.5 px, determined to about +/-1 px, and should not be quoted to three significant figures.
  Neither correction changes a conclusion. Both are recorded because the alternative is a
  record that keeps asserting something we no longer believe.
- **Retractions are preserved, not deleted.** `gt_finetune_heldout.md` keeps its original text
  under a retraction banner; its JSON companions carry machine-readable `superseded` blocks;
  the commands that would regenerate them refuse to run. The point is that no record keeps
  *asserting* the retracted claim, not that the claim disappears from history.

## Reproducibility

Public repos, MIT-licensed. The data path uses only the open bucket (anonymous S3, partial
OME-Zarr reads: no credentials, and no special hardware beyond one 24 GB GPU for training;
ScrollGT scoring itself is CPU-only).

```bash
# ScrollGT: score a prediction against registered ground truth (CPU, seconds)
git clone https://github.com/jonmarrs/scrollgt && cd scrollgt && pip install -e .
scrollgt score pred.png data/scroll1_20231210121321 --json-out card.json
scrollgt score-fibers labels.npy data/fibers_s1_00497_01497_03997_256 --json-out card.json
scrollgt check --window-px 64 --scan-um 8.0

# placement-check: does this label actually sit where it claims to?
python placement_check.py my_label.png reference.png --max-offset 8

# scroll-frames: are these two meshes' coordinates comparable?
scrollframes list PHercParis4/20230702185753

# methodology repo: the registration bug, reproduced end to end
uv run python scripts/probe_registration_offset.py
uv run python scripts/probe_placement_field.py
uv run python scripts/probe_labeled_segment_availability.py

# unit tests, CPU, including every guard above
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/ -q
```

## Links

- **ScrollGT:** https://github.com/jonmarrs/scrollgt
- **placement-check:** https://github.com/jonmarrs/placement-check
- **scroll-frames:** https://github.com/jonmarrs/scroll-frames
- Methodology repo: https://github.com/jonmarrs/vesuvius-autoresearch
- The registration bug, found, fixed and reversed:
  https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registration_offset_2026-08-07.md
- Registered-GT training data is exhausted on Scroll-1:
  https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/gt_training_data_exhaustion_2026-08-15.md
- The 1667 column transfer, BLOCKED:
  https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/w011_column_transfer.md
- Corrected baselines, all families:
  https://github.com/jonmarrs/scrollgt/blob/main/baselines/BASELINES.md
- villa issue #1522 (mesh scale metadata does not distinguish frames):
  https://github.com/ScrollPrize/villa/issues/1522
- Findings: https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/FINDINGS.md
- Lab notebook: https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/LAB_NOTEBOOK.md
- wandb: https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch
