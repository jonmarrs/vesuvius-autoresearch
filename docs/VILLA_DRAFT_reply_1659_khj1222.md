# Draft reply to @khj1222 on villa issue #1659 — corrects OUR OWN public error

**Why this one is different from the #1655 draft.** That one is courtesy: a contributor offered us a
branch and deserves an answer. **This one corrects a wrong technical claim we published on villa's
issue tracker.** #1659 asserts that `Normalize(mean=0, std=1)` "is the identity" and that the model
card's prose "contradicts itself". Both are false, and they are sitting in an open issue where the
next reader will take them as measured.

**Verified before drafting, not assumed.** albumentations 1.3.1, `Normalize(mean=0, std=1)` on
`[0, 100, 200, 255]` returns `[0.0, 0.3922, 0.7843, 1.0]` — exactly `x/255`. `max_pixel_value`
defaults to `255.0` and divides before mean/std. @khj1222 is correct.

What survives: our **ranking** of the five conventions. What does not: our **mechanism**, and our
claim that the card was self-contradictory. The card was right.

**Rate check.** A reply in an existing thread, inside the 1-per-day allowance; not a new issue. We are
at villa's 3-open-PR cap so nothing here becomes a PR.

---

## Text to post

You are right, and the correction is mine to make: the claim in this issue that `Normalize(mean=0, std=1)` "is the identity", and that the card's prose therefore contradicts itself, is wrong.

I checked it here rather than take it on faith — albumentations 1.3.1, `Normalize(mean=0, std=1)` applied to `[0, 100, 200, 255]` returns `[0.0, 0.3922, 0.7843, 1.0]`, which is exactly `x/255` and not the identity. `max_pixel_value` defaults to `255.0` and divides before mean and std are applied, as you say.

So the card's prose was correct: clip to `[0, 200]` then `Normalize` does land in roughly `[0, 0.78]`. The `clip(0,200)/255` I reported as undocumented **is** the documented transform, computed correctly. I had the ranking right and the mechanism wrong, which is the more embarrassing half to get wrong since it is the half that decides what the card should say.

Thank you for scoring against the annotations rather than firing rate — that is the check I should have run and did not. Ranking by AP is a much stronger statement than "this one over-fires", and it is worth noting your `/255` vs `/200` result reverses on three of six regions, so treating the divisor as unresolved and documenting the named transform is the right call.

The two points I raised that you left open are still open as far as I know, and neither is affected by this correction: the z-window (`layers 1-62` against a 109-layer stack) and the 2.4 µm note. I have no new evidence on either.

I have struck the incorrect paragraph in my own record of this issue.
