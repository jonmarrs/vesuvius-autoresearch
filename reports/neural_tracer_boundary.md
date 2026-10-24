# Finding 96 (exploratory): villa's neural tracer cannot seed near the CT's edge, and ScrollGT gives it the cube alone

**Exploratory, after the fact; not pre-registered.** Found on 2026-10-23 while reading finding 91's run records,
after the tracing-context test was registered (#206, commit 1dd0908d). It uses only existing runs and published rows,
CPU only. `scripts/neural_tracer_boundary.py` writes `reports/neural_tracer_boundary.json`.

## The rule

villa's neural fiber tracer (villa #2045) sets each seed's heading from a window of CT around the seed dot. The window
is 77 voxels on a side: `CT_CONTEXT_RADIUS = 38` CT voxels in `tracers/shared/ct_structure.py`. If the window crosses
the edge of the CT it was given, `_ct_context` in `tracers/fibers/frames/ct.py` raises
`SeedHeadingError('CT seed context crosses the volume boundary')`. The dot is then dropped, and counted as
`no_heading`.

On a scroll, the edge of the CT is far away. In finding 91, ScrollGT's entrant protocol ran the tracer on each cube's
CT alone (finding 85's arrays), so every face of the cube is an edge of the CT. Our tracer has no such rule: 64.5% of
its labelled voxels on `s5_07997_02997_05497_256` lie within 38 voxels of a face, against 65.2% of the volume.

## What it costs on the 21 cubes

All from finding 91's runs at its defaults. The ranges are [min, median, max].

| | 256³ cubes (10) | 512³ cubes (11) | separate? |
|---|---|---|---|
| closest traced seed to a face | 19.00 grid voxels (38 CT) on every cube | 19.00 on every cube | (the rule) |
| share of the cube where a seed's window fits | 0.348 | 0.618 | yes |
| share of seed dots dropped as `no_heading` | 0.542, 0.591, 0.696 | 0.256, 0.273, 0.357 | yes |
| share of ground-truth length on fibers with a node where a seed's window fits | 0.510, 0.669, 0.745 | 0.854, 0.898, 0.945 | yes |
| neural tracer's coverage (finding 91, tolerance 2) | 0.096, 0.237, 0.268 | 0.333, 0.461, 0.541 | yes |
| neural tracer's predicted over ground-truth length | 0.277, 0.593, 0.776 | 0.830, 1.047, 1.430 | yes |
| our tracer's coverage (ScrollGT's rows, findings 80 and 83) | 0.255, 0.610, 0.675 | 0.500, 0.574, 0.672 | no |

* **The seedable core.** A trace-grid voxel is 2 CT voxels, so a seed's window fits at trace-grid coordinates 19–108
  of a 256³ cube's 128, and 19–236 of a 512³ cube's 256.
* **Seed planes.** villa's seed planes lie at multiples of 64 trace-grid voxels. A 256³ cube has planes at 0 and 64
  on each axis, and the plane at 0 lies wholly outside the core, so half its planes can seed nothing. A 512³ cube
  loses one plane of four.

**The same scroll, the same mask model, the same settings.** Within the in-sample Scroll-5 cubes, only the size
differs between these two groups:

| in-sample Scroll 5 | 256³ (3 cubes) | 512³ (3 cubes) |
|---|---|---|
| dropped as `no_heading` | 0.571–0.678 | 0.258–0.283 |
| ground-truth length on fibers a seed can reach | 0.510–0.667 | 0.854–0.905 |
| neural tracer's coverage | 0.156–0.238 | 0.333–0.381 |
| neural tracer's predicted over ground-truth length | 0.532–0.614 | 0.957–1.158 |
| our tracer's coverage | 0.593–0.675 | 0.574–0.672 |

## What it means

* **ScrollGT's protocol, not the scroll, is a large part of why the neural tracer trails on the 256³ cubes.** The
  rule takes about a third of a 256³ cube's ground-truth length out of its reach (median 0.669 reachable), and about a
  tenth of a 512³ cube's (median 0.898). Ten of the 13 cubes on which ScrollGT says it trails our tracer are 256³.
  The other three are the in-sample 512³ cubes, where the deficit is a tolerance-2 result (finding 94).
* **It fits findings 94 and 95.**
  * Cropping the 512³ runs into octants kept the lead (finding 95), because inside a 512³ run an octant's inner faces
    are not the CT's edge.
  * On real 256³ cubes the neural tracer draws about half the centreline per unit of ground truth that it draws on
    the 512³ ones.
* **The registered tracing-context test (#206) gives each octant its own CT, so it hits the same rule.** Its P1, that
  the lead survives, was registered before this was found, and now looks likely to fail. The predictions stay as
  registered.

## What this does not show

* **How much of the gap the rule explains.** The reachable share caps the coverage, but the coverage sits below the
  cap on both sizes (median 0.237 against 0.669 on 256³ cubes, 0.461 against 0.898 on 512³). Fewer seed planes per
  unit length and fewer seeds per fiber also cut a 256³ run's output. Measuring the rule's whole effect needs the tracer
  run on each cube with real CT around it: at least 38 voxels from the scroll volume beyond each face, with the box
  still the cube. That is a GPU run and a download, and is untested here.
  *(2026-10-24: finding 97 ran it, pre-registered, in `neural_tracer_ct_context.md`. With 128 voxels of real CT
  around each of the ten 256³ cubes, the tracer's coverage rose 1.76–2.78× on every cube.)*
* **A defect in villa's tracer.** Refusing a truncated window is a reasonable choice on a scroll. The mismatch is ours:
  the protocol gave it a CT no larger than the scored cube.
* **That the reachable-share test is exact.** It is a node test, and nodes sit 1–2 voxels apart. It counts a fiber as
  reachable if any node lies where a seed's window fits; whether a seed lands there also depends on the planes and
  the presence.
