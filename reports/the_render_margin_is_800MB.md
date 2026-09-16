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

---

## What was actually reclaimed, 2026-09-14 (executed, not proposed)

Disk went **9.2 G free (100% full) → 52 G (95%)**, reclaiming **41.1 G**:

| what | freed | notes |
|---|---:|---|
| 13 fit checkpoints | 39.7 G | `baseline01`, `nosame_s1-3`, `nosamecur_s1-3`, `anchor10cov_pilot/s2/s3`, `smoke_current`, `smoke_absw5`, `smoke_nosamewind` |
| 12 stopped containers | 1.0 G | all exited 7 weeks–3 months prior, from an unrelated `marketing-engine` project |
| dangling image layers | 0.35 G | plain `image prune`, **not** `-a`, which would have deleted `vc-render:local` (13.6 GB) and cost a rebuild |

**What those 13 arms lost, precisely: the ability to RESUME their fit.** Nothing else. Verified after
the fact, not merely intended:

* 13/13 still have `meshes/fitted_<tag>/` **and** `satisfied_fitted.json` — every one remains
  re-renderable and usable for patch-selection work;
* 8/8 live-study checkpoints survive, `curbase_s8` included, whose fit was running at the time;
* the 9 `outer_*` directories (7.5 G) the analyses actually read are untouched.

Nothing in this project resumes a fit — fits always run fresh from the dataset — so the capability
given up is one that was never used. **If a future study does need to resume one of those 13, it must
refit (~3 h), and that is the whole cost.**

**Disk is no longer a constraint, and it was never the thing that killed an arm.** The 0.8 GB memory
margin above is unchanged by any of this.

---

## Margin widened to 1.4 GB, 2026-09-14 (lever 2 taken)

The ChatGPT app was closed — 12 processes, SIGTERM not SIGKILL, all exited cleanly.

| | before | after |
|---|---:|---:|
| non-villa resident | 2.1 G | **1.5 G** |
| available to a render | 29.3 G | **29.9 G** |
| render peak (measured across 3 kills) | 28.5 G | 28.5 G |
| **margin** | **0.8 G** | **1.4 G** |

Freed ~1.0 G of RSS and ~1.2 G of swap; swap pressure fell from 6.4/8 G to 5.2/8 G, which matters as
much as the RSS — a render that can spill survives where one that cannot is killed.

**This makes a render likely, not safe.** The three kills landed at 28.2, 28.5 and 28.7 G: the peak
itself wanders by about 0.5 G, roughly a third of the new margin. The filename still says 800MB
because that is what was discovered; this section is the correction.

What remains is largely not reclaimable — `claude` (491 M) is the working session, and `agy` ×3 plus
`gnome-shell` total ~680 M. **A decisive margin still needs the larger swapfile, which needs root.**

---

## Lever 1 taken, 2026-09-15: swap 8 G → 24 G, and the mechanism confirmed

A second swapfile was added — `/swap2.img`, 16 G, `fallocate` on ext4 — rather than resizing the
existing one. **Resizing would have required `swapoff`**, forcing ~5 G of swapped pages back into RAM
when only 1.6 Gi was available with a render at 26 G resident. That would very likely have killed the
render and possibly wedged the box. Adding is additive and safe while a render runs.

**The mechanism showed itself immediately.** With swap available, `curbase_s8`'s render RSS *fell*
from 26.0 G to 24.8 G as pages moved out — the kernel spilling instead of having nowhere to put them.
That is exactly what was missing when `curbase_s7` was killed three times against a nearly-full 8 G
swap.

| | before | after |
|---|---:|---:|
| swap | 8 G (5.5 G used) | **24 G** (5.6 G used, ~17 G free) |
| effective capacity | 31.3 G | **~55 G** vs a 28.5 G peak |
| OOM kills during s8's render | — | **0** |

**The trade is speed.** Paging makes a render markedly slower, and the log can go minutes between
writes — the same thrashing signature misread as a deadlock earlier that day. Quiet is not stalled.

