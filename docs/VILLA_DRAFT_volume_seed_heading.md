# Draft: fiber volume tracing seeds every dot the CT gives a heading, as training does

**NOT POSTED.** Held for a slot: villa's three-open-PR cap is full (#2141, #2258, #2259, checked 2026-10-25). The owner
approved proposing the change on 2026-10-25; posting needs the steps below first.

The patch is `repro/fibers/villa_volume_seed_heading.patch` (+23/−4: two lines removed from `_seed_heading`, one
docstring line, a new 21-line test). The measurement is finding 100 (`reports/neural_tracer_steep_heading.md`,
pre-registered), its `keep` arm. That arm gave each skipped dot villa's own signed CT axis, which is exactly what the
patched `_seed_heading` returns (bound by `tests/test_villa_draft_volume_seed_heading.py`).

## Before posting

1. **A slot.** One of our three open villa PRs has closed. Code-fix PRs are at most two a week.
2. **Re-verify against villa's main of that day.** `_seed_heading` and the module docstring unchanged (the patch
   still applies), and no PR or issue already covers it (`gh search prs --repo ScrollPrize/villa "seed heading"`).
   Checked 2026-10-25 at `322cb0899`: the patch applies; `_seed_heading` is unchanged since our pin `ccb431818`;
   #2165 changed the pool's chunking in `seed_headings` (the output order is kept) and rewrote the structure
   tensor's filtering in `shared/ct_structure.py`, both described as exact. The only related open PR, #2265, is
   VC3D's C++ fiber tracer, not this code.
3. **The GPU re-run on villa's main, if the owner approves it** (it pauses the autoresearch loop for minutes). The
   measurement is at `ccb431818`, before #2165, which says it keeps outputs exact. Until then the Details section
   says so.
4. **The owner's own commentary.** villa's CONTRIBUTING requires human-written commentary for LLM-assisted PRs, and a
   motivation from real use. The bracketed paragraph below is for the owner to write. Never check the
   personal-verification box on the owner's behalf.
5. **No AI-authorship markers** in the commit or the body, including `Co-Authored-By`.

---

**Title:** `fiber volume: trace seed dots whose CT axis is far from the presence direction, as training does`

**In one sentence:** Volume tracing now traces every seed dot the CT gives a heading for, signed along the dot's
presence direction as training's seeds are, instead of skipping the dots whose CT axis lies more than 35° from that
direction.

**One real example:** Starting with the scan around the ScrollGT fiber cube `s5_16997_03997_04497_256` (Scroll 5,
7.91 µm; `scrollprize/fiber_single_small` at its defaults), `tracing.volume` skipped 316 of the cube's 895 seed dots on
the 35° test. With this PR it traces them: coverage of the cube's hand-traced fibers rises from 0.268 to 0.343, and
precision from 0.499 to 0.510.

**Before:** `_seed_heading` returns `None` when the CT axis for the dot's family lies more than 35° from the dot's
presence direction, and the dot is never traced. Training does not skip on this: `data/seeds.py` and
`data/targets.py` seed with `oriented_seed_heading`, which signs the CT axis along the direction however far apart they
lie ("exactly as in inference and collection", its docstring says). The VC3D service and `tracing/inference.py` do
not skip either.

**After this PR:** Each dot is traced from the CT axis, signed along its presence direction. A dot is still dropped
when the CT gives no heading (`SeedHeadingError`).

**Proof:** 21 ScrollGT v0.9.0 fiber cubes, each traced with the scan around it and scored with ScrollGT's fiber scorer
(version 3, tolerance 2) against its hand-traced ground truth. The ten cubes ScrollGT's reference mask never trained
on, before → after:

