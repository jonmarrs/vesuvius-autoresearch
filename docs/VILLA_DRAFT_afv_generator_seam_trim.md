# Draft: villa's fiber generator writes a fiber twice where a block border bends both blocks' copies

**NOT POSTED.** Prepared 2026-11-07 from [finding 106](../reports/afv_generator_block_seams.md), whose registered
verdict is `SUPPORTED`. Its case at villa's defaults is [finding 107](../reports/afv_generator_default_zone.md)
(2026-11-09, `BITES_AT_DEFAULTS`). Its confirmation on Scrolls 1 and 5 is
[finding 109](../reports/afv_generator_seam_confirmation.md) (2026-11-10, `CONFIRMED`). Whether to post, and in what
form, is the owner's decision.

**Recommended form: a PR.** This fixes a defect in villa's own active code (`cli.generate` → `extend.stitch`, what VC3D
runs). villa merges fixes of that kind, and the patch is ready:
`repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch`, the amended one.

## Before posting

1. **The owner decides,** and writes the motivation paragraph below. Never tick the verification box for them.
2. **villa's limits:**
   * At most three open PRs. Two are open (#2463, #2465); the owner closed #2464 on 2026-11-08.
   * At most two code-fix PRs a week. Both were used on 2026-11-06, so not before about 11-13.
3. **Re-check villa main of that day:**
   * `extend/stitch.py` and `cli.generate` are unchanged where the patch applies (`git apply --check`).
   * The catalogue's overlap tests (15° at the ends, a strict duplicate within 0.65 voxel) are still as measured.
   * No PR or issue already trims cut ends: search "block border", "duplicate" and "stitch".
   * Checked 2026-11-09 at villa main `c3d9da6fe`: no commit touches the generator since `7e6b82164`, and the patch
     applies.
   * #2434 (open, by another contributor) changes `_compare_pair` in `extend/catalog.py`, not these lines. It still
     names the module `afv_spline_generator`, which villa main now calls `fiber_spline_generator`. Its "Not changed"
     note saw the symptom on synthetic straight fibers: cite it, and say how this differs.
4. **The real-use example at villa's own defaults is done:** finding 107, in "How often it bites" below. It ran a
   1024³ zone at block 512 on the CPU (17 hours).
5. **Size:** the patch is 47 lines of code and comments in two files, plus 54 lines of tests. That is above the 4–25
   lines our fixes usually are. The comment block above `CUT_END` can be cut if villa prefers.
6. **No AI-authorship markers** in the commit or the body, including `Co-Authored-By`.
7. **Whether to bundle finding 108's change** is the owner's decision: see "Option: bundle the cross-block change" at
   the end. The body below is the trim alone.
8. **Whether to add finding 109's figures** for Scrolls 1 and 5 is part of the same decision: see "On other scrolls"
   below. The body's measurement is still the eight Scroll-3 cubes.

---

**Title:** `fiber_spline_generator: trim the spline ends a block border cuts, so neighbouring blocks' copies chain`

**In one sentence:** where a block's border cuts a fiber, the block's spline bends over its last few voxels. The
copies of that fiber from two neighbouring blocks then fail the catalogue's overlap and duplicate tests, and both are
written. Dropping the last 16 voxels at each cut end, only where another block of the zone reads past that border,
lets the copies chain. On eight hand-traced Scroll-3 cubes run in 8 blocks, merge-penalized ERL rises on every cube,
by a median 12.8% at tolerance 4, with 12.1% fewer merges at tolerance 2.

**What happens now:** `Stitcher.add_block` gets each block's splines fitted in its read region, which is the block plus
the 32-voxel margin. At a cut border the fit bends:
* Within 2 voxels of the border, a block's spline lies a median 1.6 voxels from the spline fitted to the same field in
  one block, and 0.33 voxels at 2–4 voxels.
* True overlaps (median 0.15–0.27 voxels apart) then measure 15.3–19.5° at their ends, and the overlap test allows
  15°.
* The bent copies also fail the strict duplicate test (0.65 voxel).

Both copies stay, and each makes the other overlaps at that end ambiguous. On the eight cubes below, a median 0.246 of
the written length lies within 1.5 voxels of a different written fiber of the same family. Run as one block, the
same cubes have at most 0.0002.

**The change** (`extend/stitch.py` +40, `cli.py` +7/−4, one test file):
* `trim_cut_ends(traces, low, high, reach_low, reach_high)`: at each end of a block's spline, drop the points within
  `CUT_END = 16` voxels of a border that another block of the zone reads past. An end at the zone's reach (zone ±
  margin, the box `ExteriorBlack` already uses) is kept, and so is a spline that does not end in the cut band.
  Splines left shorter than the stitcher's `MIN_LENGTH` are dropped.
