# The spiral ink render works from published artifacts, and reads Greek

**2026-08-31.** Closes out the reachability question opened in
`reports/spiral_ink_objective_reachability.md`, which concluded the ink objective "cannot be
measured on this machine". That was wrong twice over, and both errors are worth keeping.

## Result

Ten windings of our own 30,000-step baseline fit, rendered against the published ink-3d volume:

```
lasagna flatten   1m34.78s on one RTX 4090, peak GPU 0.45 GiB
trim              grid 885x321 -> 883x303
render            8830x3030 strip, p95=8.0 (NOT 0.0)
strip content     mean 60.1, 92.7% nonzero, only 7.3% off-surface padding
```

The strip contains legible Greek across five lines (`reports/spiral_render_text_detail.png`,
mirrored to reading order). Recovering text was not the goal, it is the evidence that every stage of
the chain is aligned: fit, concat, flatten, trim, frame conversion and render.

## Two errors this corrects

**"The binaries are absent."** They were never absent upstream. They ship in the container the
volume-cartographer README recommends. The question I asked was "are they built here", when the
question that mattered was "are they obtainable here".

**"I was fighting the wrong path."** Every render before this one used `--strips`, which flattens
with flatboi. I chose it early to avoid the lasagna dependency and then spent a long time on its
failures, including a 9h12m non-converging run left going overnight. `run_single.py` passes no
`--strips`, so villa's actual pipeline is the default full-scroll concat flattened by lasagna. On
the same geometry lasagna converges in 94 seconds. The mesh was never the problem: 12,521 vertices,
manifold, single connected component, zero degenerate faces.

The `vc_obj_uv_lift` build and the `vc_tifxyz2obj` rebuild are genuine fixes to genuine gaps in the
published image, and villa#1660 reports them accurately, but they serve only the flatboi path and
were not on the critical path to the metric.

## What was actually required

| obstacle | resolution |
|---|---|
| mesh frame is 9.6 um, ink volume level 0 is 2.4 um | `--scale-segmentation 4` injected via a `--vc-render-bin` wrapper |
| `lasagna/fit.py` imports `vc3d_fiber_format`, absent from `lasagna/` | put villa's `vesuvius/src` on `PYTHONPATH` |
| no nvidia container runtime | python on the host (torch 2.11.0+cu128), native binaries in the container, workspace mounted at an identical path |
| ink volume not in the spiral dataset | it is published under `representations/predictions/ink-3d/`, and streams |

Without the first, the render still exits 0 and writes a black strip. That silent failure, not the
frame value, is what villa#1660 leads with.

## What this unblocks

`total_fg_pixels` is now measurable here, so the questions that were parked for want of it can be
asked: what the 0.09% duplicate winding coverage in
`reports/spiral_ink_objective_reachability.md` actually costs in recovered ink, and whether
`overall_fg_fraction` can see it.

Cost to know before planning: about 10 minutes per ten windings, dominated by the S3-streaming
render. A 120-winding fit is roughly two hours, so per-fit metrics are affordable but not cheap.

## Reproducing

`repro/spiral_render/setup_workdir.sh` then `run_render.sh`. The README there carries the six
obstacles and the flatboi dead end.
