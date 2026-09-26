# The from-source sampler (villa `75c79ac5f`) cannot complete our render: ~35× slower, >24 GB, 88 GB on disk by band 2

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
