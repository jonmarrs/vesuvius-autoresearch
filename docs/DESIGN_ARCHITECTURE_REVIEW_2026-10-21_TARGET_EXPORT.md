# Design and architecture review — the ScrollGT target exporter and the July benchmark report

Date: 2026-10-21. Baseline: `6a812697` (main after #166).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/export_fiber_targets.py`, which no review had read. It writes the fiber targets ScrollGT scores:
each cube's `skeleton.npz`, `mask.npz` and `meta.json`, whose `floors` it copies from a benchmark report. Also the
report it reads by default, `reports/fiber_benchmark_all_cubes.json`, and the documents that cite it.

Main has not moved since #166, and no owner PR is open. This round covers the firings from 02:13 to 05:12 UTC.

## What changed

- **The exporter wrote over ScrollGT's published targets with less than they hold.**
  - `--out-root` was documented as ScrollGT's `data/` directory, and `export` writes each cube's `meta.json` from
    scratch. ScrollGT's targets now hold three things this export does not write. Scripts here read each of them
    from ScrollGT's metas:
    - our tracer's row (`floors.tracer_strict_relink`);
    - the NML's dataset provenance (`ground_truth.nml`), which `fiber_heldout_in_sample_rows.py` and
      `afv_generator_analysis.py` require to name Dataset004;
    - on three cubes, villa's newer annotations, which ScrollGT 0.5.0 moved them to (finding 82). Those cubes have
      140, 161 and 179 scored fibers in ScrollGT, against 109, 105 and 147 in Dataset001, which `bench_cli fetch`
      downloads.
  - So an export there would drop the first two from all 11 metas, and put three cubes back on the older
    annotations, whatever report supplied the floors.
  - **Change:** the exporter writes a new target set only. It refuses before reading the report when any cube's
    target already exists in `--out-root`, and says why. Its docstring and `--out-root`'s help say so too.
- **The exporter would ship floors from another scorer, or from another probability volume.**
  - `--bench` defaults to `reports/fiber_benchmark_all_cubes.json`, written 2026-07-30 and rerun 2026-08-16. That
    is scoring version 1. The scorer changed four times in October (`fibers/provenance.py`): versions 2, 3 and 4 on
    2026-10-04, the last taking ScrollGT's definition, and 5 on 2026-10-12 with its ERL fix (ScrollGT 0.7.0, its
    version 3, finding 85).
  - The report's rows carry no scoring version, and its cubes no provenance. Its numbers are not ScrollGT's:
    - connected components' merge-penalized ERL differs from ScrollGT's published row on all 11 cubes;
    - our tracer's differs on the 6 cubes for which the July report has a tracer row (ScrollGT publishes one on all
      11; `reports/tolerance4_rescore.json` holds them);
    - on `s1_00497_01497_03997_256`, our tracer's merge-penalized ERL is 23.16 against 19.22, and connected
      components' 37.13 against 34.04.
  - The mask came from the probability file then on disk, and the floors from the report, with nothing tying them.
  - **Change:** `bench_problems` names, per cube, why a report cannot supply its floors:
    - the report's `scoring_version` is not the current one;
    - a row was scored at another version, or at a tolerance other than the report's;
    - it has no oracle row, which `export` reads;
    - it has no provenance;
    - a provenance field is missing or is not this export's: the scoring version, the hashes of the
      `_fiberprob.npy` and `.nml` it ships, the report's tolerance, the step (0.5), the in-bounds restriction, and
      the threshold (0.5);
    - a local file it would hash is missing (named, rather than a traceback).

    `bench_cli floors --all-cubes` records each of these. The committed report is refused on every cube.
- **A refusal leaves the output as it was.**
  - `main` checks every cube's floors before exporting any.
  - It then writes every cube to a staging directory inside `--out-root`, and moves them into place only once all
    have passed `export`'s own checks: shape, landing rate, scoreable-fiber count.
  - A cube that fails leaves neither the earlier cubes nor the staging directory behind.
- **The docs citing the July report as the full-cube numbers.**
  - `docs/FIBER_TRACING.md` and `reports/fiber_connectivity_eval.md` now carry a dated note naming both reasons it
    is not ScrollGT's current rows: the scorer changes, and the three cubes' newer annotations.
  - The note gives ScrollGT's current figures on the six cubes:
    - our tracer's coverage, 0.560-0.623 (the report gives 0.605-0.704);
    - connected components' lead, 5.0-8.3x on raw ERL and 1.7-2.4x on merge-penalized ERL (4.5-7.4x and 1.6-3.5x).
  - `FIBER_TRACING.md` also says that ScrollGT has held ten held-out cubes besides the eleven since 0.6.0.
  - `reports/fiber_tracer_improvement.md`'s notes called version 4 current. A dated note says that version 5
    followed on 2026-10-12, and that its percentages were not re-measured under it.