* 16 is half the CLI's margin, so two blocks still share 32 voxels of a crossing fiber, above `MIN_OVERLAP` (24).
* `cli.generate` applies it to `extract_splines`' output before `add_block`. A one-block zone is unchanged.

**Measurement:** eight hand-traced Scroll-3 cubes of 512³ (ScrollGT, 7.91 µm), each run as 8 blocks of 256, with each
block predicted from its own crop as `generate` does. The model is `Qualzz20/afv_fiber_9um` at `e189af75`, run with the
CLI's defaults (threshold 60, `--max-join-angle 45`, `--min-length 100`, no mirroring, no `--extend`). Merge-penalized
ERL is scored against the hand tracing within 2 and 4 voxels.

| | main | with the trim |
|---|---|---|
| merge-penalized ERL, τ = 4: median gain (range) | | +12.8% (+3.0% to +23.4%), up on 8 of 8 |
| merge-penalized ERL, τ = 2: median gain (range) | | +7.1% (+3.3% to +19.1%), up on 8 of 8 |
| merges, τ = 2, summed | 439 | 386 |
| written length beside a same-family copy, median | 0.246 | 0.104 |
| fibers written (one block: 4,055) | 5,236 | 4,469 |

Against the same cubes run as one block, eight blocks reach 0.703 to 0.923 of its merge-penalized ERL at τ = 4 on
main, and 0.822 to 0.963 with the trim.

**What it costs:** more crossings of the block faces are lost. Of 1,304 places where a fiber written from the cube as
one block crosses a block face, 278 are lost with the trim against 172 on main. Whole ones rise from 853 to 884, and
broken ones fall from 279 to 142. The changes run both ways: of the 178 crossings better with the trim, 176 are chained
only with it. Of the 198 crossings worse with the trim, 63 are joins main made that the trimmed copies miss. Three
reasons come up most often, in about equal measure (a crossing can have more than one):
* the trimmed overlap is shorter than `MIN_OVERLAP` (29);
* one copy lies along the other but fails the strict duplicate test, so both stay unlinked (28);
* another overlap at the same end makes the candidate ambiguous (27).

In 125, the copies were never chained. A trimmed copy reaches 16 voxels past the face instead of 32. Where the
neighbouring block's copies are short or miss the fiber, that stretch is no longer covered. Merge-penalized ERL is
scored against the hand tracing, not at these crossings, and it rises on every cube.

**How often it bites:** on every zone larger than `--block-size` along any axis (the VC3D dialog shows "N blocks to
process"). The dialog's default zone, 512³ at block 512, is one block and is not changed. At the default block size,
on a 1024³ zone of the Scroll-3 scan (8 blocks of 512) centred on the cube `s3_04494_00994_01494_512`:
* **The whole zone:** 0.120 of main's written length lies beside a same-family copy. With the trim, 0.052 does.
  Fibers written fall from 5,766 to 5,326.
* **Inside the hand-traced cube:** merge-penalized ERL rises 16.0% at tolerance 4 and 5.6% at tolerance 2, and
  merges at tolerance 2 fall from 92 to 82. Coverage falls 3.7% at tolerance 4.
* **The eight cubes above, for comparison:** in blocks of 256, coverage also fell on every cube with the trim. But
  main's blocks had covered more than the same cube run as one block, and the trimmed coverage lies within −0.005 to
  +0.014 of one block's at tolerance 4.

**Why / where this is useful:** [The owner's own words: what we were generating fibers for, and what the duplicated
copies cost when using the output.]

- [ ] I personally verified that the measurement above was produced by this change on the stated data.

## Details

* **What ran:** the #1934 head's pure-Python generator modules (`predict.predict_fibers`, `splines.extract_splines`,
  `extend.stitch`, `cleanup.ExteriorBlack` and `cleanup.clean`), called block by block as `cli.generate` calls them,
  not `cli.generate` itself. On every cube its `predict` and `extend` modules (`stitch`, `catalog`, `overlap`,
  `candidates`, `expander`) were checked byte-identical to villa main `7e6b82164`'s. Its `cleanup` and `splines`
  modules were not compared with main's; the head's `splines` predates #2440's switch to the native `vc_reader`. The
  measurement used the patch's first form, which keeps an end only at the volume's border. On these cubes the zone
  is the whole volume, and there the two forms trim alike; that was checked on 1,000 random blocks. The 1024³ zone
  ran the amended form, the patch below, with the zone's read box equal to the fetched scan.
