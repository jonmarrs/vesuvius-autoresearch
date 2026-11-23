# Design and architecture review — the owner's #450, the PHerc. 211 end-to-end comparison

Date: 2026-11-23. Baseline: `09685fb` (main after round #197's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 06:12 UTC firing on 2026-11-23. Main had not moved since round #197's merge.

It takes **#450**, finding 121. Our own fit's windings near the winning PHerc. 211 surface are snapped, flattened,
rendered and read, carried onto the winner's surface, and compared with the winning reader's map by finding 118's
numbers. `repro/first_letters/pherc0211_control/end_to_end.py` has two steps:
- `orient` decides, from the geometry and before any ink, whether each winding must be rendered flipped to sample
  along the winner's normals.
- `compare` carries each winding's maps onto the winner's lattice, from the nearest cell within 4 voxels, and scores
  them. A winding that still samples against the winner's normals stops the comparison.

`run_end_to_end.sh` chains the steps, and `run_render.sh` gains a `flip` argument. All three are registered, so this
round adds tests only.

## What changed

### Fourteen more rules of the comparison are tested (`tests/test_first_letters_0211_end_to_end.py`)

This round made 23 mutants of `end_to_end.py`, and #450's tests killed 5. Seven new test functions kill 14 of the
other 18. The last four are equivalent, below.

- **`orient` leaves a zero cosine undecided and measures only the band.** The registration says to stop if any
  cosine is missing or zero. With finding 110's distance stubbed to return exactly 0 for one winding, that winding's
  decision is `None`, `orient` exits 1, and the chain would stop. The stub also records how many of the winner's
  nodes were measured: the band's rows only, where #450's winner lay wholly inside the band.
- **`compare` stops on a winding whose cosine is exactly 0.** The code reads "samples against the winner's
  normals" as a cosine of at most 0, after the flip. #450's tests used cosines near ±1.
- **Each refusal has its own reason.** An unreadable mask, a winner's map on another lattice, and a `compare` with
  no winding of ours each stop, the last with argparse's exit 2. None of the three ran before.
- **The record's described numbers each come from their own source.** One run, with a winding that leans 0 to 3
  voxels off the sheet, maps that carry their own noise, and a mask that leaves out ten cell columns, shows that:
  - the input hashes are the studio map's and the mask's;
  - `cells_compared` counts only compared cells, fewer than the cells the winding gave;
  - the transfer distance's median is below its 95th percentile;
  - each part's r is against our maps, and its finding-118 r against the winner's own.
- **A cell share and a winding's cell count exactly at their lines are measured.**
- **A winner's cell at exactly 0.5 is ink.**

No code changed. No defect was found.

### Four mutants are equivalent

- **Dropping the `numbers is None` check from `verdict`** changes nothing: finding 118's verdict already returns
  `DOES_NOT_RUN` for `None`.
- **Dropping `which >= 0`, or dropping the winner's `ok`, from the compared cells** changes nothing. The transfer
  leaves `which` at −1 wherever the winner's lattice point is not `ok`, and the carried maps are NaN wherever `which`
  is −1, so the finiteness test removes those cells either way.
- **Dropping Reader V3's finiteness from its cells** changes nothing. Its carried maps are NaN exactly where the
  ensemble's are, and finite elsewhere, as round #197 found for `compare_readers.py`.

## Verified, no change needed

- **The orientation was decided before any ink, as registered.** `orient` recorded median cosines of −0.9950 to
  −0.9976 for the four windings, and all four were rendered flipped. `compare` measures the cosines again on the
  cells each winding gave: −0.9962 to −0.9983, which it negates for a flipped render. (This sentence first gave only
  the second range; round #199 corrected it.) The chain stops if `orient` exits 1, and refuses a winding with no
  decision.
- **This chain checks Reader V3's checkpoint before each use.** `run_end_to_end.sh` checks the SHA-256 and runs
  `check_checkpoint.py` with `|| return 1` before villa's loader sees the file. Round #197 noted that
  `run_reader_v3.sh` does not.
- **The strategy matches the record.**
  - Our windings give r 0.5194 against the winning map, on 0.8309 of its mask cells. That is past 0.30 and more than
    twice the largest control, 0.0662, so `E2E_AGREES`.
  - The winner's own surface gives 0.5388 on the same cells.
  - Reader V3 gives 0.6286, against finding 120's 0.6271.
- **The flipped render is asked for only by name.** #450's tests check that `run_render.sh` passes
  `--flip-normals` only for `flip`, and refuses any other third argument.

## Observations for the owner (not changed)

- **Two of the cell conditions in `compare` are implied by the others.** `which >= 0` and the winner's `ok` each
  follow from the finiteness of the carried maps, as the equivalent mutants show. They cost nothing and state the
  intent, but no test can tell them apart from their absence.

## Verification

- **The touched module.** `test_first_letters_0211_end_to_end.py` gives 19 passed, against 12 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #197's run.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #197's run, and 3,190 passed:
  round #197's 3,183 and the seven new cases. One of the 24 is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `09685fb`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **The three scripts are registered and unchanged.** Their mutants were run in a worktree.
- **Still not reviewed from the owner's merges since round #182:** #453, #456, #458, #461, #465, #468 to #478, #480,
  #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 23 were run again with the new tests: 19 are killed, and the four equivalent
  ones are not.
