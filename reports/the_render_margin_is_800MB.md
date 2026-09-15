# s7 did not fail; the box has been running renders on an 0.8 GB margin all along

**2026-09-14.** Operational, not a research finding. Recorded because it will recur and because
the symptom is misleading.

## What happened

`curbase_s7`'s render was OOM-killed **three times** — 18:17:59, 19:13:31, 20:16:45, each time
`vc_render_tifxyz` at 28.2–28.7 GB anon-rss. The chain retried twice, gave up
(`[fail] curbase_s7 NOT scored after retries`) and moved on to `curbase_s8`. **s7 has no
`metrics.json`, so triplet C is incomplete and the registered analysis will refuse the sample** —
correctly.

## The margin

| | |
|---|---:|
| `MemTotal` | 31.3 G |
| desktop + agent RSS (ChatGPT, gnome-shell, agy, node, claude) | 2.1 G |
| **left for a render** | **29.3 G** |
| **render peak, measured across three kills** | **28.5 G** |
| **margin** | **0.8 G** |

This is not a regression in s7. Renders have been OOM-killed on **Sep 08, Sep 12 and Sep 13** as
well — one each, where the retry then succeeded. The job has always run at the edge; s7 is the first
arm to lose three coin-flips in a row. Anything that moves 1 GB — a browser tab, an extra agent, a
heavy analysis — decides it.

## Why the symptom misleads

While thrashing, the render looks dead: GPU at 0%, log silent for 15+ minutes, the parent
`render_ink.py` asleep on a futex with **3.9 MB RSS** because it is only waiting on its child. The
real work is a 24 GB `vc_render_tifxyz` in a Docker container. **Quiet is not stalled**, and the
parent's RSS says nothing about the job's footprint.

This also exposed a live defect: `scripts/guard_heavy_analysis.py` matched only the villa venv
interpreter, so it reported "no render in flight" during the containerised stage — the one stage
where starting heavy work is most damaging. Fixed the same day; see the commit.

## The levers, in order

1. **More swap.** The swapfile is 8 G and was 6.9 G consumed before the third kill. A render that can
   spill finishes slowly instead of dying. Growing it needs disk — which
   `scripts/reclaim_fit_checkpoints.py` can supply (**39.7 G**, keeping every mesh) — and root, which
   this session does not have (`sudo -n` unavailable).
2. **Free ~1 GB of desktop memory.** The ChatGPT app alone holds ~765 MB RSS plus ~1.6 GB of swap
   across its processes. On an 0.8 GB margin that is decisive on its own.
3. **Nothing else is free.** Lowering the render's own footprint means changing `--scale` or the
   winding range, which changes what is being measured, and is not available mid-study.

## The deadline that matters

`curbase_s8`'s fit started 20:17 and takes about 3 hours. **Its render then meets the same 0.8 GB
margin**, as will s9's. Unless the margin is widened first, the chain spends roughly 12 more hours
producing two more unscored arms and the study cannot complete.
