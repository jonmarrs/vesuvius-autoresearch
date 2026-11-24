# Design and architecture review — the owner's #480, the Studio reference page

Date: 2026-11-24. Baseline: `644fe33` (main after round #221's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 06:12 UTC firing on 2026-11-24. Main had not moved since round #221's merge.

It takes **#480**, `repro/first_letters/eligible_band/reference_page.py`. The script writes a page, for the owner's
own look at a band read, that shows Studio's maps where the letters are known, each beside the same render read with
its planes reversed:
- PHerc. 211's windings w033 to w036, as finding 124 read them;
- PHerc. 343's published surface, as finding 127 read it.

Each map is drawn as the band pages draw theirs:
- the same encoding and reading orientation;
- thumbnails at one eighth with a 1 cm bar;
- `studio_band`'s ink share and largest tile share.

The page also gives the recipe's measured letter heights, and links the band pages that exist.

The script is under `repro/first_letters/`, so this round adds tests only.

## What changed

### The page's panels, edges and command are tested (`tests/test_studio_reference_page.py`)

This round made 26 mutants of `reference_page.py`, and #480's tests killed 4. Eight new test functions, 12 cases,
kill the other 22.
- **A panel with nothing rendered** has no ink share and no tile, rather than NaN or 0.
- **The image** rounds the probability (0.5 is 128), clips it to 0 and 255, and counts ink from exactly 0.5.
- **The 1 cm bar** is drawn only where it fits. It needs two columns of margin beyond the bar and at least 12 rows of
  thumbnail.
- **A map narrower than eight pixels** still gets a one-pixel-wide thumbnail.
- **The letter heights' median** is rounded to hundredths.
- **Each panel's turn**:
  - is recorded as given, with the voxel size;
  - is named on the page as "unturned", "upside down" or "mirrored, upside down";
  - comes with its text escaped.

  Without letter sizes or band pages, the page has neither section.
- **The default panels.**
  - PHerc. 211's four windings, each with its reversed map, are turned by `band_index`'s rule with the catalog's flags
    (top to bottom, right-handed), at 9.362 µm.
  - PHerc. 343's two maps take the sidecar's flips and voxel size.
  - Each panel reads the map and render its finding wrote.
- **`main`** reads the letter sizes under `--fl-root`, and links only the band pages that exist there.

No code changed. No defect was found.

## Verified, no change needed

- **The page's r values are the records'.**
  - PHerc. 211: finding 124's record gives r 0.8247, and −0.0471 for the reversed planes (the page's 0.82 and −0.05).
  - PHerc. 343: finding 127's record gives 0.6238 and 0.1015 (the page's 0.62 and 0.10).
- **The page reads what the findings wrote.**
  - `run_studio_e2e.sh` writes `wNNN.npy` and `wNNN_reversed.npy` into `pherc0211_control/work/studio_e2e/maps`.
  - `run_studio_343.sh` writes `forward.npy` and `reversed.npy` into `pherc343_repro/work/studio_343/maps`, from the
    render `pherc343_repro/work/concat_w047-w048_R5B2_z9500-11000_66.zarr`.
  - `run_studio_343.sh` also writes the reference image's sidecar and the letter sizes into `studio_343/reference`.
    It passes the same sidecar to `studio_343.py compare`, which reads its `orientation` as the page does.
- **The rendered area is `studio_band`'s**: layer 33 of the 66-layer frame, above zero. A map whose shape is not its
  render's is refused, as `studio_band` refuses it.

## Observations for the owner (not changed)

- **The band pages are checked in one place and linked from another.** `main` keeps a band page if it exists under
  `--fl-root`, but the page links it as `../PATH`, from the output folder's parent. The two agree only when the output
  folder sits directly under `--fl-root`, as `BAND_PAGES`' comment assumes. Written anywhere else, the page shows links
  that lead nowhere. Not changed: the script is registered material, and the page is for the owner's machine only.

## Verification

- **The touched module.** `test_studio_reference_page.py` gives 16 passed, against 4 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #221's run. It does not run the
  touched module.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #221's run.
  - 3,449 passed: round #221's 3,437 and the 12 new cases.
  - 4 xfailed, as in round #221.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `644fe33`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`reference_page.py` is unchanged.** Its mutants were run in a worktree. The default panels' test replaces
  `band_index`'s axis and orientation and the mesh loader through `monkeypatch`, so it checks which files and flags
  each panel is given, not the turn itself.
- **The suite was run without `nohup`**, as round #221 found it must be for `test_supervisor_startup.py`.
- **Still not reviewed from the owner's merges since round #182:** #483, #485, #488, #489, #493, #496, #505, #517 and
  #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 26 were run again with the new tests, and all 26 are killed.
