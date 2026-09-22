# Pre-registration: does a radial offset in the MESHES survive the flatten?

**Written 2026-09-22 ~15:00, before either flatten of this study ran.** Written from
`docs/preregistration/TEMPLATE.md`. Decision code `scripts/analyse_flatten_transmission.py`, tests
`tests/test_analyse_flatten_transmission.py`, both committed with this file.

## The question

The ink-maximum offset sweep (`2026-09-22_ink_maximum_offset.md`) displaces the **flattened** surface.
villa's autoresearch loop may edit only fitting code: `render_ink.py`, the flatten settings and the
scorer are frozen (`villa/spiral-fitting/autoresearch.md`, "What you CANNOT do"). So even if the sweep
finds a lever, the loop can reach it only if an offset in the **fitted meshes** reaches the flattened
surface the render reads. If the flatten puts displaced input back where it was, the lever is not
reachable from fitting code, whatever the sweep finds.

This is **a question about geometry only.** No arm is rendered; the answer says nothing about ink.

## Reachability — checked before designing the validation

* **The manipulation exists and is exact.** `radial_work_in` / `radial_work_out` hold `rad0`'s ten
  `w120–w129` meshes displaced by **−4.000 / +4.000 vx** (p1 = p99, n = 1,718,832) about the mesh axis
  (4270.7, 4819.6). `z.tif` is byte-identical to `rad0`'s in all ten; `x.tif` differs.
* **The reference exists.** `flatten_det_a` is a deterministic flatten of meshes byte-identical to
  `rad0`'s (checked on w120/w125/w129 x and z). One tree: `VILLA_SHA` `be09a8503` for all three.
* **The flatten-only path exists.** `spiral_out/run_det_chain.sh` ran it with the render binary
  stubbed out, under `FLATTEN_DETERMINISTIC=1`.

## The instrument, and the floor

`scripts/measure_flatten_normal_offset.py`, extended with an **outward**-normal reading. Controls,
all run before this registration:

| check | result |
|---|---|
| synthetic cylinder, ±4 vx, either grid orientation | reads ±4.0 |
| synthetic absorbed offset, returned re-sampled (7, 7) in-plane | T ≈ 0 (< 0.1) |
| synthetic half transmission | T ≈ 0.5 |
| **real surface**: `flat_study_in/out` vs `flat_study_zero` (exact ±4) | **T_in = T_out = 1.000** |

**Floor:** two deterministic flattens of identical input are byte-identical (normal offset 0.00),
so any non-zero T is the input difference, not flatten noise. Stock-mode re-parametrisation
(~7 vx in-plane) does not enter a normal reading (`reports/the_flatten_moves_the_grid_not_the_surface.md`).

## Prediction, fixed now

**T ≈ 1 in both directions (0.8–1.1).** Reasoning: two flattens of identical input lie 0.25 vx apart
along the normal, so the flatten keeps its output on its input surface. A displaced input is a
different surface, and the output should follow it. The risk to this prediction is regularisation:
the flatten may pull the displaced mesh toward something it fits independently of its input.

**Config read before registering, which raises the prior.** `lasagna/configs/flatten_fast_nofilter.json`
optimises one parameter group, `map_flatten_ms`, the flattening map, with losses `flatten_sdir`,
`flatten_edge_step`, `flatten_avg_offset` and `flatten_orient`. Its output is sampled at
`flatten_output_step: 20.0`, which matches the 20 vx grid spacing measured independently. On that
reading the flattener solves a parametrisation of its input surface and cannot move it. T ≈ 1 is
therefore **strongly expected**, and the study's value is turning a config reading into a
measurement. The one term whose meaning was unclear, `flatten_avg_offset`, was checked in source before
registering: `opt_loss_flatten.flatten_avg_offset_loss` (L1036) holds the mean **2D** offset of
`map_yx` (shape H×W×2) fixed. So every loss acts on the parametrisation, and **T ≈ 1 is close to
certain by construction.** A T ≈ 1 result is a confirmation, not a discovery, and will be reported as
one. T < 0.8 would mean my reading of the pipeline is wrong somewhere downstream of the map (the trim,
or the output sampling), and would be the interesting outcome.

## Decision rule (bands in the code: HI = 0.8, LO = 0.2)

| T_in, T_out | verdict |
|---|---|
| both ≥ 0.8 | **TRANSMITS.** A mesh offset reaches the flattened surface; an offset lever, if the sweep finds one, is reachable from fitting code. |
| both \|T\| ≤ 0.2 | **ABSORBED.** The flatten puts displaced input back on the same surface; an offset lever is not reachable from fitting code. |
| one ≥ 0.8 and the other not, or one ≤ 0.2 and the other not | **ASYMMETRIC.** Report both. |
| otherwise | **PARTIAL.** Report T for each direction. |

**Failure branch:** if either arm's determinism guard fails, or the three do not share one
`VILLA_SHA`, the verdict is VOID (enforced in code via `FLATTEN_MODE` and `VILLA_SHA`).

## What the result cannot do — stated before it arrives

* **It cannot show a lever exists.** That is the sweep's question.
* **It cannot show fitting code can impose a uniform offset.** The fit's own losses may resist one;
  this measures only whether the flatten would pass it through.
* **It cannot say anything about ink.** Nothing is rendered.

## Limits

One region (`w120–w129`), one magnitude (4 vx), one reference flatten. Deterministic mode fixes one
reduction order; stock flattens of the displaced meshes could land differently in-plane but, on the
evidence above, not along the normal.

## Cost

Two flattens, about 11 min each, render stubbed. Queued behind the `--cache-gb` check so it cannot
overlap a render: the flatten's CPU memory use is not measured, and on this box the OOM killer would
pick the 26 GB render first.
