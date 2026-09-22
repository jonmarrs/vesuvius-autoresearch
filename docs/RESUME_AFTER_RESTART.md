# Resume note — written 2026-09-22 before a deliberate Claude restart

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
Six arms, one done (`detfit_ns1`, −0.56% vs stock), five to go: `ns2 ns3 an1 an2 an3`.
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
