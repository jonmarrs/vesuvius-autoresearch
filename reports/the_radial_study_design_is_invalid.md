# The radial displacement study cannot work as designed: the noise moves the surface further than the manipulation

**2026-09-20.** A design verdict on
`docs/preregistration/2026-09-19_radial_displacement_causes_ink_loss.md`, reached from that study's
own control arm before its treatment arms were run.

## The problem

The study displaces **input meshes** by ±4 voxels, then runs the full pipeline: concat → lasagna
flatten → render → score. The flatten re-solves after the displacement.

`reports/the_flatten_lands_on_different_surfaces.md` measured what that flatten does between two runs
on **identical** input in this exact region (`w120-w129`):

| | value |
|---|---:|
| imposed manipulation | **4.0 vx** |
| flatten's own run-to-run surface movement | **7.15 vx mean** (p50 7.34, p90 10.75) |

**The uncontrolled movement is ~1.8× the controlled one.** With one arm per condition, an IN arm's
result is a single draw from a distribution whose spread exceeds the effect being imposed. That is
not a weak test; it is an uninterpretable one.

This was not knowable at registration. The registration assumed a **1.42%** pipeline floor from
`reports/the_determinism_floor_rests_on_one_draw.md`, which attributed the spread to the nnU-Net
scorer. The scorer contributes **0.0032%**. The flatten was never measured until this study's own
ZERO control forced it.

## Why more arms is the wrong fix

Averaging down a 7.15 vx wobble to resolve a 4 vx signal needs many renders — each ~2h — and still
measures "displacement plus whatever the flatten did to it", because **the flatten re-solves on the
displaced input and may absorb, preserve, or amplify the shift.** Nothing in the design pins which.

## The design that does work: displace the FLATTENED surface

The flatten output (`concat/w120-129_flat`) is itself a tifxyz — `meta.json` plus `x/y/z.tif` — and
`vc_render_tifxyz` consumes it directly. So:

1. flatten **once** (already done: `radial_work_rad0`);
2. copy that one flat surface, displace it radially by the test amount;
3. render and score both copies.

**Both arms then share one identical flat surface and differ only by the imposed shift.** The
stochastic flatten is upstream of the branch point, so its 7 vx wobble is removed by construction
rather than averaged down, and the displacement is exact rather than whatever survives re-solving.

The remaining noise is `vc_render_tifxyz` plus the scorer, and the scorer alone is 0.0032%.

### What it needs, and the one honest obstacle

`render_ink.py` **deletes and regenerates** any existing flatten (`if os.path.exists(flat_abs):
shutil.rmtree(flat_abs)`), and `--flatten/--no-flatten` governs the flatboi/strips path, not the
lasagna full-scroll one. There is no reuse flag.

So this needs a small patch to skip the flatten when a flat already exists — the same mechanism as
`repro/spiral_render/serial_folds.patch`, which is an established pattern here. Re-implementing the
render step outside `render_ink.py` was considered and **rejected**: it also does max-compositing and
jpg tiling, and reproducing those by hand would risk introducing exactly the differences the
comparison is meant to isolate.

## Status

**The IN and OUT arms are not run, and the registration's question stays open.** The ZERO control did
its job — it invalidated the design before four hours of renders were spent producing a number that
could not be interpreted.

What the study has already produced is worth more than its registered question: the render
reproducibility measurement (`reports/the_render_is_the_noise_floor.md`) and the flatten divergence
measurement, both of which correct floors used across this whole corpus.

## The transferable lesson

**The floor was assumed from a report that named an unmeasured mechanism.** 1.42% was attributed to
the scorer; the scorer is 950× too small; nobody had checked. A study's power analysis is only as
good as the provenance of the number it rests on, and "a previous report says X" is not provenance
when that report never measured X directly.
