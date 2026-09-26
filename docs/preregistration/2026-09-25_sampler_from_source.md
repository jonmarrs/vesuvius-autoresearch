# Pre-registration: does `vc_render_tifxyz` built from villa source score differently from the published one?

**Written 2026-09-25, before any arm was rendered.** Decision code `scripts/analyse_sampler_from_source.py`;
tests `tests/test_analyse_sampler_from_source.py`; image `repro/spiral_render/Dockerfile.sampler_src`;
chain `repro/spiral_render/run_sampler_from_source_chain.sh`. All are committed with this file.

## The question

Findings 62 and 64 covered villa's fitter and its Python render stage. The last piece of the pipeline
is the C++ sampler, `vc_render_tifxyz`, which reads the ink volume along the flat surface.

**Every render in this repo has used the sampler in villa's published runtime image.** On 2026-09-25,
a read-only registry query showed `:edge` and `:main` still at `sha256:bad516f6…`, built 2026-05-13;
there is no `:latest`. So our `VILLA_REF` pins never governed the sampler.

Upstream `render_ink.py` calls `vc_render_tifxyz` from `PATH`, and `autoresearch.md` says nothing
about where it comes from. A user who builds volume-cartographer from source today gets the sampler
at their commit. Since be09a8503 alone, 53 files on its path have changed
(`scripts/check_villa_render_path.py`); against the May binary the gap is likely larger.

**Does the from-source sampler at `75c79ac5f` produce a different `total_fg_pixels` from the
published one, on an identical flat surface?**

* **If yes,** users who build from source and users who use the image get different ink counts.
  That is a reproducibility fault in villa's own metric, with evidence.
* **If no,** end-to-end current villa is covered on every stage.

## Reachability, checked before registering

* **Image.** `Dockerfile.sampler_src` layers a from-source `vc_render_tifxyz` onto `vc-render:local`.
  * The binary and its own shared libraries go under `/opt/vcsrc`, behind a wrapper. The grafted
    `vc_tifxyz2obj`'s libraries are untouched.
  * **The first build failed.** At `75c79ac5f`, a target-only build races: core's autogen needs
    `libbacktrace.a` from an ExternalProject that is not a declared dependency. The Dockerfile now
    finds and builds every libbacktrace target first.
  * **It then built** as `vc-render:sampler-75c79ac5f`, image `239865b6`, on 2026-09-25 22:03. The
    source binary runs: `--help` exits 0, and `/opt/vcsrc/SAMPLER_SHA` reads `75c79ac5f…`.
  * An apparent hang at the `--help` build step was the build log lagging. The step's container had
    exited 0; each step is slow because the base image runs commands through a login shell.
* **Reuse.** `reuse_flatten.patch` applies cleanly to `detfit_up1`'s `render_ink.py` (dry-run).

## Arms

Each arm is a copy of `detfit_up1` with its own saved `concat/w120-129_flat`. That surface is reused
and never re-solved. Its x/y/z hash is recorded per arm and gated.

| arm | sampler | role |
|---|---|---|
| `smp_pub` | published (`vc-render:local`) | must reproduce `detfit_up1` (3,279,498): a check that the reuse path is exact |
| `smp_src_a`, `smp_src_b` | from source, `75c79ac5f` | measurement; the repeat checks determinism |

The **only** difference between arms is which image each work dir's `bin/vc_render_tifxyz` wrapper
runs. The trim binary, the Python stage (`be09a8503`), the venv and the scorer are shared.

## Decision rule (`decide()`)

| condition | verdict |
|---|---|
| any arm missing | refused |
| reuse did not engage, the flat hash differs from `detfit_up1`'s, or the wrong sampler recorded | **INVALID** |
| `smp_pub` differs from `detfit_up1` by > 0.01% | **INVALID** (the reuse path is not exact) |
| the source repeats agree within 0.01%, and \|effect\| < 0.5% | **SAMPLER INERT (within 0.5%)** |
| the source repeats agree within 0.01%, and \|effect\| ≥ 0.5% | **SAMPLER CHANGES INK** |
| the source repeats differ by d, and \|effect\| > max(0.5%, 3d) | **SAMPLER CHANGES INK (source sampler nondeterministic)** |
| the source repeats differ, otherwise | **NOT RESOLVED** |

The effect is mean(source) / `smp_pub` − 1.

## Predictions, fixed now

1. **`smp_pub` reproduces `detfit_up1` to within 0.01%.** Confidence high: same flat, same binary.
2. **The source sampler is deterministic.** Confidence moderate.
3. **Effect: withheld.** Four months of sampler changes, direction unknowable.

## What it cannot do

* **One surface, one volume, one commit.** The sampler is measured exactly on one surface; its
  effect could depend on geometry.
* **It cannot say which change matters,** only whether the binary as a whole does.
* **A difference is not a defect by itself.** Villa may have fixed sampling bugs since May. A
  difference means only that the two install routes disagree, not which one is right.

## Cost

Image build (one CMake target plus a dependency). Three renders with a reused flatten, so no
flatten runs. Roughly 1–1.5 h per arm, based on `rs_*`-style reuse renders. Serial on the GPU.

---

## Amendment, 2026-09-26 — before any source arm produced a score

**What happened.**

* `smp_pub` completed: 3,279,498.
* `smp_src_a` was SIGKILLed (exit 137) after 16 min, at 2/35 bands. No source arm ever scored.
* The chain stopped, and the rule refused a verdict, as designed.

**Cause, established from upstream source at `75c79ac5f`.** This is not a guess.

* With `--remote-url`, which villa's `render_ink.py` always passes, the new `vc_render_tifxyz`
  ignores `--volume` (our pre-filled `inkcache`). It streams the zarr into VC3D's remote-cache root
  instead: `vc_render_tifxyz.cpp` around line 1405, `Volume::NewFromUrl`.
* That root is `$VC3D_CONFIG_DIR/VC3D.ini [viewer] remote_cache_dir`, else `/volpkgs` or
  `/ephemeral`, else `$HOME/.VC3D/remote_cache` (`core/src/RemoteCacheSettings.cpp`).
* In our `--rm` container none of the first three exists and `HOME=/home/ubuntu` is discarded, so
  every run re-streamed the region from S3.
* The published May binary instead prefetches into "the existing staged cache", which is the
  `--volume` dir.
* The SIGKILL's cause (host OOM, or something else) is **not** confirmed.

**Change: the source arms' sampler wrapper only.**

* `HOME` is set to a persistent host dir, `spiral_out/vc3d_src_home`, so the streamed chunks
  persist. Arm a streams cold and arm b reads warm, so their agreement also tests cold vs warm.
* A hard `--memory 24g` is added, so an overrun fails inside the container.
* **Not changed:** the binary, `--cache-gb` (default 16, as in `smp_pub`), the flat surface, the
  Python stage and the scorer.

The failed attempt's dirs are kept as `smp_src_a_attempt1` / `smp_src_b_attempt1`. The decision rule
and predictions are unchanged.

**Separately reportable, whatever the verdict.** The two install routes read the ink volume from
different places: the staged `--volume` cache versus a remote-cache root keyed on `HOME`. A
container user of the from-source binary pays a full re-stream per render unless they persist that
root. This was found by running villa's pipeline and is not a sampling result.

Chain for the amended run: `repro/spiral_render/run_sampler_from_source_rerun.sh`.
