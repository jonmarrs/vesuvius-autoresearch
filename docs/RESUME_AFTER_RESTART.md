# Resume note — written 2026-09-22 before a deliberate Claude restart

## 2026-10-14 (evening): finding 90, the loop's model does not read ink better from deep windows

* **Finding 90** (`reports/loop_model_depth_offset.md`, pre-registered, CPU). The loop's 400-patch draw, every
  patch kept, scored with every read forced to start at one zarr slice. The incumbent reads AUC 0.5856 at z0 = 0 and
  0.5765 at z0 = 7, its lowest of the eight starts; the 10 loop candidates move by −0.0043 on average (9 of 10
  negative). Reading: **no dependence on the window's position**. Finding 89's lever (pin `depth_band` [11, 27])
  has no support from the models the loop has; a model trained only on deep windows is untested.
* Not pre-registered: each patch at its own random start (how the loop validates) gives AUC 0.5717, below every
  fixed start (0.5765–0.5875) on the same patches. A property of the measurement, not of reading.

## 2026-10-14: finding 89, the detector reads ink mostly from its deepest slices

* **Finding 89** (`reports/detector_depth_ablation.md`, pre-registered at `f9d892b0`, CPU). On control B's 400 random
  Fr143 windows the detector keeps 16 of its 26 channels at the loop's window offsets. AUC 0.7034 falls by 0.0756
  (window zarr 4–19), 0.0381 (8–23) and 0.0208 (11–26): by the rule, it depends on the position. Equal-sized
  removals differ 3.6-fold, so the signal sits in zarr 20–26 (layers 36–42); both fills agree.
* The loop's windows start uniformly at zarr 4–11, so they hold 0 to 7 of those slices. Untested lever, the owner's
  call and separate from finding 88: `depth_band` [11, 27] pins every window to zarr 11–26.

## 2026-10-14: finding 88 corrected; its readings stand, one claim withdrawn

* Validation shifts every patch by up to half a patch (`VesuviusLabeledDataset`, `jitter=True`). Finding 88's A
  and C first read the detector at the pre-shift `valid_coords`, so it was scored against targets a median 16 px
  away. Fixed in `9acb865a` (`patch_origin`, `check_origins`); any script that reads its own windows beside a
  validation patch must use `patch_origin`. The incumbent's and candidates' scores, and B, were unaffected.
* Re-run: A's detector margin +0.0010 → +0.0025 (tiled +0.0062 → +0.0147); C's +0.0655 → +0.1014; D's val_f1
  ratio 2.78 vs 10.71 → 3.71 vs 16.98. All three pre-registered readings unchanged.
* Withdrawn: "ROC AUC and AP lift point the same way". They separate comparably on both samples (12.16 vs 15.14,
  18.70 vs 19.82), so promoting on AP lift with the current sample (finding 86's option 3) is level with keeping
  the ink-free patches on separation. The difference is what the loop promotes on.

## 2026-10-13 (night): finding 88, the loop's sample cannot reward a model that reads ink

*Corrected 2026-10-14 (above): the numbers below are the first run's.*

* **Finding 88** (`reports/detector_on_loop_sample.md`, four pre-registered CPU measurements). On the loop's 97
  ink-containing patches the TimeSformer detector (fragment-wide AUC 0.709) clears the all-ink F1 by only +0.0010
  (+0.0062 tiled), while promotion needs +0.0263. A random-window control confirms the pipeline (AUC 0.7034). On the
  same 400-patch draw with its ink-free patches kept, the detector clears it by +0.0655 and the incumbent by +0.0042.
* So the loop, as configured, cannot promote even a detector-quality model; of finding 86's options keeping the
  ink-free patches separates them by far the most. Owner's decision; adopting it means a new protocol, a re-score,
  and a fresh noise probe (the 0.03 tolerance was measured under v1).
* D, scaled by the loop's own candidates: 10 cycle snapshots (`local_data/loop_candidates/`, kept by
  `scripts/snapshot_loop_candidates.sh`), scored on both samples. The detector-minus-incumbent val_f1 gap is 10.71
  candidate SDs with the ink-free patches kept against 2.78 on the loop's sample, so the recommendation stands. None
  of the 10 would be promoted under the new sample; all 10 beat the incumbent there by +0.0034 to +0.0224.

## 2026-10-13 (evening): developing while the loop runs

* The loop trains from the main checkout: never switch branches there while it runs. Work in a worktree made by
  `scripts/dev_worktree.sh add <branch>` (shared `.venv`, `local_data`, `checkpoints` and `models`, villa checked out
  at the pin; remove with `scripts/dev_worktree.sh remove <branch>`).
* Run Python in a worktree with `UV_NO_SYNC=1` or `uv run --no-sync`. A syncing `uv run` re-points the shared
  `.venv`'s editable install at the worktree, and the loop's spawned DataLoader workers would import that code;
  the mypy hook now runs `uv run --no-sync`. Tests import their own checkout's `src/` regardless
  (`pyproject.toml` `pythonpath`, `tests/conftest.py`).
