# The from-source sampler (villa `75c79ac5f`) did not complete our render; the speed comparison is WITHDRAWN

> **CORRECTION 2026-09-26, found while verifying before any outward contact.** The published-sampler arm
> `smp_pub` **never sampled**. Its render log says `[tif] all slices exist, skipping.` The chain built it
> with `cp -a` from `detfit_up1` and removed `meshes/ink` and `ink_metric`, but **not** the per-slice TIFFs
> under `concat/w120-129_flat/ink`. The published binary skips when those exist. The source-built binary
> does not skip, so both source arms really rendered.
>
> **Withdrawn:**
> * "published renders 35 bands in ~3.5 min" (it rendered none);
> * "~35× slower";
> * "`smp_pub` reproduces `detfit_up1` to 0.0015%" (it re-scored `detfit_up1`'s own TIFFs, so the
>   agreement is trivial).
>
> **Stands:**
> * the source binary was SIGKILLed at band 2 twice, the second time under a 24 GB cap;
> * it wrote 88 GB;
> * it ignores `--volume` under `--remote-url`.
>
> **Unmeasured:** how the published binary behaves on the same work. A fresh-directory, same-crop
> comparison of both binaries is running (`repro/spiral_render/sampler_repro.sh`). Finding 64 is
> unaffected: its work dirs were built fresh and its log has no skip lines.
>
> **Interim, 2026-09-26 07:1x: the fresh-directory reproduction (same full-width render (see crop note), empty `--volume`
> and `HOME`, 24 GB container cap).** The published binary completed with exit 0 in **6,710 s
> (112 min)**, at **peak memory 24.01 GiB, pinned at the cap**. Bands 1–4 took 7 min, then band 5
> alone took 22 min, which is consistent with reclaim at the ceiling. **So the published sampler
> also wants more than 24 GB at its default 16 GB cache when it really streams from S3.** The
> source binary's failure is therefore not evidence of a regression by itself. The cap distorts
> both binaries' timings. The source runs (default cache, then `--cache-gb 4`) are still in
> progress.
>
> **Reproduction complete for the source binary, 2026-09-26 08:19.** Same full-width render (see crop note), fresh dirs,
> 24 GB cap (`spiral_out/sampler_repro*/results.tsv`, `sampler_memstat/src4m/memstat.txt`):
>
> | run | exit | wall | peak | persisted |
> |---|---|---|---|---|
> | published, default cache | 0 | 6,710 s | 24.01 GiB | 0 GB |
> | source, default cache | **137 OOMKilled** | 1,166 s | 24.03 GiB | 102.6 GB |
> | source, `--cache-gb 4` | **137 OOMKilled** | 1,174 s | 24.07 GiB | 115.3 GB |
> | source, `--cache-gb 4`, cgroup `memory.stat` sampled | **137 OOMKilled** | 1,386 s | 24.14 GiB | 125.0 GB |
>
> **The kill is the program's own memory, not page cache.** At the kill, `anon` = **23.35 GiB** and
> `file` = 0.01 GiB, with essentially nothing dirty. Anonymous memory climbed 7.6 → 14.2 → 23.4 GiB
> over ~23 min while the page cache stayed below 8 GiB. **`--cache-gb` does not bound it:** at 4 GB it
> reaches ~6× that. The published binary at `--cache-gb 4`, with the same sampling, is running now; it
> decides whether this differs from the old build. Villa `main` has not touched the sampler, render
> cache, `Volume` or remote-cache settings since `75c79ac5f` (checked at `f4570bfa6`).
>
> **Published build under the same sampling, 2026-09-26 19:21.** `--cache-gb 4`, same input, same cap: its
> anonymous memory **also** climbed to **23.93 GiB** (page cache ~0.2 GiB). It was not OOM-killed, but
> after **11 h** (39,680 s) it had not finished, and I stopped it. At the default cache it finished in
> 112 min.
>
> **Final reading:**
> * **In both builds, `--cache-gb` does not bound resident memory.** At 4 GB each reaches ~24 GiB of
>   anonymous memory on this surface.
> * **This is shared, not a regression.**
> * **What differs is the failure at the ceiling.** The May build survives and crawls; the
>   `75c79ac5f` build is OOM-killed within ~20 min, while persisting ~100–125 GB. The persisting is by
>   design (its remote-cache comment).
> * **The sampling comparison remains unanswered.** It needs a machine with more RAM.
>
> **Crop note, 2026-09-26 evening.** `sampler_repro.sh` passed `--crop-height 0`. The published output is
> full width (4460 × 90680, ~46% covered), so the crop flags were ignored. Every "crop" run above is the
> **full render of the same flat surface.** The conclusions are unaffected, because all runs had
> identical input. Also verified: the published build's fresh full render is **byte-identical** on all 5
> slices to `detfit_up1`'s TIFFs from 2026-09-24, so the published sampler is deterministic.
>
> **Villa PR #1905 on our surface, and the sampling question answered, 2026-09-26 21:00.**
> PR #1905 (open, ShribyrLabs) makes each 128-row band prefetch only the chunks it samples. It was
> built at its head 280379c2, a PR commit not on villa main (`vc-render:sampler-pr1905`):
> * **Cold:** not OOM-killed. It reached band 16/35 in 43.5 min, where unpatched `75c79ac5f` was
>   OOM-killed at band 2. Our own 150 GB disk guard stopped it.
> * **Warm, reusing that cache:** **completed, exit 0, in 2,447 s**, peak anon 23.5 GiB under the
>   24 GB cap. So on this surface the patch turns an OOM kill into a completed render.
>
> **Pixel comparison** with the published build's full render, which is deterministic
> (`scripts/compare_sampler_tifs.py`, `reports/sampler_repro/`):
> * the centre slice is **byte-identical**;
> * off-surface slices differ (6–8% of pixels);
> * but **new slice 1 = published slice 0 and new slice 3 = published slice 4** (12 of ~404 M pixels
>   differ, i.e. rounding).
>
> **So the current sampler reads and interpolates the volume identically and steps twice as far along
> the normal.** At `--group-idx 1` the published build steps one level-0 voxel; current source steps
> one level-1 voxel. **Cause, from villa's history:** #1146 (2026-07-14, *"use correct isotropic
> scaling when group_idx > 0"*, commit `8ae89fdcd`) stopped scaling the normal offsets by `ds_scale`.
> That is intentional and documented in the code; it landed two months after the published image
> (2026-05-13).
>
> **Consequence:** `render_ink.py` (`--num-slices 5`, default step) max-composites a stack twice as
> thick on a source build as on the published image, so `total_fg_pixels` for the same surface depends
> on the install route. Its size on this surface is being measured now: the source TIFFs scored
> through the pinned path, against `detfit_up1`'s 3,279,498.
>
> Original title: *The from-source sampler (villa `75c79ac5f`) cannot complete our render: ~35× slower, >24 GB, 88 GB on disk by band 2*


