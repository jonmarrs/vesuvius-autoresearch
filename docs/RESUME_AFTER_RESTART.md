# Resume note — written 2026-09-22 before a deliberate Claude restart

## CURRENT STATE, 2026-09-24 ~10:30 — read this first; everything below is history

**Running (detached, pid 81433):** the `--cache-gb 8` byte-identity check, **re-run** on an idle box
(`spiral_out/run_cache_gb_check_after_sweep.sh`, log `spiral_out/cache_gb_check.log`). The 09-23 run
was stopped by the operator and is **not a result**; its partial dir went to the trash. The result lands
in reports/cache_gb_check.json, which does not exist until the check finishes (verdict IDENTICAL or
NOT_IDENTICAL over 11 files). **It is not a speed
fix:** at 8 GB the sampler still held ~23.7 GB. Adopt only on IDENTICAL, via `VC_CACHE_GB`
(`repro/spiral_render/set_cache_gb.sh`), never within a study.

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