* **Limits:**
  * Blocks of 256, not villa's default 512. A 512³ hand-traced cube has one inner face per axis only at 256. The
    1024³ zone used 512, but it is one zone and one cube.
  * 7.91 µm, finer than the model's 8.64–9.36 µm training pitch.
  * One hand tracing per cube, and eight cubes, all Scroll 3.
* **Tests:** villa's `test_stitch.py` with the patch has three new cases:
  * a fiber bent at both borders becomes one fiber only with the trim;
  * only ends at a border another block reads past are trimmed;
  * a one-block zone inside the volume is not trimmed.

  The first runs the same two blocks through `Stitcher` twice, untrimmed as main does and then trimmed. It asserts
  the defect (2 fibers) beside the fix (1). The trim lives in `cli.generate`, outside the `Stitcher`. So the new file
  cannot run on main at all (it imports `trim_cut_ends`), and "fails on main" in #2434's sense does not apply.
* **#2434's "Not changed" note** saw a fiber written twice across blocks on synthetic straight fibers, when one copy
  starts 2 voxels before its neighbour's, and left it as tuning of the overlap rules. On the model's real predictions,
  the copies differ at the cut ends, which bend. This trims those ends; it does not change the overlap rules.
* **Records:** https://github.com/jonmarrs/vesuvius-autoresearch:
  * the registration, `docs/preregistration/2026-11-06_afv_generator_block_seams.md`, and its amendment;
  * the script, `scripts/afv_generator_block_seams.py`;
  * the report, `reports/afv_generator_block_seams.md`;
  * the diagnosis of the lost crossings, `scripts/afv_generator_seam_diag.py`, and its summary,
    `reports/evidence/afv_generator_seam_diag_2026-11-07.json`;
  * the 1024³ zone at the default block size: its registration,
    `docs/preregistration/2026-11-08_afv_generator_default_zone.md`, script, `scripts/afv_generator_default_zone.py`,
    and report, `reports/afv_generator_default_zone.md`.

## On other scrolls (finding 109)

Prepared 2026-11-10 from [finding 109](../reports/afv_generator_seam_confirmation.md), whose registered verdict is
`CONFIRMED`: by its registration, the PR can state both scrolls' figures. It is not in the body above.

* **What ran:** the same measurement on ten more hand-traced cubes (fiber-skeletons, 7.91 µm), three of Scroll 1 and
  seven of Scroll 5, that no step of the generator work had used.
  * Four are 512³ in 8 blocks of 256, as the Scroll-3 cubes were.
  * Six are 256³ in 8 blocks of 128, a block size no villa user runs. They carry the ten-cube medians, so give the
    block-256 figures first.
* **Text to add to "Measurement", for the trim alone:**
  * **The four cubes in blocks of 256:** merge-penalized ERL up on 4 of 4, by a median +13.6% at τ = 4 (+4.2% to
    +21.2%) and +8.3% at τ = 2; merges at τ = 2 277 → 259; the median written-twice share 0.251 → 0.113.
  * **All ten:** up on 10 of 10, by a median +18.9% at τ = 4 (+4.2% to +63.6%) and +19.4% at τ = 2; merges at τ = 2
    325 → 298; the median written-twice share 0.409 → 0.148.
* **Text to add if finding 108's change is bundled, both changes over main:**
  * **The four cubes in blocks of 256:** merge-penalized ERL up on 4 of 4, by a median +23.0% at τ = 4 (+7.5% to
    +32.1%) and +12.4% at τ = 2; merges at τ = 2 277 → 258; the median written-twice share 0.251 → 0.033.
  * **All ten:** up on 10 of 10, by a median +31.2% at τ = 4 (+7.5% to +90.3%) and +36.2% at τ = 2; merges at τ = 2
    325 → 297; the median written-twice share 0.409 → 0.043. Over the trim alone, up on 10 of 10 at τ = 4, by a
    median +10.2%.
  * **Against one block:** eight blocks reach 0.704 to 1.110 of the same cube's merge-penalized ERL at τ = 4 (main:
    0.557 to 0.932).
