# November 2026 Progress Prize — DRAFT (started 2026-11-05; not submitted)

**The November round opened 2026-11-05 03:54 UTC (2026-11-04 Pacific)** with villa
[#2301](https://github.com/ScrollPrize/villa/pull/2301) (merge `9c343a164`):
* **deadline 11:59pm Pacific, November 30th, 2026**;
* form `https://docs.google.com/forms/d/e/1FAIpQLSeB6MC_--4UCCEGc3zalX57-uE4puRcE_vJoYJCrEt4uYaaaw/viewform`.

`scripts/check_prize_form_rollover.py` passed on 2026-11-05 at 14:41 UTC: the form is titled “November 2026 Progress
Prizes”, answers HTTP 200 and accepts responses
([record](../reports/evidence/november_form_rollover_2026-11-05.json)). Read the same day, it asks what October's
did: full name, team description, an optional Discord display name, the URL list (required), "What is your
contribution?" with the same four parts (required), and the terms. These personal fields and consent are the owner's.

**For pasting, open this file. Never copy from terminal output.** In September a terminal-wrapped line clipped
"#1780" to "#17".

## The criteria changed the day the round opened

villa [#2450](https://github.com/ScrollPrize/villa/pull/2450) (`aa8784bff`, merged by @pmh47 at 03:52 UTC on
2026-11-05, two minutes before the rollover) rewrote the Progress section of `scrollprize.org/docs/34_prizes.md`:

* **Added:** “We discourage standalone analytic, auditing or evaluation tools, and instead encourage work that directly
  **advances unwrapping or ink detection**.”
* **Added to the bug-fix bullet:** “Fixes for issues that are theoretically wrong but rarely or never cause problems in
  practice are unlikely to be awarded.”
* **Removed:** the bullet that asked submissions to “Reveal **insightful, actionable** information”, which credited
  analytic tools that “facilitated improvements to unwrapping or ink detection”.
* **Changed:** the bundling example is now “improvements to tooling”, where it was “several bugfix PRs on our
  [villa](https://github.com/ScrollPrize/villa) monorepo”.

The same commit removed “This is why better diagnostics matter just as much as better models” from the open-problems
page.

What this means here:
* **ScrollGT, inkdelta and inkagree are standalone evaluation tools,** the kind now discouraged. Cite one only where it
  changed what an unwrapping or ink-detection tool produces.
* **Each fix needs a case where it bites in practice:** a real workflow it broke or degraded, and how often.
* **villa #2258, the only November merge so far, is weak under the new sentence.** By its own description the default
  64-voxel seed spacing is unchanged, and it “does not establish a quality improvement”. At a fractional spacing of
  52.73 voxels the seed counts change 1589 → 1590, 11213 → 11175 and 1154 → 1151 on masks from Scrolls 1, 3 and 5,
  at most 0.34% ([record](../reports/villa_fractional_plane_spacing_2026-10-20.json)). It belongs in a bundle, not at
  its head.

## Merged in November

* [villa #2258](https://github.com/ScrollPrize/villa/pull/2258) (merged 2026-11-01 Pacific; `2026-11-01T14:56:47Z`,
  by @bruniss, [merge commit](https://github.com/ScrollPrize/villa/commit/bf4392a328f293b8e11d0c95083bae731ef7fd08)):
  fiber volume, keep fractional seed planes on the global grid. It merged after October's deadline (2026-11-01 06:59
  UTC), so it is November's.

## Queued, not posted

* **The seed-heading fix** ([draft](VILLA_DRAFT_volume_seed_heading.md)).
  * **Done:** the rebase onto villa main `eab6108b9` (#2440 had moved the code around it) and the rewrite of its villa
    tests for main's four-argument `ct_seed_heading`, our #360, merged 2026-11-06. Those tests were run with the
    native readers stubbed only.
  * **Still needed before posting:** `vc_reader` and `vc_object_store` built for villa main, villa's tests run against
    those builds, a GPU re-run of the two Scroll-5 cubes, and the owner's paragraph.
  * **Its case in practice** is finding 100's two held-out Scroll-5 cubes. The fix itself (finding 100's `keep` arm)
    raised their coverage ×1.11 and ×1.28. The ×1.20 and ×1.43 in finding 100 belong to a heading along the sheet, a
    rule the draft does not propose. Finding 103 found no unseen cube that skipped 20% of its seed dots: the most was
    0.167, which gained 1.040×. The post has to say how often the skip occurs.
* **The splice issue** ([draft](VILLA_DRAFT_volume_splice.md), from [finding 105](../reports/neural_tracer_link_splice.md)).
  villa's volume tracer keeps overlaps "for joining" and records each piece's links, but nothing joins the pieces.
  * **The measurement:** on the ten held-out cubes, splicing them as polylines raised ERLpen on every cube, a median
    +29% at tolerance 4 and +5.3% at tolerance 2, with merges 1,740 → 1,757.
  * **Form:** an issue, not a PR, since it adds a step villa does not have. Whether to post it is the owner's decision,
    and the owner writes its paragraph.
  * **A PR would also need** a run on an open-data volume, so villa's `fibers.vcobj` export can carry the spliced
    fibers.
* **The seam trim** ([draft](VILLA_DRAFT_afv_generator_seam_trim.md), from
  [finding 106](../reports/afv_generator_block_seams.md)). Where a block's border cuts a fiber, villa's automated fiber
  generator (VC3D's **Generate automated fibers…**) writes both blocks' bent copies.
  * **The measurement:** on eight held-out Scroll-3 cubes run in 8 blocks, trimming the cut ends raised ERLpen on
    every cube, a median +12.8% at tolerance 4 and +7.1% at tolerance 2, with merges 439 → 386 at tolerance 2. Lost
    face crossings rise, 172 → 278 of 1,304.
  * **Form:** a PR, since it fixes villa's own active code. villa's limits (three open PRs, two code fixes a week)
    rule it out before about 11-13, and whether to post it is the owner's decision.
  * **Its case in practice** is [finding 107](../reports/afv_generator_default_zone.md) (`BITES_AT_DEFAULTS`): one
    1024³ zone of the Scroll-3 scan at villa's default block size of 512. VC3D's default zone is one block, where the
    trim changes nothing.
    * **On main:** 0.120 of the zone's written length lies beside a same-family copy.
    * **With the trim:** 0.052. On the hand-traced cube at the zone's centre, ERLpen rises +16.0% at tolerance 4 and
      +5.6% at tolerance 2, with merges 92 → 82 at tolerance 2 and coverage −3.7% at tolerance 4.
  * **The rest of the defect** is [finding 108](../reports/afv_generator_cross_block_duplicates.md) (`SUPPORTED`).
    With the trim, two blocks' copies of a fiber can still lie along each other, and the catalogue keeps both.
    Suppressing such a copy (`catalog.py` +18/−2) raised ERLpen over the trim alone on every cube, a median +5.7% at
    tolerance 4 and +5.4% at tolerance 2, with merges 386 → 384 at tolerance 2. With both changes, eight blocks reach
    0.905 to 1.026 of one block's ERLpen at tolerance 4. Bundling it into the seam-trim PR is the owner's decision.
  * **On other scrolls** is [finding 109](../reports/afv_generator_seam_confirmation.md) (`CONFIRMED`): ten
    hand-traced cubes of Scrolls 1 and 5 that no step of the generator work had used.
    * **The four cut as Scroll 3's were** (512³ in blocks of 256): both changes raised ERLpen over main on every cube,
      a median +23.0% at tolerance 4 and +12.4% at tolerance 2, with merges 277 → 258 at tolerance 2.
    * **All ten:** a median +31.2% at tolerance 4 and +36.2% at tolerance 2, up on every cube, with merges 325 → 297
      at tolerance 2. The six 256³ cubes, in blocks of 128 that no villa user runs, carry these medians.
    * **The cost:** coverage at tolerance 4 fell on every cube, a median −2.3%.

## Filing-day checklist

1. Re-read the **whole** Progress section at current upstream: deadline, form and criteria. They changed on 2026-11-05
   (#2450) and mid-month in September.
2. Run the rollover check. Exit 1 means stop. If December's rollover has merged, file at the November form above.

   ```sh
   python3 scripts/check_prize_form_rollover.py \
     --form https://docs.google.com/forms/d/e/1FAIpQLSeB6MC_--4UCCEGc3zalX57-uE4puRcE_vJoYJCrEt4uYaaaw/viewform \
     --expected-title 'November 2026 Progress Prizes'
   ```
3. List every villa PR of ours merged in November in the URL field and in "Merged in November", each with its
   "(merged YYYY-MM-DD Pacific)" date, then run
   `scripts/check_filing_upstream_claims.py --month 2026-11 --filing docs/PRIZE_FILING_2026-11_DRAFT.md`; it must pass.
4. For each item, state the measured before → after on real data and how often the problem occurs.

## URL field

```text
https://github.com/ScrollPrize/villa/pull/2258
```
