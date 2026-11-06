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
after #2316 moves fiber I/O to `vc_object_store`. **October 28:** the real-data
re-run (step 3) is now at `39a8cf3a`, with the measured patch. It traced with
`--no-fibers`, so #2316's object-store export itself did not run: a local CT
crop has no open-data volume to bind.

The [finished-tile export check](VILLA_OBJECT_STORE_EXPORT_CHECK.md) now prepares
the CPU-only export/readback part of that verification on a configured host.
It plans by default, uses an isolated copy of a closed real-data run and checks
both exports against its original tile geometry and identities. Its fixture
tests are not native integration evidence; the current-main volume-tracing
CLI comparison is still required before posting.

**November 3: the pre-registered confirmation on ten unseen cubes** ([finding 103](../reports/seed_heading_confirmation.md),
decision `NO_HIGH_SKIP_CUBE`). None of the ten skipped 20% of its dots, so the coverage gain was not tested there and
still rests on finding 100's two cubes. The fix's cost stayed within the registered bounds at tolerance 2. The body
below says only what that decision allows.

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

   **Changed again: villa #2316 (`39a8cf3a`, 2026-10-26) moved fiber export from `.afv` to `vc_object_store`.** Rechecked
   2026-10-28. Villa's `vesuvius/` was the same at that day's main, `7154682e1`. Findings:
   - The patch still applies (one hunk moved by one line).
   - `_seed_heading` is unchanged.
   - Villa's tests give the same result as at `322cb0899`: the same five seed-heading cases fail without the patch,
     and all 20 tests pass with it. This time the performance tests ran beside them unpatched too (5 failed, 15
     passed; at `322cb0899`, 5 failed, 4 passed). They ran under the tracer's Python 3.14 because #2316's `volume.py`
     imports the native store (`reports/evidence/villa_volume_seed_heading_tests_39a8cf3a.txt`).
   - Of the modules the tracer loads, #2316 changes only the export, a fiber-JSON parser and comments.
   - No villa PR or issue but #2165 matches "seed heading".

   The run had to be repeated, because #2316 changed what the run writes. #2316's tracer writes its fibers at
   the end as an object store bound to an open-data volume. A local CT crop has no open-data volume, so
   `repro/fibers/run_villa_seed_heading_rerun.sh` passes `--no-fibers` and the run's tiles are its fibers. The
   comparison now reads every run's fibers from its tiles. On the recorded `322cb0899` runs that reproduces their
   comparison exactly, and every run's tiles give its `.afv`'s fibers point for point
   (`reports/evidence/villa_volume_seed_heading_rerun_322cb0899_from_tiles.json`).

   **Done 2026-10-28 at `39a8cf3a`**, with the owner's approval. The loop paused 14:34–14:39, after a cycle that was
   not one of #264's arms had started (`repro/fibers/run_villa_seed_heading_rerun_paused.sh`). The results:
   - Without the patch, the traces are identical point for point to finding 97's runs.
   - With it, they are identical to finding 100's `keep` arm.
   - The two differ from each other (`reports/evidence/villa_volume_seed_heading_rerun_39a8cf3a.json`).
   - The follow-up patch's resume tests at `39a8cf3a` give the October 26 counts
     (`reports/evidence/villa_volume_seed_resume_tests_39a8cf3a.txt`).

   **Changed again: villa #2440 (`baf5e605b`) moved the tracer's CT reading to the native `vc_reader`.** Checked
   2026-11-04 at villa main `2d4067b52`, without running anything:
   - The seed-heading patch no longer applies. `_seed_heading` now calls `ct_seed_heading(_WORKER_CT, _WORKER_SPEC,
     ...)`, which changes the hunk's context. The 35° test the patch removes is unchanged, so the behaviour it fixes is
     still on main.
   - The patch's villa test stubs `ct_seed_heading` with three arguments, `(vol, xyz, family)`. At main it is called
     with four, `(ct, spec, xyz, family)`, so the test needs rewriting with the patch. The resume patch still applies
     on its own.
   - `tile_dots` now smooths presence with `vc_reader`'s `GaussianBlur` instead of `ndimage.gaussian_filter`, so the
     seed dots may differ from `39a8cf3a`'s. The GPU re-run is due again.
   - Importing `tracing/volume.py` loads `vc_reader` directly and `vc_object_store` through `volume_store` and
     `fiber_store`. Neither is built for this commit here, so villa's tests and the re-run wait for both builds.

   **Rebased 2026-11-05 onto villa main `eab6108b9`**, as one patch for both changes,
   `repro/fibers/villa_volume_seed_heading_eab6108b9.patch` (+72/−5; local villa branch
   `fix/volume-seed-heading-main`, commit `a8eaea9aa`, not pushed). Its `volume.py` hunks are the two patches' hunks
   unchanged. Both tests needed rewriting for main:
   - The heading test's stand-in for `ct_seed_heading` now takes four arguments, `(ct, spec, xyz, family)`.
   - The resume test now replaces `open_zarr`, which reads the presence on main where `zarr.open` did, and gives the
     spec an `input_scale`. On 11-04 the resume patch was said to apply on its own. It does, but its test would have
     failed at main: `volume.py` no longer imports `zarr`.

   Villa's tests ran with the native `vc_reader` and `vc_object_store` replaced by stand-ins, because neither is built
   here (`repro/fibers/run_villa_seed_heading_tests_stubbed.sh`,
   `reports/evidence/villa_volume_seed_heading_tests_eab6108b9_stubbed.txt`):
   - Without the patch, 7 of the 12 new cases fail: the same five headings (36°, 60°, 89°, 91° and 120°) and the same
     two resume cases as at `39a8cf3a`. With it, all 12 pass.
   - Villa's three other volume test files give the same outcomes on both sides, failure for failure. Most of their
     cases fail on both sides because they need the real readers.

   This checks the patch's logic, not villa's tracer on real data. The real builds, villa's tests with them and the
   GPU re-run are still due before posting.

   Inspect an existing work directory without running traces or loading arrays:

   ```sh
   python3 scripts/seed_heading_chain_status.py status --work /path/to/W
   ```

   Exit 0 means all four latest attempts logged `DONE` and their closed output
   files remain; exit 1 means incomplete, and exit 2 means inspection failed.
   This checks presence, not numerical contents or input identity. The launcher
   exits 1 for failed/incomplete traces and writes `CHAIN_FAILED`; only a fully
   checked chain writes `CHAIN_COMPLETE`. A resume retries a failed or interrupted
   attempt and a run whose outputs disappeared. Its `chain.lock` lease refuses
   another launcher or surviving worker using the same `W`; it is not a global
   GPU reservation. Import/setup refusals exit 3. Historical logs are preserved,
   and comparison uses each run's latest attempt rather than any earlier `DONE`.
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

