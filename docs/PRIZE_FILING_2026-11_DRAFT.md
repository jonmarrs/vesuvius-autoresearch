# November 2026 Progress Prize — DRAFT (started 2026-11-05; updated 2026-11-27; not submitted)

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
* **villa #2258, the first of November's two merges so far, is weak under the new sentence.** By its own description the default
  64-voxel seed spacing is unchanged, and it “does not establish a quality improvement”. At a fractional spacing of
  52.73 voxels the seed counts change 1589 → 1590, 11213 → 11175 and 1154 → 1151 on masks from Scrolls 1, 3 and 5,
  at most 0.34% ([record](../reports/villa_fractional_plane_spacing_2026-10-20.json)). It belongs in a bundle, not at
  its head.

## Merged in November

* [villa #2258](https://github.com/ScrollPrize/villa/pull/2258) (merged 2026-11-01 Pacific; `2026-11-01T14:56:47Z`,
  by @bruniss, [merge commit](https://github.com/ScrollPrize/villa/commit/bf4392a328f293b8e11d0c95083bae731ef7fd08)):
  fiber volume, keep fractional seed planes on the global grid. It merged after October's deadline (2026-11-01 06:59
  UTC), so it is November's.
* [villa #2463](https://github.com/ScrollPrize/villa/pull/2463) (merged 2026-11-24 Pacific; `2026-11-24T14:10:01Z`,
  by @hendrikschilling, [merge commit](https://github.com/ScrollPrize/villa/commit/bcbb7e4c2a127496690db72cf8fbdd21452652a6)):
  lasagna, put `tifxyz-flow-gate-channels` in `args` in both FlowSnap presets. **Its case in practice:** as shipped,
  both presets fail before optimizing with an unknown loss-term error (villa #2458). They are used by `fit.py` and
  offered in VC3D's config picker. The review reproduced the error on main and loaded both presets at the PR's head.
  It had been recommended for merging by villa's review on 2026-11-20 Pacific.

**Open, and recommended for merging by villa's review** (checked 2026-11-24 12:36 Pacific: #2463 has merged, above;
these two have not). Each goes
above only once it merges, with its date:
* [villa #2501](https://github.com/ScrollPrize/villa/pull/2501), recommended 2026-11-21 Pacific: ink detection,
  refuse a coarse pyramid level whose depth contradicts its declared Z scale (fixes villa
  [#2107](https://github.com/ScrollPrize/villa/issues/2107)). The review pushed two fixes to the branch first: the
  downloader reports a bad level before it touches its output, and labelled discovery keeps its depth checks on the
  planes it reads. This is the stronger of the two still open under #2450.
  * **Its case in practice:** in 18 of the 33 surface volumes of the `scrollprize/datasets` `ink/` bucket, level 2
    holds only the first 17 of 65 depth slices while declaring a Z scale of 1 (#2107). On main, flat inference, the
    ink dataset and the 9 µm preparation open such a level as the whole sheet.
  * **The measurement:** recomputed in the PR on one whole level-2 chunk of `841/w00`, its slices match a 4×4 mean of
    the same level-0 slice (median correlation 0.999964), not a 4-deep pool (0.18166). #2107's reporter measured
    `ink_9um` at AUC 0.54 on the shortened level and 0.91 to 0.93 rebuilt from level 0. Those figures are the
    reporter's and were not rerun here.
  * **Scope:** main's renderer keeps depth in new renders, so the guard protects reads of the volumes already
    published, until they are rebuilt.
  * **Credit:** the rule is Bryant Le's, from his #2256, stale-closed on 2026-11-06. The PR ports it to `vc_reader`
    with his agreement. #2107 is EhimenNathan's, and the PR thanks EhimenNathan and AndreasHad04 for the pixel
    evidence.
* [villa #2465](https://github.com/ScrollPrize/villa/pull/2465), recommended 2026-11-20 Pacific: docs, a note that the
  harmonized Scroll 1 instance-label volumes mix `uint8` and `uint16`. The review pushed a wording change to the
  branch and checked all 80 volume headers. It is documentation, weak under #2450 on its own, and belongs in a
  bundle.

**Open, posted 2026-11-25, revised 2026-11-27 after villa's review:**
* [villa #2711](https://github.com/ScrollPrize/villa/pull/2711): the fiber generator's seam trim.
  * **The review** (2026-11-25) found two regressions: a trim could take a valid overlap below the catalogue's 24
    voxels, so main's one fiber became two, and a trace only one block detects in the cut band was dropped. It
    recommended merging once both are repaired.
  * **The revision** (pushed and answered 2026-11-27 Pacific, head `8a7f76803`) is
    [finding 140](../reports/afv_generator_seam_repair.md) (`REPAIR_KEEPS_THE_GAIN`). A cut end is trimmed only
    where a neighbouring block holds a matching copy and the join survives. The review's two cases are tests in the
    PR. The branch also merges villa main after #2434, which landed 2026-11-25. The figures were measured before
    #2434; finding 140's addendum 2 measured both arms again with it (`GAIN_HOLDS_AFTER_2434`), and 16 of the 22
    figures the PR quotes are the same, while six move by 1 to 4 in a count or by under 0.0004.
  * It counts for November only if it merges by the deadline.

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
  * **Form:** a PR, since it fixes villa's own active code. **Posted 2026-11-25 as villa #2711** (above), on the
    owner's decision: the trim alone, with finding 109's Scroll 1 and 5 figures.
  * **Revised 2026-11-27** after villa's review, as [finding 140](../reports/afv_generator_seam_repair.md) measured
    it. On the same eight Scroll-3 cubes, ERLpen rose on every cube, a median +9.0% at tolerance 4. Lost face
    crossings were 178 against main's 172 (the first version's 278), and coverage at tolerance 4 moved a median +0.1%.
    The median share of written length beside a same-family copy fell 0.246 → 0.176. On finding 107's zone that share
    fell 0.120 → 0.078, and the hand-traced cube's ERLpen rose +10.2% at tolerance 4.
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

## Done here in November, not in villa: the PHerc. 343 recipe on one RTX 4090

The prize page's \$1,000 tier names "spiral fitting on consumer GPUs" and an end-to-end First Letters attempt
"published with its commands, failures and costs". This is that kind of work, on a 4-core, 31 GB host with one
RTX 4090. Whether to file it, and at what length, is the owner's decision. Scripts: `repro/first_letters/`.

* **The published PHerc. 343 image rebuilt from the published windings**
  ([report](../reports/first_letters_343_reproduction.md)): 99.95% of pixels identical, none off by more than 5 of 255.
* **The mesh step run here** ([report](../reports/first_letters_343_mesh_step.md)): distance field, 30,000-step
  spiral fit, snap, flatten, render, ink.
  * **Result:** 76% and 81% of the published windings' nodes within 2 voxels of ours; ink r = 0.86 over the letter
    boxes against controls of 0.17.
  * **Cost:** 3 h 31 min from inputs on disk, 3 h 09 min of it the fit, at 10.8 GB of host memory and 12.7 GB of GPU
    memory.
  * **A failure and its cause:** the first fit was killed for memory pressure. A track file fetched over HTTP loses
    the nanosecond timestamp villa `0fb38c45` checks, so the fit unpickled 9 GiB in Python while it was also packing
    a 5.9 GiB pool. villa main already validates by content digest (#2041); restoring the timestamp fixes the old
    commit.
* **The recipe's ink models on a scroll outside their training list**
  ([report](../reports/first_letters_0841_surface_control.md)): on the team's three labelled PHerc. 0841
  surfaces, AUC 0.75 and 0.72 against the labels on the two held-out segments, with a slid-map floor of 0.53 and the
  team's own model at 0.92 and 0.87. One side of the stack reads the ink and the other is near chance.
  * **Caution:** this is a measurement of released models. Under #2450 it counts only for what it changes: an
    eligible-scroll band has to be swept on both sides, and a blank band is weak evidence.

* **The same pipeline end to end, at the place where PHerc. 211's First Letters prize was won** (findings 118 to
  124). The prize was announced on 2026-11-15 and the winner published the surface, the probability map and the CT
  image under CC BY-NC 4.0. That gave a known text place to measure this pipeline against, for the first time on a
  crushed scroll.
  * **The reader on the winner's surface**
    ([report](../reports/first_letters_0211_reader_control.md)): the recipe's four models put ink where the winning
    reader did, r = 0.53 against controls of 0.09 and below, and no letter can be read from their map.
  * **The fit** ([report](../reports/first_letters_0211_winner_band.md)): the recipe's 30,000-step fit of a
    1,500-slice band around the surface (3 h 32 min, 12.3 GB of GPU memory) reaches the winner's sheet in two
    pieces.
    * 88% of the winner's nodes lie within 2 voxels of some winding.
    * One winding follows the sheet for 34 mm and a winding two further in follows the rest, each at the PHerc. 343
      mesh step's line (half the nodes within 2 voxels).
    * The two windings between them sit between predicted sheets.
  * **A second, MIT-licensed reader** ([report](../reports/first_letters_0211_reader_v3.md)): Reader V3 on the
    winner's surface gives r = 0.63, closer than the four models but short of the registered margin. Its map shows
    a few letter shapes and no readable word.
  * **End to end** ([report](../reports/first_letters_0211_end_to_end.md)): our own fit's four windings, snapped,
    flattened, rendered, read and carried onto the winner's surface, give r = 0.52 on 83% of its cells, in 42
    minutes unattended. The same models on the winner's own surface give 0.54 on those cells, and Reader V3 loses
    nothing (0.629 against 0.627).
  * **A third permissive reader** ([report](../reports/first_letters_0211_gp_timesformer.md)): the 2023 Grand Prize
    TimeSformer finds the ink only weakly there (r = 0.24) and draws no letter shape.
  * **The winning reader, on this machine** ([report](../reports/first_letters_0211_studio_reproduction.md)): Studio
    (the winner's reader; code MIT, weights CC BY-NC 4.0, used with the owner's approval) reproduces the winner's
    map from the winner's own weights and input on one RTX 4090. r = 1.0 over 8.8 million pixels, with differences of
    bfloat16 rounding, in 75 seconds at 14.5 GB of GPU memory.
  * **Our own fit, read by the winning reader** ([report](../reports/first_letters_0211_studio_e2e.md)): the same four
    windings of our unrefined fit, read by Studio and carried onto the winner's surface, give r = 0.82 against the
    winner's map (reversed planes −0.05, slid 0.11). The image draws the winner's letters. Studio on our render of
    the winner's surface gives 0.97, so our renderer costs almost nothing and the geometry the rest.
  * **The winning reader on a second scroll** ([report](../reports/first_letters_343_studio.md)).
    On the PHerc. 343 recipe's published surface, Studio's map gives r = 0.6238 against the recipe's ensemble map.
    - **How that compares:** it is above each of the ensemble's four models measured against the other three (0.41
      to 0.6195).
    - **Controls:** 0.10 (reversed planes) and 0.21 (slid).
    - **The image:** it draws both published rows of letters, more legibly than the ensemble.
    - **Caveat:** Studio was not trained on this scroll, but its training includes a fragment, PHerc0343P, that may
      come from the same roll.
  * **Our own fit of PHerc. 343, read by the winning reader**
    ([report](../reports/first_letters_343_studio_own.md)). The mesh step's two windings, read by Studio and carried
    onto the published surface, give r = 0.90 against Studio's map of that surface (reversed planes 0.18, slid
    0.31), and draw the same letters.
    - **What it changes:** the whole route is now checked at two places with known text, a crushed anticlockwise
      scroll and a clockwise one.
    - **Cost:** 7 minutes from renders on disk.
  * **Studio's faster default tiling does not reproduce its map**
    ([report](../reports/studio_published_tiling.md)). It is 2.4 times faster, but gives r = 0.94
    against the winner's command, short of the 0.98 line. Band reads keep the winner's command.
  * **Two geometry changes tested at the known place** (findings 131 and 134, on PHerc. 211's winner surface;
    reports: [denser grid](../reports/first_letters_0211_dense_read.md),
    [three passes](../reports/first_letters_0211_snap_passes.md)). Both put more of every winding on the predicted
    sheet, and neither read better beyond the noise:
    - **Subdividing the windings twice before the snap:** +0.034 at the median within 2 voxels of the sheet; r 0.8168
      against 0.8267 for the same route on the fit's grid (margin 0.02).
    - **Three snap passes of those windings:** a further +0.036; r 0.8217 against 0.8188 for one pass.
    - **What it changes:** the band reads keep both, on registered tie-breaks. Each extra snap pass adds about a
      quarter of an hour to a band read. The share of a winding on the predicted sheet did not predict how well
      Studio reads it, within these changes.
  * **The depth Studio reads at, tested at the known place**
    ([report](../reports/first_letters_0211_depth_sweep.md)). Studio's 16 planes were moved from 8 layers in to 8
    layers out of the window the band reads use, on both geometries above. Both read best with no shift: r 0.8247 and
    0.8135.
    - **The tolerance:** over ±2 layers r changes by at most 0.041. It halves 6 layers outward and stays above half 8
      layers inward.
    - **What it changes:** the band reads keep their window. A uniform depth offset of a layer or more is not what
      keeps r at 0.82 there.
  * **A fit declared to turn the wrong way, tested at the known place**
    ([report](../reports/first_letters_0211_wrong_hand.md)). The same band was fitted again with the spiral declared
    clockwise, against the catalog's anticlockwise. Read by Studio, it matches the winner's map as well as the
    published direction does: r 0.841 on 0.8337 of the winner's cells, against 0.8247 on 0.8309.
    - **How:** the fit did turn the other way in the scan. Its windings still lie on the sheets and step across them,
      a net 1.78 to 1.89 sheets a turn.
    - **What it changes:** a band of a scroll whose winding direction is not published can be read with either
      direction declared. Each page then carries a sheet's text in pieces, broken where its winding changes sheet.
  * **The PHerc. 306B team's glyph network, ranking a band read of the known place**
    ([report](../reports/first_letters_0211_band_triage.md)). The same band was read whole, the way we read eligible
    bands: 80 windings, and every window scored by the network the PHerc. 306B team used to find their line. A window
    on the winner's text ranks 2nd of 467; counting only the windows on their own grid, 9th of 400.
    - **How:** their network and weights, re-implemented from their commit. The text's best window is one our version
      adds at each winding's end; without those windows the text ranks 9th.
    - **What it changes:** it orders where to look first in a band read. It does not separate text from texture: the
      window ranked above the text shows no letters, nor do the two below it that were looked at (3rd and 5th), and
      the scores are within a fraction of a logit of each other.
    - **Credit:** the network is Liam Warner's and Nicola Bodill's; its code is MIT and its weights CC BY-NC 4.0.
  * **What it shows:** on one RTX 4090, the published recipe's unrefined fit finds the ink at a known text place, and
    with the winning reader it draws that place's letters. With the recipe's released readers it draws none, so the
    reader was the missing piece, not the geometry.
  * **Failures and fixes on the way:**
    * a depth bug in the PHerc. 343 mesh step's transfer code;
    * the band verdict crashing on an unscored fit (also fixed in #441);
    * villa's environment unable to read the winner's LZW surface files;
    * villa's `_spliced` twins counted as windings;
    * the need to render our windings with flipped normals;
    * this machine's uv lacking the winner's pinned Python, solved by the winner's own bootstrap.
  * **Caution under #2450:** this measures the recipe and released readers. It counts only for what it changes:
    which reader to use, and how to read a band.

* **The submission image from a band read** ([README](../repro/first_letters/submission/README.md), our #493,
  merged 2026-11-22). `repro/first_letters/submission/` feeds the recipe's MIT `make_submission_image.py`, the
  script behind an accepted submission, with a band read's mesh, 66-layer render and Studio map. It adds a
  reversed-plane control drawn with the same stretch and a check of how near isometric the flattening is. The rules
  ask for a low-distortion flattening; the script reports only its area ratio.
  * **Dry runs at the two places with known text:** PHerc. 343 (our w047, 14 letters carried from the published
    image, 4.00 cm²) and PHerc. 211 (our w035, at the winner's crop) both come out in reading order.
  * **The flattening check:** 0.93 to 0.98 of our meshes' edges are within 10% of their flat length, against 0.89 to
    0.98 for the accepted meshes.
* **A defect in that script, reported upstream**
  ([Nieuwlaar/pherc343-first-letters#2](https://github.com/Nieuwlaar/pherc343-first-letters/issues/2), posted
  2026-11-22; open, with no reply at 2026-11-24 12:36 Pacific). The script takes the reading orientation from the mesh and the axis alone: it flips
  left-right when θ grows along the columns and top-bottom when z grows down the rows. That holds in PHerc. 343's
  frame only.
  * **The case in practice:** on the PHerc. 211 winner's published surface and axis it flips both ways, and turns
    an image that reads upright by 180 degrees. Our wrapper passes the flips from the catalog's two flags instead.
  * **How often it bites:** of the 57 volumes in the open-data catalog with both flags set, the rule holds on 18.
    36 have z running top to bottom, as PHerc. 211 does, so the image comes out turned by 180 degrees. On the 3
    volumes with left-handed coordinates it would come out mirrored; that follows from the same rule and was not
    checked on data. The other 17 volumes have a flag unset
    ([record](../reports/evidence/catalog_orientation_flags_2026-11-22.json), latest catalog snapshot, 2026-11-19).
  * **Caution:** it is a report with a suggested change, not a merged fix. Once known, a turned image is undone by
    hand. Until then, someone looks for letters in an image that is upside down.
* **Studio without the windows that hold no CT** ([report](../reports/studio_skip_empty_windows.md)).
  The winner's inference loop, unchanged except that it skips each window whose 128-pixel crop holds no CT, gives
  the same map: largest difference 0.00075, no pixel across 0.5.
  * **The gain:** 0.5918 and 0.5781 of the full loop's time on two band windings, where 41% and 43% of the windows
    hold no CT. On the PHerc. 211 winner's input, nearly all CT, 0.9168.
  * **What it changes:** Studio is the slowest step of a band read, and reads registered after this use the skip.
  * **For the owner:** the two band windings are PHerc. 0826's, an eligible scroll. The report carries numbers only
    and no image, but the line below excludes anything made from a still-eligible scroll. Whether this item is
    filed, and whether to offer the change to the winner, is the owner's decision.

Not for this filing: anything made from a still-eligible scroll. That includes our band reads of eligible scrolls,
their costs and geometry among them, and any ranking of their windows. PHerc. 211's prize was announced on
2026-11-15, so its results may be described.

## "What is your contribution?"

A draft for the owner's review; paste from this file. Every number in this section and the next is one the sections
above state from a report or record, and a test holds them to the same values.

**(1) Which scroll data.**
* PHerc. 211, at the place where its First Letters prize was won (announced 2026-11-15): the winner's published
  surface, probability map and CT image (CC BY-NC 4.0), and our own band fit of the public CT, surface prediction,
  lasagna and spiral tracks around it.
* PHerc. 343: the First Letters recipe's published surface and windings, and our own fit of its band.
* PHerc. 0841: the recipe team's three labelled surfaces.
* villa: the lasagna FlowSnap presets and the fiber volume's seed planes.

All of it on one RTX 4090, on a 4-core, 31 GB host.

**(2) How it increases the probability of reading.**
* **Merged into villa this month:**
  * [villa #2463](https://github.com/ScrollPrize/villa/pull/2463), merged on 2026-11-24. Both lasagna FlowSnap presets
    failed before optimizing with an unknown loss-term error (villa #2458). They are used by `fit.py` and offered in
    VC3D's config picker, and now load.
  * [villa #2258](https://github.com/ScrollPrize/villa/pull/2258), merged on 2026-11-01, keeps fractional seed planes on
    the fiber volume's global grid. Its effect is small (seed counts change by at most 0.34%), so it is supporting
    work.
* **The First Letters route, end to end on one consumer GPU, checked at two places with known text.** Our unrefined
  spiral fit, read by the winning reader (Studio), draws the winner's letters at PHerc. 211: r = 0.82 against the
  winner's map, reversed planes −0.05. At PHerc. 343 our fit's windings give r = 0.90 and draw the same letters. With
  the recipe's released readers the same place gives r = 0.53 and no readable letter, so the reader was the missing
  piece, not the geometry.
* **Choices for reading a band, each tested at the known place:**
  * a fit declared to turn the wrong way reads the text as well as the published direction (r 0.841 against
    0.8247), so a scroll whose winding direction is not published can still be read band by band;
  * Studio reads best at the depth the band reads use, with no shift;
  * subdividing and re-snapping the windings puts more of them on the sheet but reads no better;
  * the PHerc. 306B team's glyph network ranks a window on the known text 2nd of 467 in a whole band read, so it can
    order where to look first. It does not separate text from texture.
* **Submission images:** our wrapper around the recipe's `make_submission_image.py` adds a reversed-plane control and
  a flattening check. A defect in that script's reading orientation is reported upstream: on 36 of the 57 catalogued
  volumes with both flags set, it would turn the image by 180 degrees.

Left out on purpose: Studio's skip of windows that hold no CT. Its timings were measured on an eligible scroll's
windings, and whether that item is filed is the owner's decision (above).

**(3) What it enables that was not possible before.**
* Reading a whole band of a scroll with the winning reader on one RTX 4090, with every step's cost published: at
  PHerc. 211, a 1,500-slice band fitted in 3 h 32 min and 80 windings read.
* Reading a band of a scroll whose winding direction is not published.
* A short list of where to look first in a band read.

**(4) Evidence.**
* Registered studies were pre-registered before their data; checks added after a result are labelled as such.
  Reports, records and scripts: https://github.com/jonmarrs/vesuvius-autoresearch (`reports/first_letters_0211_*.md`,
  `reports/first_letters_343_*.md`, `reports/first_letters_0841_surface_control.md`,
  `reports/studio_published_tiling.md`, `repro/first_letters/`).
* Every figure in those reports is bound by a test to the record that produced it.
* villa #2463's case: the review reproduced the error on main and loaded both presets at the PR's head.

## Required disclosure — include it

* **Predictions that failed this month**, as each report states:
  * the reader control: `READER_PARTLY` predicted, `READER_AGREES` found;
  * Reader V3: `V3_CLOSER` predicted, `V3_NO_CLOSER` found, short of its margin;
  * Studio's published tiling: adoption predicted, the winner's tiling kept;
  * the wrong-direction fit: a partial read predicted, an equal one found;
  * the glyph network: a high rank on w035 predicted, 2nd found, on w033.
* **Our own addition raised a rank:** the glyph network's best window on the text is one our version adds at each
  winding's end. On the team's own window grid the text ranks 9th of 400.
* **Licences:** Studio's weights and outputs and the glyph network's weights are CC BY-NC 4.0, used with the owner's
  approval. Studio's training includes a fragment, PHerc0343P, that may come from the same roll as PHerc. 343.
* **ScrollGT, inkdelta and inkagree** are evaluation tools and are not claimed here.

## Do not add

Anything made from a still-eligible scroll (above), and any claim the sections above do not state.

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
https://github.com/ScrollPrize/villa/pull/2463
```