* Never run `uv sync` in the main checkout: the `vesuvius` package is installed from `villa/vesuvius`, outside
  `uv.lock`, and an exact sync removes it. (`vesuvius_c` is too, from an ignored leftover of villa's deprecated
  vesuvius-c, villa #1128; nothing here imports it.)

## 2026-10-13 (evening): lasagna off, incumbent re-scored; the loop can start

* Owner's call: get the loop running. `config.json` `use_lasagna: false`; the loop's `use_lasagna` tweak is pinned
  to `[False]` (restore `True` only once the warp runs on the GPU and inference applies it too).
* `best_model.pt` re-scored with `scripts/reevaluate_best_model.py --update-stored --unwarped`: val_f1 0.727323
  under `seeded-sample-400-v2+z1-27` (97 of 400 patches), all-ink F1 0.730993, margin -0.003670, AUC 0.5615.
  A candidate must reach val_f1 > 0.757323 with AP lift > 1.02 to be promoted.
* A 30 s isolated cycle (`checkpoint_out` set) warm-started 288/288 tensors, validated with 0 batch errors and 0
  lasagna fallbacks. Start with `./start.sh`; the watchdog keeps it running.
* Still open: the promotion metric (margin over the floor, ink-free patches, or AP lift / AUC), and the untested
  depth-of-context difference (the detector reads 26 slices, the loop 16).

## 2026-10-13 (afternoon): finding 87, the depth band was in layer numbers; corrected to `[1, 27]`

* **Finding 87** (`reports/ink_depth_profile.md`, read-only, not pre-registered). The fragments' zarrs are 33 slices
  (surface-volume layers 16–48), so `depth_band: [17, 43]` (the detector's layer files) lay past the volume and every
  dataset build refused it. In zarr slices the detector's band is `[1, 27]`; `config.json` now says so (protocol
  `seeded-sample-400-v2+z1-27`), guarded by `tests/test_config_depth_band_fits_fragments.py`.
* Under protocol v2 every validation window already contained layer 32; ink contrast is weak at every depth. The depth
  hypothesis does not explain finding 86's near-constant incumbent. Still open for the owner: lasagna, the promotion
  metric, and whether to keep the band at all.

## 2026-10-13: depth band implemented; the loop will not start until re-scored

* Patches now read inside `depth_band: [17, 43]` (`config.json`); the validation protocol is
  `seeded-sample-400-v2+z17-43`. The loop prints "Not starting" until the incumbent is re-scored.
* Order on the GPU host: check the fragments' depth (at least 43 slices), **decide lasagna** (the
  re-score applies the incumbent's recorded `use_lasagna: true`, which strict reads refuse on uint8),
  then run `scripts/reevaluate_best_model.py --update-stored` and `./start.sh`. See
  `docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-13_LOSSES_AND_UPDATE.md`, "Restarting the loop".

## 2026-10-12 (night): finding 86; the loop migration is HELD for owner decisions

* **Finding 86** (`reports/loop_v2_constant_control.md`, post-hoc, not pre-registered). The GPU-host dry run of
  `scripts/reevaluate_best_model.py` scores the incumbent at 0.7271 under protocol v2, but calling every pixel ink
  scores 0.7310 on that sample (ink prevalence 0.5760). Against each sample's all-ink floor the incumbent went from
  +0.0548 (v1, one strip) to −0.0039 (v2); AUC 0.6689 → 0.5527. The re-score tool now prints the floor and both margins.
* `use_lasagna: true` has been a silent no-op in every logged loop run: this host has no `nvcc`, so the loader returns
  unwarped patches (980 + 2,185 fallback warnings in `run.log.old` / `run.log`).
* **Not run, deliberately:** `--update-stored`, the commit, `scripts/f1_noise_probe.py` (its sigma would be squeezed
  by the all-ink ceiling) and `./start.sh`. Owner decisions listed in the report: lasagna (toolkit, config, or fail
  loudly) and the promotion metric (margin over the floor, ink-free patches, or AP lift / AUC).
* Ruled out as a villa PR: villa's skeleton metric raising on `wandb.log` without a run. villa's own `evaluate.py`
  always calls `wandb.init`, so only standalone callers (ours, fixed in #42) hit it.

## 2026-10-12 (evening): findings 84–85 folded into the October draft; #1934 reply posted

* **POSTED 2026-10-12 20:23Z:** the finding-85 reply on villa #1934
  (https://github.com/ScrollPrize/villa/pull/1934#issuecomment-6131993208). User-approved, with the ScrollGT paragraph
  removed at the user's direction. It used the day's villa reply slot. No nudges; read and record any reply.

* ScrollGT **v0.7.0** is tagged and re-vendored (vesuvius-autoresearch #34 + #35, main `e3d99e53`).
* The October draft now carries finding 84 (the Scroll-5 miss is real: no frame offset, no threshold rescue, 20–25%
  of the fiber unseen) and finding 85 (#1934's generator covers 19–38%; ScrollGT's old ERL flattered it). Sixteen
  failed predictions disclosed. Bound by `tests/test_filing_2026_10_numbers.py`.
* The reply's draft and pre-post checks are in `docs/VILLA_DRAFT_1934_afv_generator.md`. At posting, #1934's head was
  still `2d8577ed` (the measured commit).
* villa #1928 (inkdelta catalogue) is still open, last updated 09-29: the bot will likely close it ~10-13. Record it and
  let it go.
* Next villa new item no earlier than 10-16. Upstream `origin/main` (`4eecd08fd`) is 9 commits past our pin, and
  `scripts/check_villa_render_path.py 9afddaf0f 4eecd08fd` exits 1. #1863 changed `render_ink.py` (help text only:
  `--remote-url` deprecated, and no spiral caller uses it) and `vc_render_tifxyz.cpp` (remote-URL volume loading). The
  sampler change reaches a render only through an image rebuild. Treat renders across the two refs as not comparable
  until checked.

## 2026-10-11 (late): #2044 merged; villa pin bumped to it

* **villa #2044 MERGED** 2026-10-11 18:49 PDT (@pmh47, `9afddaf0f`). Seven merged in all; only #1928 is open.
* Merged here: #25, #27, #28, #30, #31. ScrollGT #3 merged and **v0.6.0 tagged**; CI green.
* **The pin moved `be09a8503` → `9afddaf0f`** (118 commits, fast-forward) at the user's request. `ink-detection/`
  changed only in `optimized_inference/` (4 files); `train_scrolls` is untracked local data and is untouched. No
  deleted or renamed villa file is referenced here.
  * **The spiral render path changed:** `lasagna/fit.py` (the flatten), `render_ink.py`, `tifxyz.py` and
    `get_ink_metrics.py` (`scripts/check_villa_render_path.py be09a8503 9afddaf0f` exits 1). A new render is not
    comparable with the `be09a8503` corpus unless it sets `VILLA_REF=be09a8503`, which still resolves. Unpinned renders
    follow the submodule's `origin/main`, now `9afddaf0f`.
* **Next:** ScrollGT v0.7.0 (headline ERL×coverage), then fold findings 84–85 into the October draft, then the
  finding-85 comment on villa #1934 for the user's approval.

## 2026-10-11 (night): September paid $250 for merged villa PRs only; villa fixes first

* **September result:** $250, "for assorted useful merged villa PRs". The repos, ScrollGT and the findings were not
  cited. The user chose: villa fixes first, fiber work second; code-fix PRs up to 2/week (the 3-open cap still binds).
* **villa #2022 MERGED** 2026-10-11 (@pmh47). Only #1928 is open.
* **Next villa PR, drafted and measured, NOT posted** (branch `villa-draft-ink-metrics-folds`):
  `get_ink_metrics --sequential-folds` plus in-place fold averaging. Stock is OOM-killed on an outer strip in a 26 GiB
  budget; sequential scores it at 13.8 GB. It needs the user's go-ahead. Push it via the GitHub API per the SOP, with
  no AI markers.
* **Findings:**
  * 84 (PR #27): the Scroll-5 held-out miss is real, not a frame offset or a threshold.
  * 85 (PR #28): the AFV generator covers about 25% of the hand-traced fiber.
  * **ScrollGT's ERL is coverage-conditional:** deleting fragments raises it. ERL×coverage is exact. The fix awaits
    the user's decision.
* **ScrollGT 0.6.0:** PR #3 open; all 10 held-out targets built. After merge: tag v0.6.0, check CI.
* **October draft:** PR #25. It leads with merged villa PRs; add each new merge.

## 2026-10-11 (evening): finding 83; ScrollGT held-out split in progress

* Merged: vesuvius-autoresearch #19 (finding 82) and ScrollGT #2. **ScrollGT v0.5.0 tagged** on `af4ab23` (CI green).
* **Finding 83** (prereg `8a7b2d4f`, report `2281b68c`, **PR #24** to main, merges cleanly). All 10 held-out cubes
  pass the gate.
  * P1 FAILED: Scroll-3 median connected-components coverage is 0.826, against 0.822 in sample. No drop.
  * P2 held: the two new Scroll-5 cubes are at 0.64 and 0.53.
  * P3 held 10/10, P4 held 8/8.
  * Post-hoc voxel recall of villa's label agrees (`scripts/fiber_mask_vs_label.py`).
* **ScrollGT 0.6.0** (branch `heldout-split`, not yet pushed):
  * Its new `add_fiber_target` tool writes a target only if every row equals finding 83's.
  * 10 `held_out` targets; held-out tables in BASELINES, bound to the generator by a new ScrollGT test.
  * `aggregate_fiber_scores` refuses to mix held-out and in-sample cards; the report labels a held-out card.
  * Targets are built by a detached script (`add_heldout_targets.sh` in the session scratchpad). If the session dies,
    re-run its command for each missing `data/fibers_<cube>`.
* **Still waiting on the user:** the generator entrant (prereg `c5b3d6ae`). Everything is ready, but the auto-mode
  classifier blocks running the PR's code. The user can allow it or run `repro/fibers/run_afv_generator_chain.sh`.
* October draft (deadline 10-31): fold in findings 82–83 and ScrollGT 0.5.0/0.6.0 once their PRs are merged.

## 2026-10-11: ScrollGT's fiber ground truth audited; held-out split running

* **Finding 82** (vesuvius-autoresearch PR #19, open): villa's fiber-skeletons Dataset004 revised 3 of ScrollGT's 11
  fiber cubes (+21% to +37% fiber length). Re-scored, pre-registered: no ranking reverses. Connected-components
  coverage (the mask's recall) falls from 0.88–0.93 to 0.76–0.82. `fiber_hz_vt`'s training fingerprint matches
  Dataset002, so it trained on all 11 targets. PR #19 also corrects finding 80's "3.9–6.3×" to 3.9–6.2×.
* **ScrollGT PR #2** (branch `current-annotations`, 0.5.0, open): the 3 targets on Dataset004, NML provenance on all
  11, card field `ground_truth_nml`, in-sample disclosure. After merge: tag v0.5.0 and check CI.
* **Held-out split** (prereg `8a7b2d4f`, branch `fiber-heldout-split`, stacked on PR #19): 10 Dataset004 cubes the
  mask never trained on (8 × Scroll 3 512³, 2 × Scroll 5 256³). The chain `repro/fibers/run_heldout_chain.sh` started
  2026-10-11 03:19, detached. It is resumable, writes to `spiral_out/fiber_heldout/run/`, and the analysis runs at its
  end. Then: report, finding 83, ScrollGT `held_out` split.
* **Waiting on the user:** running villa PR #1934's `.afv` generator (Qualzz) as a ScrollGT entrant would execute
  unmerged third-party code and unpickle a third-party checkpoint. A sparse clone is at `spiral_out/afv_gen/pr1934`
  (`2d8577ed`), not installed or run. `scripts/afv_to_labels.py` (`64cc8dd6`) turns any `.afv` into a ScrollGT
  labelling.


## 2026-10-09: villa #2022 opened; tracer re-score in flight

* **villa #2022 is OPEN** (the runner-doc fix): gate 33/33 at `a329895ea`. The next new villa item is no earlier than 10-16.
  No nudges.
* **Fiber scorer** standardized on ScrollGT's definition (v4 here = ScrollGT v2), with a vendored sync test. ScrollGT
  v0.4.0 is released.
* **Tracer re-score** (prereg `f5f775c3`, Amendment 1 `aa1c5712`): the 8 cubes at 256³ are done, with exact fidelity.
  P2 FAILED (s5_14997). The 512³ cubes are running with `--detect-block 128`. The chain is resumable:
  `TRACE_EXTRA="--detect-block 128" repro/fibers/run_tracer_rescore.sh`, with output in `spiral_out/tracer_rescore/`.
* Full suite after PRs #8-#15: 2504 passed.


## 2026-10-04 (later): findings 77 and 78; in-sample caveat

* **Finding 77:** labels exist only inside `supervision.zarr`. Findings 71–76 were re-analysed there:
  74 does not survive as stated, and 75 survives smaller. inkagree 0.3.0 evaluates supervised-only.
* **Finding 78:** the registered tracking-gap test held but was weak (near-duplicate arms).
  * Descriptive: villa's scorer marks 0.91% of the annotated region, about 2% of labelled ink.
  * **villa's ink training set is exactly the 8 labelled segments, with no validation masks.** The ink3d
    render may be in-sample on them. This is disclosed in the October draft and the inkagree README
    (`eb33a33`).
* villa upstream at `5a4388f08` (#1947/#1948: prize automation and docs). It does not touch
  `spiral-fitting/autoresearch.md`; the October form URL and deadline match the draft.
* **Next:** runner PR on or after 10-06 (gate first). The October filing is due 10-31.
* **Soft-count study DONE: finding 79** (`reports/soft_count_study.md`). P1 failed (pinned R 0.91), P2 held
  barely, P3 held (current R 0.52). It is NOT recommended to villa; S trades inward for outward sensitivity.
* **Fiber scorer:** autoresearch v3 is `e28be06d` (PR #7 plus the zero-length-edge fix). ScrollGT `main` was fixed by an
  external contributor (scrollgt#1, Luke Finigan, a path walk). Release 0.4.0 is in progress on the local branch
  `release-0.4.0`: version stamp, guard, notice; the 512³ floors are being verified. Then the full suite, merge, tag, push.


## 2026-10-04: finding 75 (install route vs villa's labels)

* At the metric's settings, the source build's band beats the published image's (8 of 8, about +8% AP),
  and step 2.0 beats 1.0 (8 of 8, about +10%). Both predictions FAILED. The October draft carries it.
  `reports/install_route_band_vs_labels.md`.
* Disk: `spiral_out/route_cache` (253 GB) was DELETED on 2026-10-04 with the user's approval.
* A possible villa item (NOT drafted): this answers #1588's stale-image question with labels, but #1588 is
  under the no-add rule. The user decides.


## 2026-10-03 (night): finding 74 via inkagree; inkagree public at 0.2.2

* **Finding 74:** the tutorial's slice step 0.5 agrees best with villa's labels (vs 0.25: 8 of 8, about
  −5% AP; vs 1.0: 7 of 8, about −11%; vs 2.0: 8 of 8, about −38%). Predictions 2 and 3 FAILED (seven failed
  predictions are now disclosed in the October draft). `reports/sampling_band_vs_labels.md`.
* inkagree is public (`github.com/jonmarrs/inkagree`, 0.2.2). Real use found two bugs: the CLI separator,
  and the missing imagecodecs dependency.
* Disk: `spiral_out/band_cache` (44 GB, the band study's chunk cache) was DELETED on 2026-10-03 with the
  user's approval. 944 GB free.


## 2026-10-03 (late): inkagree 0.1.0 built locally; publishing awaits the user's OK

* The user chose to turn this month's label check into a tool. **inkagree** is at
  `projects/inkagree`, local commit `45e3345`, **no remote yet**.
  * It renders a segment's 3D ink prediction onto villa's label frame and compares two arms: exact
    AP/AUC, an alignment gate (flat → aligned, no ink → undetermined), and a paired bootstrap.
  * It reproduces findings 71 and 72 exactly (16/16; `reports/inkagree_validation.md`).
  * Clean-venv install works; 21 offline tests pass.
* **Next:** with the user's approval, create a public `jonmarrs/inkagree`, push, and check CI. Then
  consider adding it to the October draft (only once it's public).


## 2026-10-03: render chunk cache DELETED (user approved)

* `spiral_out/interp_smoke/vchome` (399 GB: VC3D's remote cache of the public `v3-78k-fullsup` ink-3d
  zarr) was deleted on the user's explicit instruction. Free disk went from 550 GB to 948 GB. Every result
  derived from it is committed. A new render on `vc-render:sampler-f637f3b35` re-streams it from S3.


## 2026-10-03 (evening): finding 73; the f70/f72 gap explained

* **Finding 73:** grid cell size drives the linear/smooth difference.
  * On 80-voxel grids (segment meshes subsampled 4×, like spiral surfaces) the count moves a 6.2%
    median per window (−32% to +42%), −7.9% to +19.4% per segment.
  * The scorer's label agreement does not consistently change (P2 FAILED). The raw render is slightly
    more faithful under smooth (resolved in 6 of 8, about 1–2% of AP; secondary).
* Shared-p95 test: per-crop normalisation is NOT the cause (prediction failed).
* inkdelta 0.5.2 quotes both grid scales. The October draft now discloses five failed predictions and
  stays test-bound (8 tests).
* **The #1818 line is complete (f70–f73).** No further #1818 studies are planned.


## 2026-10-03: October filing DRAFT exists

* `docs/PRIZE_FILING_2026-10_DRAFT.md` is in the four-part shape, and every number is bound by
  `tests/test_filing_2026_10_numbers.py`. The test caught my +4.2%, which is +4.1%. **Not
  submit-ready:** villa hasn't published the October form. Add the runner PR after 10-06, and re-read
  the whole Progress section of `34_prizes.md` on filing day.


## 2026-10-03 (later): finding 72, the #1818 line closed

* **Finding 72:** in villa's own pipeline, smooth moves the scorer count about 1% per window (tail ±9%)
  and its label-AP not at all. Prediction 1 failed (15% vs 25% of windows ≥ 5%); prediction 2 held. Finding
  70's ±20% now carries a scope correction (it used per-crop p95). **#1818 line: closed.** Smooth is
  neither better nor worse for reading by villa's labels; don't mix modes (inkdelta 0.5.0).
* **Disk: the chunk cache `spiral_out/interp_smoke/vchome` is 399 GB** (552 GB free). Ask the user
  before deleting it.


## 2026-10-03: finding 71, villa labels on the current frame

* **Finding 71:** against villa's labels (8 Scroll-1 segments, 2.4 µm frame) smooth vs linear renders
  are equally faithful: ΔAP ≈ −0.0001, verdict no consistent difference. With finding 70 this points at
  the 2D scorer's sensitivity (inferred). `reports/surface_interpolation_vs_labels.md`.
* **Next study (not started):** score these labelled segments' renders with villa's 2D scorer, linear
  vs smooth, and test whether its count swings while its agreement with the labels does not.
* **Strategic, for the user:** villa's labels on the current frame make
  `gt-training-data-exhausted` stale and erode ScrollGT's premise. Not acted on.
* Disk: the chunk cache `spiral_out/interp_smoke/vchome` is now **157 GB**, and
  `spiral_out/gt_interp/study` is 2.5 GB. Delete only with the user's OK.


## 2026-10-02: finding 70 (villa #1818 smooth interpolation), inkdelta 0.5.0, merges

* **Finding 70:** #1818's default is byte-identical to earlier builds. `smooth` moves per-window ink
  from −20% to +18% (pooled −1.3%), beyond a post-hoc control (≤ 2.8%). My registered prediction
  failed. `reports/surface_interpolation_relocates_ink.md`. **inkdelta 0.5.0** (`1b5b7df`) flags
  mixed modes. Not posted to villa: it would be a candidate item, and it needs approval and a slot.
* Image `vc-render:sampler-f637f3b35` is built. The remote chunk cache
  `spiral_out/interp_smoke/vchome` is **118 GB** and can be deleted with the user's OK.
* Merged two upstream changes today (`bd8b95f7`; PR #1 `20df4cb0`) and fixed the mypy/ruff errors
  that blocked every Python commit (`90739342`).
* **Villa runner PR:** the gate passes except the SHA check (upstream moved). On 10-06, update the
  body SHA and re-run `scripts/check_villa_runner_pr.py`.


## 2026-09-29 (late): villa runner PR APPROVED for ≥ 2026-10-06, conditional on re-checks

* The user approved opening the autoresearch.md runner PR once the weekly slot opens, on condition
  that everything is double-checked on the day. Procedure: top of
  `docs/VILLA_DRAFT_autoresearch_runner_section.md`. Gate:
  `scripts/check_villa_runner_pr.py`, which passed 33/33 on 09-29 and fails correctly at an older ref.
* The pre-post audit found three more silent failures, all now in the patch:
  * `FIT_SPIRAL_CONFIG_OVERRIDES` from the environment is dropped, so variants run as the baseline;
  * `WANDB_MODE=disabled` is overridden;
  * `--output` must be empty.
  The patch now also fixes the launch.sh recipe (line 160), which it had left contradicting itself.

## 2026-09-29 (evening): inkdelta 0.4.0, finding 69

* villa's shipped `runners/run_single.py` does not write the layout `autoresearch.md` documents. It
  writes `seed-<s>/` dirs and no logs. inkdelta 0.3.0 called runs in that layout INVALID. **0.4.0
  (`65f63ba`, pushed, CI 8/8) reads it.** Both corpus validations are unchanged.
  `reports/villa_runner_layout_vs_autoresearch_doc.md`.
* villa doc-defect PR **drafted only**: `docs/VILLA_DRAFT_autoresearch_runner_section.md`. It needs
  the user's approval and the next weekly slot (≥ 10-06). The open question is answered: the
  documented runner was never in villa's tree. The draft now carries a 7-line patch. It also records
  a silent failure: pinned by `CUDA_VISIBLE_DEVICES` without `--gpus`, the shipped runner fits as one
  process (`scripts/probe_villa_runner_gpus.py`).
* #1928: open, vercel comment only. Do not nudge or push to it. **Nothing is running.**

## 2026-09-29 — SEPTEMBER PRIZE FILED

* Filed by the user on 2026-09-29; tagged `submission/2026-09` at 93df6a26. The form asked for URLs
  plus a four-part contribution answer. The October form URL will differ again, so re-read
  `34_prizes.md` next month.
* **Nothing is running.** Villa #1928 is open; do not nudge.

## 2026-09-29 update

* **B is DONE:** villa catalogue PR **#1928** is open (+2/−0). Do not nudge; the bot auto-closes it
  after 14 idle days.
* **The same-winding extension** has `s4` and `s5` scored; `s6` has been rendering since 03:50.
  Run `scripts/analyse_samewinding_extension.py` when `SEQUENCE DONE` appears. The filing test
  then fails until both filing texts quote the new primary interval.

## CURRENT STATE, 2026-09-28

* **RUNNING since 2026-09-28 13:49 PDT, detached:** the same-winding extension
  (`docs/preregistration/2026-09-28_samewinding_extension.md`, committed 2a3db396 before the first
  fit). `run_arm_sequence.sh` fits, renders and scores `nosamecur_s4`, `s5` and `s6`, with
  `VILLA_REF=be09a8503`. Log: `spiral_out/samewinding_ext_chain.log`. It takes ~18 h, and the chain
  resumes if restarted with the same command. When `SEQUENCE DONE` appears, run
  `python3 scripts/analyse_samewinding_extension.py`. It applies the gates, and a failing arm is
  re-rendered, not dropped.
* **inkdelta 0.3.0** (d5e6e0f) is released: a measured `--cv` floors the Welch interval.

* **B tomorrow (2026-09-29 or later):** the draft is ready and pre-checked. The duplicate search was
  clean on 09-28, and `pip install git+…` was tested. Re-run the search on the day, read the live
  Segmentation → Tools section, then open the PR. No AI markers. A maintainer has 14 days before the
  bot auto-closes it; **do not nudge**.
* **Filing (user files by 09-30):** the SUBMIT text changed on 09-27. It now adds the all-nine-seed
  same-winding interval, −2.89% [−7.98%, +2.19%] (`reports/control_sensitivity.md`). All ten artifacts
  the filing test reads were regenerated on 09-28. Nine were identical. `noise_floor_by_tier.json` was
  stale (it still held the withdrawn 0.0263); it is fixed, and the test now catches staleness.
* **Research, 09-27/28:** inkdelta's second validation passed (7 registered intervals reproduced). It
  found the survey's two wrong rows and the "cross-tree" stage error: every current-tier fit ran from
  one unchanged `d8c5f488a` copy, and the split is at the render. Findings 67 and 45 are corrected.

## (previous) CURRENT STATE, 2026-09-27 evening

**October plan (user chose "A, then B"):**

* **A: DONE.** `inkdelta` 0.1.0 is public at https://github.com/jonmarrs/inkdelta, validated 6/6
  pre-registered (`reports/inkdelta_validation.md`). A cold clone installs and passes.
* **B: step 3 is TODO on or after 2026-09-29.** Run a duplicate search, then open the villa catalogue
  PR from `docs/VILLA_DRAFT_catalogue_inkdelta.md`, with no AI markers.
* **The September filing** now cites inkdelta in Field 3 (test-bound). **File by 09-30.**


**2026-09-27 later:** villa PR **#1886** (@ItIsCuthNotCup, merged by @pmh47 09-25) fixes our **#1660**, citing
it. The filing's Field 2 credits it as "a report acted on, not a measurement adopted", and
`scripts/check_filing_upstream_claims.py` live-verifies it (PASS). Field 1 also carries findings 65–66.
**The filing is complete: re-read Fields 1–2 and file by 09-30.** No comment posted on #1660 or #1886.

**Nothing is running.** Step-2 across surfaces DONE (finding 66): +4.97% to +9.19%, mean +6.48%, all positive. `reports/step2_across_surfaces.md`. Not posted to villa (no-nudge rule on #1588).

**Sampler line concluded (finding 65, `reports/source_sampler_cannot_complete_here.md`):**
* `--cache-gb` does not bound resident memory in either the published or the source build.
* villa PR #1905 lets the current source build complete our render.
* The current sampler reads the volume identically, but steps 2× along the normal (villa #1146, 07-14,
  after the 05-13 image). That makes `total_fg_pixels` **+5.32%** on our surface (3,279,498 → 3,453,819;
  re-score floor 59 px).

**Outward, POSTED with the user's approval after verification:** a reply on villa **#1588** (the
stale-image tracker) with that measurement, comment 5852564965, 2026-09-26. **Do not add to it or nudge.**
No new issue was opened; the weekly new-item slot is still 2026-09-29.

Scratch caches: **DELETED 2026-09-27** with the user's approval (530 GB; free disk 445 → 975 GB). 18 merged worktrees and their local branches removed. **October: user chose A (objective-hygiene checker) then B (catalogue listing)** -- `docs/NEXT_DIRECTIONS_2026-10.md`.

**STOPPED 2026-09-26 04:59 — the amended source-sampler re-run died the same way (exit 137 at band 2,
now under a 24 GB cap; 88 GB cache written). No sampling verdict; finding 65 records the resource
regression. Nothing is running. `spiral_out/vc3d_src_home` (88 GB) kept pending a decision.**

(was) **IN FLIGHT since 2026-09-26 04:42: amended re-run of the two SOURCE sampler arms** (amendment in
`docs/preregistration/2026-09-25_sampler_from_source.md`, committed `cc5c6e0b`). Persistent remote
cache at `spiral_out/vc3d_src_home`, `--memory 24g`. Log `spiral_out/sampler_rerun_chain.log`;
terminal `SAMPLER_RERUN_DONE`. When done:
`.venv/bin/python scripts/analyse_sampler_from_source.py --out reports/sampler_from_source_verdict.json`.

**(earlier) STOPPED 2026-09-25 22:42 — sampler-from-source chain: `RENDER_FAILED smp_src_a`, exit 137 (SIGKILL,
likely OOM — the source-built sampler defaults to `--cache-gb 16` and ran ~6× slower than the
published one, 2/35 bands in 8 min).** `smp_pub` completed. No verdict: the rule needs both source
arms. Nothing is running. Next: re-run the source arms with a bounded cache (a registered
amendment, since it changes a sampler setting) — ask first. Original entry:

**(was) IN FLIGHT since 2026-09-25 22:05: sampler-from-source study** (`docs/preregistration/2026-09-25_sampler_from_source.md`,
committed `1a8c685c` before any arm). `detfit_up1`'s own flat surface is re-sampled by the published
sampler (`smp_pub`) and by `vc_render_tifxyz` built from villa `75c79ac5f` (`smp_src_a/b`, image
`vc-render:sampler-75c79ac5f`). Chain pid 282526 (parent systemd --user). Log
`spiral_out/sampler_src_chain.log`; terminal `SAMPLER_CHAIN_DONE`; failures
`*_FAILED|SMP_ABORTED|WRAPPER_EDIT_FAILED|PATCH_FAILED`. When done:
`.venv/bin/python scripts/analyse_sampler_from_source.py --out reports/sampler_from_source_verdict.json`.

The upstream render-path study is DONE (finding 64):
RENDER PATH INERT, +0.0005% on fixed meshes. `reports/upstream_render_path_is_inert.md`.
Filing Field 1 now carries one test-bound clause on it.

**Upstream-fitter re-measurement DONE (finding 62).** Chain finished 09-25 09:33, all gates passed.
NO DETECTED CHANGE: **+4.82%, CI [−7.51%, +17.15%]** for three fits on villa `75c79ac5f` vs
`curbase_s4..s9`, everything after the fit held at `be09a8503`. `reports/upstream_fitter_no_detected_change.md`.
The September filing's Field 1 now quotes that interval instead of "not re-measured" (test-bound).
**Review Field 1 before pasting; deadline 09-30.** The upstream tree is `villa-spiral-upstream`
(own venv); its fits are tier `upstream` in `scripts/arm_tiers.py`.

## STATE AT 2026-09-24 ~17:15 — history

**Upstream moved 2026-09-23/24 (checked at villa `75c79ac5f`).** #1887 added "release model weights and
training data where applicable" to the Progress criteria (filing's Field 3 now answers it; form URL and
deadline unchanged). #1871 "Spiral simplification" removed dense-spacing, unverified patches and the
influence anchor loss; absolute- and same-winding supervision survive. The filing now dates its
numbers to `be09a8503`; **nothing has been re-measured on the simplified fitter.**

**Added 2026-09-24 evening: spiralcheck validated (finding 61).** The community evaluator, run on the
twelve pooled-floor fits under a pre-registration, is **NOT DISCRIMINATING HERE**: no config separation,
no within-config ink tracking, seed CV 7.4% on its violated fraction. One post hoc lead (outer-winding
gap *shape* changes under the anchor ablation; the mean gap does not). `reports/spiralcheck_is_not_discriminating_here.md`.
The September filing's Field 1 now carries one test-bound paragraph on it (**review before pasting**).
No note to spiralcheck's author has been sent; that needs approval.

**Nothing is running and nothing is queued.**

**`--cache-gb 8`: NOT ADOPTED (decided 2026-09-24).** The re-run on an idle box showed no useful memory
saving (27.2 GB vs 27.8 GB) and ~3× slower bands, so the byte-identity check was stopped as moot. It is
**not a result**; both stops are logged in `spiral_out/cache_gb_check.log`. Keep the default. See
`repro/spiral_render/README.md` section 14.

**Done and on main this week** (see `reports/SPIRAL_FINDINGS_SUMMARY.md`, findings 54–60): pooled
fit-only floor 0.0736 [0.051, 0.134]; no free offset lever; flatten transmits a mesh offset (T = 0.94);
scorer translation-invariant; half-pixel re-sampling suffices; scorer and render both amplify.
**Nothing else is queued.**

**Outward:** villa 5 merged (#1721/#1722/#1780/#1805/#1842), **0 open**, #1866 **closed by @pmh47 with a
reason** (spiral stage non-deterministic too; noise notes not useful to agents): do not reply, do not
propose another noise note. #1723/#1728 bot-closed. The September filing
(`docs/PRIZE_FILING_2026-09_SUBMIT.md`) is current and its live checker passes. **Deadline 09-30.
Re-read villa's `34_prizes.md` for the form URL at filing time.**

**The pin** is still `be09a8503`. Upstream has moved; a bump needs `scripts/check_villa_render_path.py`
and must not happen mid-study.

## What survives the restart, and what does not

| | survives? | why |
|---|---|---|
| **The pooled-floor chain** (`run_pooled_chain.sh`, pid was 3937955) | **YES** | Launched `setsid nohup … & disown`; its parent is `systemd --user`, not `claude`. Verified by walking `/proc/<pid>/stat` ppid to init. |
| Renders/scoring it spawns | **YES** | children of the chain |
| **Monitors** (`Monitor` tool watches) | **NO** | session-scoped; they live under the `claude` process and end with it |
| Background `Bash` tasks | **NO** | same, and they were already being reaped mid-session |
| Repo state, registrations, decision code, tests | **YES** | committed and pushed; `main` @ `a9dd1710` |
| `~/.claude/.../memory/` | **YES** | on disk, loaded next session |
| Conversation context | only with `claude --continue` / `--resume` | otherwise reconstruct from this file + MEMORY.md |

## What is in flight

**Pooled fit-only floor study** — `docs/preregistration/2026-09-22_pooled_fit_only_floor.md`.
**DONE 2026-09-22 22:30:** pooled fit-only CV **0.0736 [0.0506, 0.1344]**, df = 9, band BETWEEN (the
point estimate is 0.0014 under the 0.075 edge; the interval spans all three bands), MDE 3v3 **16.8%**.
Predictions 1 and 2 met. `reports/the_pooled_fit_only_floor.md`. Step 3 below ran automatically.
(Original note: six arms, one done (`detfit_ns1`, −0.56% vs stock), five to go.)
Log: `spiral_out/pooled_chain.log`. Each arm ~2.5 h, so the twelve-arm sample lands ~01:00 on 09-23.

**Do not compute anything from a partial sample** — `scripts/analyse_pooled_fit_only_floor.py`
refuses fewer than twelve arms by design, and the refusal is the point.

## On restart, do this

1. **Check the chain is still alive** (it should be):
   ```
   pgrep -u "$USER" -x bash | while read p; do tr '\0' ' ' < /proc/$p/cmdline | grep -q run_pooled_chain && echo "alive: $p"; done
   grep -cE ARM_DONE /home/jon/openclaw-workspace/Neo-VM/spiral_out/pooled_chain.log
   ```
2. **Re-arm one monitor** on the chain (the others watched finished logs and are not worth restoring):
   ```
   tail -n 0 -F .../spiral_out/pooled_chain.log | grep -E --line-buffered "ARM_DONE|GUARD_FAILED|RENDER_FAILED|SCORE_FAILED|POOLED_CHAIN_DONE|Traceback|Killed|OOM"
   ```
   The upstream-villa watcher (`check_villa_render_path.py` driver) is also worth re-arming; it has
   caught two real sampler-path changes this week.
3. **When all six finish**, run the registered analysis and nothing else first:
   ```
   ./.venv/bin/python scripts/analyse_pooled_fit_only_floor.py --json reports/pooled_fit_only_floor.json
   ```

## Queued behind it, already registered and coded

**Ink-maximum offset sweep** — `docs/preregistration/2026-09-22_ink_maximum_offset.md`,
decision code `scripts/analyse_ink_maximum_offset.py`, tests green.
Needs four arms built (`offset_m2`, `offset_p1`, `offset_p2`, `offset_p3`) from
`radial_work_rad0/meshes/concat/w120-129_flat` via
`scripts/build_radial_displacement_arm.py --single`.
**Build them only when the machine is idle** — mid-chain there is ~1 GB RAM free and 12 GB of swap
in use; see the pre-launch checklist in `docs/preregistration/TEMPLATE.md`.

**QUEUED 2026-09-22 13:14, detached** (pid 3980709, own session, off the claude tree):
`spiral_out/run_offset_sweep_after_pooled.sh` (committed copy:
`repro/spiral_render/run_offset_sweep_after_pooled.sh`), log `spiral_out/offset_sweep.log`,
per-arm render logs `spiral_out/offset_<arm>.render.log`. It waits for the pooled chain's pid, and
**only if the log ends in `POOLED_CHAIN_DONE`**: runs the pooled analysis first (step 3 above —
so that step is already done when you arrive), then builds and verifies all four surfaces (achieved
shift, `z.tif` byte-identical to `flat0`, same valid points and axis), stages each from
`flat_study_zero`, renders serially with `RENDER_REUSE_FLATTEN=1`, **kills the arm if the reuse
line does not appear** (the fallback silently re-flattens), checks the docker image id against the
pinned one, and finally runs `analyse_ink_maximum_offset.py --json reports/ink_maximum_offset.json`.
Expect results ~09:00–10:00 on 09-23. Markers to grep: `OFFSET_SWEEP_ABORTED|BUILD_FAILED|GUARD_FAILED|RENDER_FAILED|SCORE_FAILED|ARM_DONE|OFFSET_SWEEP_DONE`.

**RUNNING 2026-09-23 15:24 (pid 2954):** `spiral_out/run_resampling_or_distortion.sh`, log
`spiral_out/resampling_or_distortion.log`, registration
`docs/preregistration/2026-09-23_resampling_or_distortion.md`. Two renders with the flatten reused:
`rs_t005` (half-pixel re-sample, primary) then `rs_t05`, then the analysis. Results due ~19:30–20:00.
Scripts run from byte-identical copies in `spiral_out/rsd_scripts/`. Markers:
`GUARD_OK|ARM_DONE|RSD_DONE|FAILED|ABORTED`. All earlier queued studies are DONE and on main.

**STATUS 2026-09-23 10:58.** Offset sweep DONE: NO FREE LEVER (`reports/no_free_offset_lever.md`). The
`--cache-gb 8` check was **STOPPED by the operator** at band 7/34 after ~4 h (bands of 75–84 min,
~15 h ETA). NOT a result: byte identity is untested. It is logged in `spiral_out/cache_gb_check.log`;
remove `spiral_out/cachetest_g8` before any re-run. Interim: at 8 GB the sampler still held ~23.7 GB
with 2.58M faults, so the cache is not the main consumer. The transmission study was relaunched at
once with `NO_WAIT=1` (pid 4145720), and the scorer test was re-queued behind it (pid 4145827).

**Behind the sweep, also detached (pid 3984839, since stopped, see above):** `spiral_out/run_cache_gb_check_after_sweep.sh`
(committed copy in `repro/spiral_render/`), log `spiral_out/cache_gb_check.log`; its result goes to
reports/cache_gb_check.json, which does not exist until the check has run. An engineering
check, not a study. It runs only if the sweep logged
`OFFSET_SWEEP_DONE`, re-renders `flat_study_zero`'s surface into `cachetest_g8` with `--cache-gb 8`,
and byte-compares all 11 outputs. `IDENTICAL` means future studies may adopt the setting, which
should stop the swap thrash. `NOT_IDENTICAL` means they may not. **Never adopt it mid-study either
way.** Reasoning: `reports/holding_the_flatten_fixed_collapses_the_floor.md`, 2026-09-22 addendum.

**Third in line, detached (pid 4013391):** `spiral_out/run_flatten_transmission_after_cache_check.sh`
(committed copy in `repro/spiral_render/`), log `spiral_out/flatten_transmission.log`. It implements
`docs/preregistration/2026-09-22_does_the_flatten_transmit_a_mesh_offset.md`: two deterministic
flatten-only arms (render stubbed, about 11 min each) of the ±4 vx pre-flatten meshes. It runs only
if the cache check logged `CACHE_CHECK_DONE`. It answers whether villa's loop could REACH an offset
lever from fitting code. T ≈ 1 is expected by construction (the flattener optimises only a 2D map), so
a T ≈ 1 result is a confirmation.

**Fifth, detached (pid 4028148):** `spiral_out/run_scorer_translation_after_transmission.sh`
(committed copy in `repro/spiral_render/`), log `spiral_out/scorer_translation.log`. It runs its
builder and analysis from byte-identical copies in `spiral_out/stx_scripts/`, NOT from the repo, so it
does not depend on its branch being merged. It implements
`docs/preregistration/2026-09-22_scorer_translation.md`: ten scoring-only arms of `rad0`'s strip,
offset by up to 512 px as lossless PNG, about 3 h. It runs only if the transmission study logged
`TRANSMISSION_DONE`. Why: `rad0`/`rad0b` cover the same strip area (0.998) yet differ 3.04% in ink
DENSITY, so this asks whether the scorer's tile placement alone moves the objective.

If the pooled chain FAILS, the sweep does nothing (exit 3) — decide whether to re-run the pooled
arm first, then relaunch with `CHAIN_PID=<new chain pid>` or, with no chain running, remove the wait.

## Outward state

- **villa PR #1866** open (flatten determinism), posted 2026-09-22. **Do not nudge.**
- **villa PR #1842** open (fraction guard). Both count against villa's 3-open cap.
- Next new-PR slot under the standing 1/week rule: **2026-09-26**.
- **September prize filing** submit-ready at `docs/PRIZE_FILING_2026-09_SUBMIT.md`, deadline
  **2026-09-30**. Re-read villa's `34_prizes.md` for the form URL at filing time — it has changed
  three months running. Upstream claims re-verified 2026-09-22: PASS.

## The pin

Submodule is at `be09a8503` and **must not move** while the chain runs — every arm's `VILLA_SHA`
must match or the study's registered failure branch voids the pooled figure. Upstream is ~42 commits
ahead; that is expected and fine.
