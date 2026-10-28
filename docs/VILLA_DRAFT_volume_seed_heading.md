# Draft: fiber volume tracing stops skipping seed dots on the 35° test, as training does

**NOT POSTED.** Held for a slot: villa's three-open-PR cap is full (#2141, #2258, #2259, checked 2026-10-25). The owner
approved proposing the change on 2026-10-25; posting needs the steps below first.

The patch is `repro/fibers/villa_volume_seed_heading.patch` (+23/−4: two lines removed from `_seed_heading`, two
docstring lines reworded, a new 21-line test). The measurement is finding 100 (`reports/neural_tracer_steep_heading.md`,
pre-registered), its `keep` arm. That arm gave each dot that fails the 35° test villa's own signed CT axis, which is
exactly what the patched `_seed_heading` returns (bound by `tests/test_villa_draft_volume_seed_heading.py`).

**October 26 review:** apply `repro/fibers/villa_volume_seed_resume.patch` after that measured patch.
It records `seed_heading_selection='signed_ct_axis_v1'` in `run.json`, so the existing settings check refuses
to mix tiles from the old 35° rule with new tiles. The original measured patch and GPU records stay unchanged;
the follow-up changes run compatibility, not the fresh-run heading calculation.
Both patches are pushed as `jonmarrs/villa:fix/volume-seed-heading` at
`d1de9ec1e2e17ecd0f06754041141dfda243ddb3`;
[compare the prepared branch](https://github.com/ScrollPrize/villa/compare/main...jonmarrs:fix/volume-seed-heading?expand=1).

**October 27 source check:** both patches apply to Villa main `39a8cf3a`
after #2316 moves fiber I/O to `vc_object_store`. This is an application check,
not a new CLI or GPU run. The real-data re-run below remains at `322cb0899`;
verify the object-store CLI path before posting. The older AFV command is not
evidence that the new integration has run successfully.

The [finished-tile export check](VILLA_OBJECT_STORE_EXPORT_CHECK.md) now prepares
the CPU-only export/readback part of that verification on a configured host.
It plans by default, uses an isolated copy of a closed real-data run and checks
both exports against its original tile geometry and identities. Its fixture
tests are not native integration evidence; the current-main volume-tracing
CLI comparison is still required before posting.

## Before posting

1. **A slot.** One of our three open villa PRs has closed. Code-fix PRs are at most two a week.
2. **Re-verify against villa's main of that day.** `_seed_heading` and the module docstring unchanged (the patch
   still applies), and no PR or issue already covers it (`gh search prs --repo ScrollPrize/villa "seed heading"`).
   Checked 2026-10-25 at `322cb0899`: the patch applies, and `_seed_heading` is unchanged since our pin
   `ccb431818`. #2165 ("without changing inference outputs") has since rewritten the volume tracer's hot path:
   seed headings, path features and advancement, structure tensors, crop sampling and an optional CUDA graph. It
   checked each part for exact outputs, not a whole run. The only related open PR, #2265, is VC3D's C++ fiber
   tracer, not this code.
3. **The GPU re-run on villa's main.** Done 2026-10-25 at `322cb0899`, with the owner's approval (the loop paused
   13:16–13:21). villa's own CLI traced the two held-out Scroll-5 cubes with finding 97's inputs and command. Without
   the patch, the traces are identical point for point to finding 97's runs at `ccb431818`; with it, to finding
   100's `keep` arm (`repro/fibers/run_villa_seed_heading_rerun.sh`,
   `reports/evidence/villa_volume_seed_heading_rerun.json`). If villa's tracer changes again before posting, re-run
   it.
4. **The owner's own commentary.** villa's CONTRIBUTING requires human-written commentary for LLM-assisted PRs, and a
   motivation from real use. The bracketed paragraph below is for the owner to write. Never check the
   personal-verification box on the owner's behalf.
5. **No AI-authorship markers** in the commit or the body, including `Co-Authored-By`.

---

**Title:** `fiber volume: trace seed dots whose CT axis is far from the presence direction, as training does`

