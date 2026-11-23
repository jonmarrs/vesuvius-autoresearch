# Design and architecture review — the owner's #469, the band read's inspection page

Date: 2026-11-23. Baseline: `44d2423` (main after round #206's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 15:12 UTC firing on 2026-11-23. Main had not moved since round #206's merge.

It takes the first part of **#469**, which reports finding 125 and adds three tools for the band reads:
`band_index.py`, `band_geometry.py` and `band_record.py`. This round takes
`repro/first_letters/eligible_band/band_index.py`, which builds the page the owner inspects a band read on:
- it orders the windings by their largest tile ink share, an order of inspection only;
- it turns each image into reading orientation by the recipe's rule, from the winding's mesh, the scroll axis and
  the catalog's two orientation flags;
- it writes a thumbnail, and with `--geometry` a trust mask turned the same way, beside each winding's numbers.

Its `orientation` also decides the flips of the band submission (`repro/first_letters/submission/`), and
`reference_page.py` turns PHerc. 211's panels by it. `band_geometry.py` and `dense_snap.py` read the axis with it.
The script is under `repro/first_letters/`, so this round adds tests only. `band_geometry.py` and `band_record.py`
are for later rounds.

## What changed

### Thirty more rules of the page are tested (`tests/test_first_letters_band_index.py`)

This round made 37 mutants of `band_index.py`, and the existing tests killed 6. Thirteen new test functions, 14
cases, kill 30 of the other 31. The last is equivalent, below.
- **The order breaks ties by name**, whatever order the summary lists them in.
- **The axis is read in z order**, whatever order its file gives the control points in.
- **The senses are measured as the rule says.**
  - Theta is taken round the axis's own x and y. A test puts the axis where using x for y would view the winding
    from beyond it, which reverses theta's sense.
  - A winding that crosses the negative x direction, where atan2 jumps from π to −π, is unwrapped.
  - Along a row, the sense is the median step, so one fold back does not turn a winding.
  - A row's height is its median node, so one node far above its row does not turn it.
- **Missing nodes are left out of both senses.** A test marks them −1, as a tifxyz and the submission do, in the
  first eight of each row's twelve nodes. Counted in, they would put each row's height at −1, and their steps would
  make theta's median zero.
- **A single row or column has no sense along it.** The sign is 0 and that flip is off, rather than an error.
- **The page turns what it shows.**
  - Each image, its thumbnail at one eighth and its trust mask are turned the same way.
  - The mask keeps its three values when it is shrunk.
  - Each row says how its image was turned ("mirrored, upside down", "upside down" or "unturned"), and the rows are
    ranked from 1.
  - Without `--geometry`, no masks are made.
- **The page stops on a missing image or mask**, and a map smaller than eight pixels still gets a one-pixel
  thumbnail.
- **The command line** reads the fit's excess from the quality record's windings and the geometry's trusted share
  and masks. It refuses a flag other than `true` or `false`, so `True` is not read as false.

No code changed. No defect was found.

### One mutant is equivalent

**Taking the median of a row with no node in it, without the guard,** gives the same NaN. It only adds a warning.

## Verified, no change needed

- **The rule covers both frames as documented.** In PHerc. 343's frame (z bottom to top, right-handed), it flips
  top to bottom when z rises with row, and mirrors when theta rises with column. A z that runs top to bottom
  reverses both senses, and left-handed coordinates reverse theta's. The existing test checks five frames, among
  them the two PHerc. 211 cases the docstring cites: the winner's surface unturned, and our w035 mirrored only.
- **The submission's dry runs used it.** `repro/first_letters/submission/README.md` records flips true/true for
  PHerc. 343's w047, where the recipe's script's own measurement agrees. For PHerc. 211's w035 it records the mirror
  only, and the image then read in the winner's order by eye.
- **The page stays on this machine.** It writes only under the summary folder, and links images by relative paths.

## Observations for the owner (not changed)

- **A sense that cannot be measured leaves the image unturned without a warning.** A single row or column, or steps
  whose median is zero, give a sign of 0 and no flip. The submission's `orientation.json` carries both signs, so a
  0 would show there, but its driver passes the flips on without reading them. In PHerc. 343's frame the recipe's
  script then checks the flips itself; in PHerc. 211's frame, which PHerc. 0358 shares, nothing would.

## Verification

- **The touched module.** `test_first_letters_band_index.py` gives 21 passed, against 7 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #206's run.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #206's run.
  - 3,276 passed: round #206's 3,262 and the 14 new cases.
  - 3 xfailed, as in round #206.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `44d2423`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`band_index.py` is unchanged.** Its mutants were run in a worktree.
- **The recipe's own `measure_orientation` was not read.** It is in the recipe's repository, which this session
  cannot read. The rule was checked against the module's docstring and the submission's dry runs.
- **Still not reviewed from the owner's merges since round #182:** the rest of #469 (`band_geometry.py` and
  `band_record.py`), #471 to #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 37 were run again with the new tests: 36 are killed, and the equivalent one is
  not.