**2026-09-26.** Outcome of `docs/preregistration/2026-09-25_sampler_from_source.md`, including its
2026-09-26 amendment. **No sampling verdict.** The registered rule needs both source arms scored, and
none ever was.

## What was run

The input was one flat surface: `detfit_up1`'s own `w120-129_flat`, reused and never re-solved. Its
hash `bfd9ef80…` was checked in every arm. It was sampled from the same S3 ink zarr (level 1,
`--scale 0.25`) by two binaries. Villa's `render_ink.py` invoked both identically.

| | published (`:edge` = `:main`, `bad516f6`, 2026-05-13) | built from source, `75c79ac5f` |
|---|---|---|
| render of 35 bands | **~3.5 min** (arm 20.5 min, of which scoring 16.7 min) | **2 bands in 7 m 32 s**, self-reported ETA 124 min |
| memory | within the default 16 GB chunk cache; completed | **SIGKILL, exit 137, at band 2 — twice**: once uncapped (host), once under `--memory 24g` |
| disk | none persisted (`--volume` cache stayed empty) | **88 GB** written by band 2: level 1 twice (25 GB raw `1/`, 63 GB `level_1/`) |
| result | 3,279,548 (`smp_pub`, reproduces `detfit_up1`'s 3,279,498 to 0.0015%) | none |

**Cache size was not changed.** Both binaries ran at their default `--cache-gb 16`.

## Why, as far as the source shows

* With `--remote-url`, the new binary opens the zarr through `Volume::NewFromUrl` and VC3D's shared
  remote-cache service (`vc_render_tifxyz.cpp`, around line 1405). It persists fetched chunks under
  a remote-cache root, which is `$HOME/.VC3D/remote_cache` when no `VC3D.ini`, `/volpkgs` or
  `/ephemeral` exists (`core/src/RemoteCacheSettings.cpp`).
* **First attempt:** the root sat inside a discarded container.
* **Amended attempt:** the root was persisted to the host. That fixed the discarding, not the cost:
  the binary still wrote 88 GB and exceeded 24 GB of RAM within two bands.
* **Not established:** why it holds so much more, and why the decoded `level_1/` copy is ~2.5× the
  raw one. That would need profiling inside the binary.

## What this does and does not show

* **It shows** that on a 31 GB, 1-GPU machine, rendering our region, villa's current sampler built
  from source does not complete at default settings. The published May binary does so in ~3.5 min.
  Anyone running villa's pipeline in a container on similar hardware would hit this.
* **It does not show** that the new sampler samples differently. That question stays **unanswered**.
* **It does not show a bug.** The new remote-cache design may be meant for machines with far more
  RAM and disk, and may be amortised across many renders. This is one configuration, measured
  twice.

## Status

* **Stopped.** Nothing is running.
* **Kept as evidence:** the failed dirs (`smp_src_a_attempt1`, `smp_src_a`, `smp_src_b`, unrun), and
  the 88 GB cache at `spiral_out/vc3d_src_home`. Not deleted without approval.
* **Possible next step, needs a decision:** a second amendment with a much smaller `--cache-gb`
  (e.g. 4) on the source arms. That would test whether the memory cap is the only obstacle.
  Cache size should not change sampled values, but that was never verified here (see
  `repro/spiral_render/README.md` section 14).
* **Possibly reportable to villa** as a resource regression between install routes. That is
  outward, falls under the posting policy, and needs approval.
