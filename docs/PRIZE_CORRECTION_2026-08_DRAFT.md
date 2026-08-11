# Correction to the July 2026 Progress Prize submission

**Status: DRAFT, NOT SENT.** Awaiting Jon's review and explicit go-ahead.

**Why a correction is owed.** The July filing (submitted 2026-07-29 via
https://forms.gle/xoF5C3QsYutKP97x7) built its headline on a result that was wrong, and the
`#robots` announcement of 2026-07-29 repeated it publicly. The cause was our own bug. The
corrected result is better than the one filed, not worse, but the filed evidence was false
and the public post is still telling people something untrue about their own models.

**House style (Jon's call, 2026-07-29):** no em-dashes or en-dashes as punctuation. Both
drafts below follow it.

**Two channels, because the error went out on both:**

1. the submission form, which is the official record;
2. `#robots`, which is public and where people may have acted on the wrong number.

Of the two, the Discord correction is the more urgent: the post tells readers that beating
ROC-AUC 0.60 on the held-out target "would be news," when in fact several already published
models were over that bar the whole time.

---

## A. Form / organiser correction

> **Correction to our July 2026 Progress Prize submission (ScrollGT + surface renderer),
> submitted 2026-07-29.**
>
> Two central claims in that submission were wrong. We found both after filing, published
> the retraction ourselves, and are reporting them here rather than leaving the record
> standing.
>
> **1. The held-out "everything reads at chance" result was our own bug, and it reverses.**
>
> Our registration code applied a single hardcoded surface-volume shape, belonging to one
> segment, to every segment. On the held-out flagship (20231210121321) that scaled the
> region crop wrongly and emitted a ground-truth label displaced and stretched about 1766
> voxels out of place. Everything scored against it looked like chance.
>
> Re-registered and re-scored, same segment, same models:
>
> | model (clean held-out) | as filed | corrected |
> |---|---|---|
> | released canon prediction | ROC-AUC 0.563 | **0.753** |
> | our 2-scroll distilled student | 0.553 | **0.731** |
> | our 3-scroll distilled student | 0.558 | **0.746** |
> | all-positive floor | 0.501 | 0.518 |
>
> AP-prevalence-lift moves from about 1.15 (chance) to 2.15 through 2.44. Our filing said
> "we do not have a strong ink detector" and "on held-out human ground truth our own models
> read at chance." The first is still fair; the second is false. The models were reading
> held-out ink the whole time and our benchmark was measuring its own misalignment.
>
> The GT fine-tuning negative result in the filing is also retracted: it was fine-tuning on
> the displaced label, so it measured nothing.
>
> Worth stating plainly, since the filing leaned on measurement discipline: our own
> alignment gate caught this and we overrode it. The gate failed at teacher-enrichment 1.68,
> we attributed that to a weak teacher, and we built a teacher-free gate to get past it. On
> the fixed pipeline the same check scores 6.01. The gate was right and we explained away a
> true positive. We also cited an 8-voxel correspondence residual as evidence of correct
> placement; a residual measures scatter, not position, and it sat at 8 voxels while the
> label was 1766 voxels out.
>
> **2. The renderer's novelty claim is unsupported.** We wrote that our surface renderer
> makes the bucket's mesh-only segments readable "for the first time." That is false. villa
> already ships `vc_obj2tifxyz` and `vc_render_tifxyz`, which cover both of our input paths
> and are more capable (remote zarr streaming, multi-VM parts, pyramid generation). The
> honest remaining differences are that ours is pure Python with no C++ build and emits
> detector-format output directly. That is convenience, not capability.
>
> **What changed as a result.** The pipeline now gates on placement directly: a registration
> is rejected unless label-versus-prediction agreement peaks at zero shift. Nothing tested
> that before, which is how the error shipped. We also publish each target's resolution
> limit, about 0.31 mm on the held-out target, since a residual placement uncertainty
> remains that is irreducible for this method (the 2023 and 2026 segmentations of the same
> sheet are materially different surfaces).
>
> Full detail, reproduction steps, and the corrected leaderboard:
> https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registration_offset_2026-08-07.md
>
> Both objections were surfaced by erdpx closing villa PR #1280 on 2026-08-06. We checked
> the objections instead of assuming a listing-policy rejection, and both were correct.
>
> Jon Marrs, jdmarrs@gmail.com

---

## B. `#robots` correction post

Uses the two-message template: the model output boundary is marked explicitly, and message 2
is left for Jon's own words (this satisfies the "separate model output from human commentary"
rule that the July post only satisfied implicitly).

### Message 1

> *AI disclosure: Claude Opus 5.*
>
> **Correction to our ScrollGT post of 2026-07-29.** Two claims in it were wrong, and one of
> them was about your models, not just ours.
>
> That post said our distilled models "drop from 0.79+ on train-exposed regions to ~0.55
> held-out," and that beating ROC-AUC 0.60 on the held-out target "would be news." Both were
> artifacts of a bug in our own registration code, which applied one segment's hardcoded
> surface-volume shape to every segment and left the held-out ground truth about 1766 voxels
> out of place.
>
> Corrected, same segment, same models:
>
> ```
> released canon prediction   0.563 -> 0.753 ROC-AUC   (lift 1.15 -> 2.15)
> our 2-scroll student        0.553 -> 0.731           (lift 1.16 -> 2.34)
> our 3-scroll student        0.558 -> 0.746           (lift 1.17 -> 2.44)
> all-positive floor          0.501 -> 0.518
> ```
>
> So the 0.60 bar was not a challenge; published models were already well past it and our
> benchmark was measuring its own misalignment. If you scored against the ScrollGT pixel
> targets before 2026-08-07, your number was wrong and probably too low. Please re-pull and
> re-score.
>
> ──── MODEL OUTPUT ENDS ────

### Message 2 (Jon's own words, not drafted here)

Left deliberately blank. Suggested substance, in your words rather than mine:

- that you are the one who chose to publish the retraction rather than quietly re-run;
- that erdpx's review on villa PR #1280 is what prompted the check, and it was correct;
- anything you want to say about how the benchmark now gates placement.

---

## C. What is now different, if asked

- **Placement gate.** `register.placement_peak` is enforced in every gate mode: agreement
  must peak at zero shift. Threshold 48 level-2 px, derived from a measured floor and about
  9x below the 435 px bug it exists to catch. A regression test fails if that margin erodes.
- **Published resolution limits.** 0.31 mm on the held-out target, 0.45 mm global on the
  train-exposed one, with per-tile scatter published too because the global figure is
  optimistic (worst tile about 0.96 mm).
- **Retracted, not re-scored:** the GT fine-tune row, which was trained on the displaced
  label and needs retraining before it can be scored at all.

## D. Open question for Jon before sending

The train-exposed target carries about 1 mm local placement error. We already withheld a
fourth region for a weaker reason (unverifiable orientation). If we are going to withhold
it, that should happen **before** this correction goes out, so the correction describes the
final state rather than needing a follow-up.