**In one sentence:** Volume tracing no longer skips the seed dots whose CT axis lies more than 35° from the dot's
presence direction: as training's seeds do, they take the CT axis signed along that direction.

**One real example:** Starting with the scan around the ScrollGT fiber cube `s5_16997_03997_04497_256` (Scroll 5,
7.91 µm; `scrollprize/fiber_single_small` at its defaults), `tracing.volume` skipped 316 of the cube's 895 seed dots on
the 35° test and traced 288. With this PR it skips none on that test and traces 507, 251 of them dots that fail it;
the rest of the 895 lie on fibers already written. Coverage of the cube's hand-traced fibers rises from 0.268 to
0.343, and precision from 0.499 to 0.510.

**Before:** `_seed_heading` returns `None` when the CT axis for the dot's family lies more than 35° from the dot's
presence direction, and the dot is never traced. Training does not skip on this: `data/seeds.py` and
`data/targets.py` seed with `oriented_seed_heading`, which signs the CT axis along the direction however far apart they
lie ("exactly as in inference and collection", its docstring says). The VC3D service and `tracing/inference.py` do
not skip either.

**After this PR:** A dot that fails the 35° test is traced like any other, from the CT axis signed along its presence
direction. A dot is still dropped when the CT gives no heading (`SeedHeadingError`) and, as before, when it lies on a
fiber already written.

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

* **Measured at `ccb431818`, re-checked at `322cb0899`.** #2165 has since rewritten the tracer's hot path and
  checked each part for exact outputs. On the two Scroll-5 cubes, villa's CLI at `322cb0899` gives the same traces
  point for point as at `ccb431818`, both without this PR and with it, so their rows above hold on main. The
  Scroll-3 and in-sample cubes were not re-run.
* **How:** villa's own `tracing.volume` `main()`, with only `seed_headings` swapped for a copy that changes what
  happens to a dot that fails the 35° test. With the dots still skipped, that copy first reproduced villa's run of
  `s5_13497_01497_02497_256` point for point. Launcher, registration, data and scoring:
  https://github.com/jonmarrs/vesuvius-autoresearch (`scripts/neural_tracer_heading_arm.py`,
  `reports/neural_tracer_steep_heading.md`).
* **Resume compatibility:** `seed_heading_policy` in `run.json` names the CT heading shared with training and stays
  unchanged. The follow-up patch adds `seed_heading_selection='signed_ct_axis_v1'` to the run record. An old record
  missing that field, or naming another selection rule, is refused before completed tiles are loaded. Start in a new
  output directory to use this change; keep the old implementation to finish an existing run. Do not relabel an old
  record or copy its finished tiles into the new run. A matching new record still resumes normally.
* **A heading along the sheet recovered more** on those two cubes: the presence direction projected into the CT's
  sheet plane gave 1.20× and 1.43× coverage. That is a new rule the model never trained on, so it is not proposed here.
* **Limits:** the gain is on two cubes of one scroll, both cubes on which ScrollGT's reference mask also does poorly.
  One checkpoint at its defaults. The presence is a substitute: ScrollGT's `fiber_hz_vt` probability, not lasagna's.
  The CT is 7.91 µm, read on a 2-voxel trace grid; the checkpoint trained at 9.6 µm.
* **Tests:** the new `fibers/tests/test_volume_seed_heading.py`, run at `322cb0899`. Without the change 5 of its 9
  cases fail (the dots at 36°, 60°, 89°, 91° and 120°); with it all 9 pass, and so do the 11 in
  `test_volume_performance.py`. Run on Python 3.10.19; the package asks for 3.14 (our tracer environment, which has
  it, has no pytest).

The October 26 follow-up adds three resume regressions. With only the measured heading patch, the missing-policy
and old-policy cases fail and the matching-policy case passes. With both patches, all three pass. These tests exercise
the real `main()` settings validation with model/volume construction replaced, stopping before tile loading or GPU
work. The existing heading and performance checks were rerun alongside them; see the dated review record.