- **Tests** (`tests/test_export_fiber_targets_bench.py`, 31):
  - the committed report is refused on every cube;
  - a current report on the shipped files passes, at tolerance 2 or 4;
  - each mismatch is named alone. That covers the report's version, and a version on a row other than the first: a
    stale `tracer_strict_relink`, or a row with none. It also covers a row's tolerance, a missing oracle row,
    missing or empty provenance, and each provenance field;
  - each provenance field missing is named;
  - another probability volume or skeleton is refused, and a missing local file is named;
  - `main`:
    - exports every cube into place;
    - refuses an existing target before reading the report;
    - refuses a report, or one missing a cube, before exporting any;
    - leaves the output empty when a cube's export fails partway.

  Every check is load-bearing: 14 mutants each fail the tests. They include:
  - the rows checked only first, or only `oracle`;
  - a missing provenance field let through;
  - the tolerance hard-coded;
  - the missing-file and oracle checks dropped;
  - the existing-target check dropped;
  - exporting straight into `--out-root`;
  - the staging directory kept;
  - `main` iterating the report's cubes.

## Verified, no change needed

- **A report `bench_cli floors --all-cubes` writes with this checkout passes the floor check.** The independent
  review ran the real `_floors_all_cubes` on stubbed inputs: every cube passes. In particular:
  - the report's tolerance and the provenance's are the same argument;
  - the probability hash is the cache record's, the hash of the `.npy` read;
  - a carried-over tracer row at another version is refused.
- **The exporter's other checks:**
  - it refuses a cube whose semantic-label landing rate is below 0.999;
  - it refuses one whose scoreable-fiber count differs from the report's oracle row;
  - it refuses a shape mismatch;
  - its split is derived from the scroll, and refuses an unknown one.
- **`skeleton.npz`**: each fiber's edges are rebased onto the concatenated coordinates, with fiber and edge offsets
  to split them again.
- **`mask.npz`** packs the thresholded mask with its shape, so it unpacks to the scoring mask exactly.

## Observations for the owner (not changed)

- **Whether this exporter has a use left.** It covers the 11 in-sample cubes, not the 10 held out, and writes
  neither our tracer's row nor the NML's provenance. A report from this checkout's `bench_cli` records our scoring
  version 5, the same definition as ScrollGT's version 3 under our numbering, so its rows would read 5. If ScrollGT
  maintains its targets itself, the exporter could be retired.
- **The mask's model is not checked.** A report scored on another model's probabilities passes, and the exported
  meta still names `scrollprize/fiber_hz_vt`. The provenance records the model's file hashes (`inference`), but
  there is no recorded hash of the published model to compare them with.
- **`reports/fiber_benchmark_all_cubes.json` is kept as the July record.** Regenerating it needs the cubes and the
  model, which this container has neither of, and a GPU or a long CPU run.

## Verification

- `pytest tests/test_export_fiber_targets_bench.py tests/test_export_fiber_targets_split.py`: 45 passed.
- Ruff, ruff format and mypy are clean on the changed files. No test reads the edited documents.
- **The standard suite** on the first commit (`14b9dbe6`) ran as on main: 2690 passed, with the same 42 failures and
  2 errors, all environmental. It does not include the exporter's tests. The smoke test gave 9 of 11 passed and 2
  skipped, as on main.
- **Independent review** of the first commit. Its blocking finding was the existing-target damage above: the first
  commit's refusal message pointed at a report that would pass and still do it.

  It confirmed:
  - the version dates;
  - the July report's contents and how they differ from ScrollGT's rows;
  - that a current `bench_cli` report passes;
  - the first commit's 9 mutants.

  Its should-fix findings:
  - the tests checked only the first row, and no missing provenance field;
  - a refusal by `export` partway left earlier cubes written;
  - the mask's model was unchecked (an observation above);
  - the notes gave only the scorer as the cause.

  Its nits:
  - row tolerance, `step` and the in-bounds restriction unchecked;
  - a traceback for a missing local file;
  - the wording about the tracer rows;
  - the GPU;
  - the stale "version 4 current" and "eleven cubes".

  All are addressed above.