Made persistent the same night: `/swap2.img none swap sw 0 0` was appended to `/etc/fstab` and the
entry verified — six fields in the right order, no duplicate of either swapfile, and the file itself
`root:root` mode `600`. Worth verifying rather than assuming, since a malformed `fstab` can block a
boot.

### A defect this exposed in `recover_arm.sh`

Its precheck compared **`MemAvailable` alone** against 30 G. On a 31.3 G box that is never true once
anything is running, so it would have refused forever — and it ignored the quantity that actually
decides the outcome. Capacity is **RAM plus free swap**: a render that can spill survives its peak,
one that cannot is killed at it. Now fixed to sum both and report the split.


### Outcome: s8's render survived the peak

With 24 G of swap, `curbase_s8`'s render held steady at **24.8 G resident with zero OOM kills**,
against the 28.2–28.7 G band that killed `curbase_s7` three times. 1.13 M major faults confirm it was
paging steadily rather than hitting a wall.

The cost is exactly the predicted one: **band 4 of 37 at 30 minutes, ETA ~3 h**, against s7's ~2.2 h
for a comparable strip. A slow render instead of a dead one.

(s8 has **37** bands, not s7's 35 — a detail worth knowing before writing any progress check that
matches a band count, which is how one ad-hoc check of mine reported no progress on a render that was
progressing fine.)

### Overnight outcome: s8 rendered in 194 minutes, and my extrapolation was wrong

`curbase_s8` rendered and scored: **`total_fg_pixels` 2,881,173**, inside the registered validity
gate, with **zero OOM kills** all night. `curbase_s9`'s fit then completed `rc=0` and its render
began.

**The 13+ hour estimate was badly wrong — it took 3h14m.** These renders are *front-loaded*, exactly
as `run_outer_arms.sh` says in a comment written for this purpose:

```
band 31/37  194m01s      band 34/37  194m06s
band 32/37  194m03s      band 36/37  194m07s
band 33/37  194m05s      band 37/37  194m08s
```

Bands 31–37 finished **within eight seconds of each other**. The early bands are slow while the box
builds swap pressure; the late ones are nearly free.

The failure was not the arithmetic but overriding a correct, documented warning with an inference
from five early samples. The driver comment says in terms: *"DO NOT panic at the in-tool ETA, and do
not read cumulative elapsed as per-band cost."* Having read that, I reasoned that it described renders
fitting in RAM rather than one thrashing, and dismissed it. It described this.

**What stands:** the working-set measurement (32.8 G against 31.3 G of RAM) is real, and swap is what
made the difference between s7 dying three times and s8 finishing. What does not stand is the
conclusion drawn from it — that thrashing makes a render effectively unfinishable. It makes it about
2× slower, not 6×.

### Confirmed: working set, not band count, sets the render time

`curbase_s9` rendered and scored while `curbase_s8`'s result was still fresh, giving a clean contrast
on nearly identical strips:

| arm | bands | render time | peak working set | |
|---|---:|---:|---:|---|
| `s8` | 37 | **194 m** | **32.8 G** | exceeds 31.3 G of RAM — thrashed |
| `s9` | 36 | **88 m** | **~26 G** | fits — no thrashing |

**One band apart, 2.2× the wall time**, and the difference is entirely whether the working set fits in
RAM. This settles the question the earlier sections were guessing at: band count is not the
discriminator (`s6` rendered fine with 36, `s7` died with 35, `s8` has 37), the working set is.

That is precisely what `scripts/sample_render_footprint.py` exists to make predictable, and it is why
the sampler records resident **and** swapped pages: resident alone *falls* as a render thrashes
harder, so it would have read as pressure easing at the exact moment things got worse.

Both arms cleared the registered validity gate: `s8` 2,881,173 and `s9` 2,818,864, against
2,398,918–3,639,084.

`curbase_s7`'s recovery render began automatically when the chain cleared, and its own log confirms
the pin held: `[setup_workdir] villa be09a8503 -> be09a85035059fd8...`. So the recovered arm is
render-equivalent to `s8` and `s9`, and triplet C stays internally clean.

### s7 measured: 31.3 G, and why resident alone would have misled

