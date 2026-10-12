# Reply to ScrollPrize/villa#1934 (AFV generator): DRAFT, NOT POSTED. Needs the user's approval of this text.

Target: comment on #1934 (@Qualzz, open), the PR that finding 85 measured. It is a reply, not a new thread, so the weekly
new-item slot is not used. The user's decision (2026-10-11): share finding 85 here only after ScrollGT's ERL fix landed
(v0.7.0, tagged 2026-10-12), and only with text the user approves. No AI sign-off.

**Why it passes the substance test.** The PR's author note says: "I don't know yet how useful this will by just
guessing." This answers that with a measurement against hand-traced fibers, which nobody else has posted on the PR.

## Pre-post checks (redo on the day)

* PR head is still `2d8577ed` (checked 2026-10-12). If it moved, say which commit was measured. Do not re-run silently.
* No human comments on #1934 yet (only the vercel bot, checked 2026-10-12). Re-read the thread first.
* Reply rate: at most 1 villa reply per day. Check nothing else has gone out that day.
* #1934 was last updated 2026-10-01, so villa's 14-day inactivity bot may close it around 2026-10-15. A comment resets
  that clock. That side effect is neutral, but the user should know about it. If the bot has already closed it, do
  not post.
* Every number below is bound by `tests/test_villa_draft_1934_numbers.py` to `reports/afv_generator_entrant.json`
  and `reports/fiber_miss_diagnostic.json`.
* Optional: strike the ScrollGT paragraph if it reads as promotion. It is there because a pre-0.7.0 ERL comparison
  would mislead anyone tuning this PR's length filter.

---

You wrote that you don't know yet how useful this is without guessing, so here is one measurement against hand-traced fibers.

I ran this PR at `2d8577ed` with `Qualzz20/afv_fiber_9um` at `e189af75`, every default (threshold 60%, 512 blocks, 100-voxel minimum length, black distance 16, 45° joins, no `--extend`), on the 21 hand-traced cubes in villa's `fiber-skeletons` datasets: 5 from Scroll 1, 8 from Scroll 3 and 8 from Scroll 5, at 7.91 µm. All 21 ran without a failure. Coverage, the share of hand-traced fiber length within 2 voxels of a generated fiber:

- **0.19–0.38 on 19 cubes.**
- **0.04 and 0.08 on two Scroll 5 cubes from Dataset004** (`s5_13497_01497_02497` and `s5_16997_03997_04497`: 10 and 27 fibers, against 166 and 282 hand-traced). On those two, `fiber_hz_vt`, the model yours was fine-tuned from, has no voxel at P ≥ 0.05 within 2 voxels of 20% and 25% of the fiber. I did not run the same check on your model.

Caveats:

- 7.91 µm is finer than the 8.64 and 9.362 µm pitches your model card lists. I did not test resampling.
- `fiber_hz_vt` trained on 11 of these cubes, so on those the base model has seen the data.
- Defaults only. The 60% threshold and the 100-voxel minimum length both trade coverage away, so they are what I would vary first. I did not test `--extend`.

If you score it with ScrollGT, use 0.7.0 or later. Earlier versions averaged ERL over the covered fiber only, so dropping short chains, which the minimum-length filter does, raised the score. 0.7.0 divides by the hand-traced length.

Per-cube numbers: https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/afv_generator_entrant.md. The run script is `repro/fibers/run_afv_generator_chain.sh` in the same repo.