**Ten cubes these numbers never saw:** the fiber-skeletons cubes that ScrollGT does not ship (Scroll 1 and Scroll 5),
traced the same way before and after this PR. None of them skipped 20% of its seed dots on the 35° test (the most was
0.17), so they do not test the coverage gain, which rests on the two Scroll-5 cubes above. They do bound the cost. On
each of the ten, precision fell by at most 0.013 and merge-penalized ERL by at most 2.7%. At tolerance 4, one cube
lost 6.2% of merge-penalized ERL. On the seven cubes that skipped under 2% of their dots, coverage moved by
0.9998–1.0063×.

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

* **Measured at `ccb431818`, re-checked at `322cb0899` and `39a8cf3a`.** #2165 has since rewritten the tracer's hot
  path and checked each part for exact outputs, and #2316 moved fiber export to `vc_object_store`. On the two
  Scroll-5 cubes, villa's CLI at `39a8cf3a` gives the same traces point for point as at `ccb431818`, both without this
  PR and with it, so their rows above hold on main. It ran with `--no-fibers`, because the inputs are local crops.
  The Scroll-3 and in-sample cubes were not re-run.
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
  The ten further cubes skipped too few dots to test it.
  One checkpoint at its defaults. The presence is a substitute: ScrollGT's `fiber_hz_vt` probability, not lasagna's.
  The CT is 7.91 µm, read on a 2-voxel trace grid; the checkpoint trained at 9.6 µm.
* **Tests:** the new `fibers/tests/test_volume_seed_heading.py`, run at `39a8cf3a` on Python 3.14.3 (and at
  `322cb0899` on 3.10.19). Without the change 5 of its 9
  cases fail (the dots at 36°, 60°, 89°, 91° and 120°); with it all 9 pass, and so do the 11 in
  `test_volume_performance.py`.

The October 26 follow-up adds three resume regressions. With only the measured heading patch, the missing-policy
and old-policy cases fail and the matching-policy case passes. With both patches, all three pass. These tests exercise
the real `main()` settings validation with model/volume construction replaced, stopping before tile loading or GPU
work. The existing heading and performance checks were rerun alongside them; see the dated review record. At
`39a8cf3a` (2026-10-28) the result is the same: two of the three fail with the measured patch alone, and all pass
with both, beside the 9 heading and 11 performance checks.
