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
