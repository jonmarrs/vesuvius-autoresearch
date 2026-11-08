# Draft: villa's fiber generator writes a fiber twice where a block border bends both blocks' copies

**NOT POSTED.** Prepared 2026-11-07 from [finding 106](../reports/afv_generator_block_seams.md), whose registered
verdict is `SUPPORTED`. Whether to post, and in what form, is the owner's decision.

**Recommended form: a PR.** This fixes a defect in villa's own active code (`cli.generate` → `extend.stitch`, what VC3D
runs). villa merges fixes of that kind, and the patch is ready:
`repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch`, the amended one.

## Before posting

1. **The owner decides,** and writes the motivation paragraph below. Never tick the verification box for them.
2. **villa's limits:**
   * At most three open PRs. All three slots were taken on 2026-11-06 (#2463, #2464, #2465).
   * At most two code-fix PRs a week. Both were used on 2026-11-06, so not before about 11-13.
3. **Re-check villa main of that day:**
   * `extend/stitch.py` and `cli.generate` are unchanged where the patch applies (`git apply --check`).
   * The catalogue's overlap tests (15° at the ends, a strict duplicate within 0.65 voxel) are still as measured.
   * No PR or issue already trims cut ends: search "block border", "duplicate" and "stitch".
   * #2434 (open, by another contributor) changes `_compare_pair` in `extend/catalog.py`, not these lines. It still
     names the module `afv_spline_generator`, which villa main now calls `fiber_spline_generator`. Its "Not changed"
     note saw the symptom on synthetic straight fibers: cite it, and say how this differs.
4. **A real-use example at villa's own defaults** would answer "how often it bites" directly: a zone of more than one
   512 block, main against patched. The measurement below uses blocks of 256 on 512³ cubes, because the hand-traced
   cubes are 512³. A 1024³ zone at block 512 needs no hand tracing for the written-twice share. On the GPU it takes
   minutes (the owner's decision); on the CPU about a day.
5. **Size:** the patch is 47 lines of code and comments in two files, plus 54 lines of tests. That is above the 4–25
   lines our fixes usually are. The comment block above `CUT_END` can be cut if villa prefers.
6. **No AI-authorship markers** in the commit or the body, including `Co-Authored-By`.

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

**What it costs:** more crossings of the block faces are lost. Of 1,304 places where a hand-traced fiber crosses a
block face, 278 are lost with the trim against 172 on main. Whole ones rise from 853 to 884, and broken ones fall from
279 to 142. The changes run both ways, and 176 crossings are chained only with the trim. Of the 198 crossings worse with
the trim, 63 are joins main made that the trimmed copies miss. Three reasons come up most often, in about equal
measure (a crossing can have more than one):
* the trimmed overlap is shorter than `MIN_OVERLAP` (29);
* one copy lies along the other but fails the strict duplicate test, so both stay unlinked (28);
* another overlap at the same end makes the candidate ambiguous (27).

In 125, the copies were never chained. A trimmed copy reaches 16 voxels past the face instead of 32. Where the
neighbouring block's copies are short or miss the fiber, that stretch is no longer covered. Merge-penalized ERL counts
both, and it rises on every cube.

**How often it bites:** on every zone larger than `--block-size` along any axis (the VC3D dialog shows "N blocks to
process"). The dialog's default zone, 512³ at block 512, is one block and is not changed.

**Why / where this is useful:** [The owner's own words: what we were generating fibers for, and what the duplicated
copies cost when using the output.]

- [ ] I personally verified that the measurement above was produced by this change on the stated data.

## Details

* **What ran:** the generator's own modules at villa main `7e6b82164` (`predict.predict_fibers`,
  `splines.extract_splines`, `extend.stitch`, `cleanup.ExteriorBlack` and `cleanup.clean`), called block by block as
  `cli.generate` calls them, not `cli.generate` itself. The measurement used the patch's first form, which keeps an
  end only at the volume's border. On these cubes the zone is the whole volume, and there the two forms trim alike;
  that was checked on 1,000 random blocks.
* **Limits:**
  * Blocks of 256, not villa's default 512. A 512³ hand-traced cube has one inner face per axis only at 256.
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
    `reports/evidence/afv_generator_seam_diag_2026-11-07.json`.