`curbase_s7`'s recovery render was sampled directly rather than inferred from its kills:

```
rss 20.42 G  +  swap 10.92 G  =  working set 31.34 G
```

That completes the picture across three arms of the same study:

| arm | working set | render | |
|---|---:|---:|---|
| `s9` | ~26 G | 88 m | fits in RAM |
| `s7` | **31.3 G** | in progress, band 12/35 at 102 m | thrashes |
| `s8` | 32.8 G | 194 m | thrashes |

Yesterday's estimate of s7's footprint came from the OOM kills, which report **anon-rss** — 28.2–28.7 G,
resident only, at the moment of death. The true working set is higher because it excludes what was
already paged out. The kills were not wrong; they measure a different thing.

**This is the clearest argument for sampling both numbers.** At the moment above, resident alone reads
**20.4 G** — comfortable, on a 31.3 G box — while a third of the job sits in swap. Anything watching
RSS would have called this arm healthier than `s9`, which actually fits.

## Second reclaim, 2026-09-16: the finished study's checkpoints

With the consensus study complete — 9/9 arms scored, verdict CONFIRMED and written, k=2 follow-up
done — the protection `reclaim_fit_checkpoints.py` placed on `curbase_s1–s9` was lifted with `--also`
and their checkpoints removed: **35.6 G freed, 30 G → 65 G (97% → 94% full)**.

**Verified by re-deriving the result, not by listing files.** After the reclaim the registered analysis
was re-run and reproduced its verdict exactly — **A-vs-C 0.875, B-vs-C 0.893, CONFIRMED** — which is
the only check that proves nothing the study depends on was deleted. All nine arms keep their meshes
and `satisfied_fitted.json`, and the 8.8 G of `outer_*` directories the analysis actually reads are
untouched.

Cumulative across both reclaims: **76.7 G**, with every arm still re-renderable.

### What was deliberately left, and one trap

* **`~/.cache/uv` (43 G), `pre-commit` (3.9 G), `ms-playwright` (3.7 G)** — regenerable, but they
  belong to the wider environment rather than this project. Clearing them would slow or break other
  work for space that is no longer needed.
* **Docker reports 18.98 G of "reclaimable" images — do not `docker image prune -a`.** That figure
  counts every image not bound to a *running* container, and with no render in flight it includes
  **`vc-render:local` (13.6 G)**, which every render needs and which costs a rebuild to replace. The
  plain `docker image prune` used yesterday only removes dangling layers and is safe.
* **Docker volumes show 4.754 G "100% reclaimable"** — not touched, because a volume's contents are
  not identifiable from that summary.


## The disk constraint is gone, 2026-09-16 — memory is not

The VM's virtual disk was grown **1 TiB → 2 TiB** on the KVM host; the guest kernel logged
`vda: detected capacity change`, and `growpart /dev/vda 2` + `resize2fs /dev/vda2` extended the
partition and filesystem to fill it.

| | before | after |
|---|---:|---:|
| filesystem | 1006.85 GiB | **2014.79 GiB** |
| available | 64.86 GiB | **1031.84 GiB** |
| full | 94% | **47%** |
| ext4 reserved | 51.22 GiB | **92.17 GiB** |

**Everything in this report about disk pressure is now historical.** The 41.1 G and 35.6 G reclaims
were correct when made and their verification still stands, but neither should be cited as evidence
the box is short of space, and no future study needs to budget 5 G per arm against a tight margin.

Two things did *not* change, and they are the ones that matter:

* **Memory is still the binding constraint.** 31.3 GiB of RAM against a measured ~28.5 GiB render
  peak. That is what killed `curbase_s7` three times, and a larger disk does nothing for it. The
  24 GiB of swap is what makes a thrashing render survive, at roughly 2× the wall time.
* **ext4's reserve scales with the filesystem**, so growing the disk silently set aside another
  ~41 GiB: 51.22 → 92.17 GiB. `tune2fs -m 1 /dev/vda2` would return ~72 GiB of that. Not urgent at
  47% full, recorded so it is not rediscovered as a mystery.
