# Fiber mask miss diagnostic

`scripts/fiber_miss_diagnostic.py` checks whether the reference fiber mask misses
annotated fibers because of a rigid offset, a threshold, or a remaining miss.
It uses ScrollGT's resampled ground-truth points, a length-weighted coverage at
tolerance 2 voxels, shifts within ±4 voxels and the registered threshold family.
It runs on CPU and does not train a model or run a tracer.

## Run on explicit inputs

Use a ScrollGT checkout containing the finding-84 targets and its source package,
and the matching cached probability arrays. Repeat `--prob-dir` for separate
in-sample and held-out caches. Paths may be absolute; the command works from any
working directory.

```sh
/path/to/vesuvius-autoresearch/.venv/bin/python \
  /path/to/vesuvius-autoresearch/scripts/fiber_miss_diagnostic.py \
  --scrollgt-root /path/to/scrollgt \
  --prob-dir /path/to/in_sample_probability_cache \
  --prob-dir /path/to/held_out_probability_cache \
  --out /path/to/new_results/fiber_diagnostic.json
```

The full run checks the fixed 21-target inventory before computing any cube.
Missing targets, missing probabilities or multiple distinct probability files
for a cube are errors. It does not infer a complete sample from a directory's
current contents. Recorded target splits must match the registered inventory.

For a descriptive check of named cubes, add:

```sh
--cubes s5_13497_01497_02497_256 s5_16997_03997_04497_256
```

This produces `mode: descriptive_subset` and per-cube instrument checks, with
no full-sample verdict. Duplicate or unknown selections are errors. Omitting
`--cubes` produces `mode: registered_full` and requires all 21 cubes, including
every in-sample control.

## Evidence and failure behavior

Probabilities must be finite real values in [0, 1] in a nonempty 3D ZYX array.
Masks must be boolean and have exactly the probability shape. Rounded sample
indices must be integer ZYX triples, with finite nonnegative lengths and positive
in-bounds length at every evaluated shift. No in-bounds length is an invalid
measurement, rather than a measured zero coverage.

An empty mask has zero coverage. The all-background SciPy distance transform
otherwise measures a virtual point outside the array, which can look like a
nearby detection. A perfect-coverage threshold sweep has no missed length, so
its `soft_miss_fraction` is JSON `null`. If that quantity is needed for the
registered Scroll-5 comparison, the instrument fails and emits no conclusion.

Before a verdict, numeric gate and decision inputs must be finite fractions,
gains and soft-miss fractions must agree with their component measurements,
the probability threshold must reproduce the shipped mask, and both coverage
instruments must reproduce the published connected-components floor. Failed
instrument or control checks emit no conclusion and return a nonzero exit code.
The same instrument gates apply to descriptive subset outputs.

`THRESHOLD_RESCUES` requires both new Scroll-5 cubes to reach the registered
in-sample coverage minimum. Rescue of one cube is `THRESHOLD_PARTIAL`; P2's
truth value still follows the original rule. This avoids describing one cube's
recovery as recovery of both.

## Result publication and provenance

`--out` is required and must name a new `.json` file outside the ScrollGT and
probability input trees. Existing files and symlinks are refused. A staged file
is published after strict JSON serialization succeeds. Read or serialization
errors cannot publish a partial result. A finite failed-gate report can be
published for inspection, but the process exits unsuccessfully.

Contract 2 outputs record the mode, input roots, registered settings, per-cube
results and verdict or subset instrument status. Keep inputs stable and serialize
writers. Roots are provenance declarations, not content hashes or immutable
snapshots; the report does not certify physical registration or a particular
model's identity. Probability validation and density counting use slabs, and
NumPy caches are memory-mapped. The distance transform still needs memory for
the full cube; this is not a total-memory cap.

The historical [finding-84 report](../reports/fiber_miss_diagnostic.md) was run
with the preregistered analysis at commit `93115122`. Its JSON and preregistration
remain unchanged. The October 12 repair tightens the current instrument and
publication contracts; applying the repaired verdict to the saved 21 rows
reproduces the saved verdict exactly. Rerunning the real target volumes remains
a separate verification step.

Tests for local calculations, gates, sample completeness and publication run
without a sibling ScrollGT checkout. The four direct ScrollGT equivalence tests
still require that checkout and explicitly skip when it is unavailable.
