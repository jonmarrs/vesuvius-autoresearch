# Design and architecture review — the owner's #468 and #470, the filing draft's Studio lines and the dense snap

Date: 2026-11-23. Baseline: `d3100b9` (main after round #205's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 14:12 UTC firing on 2026-11-23. Main had not moved since round #205's merge.

It takes two of the owner's merges:
- **#468** adds findings 122 to 124 to the November filing draft: the 2023 Grand Prize TimeSformer, Studio
  reproducing the winner's map on this machine, and Studio reading our own fit of the winner's place.
- **#470** registers and reports finding 130: does snapping a twice-denser winding grid keep more of the rendered
  surface on the predicted sheet? `repro/first_letters/eligible_band/` gains three files:
  - `densify_winding.py` subdivides a winding's grid, keeping the original nodes and adding bilinear midpoints. A
    new node exists only where every node it takes weight from exists.
  - `dense_snap.py` compares the two arms, with finding 125's grid as `outer80` and the denser one as `dense2`.
  - `run_dense_snap.sh` runs densify, snap, flatten and compare, each only if the one before exited 0.

Both scripts are registered, and the filing draft is the owner's, so this round adds tests only.

## What changed

### Thirteen more rules of the dense snap are tested (`tests/test_first_letters_dense_snap.py`)

This round made 23 mutants of the two scripts, and #470's tests killed 9. Nine new test functions, ten cases, were
added. Eight of them, nine cases, kill 13 of the other 14. The last mutant is equivalent, below. The ninth function
is a strict xfail, below.
- **A missing centre node removes exactly its eight new neighbours**, which between them take it as each of the four
  corners. Every original node is kept where it was. This holds for a node marked −1 and for one that is NaN.
- **A factor below one is refused.**
- **A winding without a recorded scale takes the default 0.05**, and doubles it.
- **The verdict at its other edges.** No windings does not run, and a median on the triangles of exactly 0.95 helps.
- **The comparison does not run without any gate.** An empty gate folder would otherwise read as every step passing.
- **The verdict reads the dense arm's triangles.** A dense arm that gains on the sheet but lies 5 voxels off its own
  snapped triangles gives `DENSE_SNAP_NO_GAIN`.
- **The radius terciles split the nodes in thirds**, and **the comparison is measured once.**

No code changed.

### One mutant is equivalent

**A one-row grid indexing its rows from row 0 instead of from zeros** changes nothing. With one row, `h - 2` is −1,
and row −1 is the only row.

### A strict xfail marks a crash in the comparison

The distance field gives NaN outside its extent and on its no-data cells. A winding whose final nodes in one radius
tercile all fall there has no finite distance in that tercile, and `measure` gives `None` for it, as written. The
summary then takes the median of the windings' values for each tercile, and `np.median` raises `TypeError` on the
`None`. So one such winding stops the whole comparison, and no verdict is written. The test is a strict xfail: once
the comparison completes with `None` in the row, it passes and its mark has to come off.

Read from the code, not tested: a winding with no value anywhere gets `None` for its whole share, and the gain's
subtraction raises in the same way.

## Verified, no change needed

- **The verdict is the registered table's.** The median gain over the six windings is +0.0697, at least +0.05, and
  the dense arm's median share on its snapped triangles is 0.9877, at least 0.95. Every step exited 0, so
  `DENSE_SNAP_HELPS`. #470's report test checks each table against `reports/first_letters_dense_snap.json`.
- **The report's described lines match the record.**
  - The tercile medians gain +0.0707, +0.0886 and +0.0730, so "+0.07 to +0.09 in each third".
  - The snapped nodes' median share rose by +0.0581.
  - w070 ends at 0.5651, after 0.5771 to 0.6241 at the snapped nodes.
  - The snapped nodes are about four times as many on the dense arm: 23,883 against 6,056 on w020, for example.
- **The filing draft's new lines match their records.**
  - The TimeSformer's r = 0.24 is finding 122's 0.237.
  - Studio's reproduction is finding 123's r 1.0 over 8,838,800 pixels in 75 seconds. Its 14.5 GB is 14,481 MiB, the
    conversion round #199 noted.
  - Our fit read by Studio gives finding 124's r 0.8247, controls −0.0471 and 0.1141, and 0.9745 on our render of
    the winner's surface.
  - The note that this machine's uv lacked the winner's pinned Python, solved by the winner's own bootstrap, matches
    the driver's amendment.

## Observations for the owner (not changed)

- **A winding partly outside the distance field stops the comparison.** It did not arise in finding 130: every
  tercile of all six windings has a value in the record. The comparison is measured once, so the crash matters only
  if `dense_snap.py` is reused, for windings that run past the surface prediction.
- **The no-gate case is stricter than the registration.** The registration's `DOES_NOT_RUN` is "a step failed". The
  code also gives it when no gate was written at all. The driver writes the densify step's gate, and compares
  only after densify exits 0, so the two agree on every run the driver can make.

## Verification

- **The touched module.** `test_first_letters_dense_snap.py` gives 18 passed and 1 strict xfail, against 9 passed
  before. `test_first_letters_dense_snap_report.py` gives its 4.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #205's run.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #205's run.
  - 3,262 passed: round #205's 3,253 and the nine new passing cases.
  - 3 xfailed: round #200's two and this round's.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `d3100b9`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`densify_winding.py` and `dense_snap.py` are registered and unchanged.** Their mutants were run in a worktree.
  The crash was confirmed in a scratch probe before its test was written.
- **Still not reviewed from the owner's merges since round #182:** #469, #471 to #478, #480, #483, #485, #488,
  #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 23 were run again with the new tests: 22 are killed, and the equivalent one is
  not.
