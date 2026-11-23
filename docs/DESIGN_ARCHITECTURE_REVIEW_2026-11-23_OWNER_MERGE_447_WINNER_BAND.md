# Design and architecture review — the owner's #447, the PHerc. 211 winner band

Date: 2026-11-23. Baseline: `fe0319f` (main after round #195's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 04:12 UTC firing on 2026-11-23. Main had not moved since round #195's merge.

It takes **#447**, finding 119. It measures whether the recipe's fit of PHerc. 211's band z 7650–9150 puts a winding
on the surface that won the prize. `repro/first_letters/pherc0211_control/winner_sheet.py` has two steps:
- `choose` scores every raw winding against the winner's nodes in the band, takes finding 110's choice, and writes
  the snap list: the chosen winding and its index neighbours. It also describes how much of the winner lies near
  any winding, and, given a distance field, the chosen winding's tiles against the winner.
- `verdict` scores the snapped copy of the chosen winding and applies the registered table.

`run_after_fit.sh` chains the registered steps. `env.sh` now derives each array's chunk range from the band, and
gives a second band of one scroll its own run directory. The script and launchers are registered, so this round adds
tests only.

## What changed

### Sixteen more rules of the measurement are tested (`tests/test_first_letters_0211_winner_band.py`)

This round made 30 mutants of `winner_sheet.py`, and #447's tests killed 14. Five new test functions, six cases, kill
the other 16:

- **The band starts at z 7650 and leaves out missing nodes.** #447's test had no node at 7650 and no missing node.
- **The snap list keeps the width of the chosen name.** The neighbours of `w0100` are `w0099` and `w0101`. A fixed
  width of three would find neither.
- **`near_any` counts a node exactly on each line, over the band's nodes only.** A winding exactly 2 voxels off
  counts within 2, one 3 voxels off counts within 4 only, and the shares are of the band's nodes.
- **`choose` and `verdict` measure only the winner's nodes inside the band.** In #447's tests the winner lay wholly
  inside the band, so either step could drop the band mask unnoticed. The new test's winner lies two thirds below
  the band, and the windings reach only just below it. Measured over the whole winner, the right winding would
  cover too little of it to be chosen, and its snapped copy would read `PARTLY_ON_IT`. The test also pins the band's
  node count, the order of `three_closest`, and that a winding with no median is left out of it.
- **The described tiles are the chosen winding's, against the band's part of the winner.** #447's tests never pass
  `--sdt`, so none of that path ran. With a stub distance field, the new test checks that:
  - the field is opened at group 1;
  - the lower tile row, below the band, is not scored;
  - the scored tile is labelled `chosen`;
  - a winding smaller than one tile gives no summary.

No code changed. No defect was found.

## Verified, no change needed

- **The verdict applies the registered table.** #447's tests check each line of it at its edge.
- **Spliced twins are never raw windings.** `mesh_step_analysis.winding_index` uses `re.match`, so it reads
  `w031_spliced` as winding 31. The `_spliced` test in `raw_windings` is what keeps the twin out, and #447's test
  covers it.
- **The chunk ranges cover the band and 64 slices either side.** `env.sh` still gives the default band's chunks,
  25–31, 39–46 and 79–92. #447's test checks the z 7650 band's ranges against each array's chunk size.
- **The strategy matches the record.** `docs/RESEARCH_STRATEGY.md` gives 31% of the winner's nodes within 2 voxels.
  The record's snapped chosen winding has 0.3122 of the 21,888 band nodes within 2 voxels, which reads
  `PARTLY_ON_IT`.
- **`run_after_fit.sh` runs `winner_sheet.py` in this repository's environment.** The winner's tifxyz files are
  LZW-compressed, and villa's environment cannot read them. #447's test checks the order of the steps and that
  nothing is uploaded.

## Observations for the owner (not changed)

- **`three_closest` can list a winding that could not be chosen.** It ranks every winding that has a median,
  including those that cover less than half of the winner's band. It is described, not registered.
- **One test of the PHerc. 813 band depends on the machine's free disk.**
  `test_first_letters_0813_band.py::test_a_render_is_refused_when_the_disk_is_nearly_full` runs the render guard
  with `FL_MIN_FREE_GB` unset and expects it to pass. That needs 50 GB free under the run directory. This container
  has less, so the case fails here, on main as on this branch.

## Verification

- **The touched module.** `test_first_letters_0211_winner_band.py` gives 14 passed, against 8 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #195's run.
- **The test modules outside the suite**, now all 308, give 24 failing ids and 3,162 passed:
  - the 264 modules of the earlier list give the same 23 failing ids as round #195;
  - on `fe0319f` the 44 added to it gave 374 passed and the free-disk case failed, and on this branch they give the
    same, plus the six new cases.
- **The doc audit**, run alone, lists the same unresolved references as on `fe0319f`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`winner_sheet.py` and its launchers are registered and unchanged.** Their mutants were run in a worktree.
- **Rounds #182 to #195 ran an out-of-suite list fixed on November 17.** It missed 44 test modules added since,
  #447's two among them. Those rounds' records said "the same 264 modules", which was true, but the list was not
  every module outside the suite. From this round the list is rebuilt each round from the tracked test modules: 308
  now. Of the 44, only the free-disk case above fails here.
- **Still not reviewed from the owner's merges since round #182:** #448, #450, #453, #456, #458, #461, #465, #468 to
  #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 30 were run again with the new tests, and all 30 are killed.
