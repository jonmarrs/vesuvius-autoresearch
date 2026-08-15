# Correction to the July 2026 Progress Prize submission

**Status: PARTIALLY SENT.**

- **Section B (`#robots`): POSTED 2026-08-14** as a thread reply under the 2026-07-29
  announcement. Verbatim record: `DISCORD_POSTED_robots_2026-08-14_CORRECTION.md`. Posted
  as a reply rather than an edit, because the original was already near Discord's
  2000-character limit; the trimmed reply came to 1931 characters.
- **Section A (form / organiser): WILL NOT BE SENT.** Decided by Jon, 2026-08-14: the July
  review window closed on 07-31 and the judges are most likely done, so a separate email
  would not reach a live decision and risks reading as angling for reconsideration.
  Deliberate call, not an oversight.

  Residual exposure, for the record: of the two retracted claims, the held-out result
  *understated* our models, so leaving it uncorrected costs us rather than flatters us. The
  renderer's "for the first time" novelty claim is the one that runs the other way, and it
  remains in the official record unchallenged.

  **If an August submission is filed, open it with a short corrections note covering both.**
  Same reviewers, no separate outreach, reads as diligence. If nothing is filed, this lapses
  and the public record (repos + `#robots`) stands corrected regardless.

  The identified channel, should it ever be needed, is `team@scrollprize.org` (the FAQ
  designates it for reaching organisers about progress and submissions). NOT
  `grandprize@scrollprize.org`, which is the Grand Prize / First Letters submission intake,
  and not the Google Form, whose July window is closed and which would read a correction as
  a new entry.

**Updated 2026-08-14** to describe the final state. The first draft was written on 08-07,
before a second copy of the same bug was found, before the third pixel target was measured,
and before both `20230702185753` targets were retired. Sending the earlier version would
have required a follow-up correction to the correction.

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
ROC-AUC 0.60 on the held-out target "would be news," when several already published models
were over that bar the whole time.

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
> read at chance." The first is still fair. The second is false: the models were reading
> held-out ink the whole time and our benchmark was measuring its own misalignment. We would
> not claim more than that, since the students land at or just below the teacher's 0.753, so
> this is faithful distillation of a teacher that reads, not evidence of beating it.
>
> The GT fine-tuning negative in the filing is also retracted. A **second copy** of the same
> hardcoded constant, in a different module, fed its training data. On one of its training
> segments (20231005123336) the assumed surface-volume shape was 50600x36400 against a true
> 34880x97280, a 167% error in x and the wrong aspect entirely. That model trained on
> badly misplaced labels, so its result measured nothing.
>
> Worth stating plainly, since the filing leaned on measurement discipline: **three separate
> times, an instrument told us something was wrong and we attributed it to the data instead
> of our code.**
>
> - the alignment gate failed at teacher-enrichment 1.68 on the held-out segment. We called
>   the teacher weak and built a teacher-free gate to get past it. It scores 6.01 on the
>   fixed pipeline.
> - a fourth region was withheld from the benchmark because enrichment sat near 1 for all
>   four orientation candidates, which we read as a chance-quality teacher. It scores 4.88
>   on the fixed pipeline. The teacher was fine; our registration was broken.
> - we cited an 8-voxel correspondence residual as evidence of correct placement. A residual
>   measures scatter, not position. It sat at 8 voxels while the label was 1766 voxels out.
>
> **2. The renderer's novelty claim is unsupported.** We wrote that our surface renderer
> makes the bucket's mesh-only segments readable "for the first time." That is false. villa
> already ships `vc_obj2tifxyz` and `vc_render_tifxyz`, which cover both of our input paths
> and are more capable (remote zarr streaming, multi-VM parts, pyramid generation). The
> honest remaining differences are that ours is pure Python with no C++ build and emits
> detector-format output directly. That is convenience, not capability.
>
> **What changed as a result.**
>
> - Registration is now gated on **placement** directly: a label is rejected unless its
>   agreement with the reference peaks at zero shift. Nothing tested that before, which is
>   how the error shipped.
> - The level-0 shapes now live in one place, with an accessor that raises rather than
>   guessing, and a test that fails if a hardcoded copy reappears anywhere in the package.
> - Each target publishes its **resolution limit** rather than burying it. On the held-out
>   target that is about 0.31 mm.
> - **Both 20230702185753 pixel targets have been retired as non-scoring.** Local placement
>   error there reaches about 1.9x the 512 micron prize analysis window, so within one window
>   a model could be scored against ground truth from a different part of the sheet. The
>   scorer refuses them. Their published rows are kept as a train-region contrast, clearly
>   marked as a record rather than a leaderboard.
>
> **This leaves ScrollGT with one scoreable pixel target, not three.** That is a real
> reduction in what the submission offers, and we would rather state it than let the earlier
> framing stand. The column-level and fiber-connectivity target families are unaffected:
> they use different ground truth and no registration bridge.
>
> Full detail, reproduction steps, and the corrected leaderboard:
> https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registration_offset_2026-08-07.md
>
> Both original objections were surfaced by erdpx closing villa PR #1280 on 2026-08-06. We
> checked them instead of assuming a listing-policy rejection, and both were correct.
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
> So the 0.60 bar was not a challenge. Published models were already well past it and our
> benchmark was measuring its own misalignment. **If you scored against the ScrollGT pixel
> targets before 2026-08-07, your number was wrong and probably too low. Please re-pull and
> re-score.**
>
> Two further changes worth knowing before you do:
>
> - Registration is now gated on **placement**, meaning agreement has to peak at zero shift.
>   The old gate checked correspondence residual, which measures scatter and never
>   constrained position: ours read 8 voxels while the label was 1766 voxels out. If you
>   build registered ground truth, this check is about ten lines and we would suggest adding
>   it.
> - **Both 20230702185753 pixel targets are now non-scoring** and the scorer refuses them.
>   Local placement error there is about 1.9x the 512 micron analysis window, so a score
>   there can be against a different part of the sheet. That leaves one scoreable pixel
>   target, 20231210121321. Column and fiber targets are unaffected.
>
> ──── MODEL OUTPUT ENDS ────

### Message 2 (Jon's own words, not drafted here)

Left deliberately blank. Suggested substance, in your words rather than mine:

- that you chose to publish the retraction rather than quietly re-run;
- that erdpx's review on villa PR #1280 is what prompted the check, and it was correct;
- anything you want to say about the placement gate, which is the reusable part.

---

## C. Current state, if asked

| | |
|---|---|
| scoreable pixel targets | **1** (`20231210121321`, 0.31 mm resolution limit) |
| retired as non-scoring | both `20230702185753` regions (local error ~1.9 analysis windows) |
| withheld | `20231005123336` (placement 55.1 px, over the 48 px gate) |
| unaffected | PHerc 1667 column targets, all six fiber targets |
| GT fine-tune | retired, cannot be retrained: all four training regions fail or drop |

## D. Settled, no longer blocking

The earlier draft asked whether to withhold the marginal targets before sending. **Decided
2026-08-14: both `20230702185753` targets are non-scoring**, implemented behind a
`scoring.enabled` flag with the scorer refusing them. This draft describes that final state,
so it can go out without needing a follow-up.

Nothing else is outstanding. The remaining judgement is Jon's: whether to send, and whether
both channels or only `#robots`.
