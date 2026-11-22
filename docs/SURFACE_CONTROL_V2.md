# Candidate surface-control calculator v2

[The v2 calculator](../repro/first_letters/pherc0841/surface_control_v2.py)
addresses the precision finding in the [repository audit](REPOSITORY_AUDIT.md).
It is prepared and CPU-tested for a **future registration**. It has not been
adopted by a registered study or run on the original scroll inputs.

Finding 111's [calculator](../repro/first_letters/pherc0841/surface_control.py),
[registration](preregistration/2026-11-13_first_letters_0841_surface_control.md),
shell launchers and published records remain the as-run method. Those launchers
continue to call the original calculator. Do not replace them with v2 or reuse
their output paths for a new measurement.

## Precision contract

- Sweep selection compares the computed AUCs before any rounding. Genuine ties
  retain the original order: nearest depth to zero, then the reverse side;
  any remaining tie retains the sweep's ascending depth order.
- P1 compares the computed AUC with `0.60` and with the computed largest slid
  floor plus `0.05`. P2 compares it with `0.75`. These are ordinary binary64
  comparisons, with no added tolerance or rounding step.
- JSON retains the computed Python floats with round-trip precision, including
  every swept AUC, floor direction and other-side diagnostic. Sweep console rows
  use four decimals for display only. A printed `0.7500` can therefore fail P2.
- Confirmation recomputes P1/P2 from metrics rather than trusting stored flags.
  Invalid/nonfinite metrics fail; a missing floor cannot pass P1. A held-out
  segment must meet the existing 1,000-cells-per-class scoring requirement.
- Sweep and confirmation records identify schema `2` and protocol
  `first-letters-surface-control/v2`. Confirmation rejects historical or
  differently versioned sweeps and verifies the chosen row against the raw
  sweep table. It records the SHA-256 of the same captured bytes it parsed.
  A version field does not authenticate data or recover precision already lost
  in another producer; do not relabel an old rounded record as v2.
- Missing/nonzero render or ink exit records produce `DOES_NOT_RUN` before
  loading scientific inputs. Segment and gate names must be unique. Outputs
  use exclusive creation and cannot replace an existing measurement.

The label projection, scoring mask, ensemble, shifted floor and `Segment`
implementation are retained snapshots of the historical calculator, checked
for source equivalence by the tests. The snapshot is deliberate: factoring
the old registered method into a mutable shared implementation would change
what its retained script executes. V2 uses the same geometry/map helpers from
this checkout and refuses cached helpers from another checkout.

The synthetic rank fixture measures AUC `0.74996`. V1 stores `0.75` and passes
P2; v2 retains `0.74996` and fails it. A second fixture scores `0.74998` and
wins a sweep over `0.74996`, even though both print as `0.7500`. The published
Finding 111 rows (`0.7478`, `0.7194`) remain below P2 and its published
`BLOB_LEVEL_SIGNAL` verdict remains unchanged. This comparison of stored rows
is not a remeasurement of the original maps.

## Adoption before the next measurement

Write a new registration that pins the v2 source revision and its geometry/map
helpers, states this precision contract, fixes the inputs, segment roles,
depth range, step gates and output paths, and includes the existing label
alignment checks. V2 only calculates scores and decisions; it does not perform
or certify alignment, render/model steps, input provenance or preregistration.
No new claim about the scientific meaning of the `0.75` line is introduced.

Run in a new work directory using the scientific environment. For example,
after the newly registered render/ink steps have produced the inputs:

```sh
python -I repro/first_letters/pherc0841/surface_control_v2.py sweep NEW_WORK/sweep.json \
  --segment DEVELOPMENT MESH MAPS RENDER LABELS --depths LO HI

python -I repro/first_letters/pherc0841/surface_control_v2.py confirm NEW_WORK/confirm.json \
  --choice NEW_WORK/sweep.json --gate NEW_WORK/gate \
  --segment HELD_OUT_A MESH_A MAPS_A A_66.zarr LABELS_A \
  --segment HELD_OUT_B MESH_B MAPS_B B_66.zarr LABELS_B
```

Replace uppercase placeholders with the newly registered values. Gate records
in this example are `render_A.json`, `ink_A.json`, `render_B.json` and
`ink_B.json`; names come from render basenames with `_66.zarr` removed.

The curated validation runner includes
[the v2 regressions](../tests/test_surface_control_v2.py). They use real synthetic
pair ranks, JSON round trips and CLI orchestration; no original scroll/GPU
validation is implied.