| cube | dots skipped before | coverage | precision | merge-penalized ERL |
|---|---|---|---|---|
| s5_13497_01497_02497_256 | 242 of 910 | 0.333 → 0.369 | 0.364 → 0.347 | 11.41 → 12.55 |
| s5_16997_03997_04497_256 | 316 of 895 | 0.268 → 0.343 | 0.499 → 0.510 | 9.87 → 11.82 |
| s3_00994_00494_01994_512 | 740 of 10,029 | 0.643 → 0.649 | 0.486 → 0.472 | 34.65 → 34.95 |
| s3_00994_01994_00494_512 | 384 of 10,860 | 0.649 → 0.651 | 0.594 → 0.591 | 42.08 → 42.53 |
| s3_00994_02494_01494_512 | 960 of 10,879 | 0.571 → 0.579 | 0.507 → 0.495 | 29.60 → 29.02 |
| s3_01994_01494_00994_512 | 676 of 9,513 | 0.578 → 0.585 | 0.560 → 0.551 | 32.12 → 31.84 |
| s3_01994_01994_01494_512 | 646 of 10,503 | 0.597 → 0.603 | 0.544 → 0.537 | 32.06 → 32.72 |
| s3_02994_02494_01994_512 | 127 of 11,925 | 0.674 → 0.678 | 0.555 → 0.553 | 41.50 → 41.79 |
| s3_03494_01494_00494_512 | 539 of 10,154 | 0.611 → 0.615 | 0.664 → 0.652 | 35.03 → 35.03 |
| s3_04494_00994_01494_512 | 455 of 11,576 | 0.623 → 0.625 | 0.538 → 0.533 | 26.25 → 25.67 |

What to look at: the two Scroll-5 cubes gain 1.11× and 1.28× coverage, where the skip dropped 0.27 and 0.35 of the
seed dots. On Scroll 3 coverage rises on all eight cubes, by 1.003–1.012×. Precision moves by −0.017 to +0.011. On the
eleven cubes the reference mask trained on, the skip dropped only 3–166 dots per cube, and coverage moves by
0.996–1.003×, precision by at most 0.002.

[Attach `reports/figures/villa_volume_seed_heading_s5_16997.png`.] The image shows `s5_16997_03997_04497_256`'s
hand-traced fibers, projected along z, marked where a traced fiber passes within 2 voxels, as ScrollGT's scorer counts
coverage. Orange is the 0.091 of the ground-truth length covered only with this PR. Red is the 0.016 covered only on
main. Most of the orange runs diagonally in this view.

**Why / where this is useful:** [The owner's own words: what we were doing with the tracer when we found this, and why
it matters to someone tracing fibers.] Where the sheets are steep, the CT's axis for an H fiber (the sheet's
horizontal line) often points away from the fiber, and those are the dots the skip drops. On the two Scroll-5 cubes
the share of dots in sheets tilted more than 45° is 0.84 and 0.78. Anyone tracing such a region with `tracing.volume`
gets more of its fibers. Elsewhere almost nothing changes.

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

* **Measured at `ccb431818`, before #2165.** `_seed_heading` is unchanged since, so the patch applies to `322cb0899`
  as written. #2165 says it keeps outputs exact. [The GPU re-run on current main, if done.]
* **How:** villa's own `tracing.volume` `main()`, with only `seed_headings` swapped for a copy that changes what
  happens to a dot that fails the 35° test. With the dots still skipped, that copy first reproduced villa's run of
  `s5_13497_01497_02497_256` point for point. Launcher, registration, data and scoring:
  https://github.com/jonmarrs/vesuvius-autoresearch (`scripts/neural_tracer_heading_arm.py`,
  `reports/neural_tracer_steep_heading.md`).
* **Not touched:** `seed_heading_policy` in `run.json` names the CT heading, which training shares, so it is unchanged.
  A run started before this change therefore resumes under the new rule. If such a resume should be refused, one more
  field in the volume's `run.json` record does it.
* **A heading along the sheet recovered more** on those two cubes: the presence direction projected into the CT's
  sheet plane gave 1.20× and 1.43× coverage. That is a new rule the model never trained on, so it is not proposed here.
* **Limits:** the gain is on two cubes of one scroll, both cubes on which ScrollGT's reference mask also does poorly.
  One checkpoint at its defaults. The presence is a substitute: ScrollGT's `fiber_hz_vt` probability, not lasagna's.
  The CT is 7.91 µm, read on a 2-voxel trace grid; the checkpoint trained at 9.6 µm.
* **Tests:** the new `fibers/tests/test_volume_seed_heading.py`, run at `322cb0899`. Without the change 5 of its 9
  cases fail (the dots at 36°, 60°, 89°, 91° and 120°); with it all 9 pass, and so do the 11 in
  `test_volume_performance.py`. Run on Python 3.10.19; the package asks for 3.14 (our tracer environment, which has
  it, has no pytest).