* **What it costs there:**
  * Coverage at τ = 4 falls on every cube: by a median 3.5% with the trim (2.0% to 6.7%), and 2.3% with both changes
    (1.1% to 6.2%).
  * Of 910 face crossings, 148 are lost with the trim and 125 with both, against 84 on main.
* **Limits to state:**
  * Seven of the ten cubes are in the base model's training set. The three that are not rose +7.5%, +32.1% and +57.4%
    at τ = 4 with both changes.
  * No cube ran at villa's default block size of 512.
  * `s5_16997_03497_03997_256` stays at 0.704 of its one-block ERL with both changes (main: 0.587). Not diagnosed.
  * With these added, "eight cubes, all Scroll 3" in "Limits" above becomes eighteen cubes of Scrolls 1, 3 and 5.
* **Records:** finding 109's registration, `docs/preregistration/2026-11-09_afv_generator_seam_confirmation.md`,
  script, `scripts/afv_generator_seam_confirmation.py`, and report, `reports/afv_generator_seam_confirmation.md`.

## Option: bundle the cross-block change (finding 108)

Prepared 2026-11-09 from [finding 108](../reports/afv_generator_cross_block_duplicates.md), whose registered verdict is
`SUPPORTED`. It is not in the body above.

* **What it fixes:** with the trim, two blocks' copies of a fiber still lie along each other where both blocks read it,
  and both are written. `compare()` classifies them as duplicates, but `_compare_pair` lets only `strict_duplicate`
  (a median 0.20 voxel) suppress one. Each block fits its splines to its own field, so the copies lie a few tenths of
  a voxel apart.
* **The change:** `extend/catalog.py` +18/−2 (`cross_block_duplicate`, its call in `_compare_pair`'s branch for
  sources of different blocks, and the comment there), and two tests in `test_stitch.py` (+34). The patch is
  `repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch`, on top of the trim. The local villa
  branch `fiber-generator-cross-block-duplicates` holds both changes.
* **For bundling:**
  * villa allows three open PRs and two are open, so a second PR has no slot.
  * The change was measured on top of the trim. Alone, it would be measured against a base villa does not have.
* **Against:** the PR grows from 47 to 65 added lines of code and comments in three files, further from the small fixes
  villa merges most readily.
* **Text to add if bundled:**
  * **The change:** "`extend/catalog.py`: where two sources come from different blocks, a copy that `compare()`
    classifies as a duplicate of the other (the shorter copy, inside the longer one's box ± `MAX_P90`) is suppressed,
    as a strict duplicate is. Sources of one block are never compared so, and adjacent fibres of one block are kept."
  * **Measurement, over the trim alone on the eight cubes:** merge-penalized ERL up on 8 of 8, by a median +5.7% at
    τ = 4 (+2.5% to +10.2%) and +5.4% at τ = 2; merges at τ = 2 386 → 384; the median written-twice share
    0.104 → 0.032.
  * **Both changes over main:** a median +17.6% at τ = 4 (+6.3% to +31.0%) and +13.2% at τ = 2, with merges at τ = 2
    439 → 384. As a fraction of the same cube run as one block, eight blocks reach 0.905 to 1.026 at τ = 4 (main:
    0.703 to 0.923).
  * **How often it bites, the 1024³ zone at block 512:** the written length beside a same-family copy falls from
    0.052 with the trim to 0.017 (main: 0.120). In the cube, ERLpen rises +3.4% at τ = 4 over the trim, and +20.0%
    over main.
  * **Tests:** two blocks' copies of one fiber 0.3 voxel apart are written once, and twice with
    `cross_block_duplicate` disabled, as main does. Two fibres 2 voxels apart, seen by both blocks, stay two; main
    writes four.
  * **Limits:** measured on top of the trim only. Two distinct fibres less than 1.5 voxels apart, where both blocks see
    both, could be merged; on the eight cubes merges and coverage did not move against the change, and the test
    covers fibres 2 voxels apart.
  * **Records:** finding 108's registration, `docs/preregistration/2026-11-09_afv_generator_cross_block_duplicates.md`,
    script, `scripts/afv_generator_cross_block_duplicates.py`, and report,
    `reports/afv_generator_cross_block_duplicates.md`.
* **villa #2434** (open, by another contributor) edits another part of `_compare_pair`, for ends meeting at a shared
  point. The two merge cleanly in `catalog.py`, and only `test_stitch.py` conflicts, where both add tests at one spot.
