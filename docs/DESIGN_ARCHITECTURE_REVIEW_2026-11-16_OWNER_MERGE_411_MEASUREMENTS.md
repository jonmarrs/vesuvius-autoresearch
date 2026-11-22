# Design and architecture review — the owner's #411, the measurements

Date: 2026-11-16. Baseline: `da27038` (main after #437).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the hourly firings from 02:12 to 05:12 UTC on 2026-11-16. The session could not run between
about 02:40 and 05:11 UTC.

It takes the second slice of **#411**, finding 110: the measurements in
`repro/first_letters/pherc343/mesh_step/mesh_step_analysis.py`. Round #172 covered the module's decision path.
The measurements are the mesh loader, the normals, the surface distance behind P1, and the lattice, ink transfer,
ensemble, high-pass and slid control behind P3. Findings 111 and 112 read their meshes and normals through the
same functions.

Main moved during the round, from `c463e40` to `da27038`. The owner merged five PRs between 02:18 and 04:49 UTC:
#425, #427, #433, #436 and #437, 40 files. They are merged into this branch without conflict, they do not touch
the module, and their review is left to later rounds.

## What changed

### Twenty-seven guards of the measurements are now tested (`tests/test_first_letters_343_mesh_step.py`)

The module is registered, so it is left as it is. This round made 54 mutants of the measurements. The module's
tests, #411's and round #172's, killed 26. Eleven new test functions (18 cases) kill 27 of the other 28, and the
last cannot change a result.

- **The loader keeps x, y and z in order.** A loader that read the three files in another order passed every
  test, because a distance is the same in a frame whose axes are swapped. The new test also binds which nodes
  exist: zero is a position, and −1 in any one coordinate, a NaN or an infinity is no node.
- **A normal is not taken across a missing node.**
- **The surface distance** now has tests for these:
  - a node is covered up to exactly 30 voxels sideways, measured across the normal, so 28 sideways and 13 along
    the normal is covered;
  - a missing node of the other surface is never a partner, even when its stored position is the nearest;
  - the five quantiles are the ones they are named, the median is the 50th, and "within 2" includes 2;
  - `b_nodes` counts the nodes that have a normal.
- **The ink transfer takes the nearest source**, not the last one within reach, and the earlier one on an exact
  tie.
- **`normals_agree` is the median cosine**, so a minority of cells that run backwards does not move it.
- **The ensemble standardises each model over the mask and weighs the models equally.** Cells outside the mask
  are not read for the mean or the SD, and a model with a thousand times the range counts as much as another.
- **`pearson` has no value for a constant side or an empty one.**
- **The high-pass weighs the local mean by the cells it has.** A constant map leaves nothing, up to the edge of
  the mask.
- **Each of the four slides reads only the cells its slid map covers**, and the control is the largest absolute
  value, so a strongly negative slide counts. #411's test covered the wrap of the rightward slide.

No code changed.

## Verified, no change needed

- **Each measurement does what its docstring says** on every case this round probed.
- **Every caller masks the normals.** `grid_normals` gives a missing node a normal when its four neighbours
  exist. `surface_distance` keeps only nodes that exist and have a normal, and so do finding 111's mesh comparison
  and finding 112's score. Rounds #170 and #171 bound the last two, and this round binds the first.
- **One bound in `lattice_points` cannot be met.** A cell centre lies at (4i + 1.5) / 20 nodes, which is never a
  whole number, so "at or before the last node" and "before the last node" are the same test. That is the mutant
  no test can kill.
- **#411's tests already bind the rest of the sample**: the reach of the ink transfer, the lattice's weights and
  both of its constants, the direction of each slide, the high-pass's mask, and a model that is constant.

## Observations for the owner (not changed)

- **`grid_normals` returns a normal for a node that does not exist.** It takes central differences from the four
  neighbours and never reads the node itself. Its docstring does not say so. Every caller in the repository masks
  the result, so nothing is wrong today; a new caller that trusted the returned mask alone would score missing
  nodes.
- **The band verdict command still fails on a full fit with no scored winding.** Round #171 reported it. #425
  and #427 have since changed `band_fit_verdict.py` to take the arms as arguments, and on `da27038` the command
  still raises `KeyError: 'excess_median'` for that case and writes no record. The script is edited when a new
  band is registered, so the fix can go with the next registration.

## Verification

- **The touched module.** `test_first_letters_343_mesh_step.py` gives 88 passed, against 70 on `da27038`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,013 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 225 modules give 234 failing ids. 173 are the ids of round #172's run. The other 61
  are in three modules that came with the owner's merges: `tests/test_experimental_interfaces.py`,
  `tests/test_proofreader_session.py` and `tests/test_regional_memory_profile.py`. Run alone on `da27038`, the
  three give the same 61, each for want of the villa checkout.
- **The test modules outside the suite.** The 259 modules give the same 23 failing ids as round #172's run, and
  2,615 passed. The run before the merge gave 2,594, against round #172's 2,576.
- **The doc audit**, run alone, lists the same unresolved references as on `da27038`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

`da27038` itself was run only for the three new modules. Every failing id is this container's: it has no villa
checkout.

## A note on this round's work

- **The round was validated twice.** The first run was on `c463e40` with the new tests and gave the same failing
  ids as round #172's. The owner's five merges arrived while the session was down, so the suite and the modules
  outside it were run again on the merged tree, and the figures above are from that run.
- **Still not reviewed in #411:** `transfer_maps.py`, `snap_chunks.py`, `s3_fetch.py` and `s3_plan.py`, the
  launchers, the setup files and the README.
- **Still not reviewed:** #422, #424 and #428, the five merges named above, the rest of #390, the rest of #396,
  and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample** of the measurements. Both of the module's test files passed here before the
  mutants were run. The 28 survivors were run again against the new tests; the 26 that the module's tests killed
  were not.
- **The exact tie in the ink transfer is tested on whole-number positions.** Lattice points are interpolated,
  and two interpolated sources do not tie exactly.
