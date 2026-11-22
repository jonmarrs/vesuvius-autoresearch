# Design and architecture review — the owner's #411, the decision path

Date: 2026-11-16. Baseline: `6c80230` (main after round #171's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 01:13 UTC firing on 2026-11-16. Main had not moved. It takes the largest of the PRs the owner
merged while the session was down: **#411**, merged at 19:31 UTC on 11-13, 30 files.

#411 is finding 110. The earlier kill test rebuilt the published PHerc. 343 image from the published windings.
This run made the windings on the owner's machine with the recipe's fit, snap and flatten, and asked two things of
them: do they lie on the published sheets, and do they carry the published ink? The decision is `REPRODUCED`.
Findings 111 and 112, reviewed in rounds #170 and #171, both import its analysis module.

#411 is too large for one round at the depth this session can afford. This round takes the decision path of
`repro/first_letters/pherc343/mesh_step/mesh_step_analysis.py`: P1, the choice of windings, P2, the orientation,
the gate, the line that decides P3, the table, and the commands that run them. The last section lists the rest.

## What changed

### Nineteen guards of the decision path are now tested (`tests/test_first_letters_343_mesh_step.py`)

The module is registered, so it is left as it is. This round made 54 mutants of the decision path, nine of them of
its constants. #411's 49 test functions killed 35. Eleven new test functions (16 cases) kill the other 19:

- **P1 and the choice hold at their bounds.** A share of exactly 50% within 2 voxels and a median of exactly 3
  hold P1, and a candidate covering exactly half of a published winding can be chosen. One covering 45% cannot.
- **Neighbours are one apart, in the published order**, however the record orders its two windings. Two apart is
  not neighbours.
- **The orientation is the weakest cosine**, and a cosine of exactly zero has no orientation.
- **`select` wants exactly two published windings** and candidate folders with different names.
- **A step killed by a signal did not run.** A negative exit code fails the gate, as a positive one does.
- **A third published winding is refused** by the table.
- **P3 holds on its floor and on twice each control**: r of exactly 0.50 with controls of 0.25 and −0.25. A hair
  under the floor, or a control a hair over half of r, fails it.
- **The letters are evaluable from half of their cells.**
- **The verdict command does not read the records of a run that failed**, so it needs neither file, and reads
  both for a run that passed.
- **The select command says when its picks are not neighbours.**

No code changed.

## Verified, no change needed

- **The decision recomputes from the record.** With the gate, the two final windings and the ink comparison taken
  from `reports/first_letters_343_mesh_step.json`, `verdict` returns the stored record, field for field:
  - all nine step records exited 0;
  - P1: 75.61% and 80.54% of published nodes within 2 voxels, against at least 50%, and medians of 0.90 and 0.73
    voxels, against at most 3;
  - P2: the chosen windings are w047 and w048, consecutive in the published order;
  - P3: r of 0.8622 over the letter boxes, against at least 0.50 and at least twice each control. The controls
    are 0.1674 and 0.1729, so r is 4.99 times the larger. 98.78% of the letter cells were compared, against at
    least 50%.
- **The report's P1 table, its control and its raw-winding figures match the record.** It says plainly that the
  raw fitted windings, before the snap, would have failed P1 (33.1% and 47.3% within 2 voxels).
- **The order of events.** The registration and the scripts were committed together (ff5ab89, 15:33 PST on
  11-12), and the results four hours later (29cd763, 19:33 PST on 11-12). Nothing in the directory changed between
  the two or since, and neither has the record or the registration.
- **The code's table is the registration's**, row for row, including the `_WITH_REDUCED_FIT` suffix and the rule
  that a failed step leaves P1 to P3 unread. #411's tests kill a mutant of each row.
- **#411's tests are thorough here.** They killed 35 of the 54 mutants, including eight of the nine constants,
  every row of the table, and every rule of the gate that this round sampled.

## Observations for the owner (not changed)

- **The registration covers the comparison, not the fit.** It says it was written "before any winding fitted here
  has been compared with the published windings or with their ink". The chain's steps take 3 h 31 min, of which
  the fit is 3 h 9 min, and the results were committed 4 h 0 min after the registration. So the fit may have been
  running, or done, when the registration was committed. That is consistent with what the registration claims,
  and the fit's settings are the recipe's. A reader should not take it to mean that nothing had run.
- **This round found no defect in the decision path.**

## Verification

- **The touched module.** `test_first_letters_343_mesh_step.py` gives 70 passed, against 54 on `6c80230`. With the
  report's module that is 74 passed, against 58.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 222 modules give the same 173 failing ids as round #171's run.
- **The test modules outside the suite.** The 257 modules give the same 23 failing ids as round #171's run, and
  2,576 passed against 2,560.
- **The doc audit**, run alone, lists the same unresolved references as on `6c80230`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

The baseline is round #171's branch run, whose tree is `6c80230`'s. Both sets of failing ids are this container's:
it has no villa checkout.

## A note on this round's work

- **Finding 110 was checked from its record, not rerun.** The run needs the scan, villa's fit, the four ink models
  and a GPU.
- **Not reviewed in #411:**
  - the module's measurements: the surface distance, the lattice, the ink transfer, the ensemble, the high-pass
    and the slid control;
  - `transfer_maps.py`, `snap_chunks.py`, `s3_fetch.py` and `s3_plan.py`;
  - the ten launchers, the seven setup files and the README;
  - the report below its P1 section, and the edits to `docs/RESEARCH_STRATEGY.md`.
- **Still not reviewed:** #422, #424 and #428, the rest of #390, the rest of #396, and the parts of #421 and #423
  that rounds #170 and #171 listed.
- **The mutants are a sample** of the decision path. Both of #411's test modules passed here before the mutants
  were run. The 19 survivors were run again against the new tests; the 35 that #411's tests killed were not.
- **The P3 bounds are tested with the three deciding numbers set by hand.** A correlation does not land on exactly
  0.50 from data, so the test replaces the two functions that compute them.
