# Resume note — written 2026-09-22 before a deliberate Claude restart

## 2026-10-03 (night): finding 74 via inkagree; inkagree public at 0.2.2

* **Finding 74:** the tutorial's slice step 0.5 agrees best with villa's labels (vs 0.25: 8 of 8, about
  −5% AP; vs 1.0: 7 of 8, about −11%; vs 2.0: 8 of 8, about −38%). Predictions 2 and 3 FAILED (seven failed
  predictions are now disclosed in the October draft). `reports/sampling_band_vs_labels.md`.
* inkagree is public (`github.com/jonmarrs/inkagree`, 0.2.2). Real use found two bugs: the CLI separator,
  and the missing imagecodecs dependency.
* Disk: `spiral_out/band_cache` (the band study's chunk cache) can be deleted with the user's OK.


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
