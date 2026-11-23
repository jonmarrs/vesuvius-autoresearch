# Design and architecture review — the owner's #472, the thin band render

Date: 2026-11-23. Baseline: `19b11af` (main after the owner's #524).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 22:12 UTC firing on 2026-11-23. Main had moved since round #213's merge. The owner's #524 updates
the November filing draft and adds `scripts/record_villa_open_prs.py` with its record. It is listed below for a later
round.

It takes **#472**, which registered finding 129, PHerc. 0813's band read, and its amendment 1: render the 18 layers
Studio reads instead of all 66.
- `repro/first_letters/eligible_band/run_render.sh` takes `RENDER_SLICES`, an even count from 18 to 66, renders
  that many centred layers, and names the output `wNNN_N.zarr`.
- `render_frame.py` maps a layer of the 66-layer frame to its index in a centred render of fewer layers.
- `env.sh` gives each scroll its own scan, and adds PHerc. 0800.

Both scripts are under `repro/first_letters/`, so this round adds tests only.

## What changed

### The render is run, not only refused (`tests/test_first_letters_thin_render.py`)

#472's tests run the render only far enough to refuse a bad layer count, and check the rest by its text. With
`render_frame.py`'s own tests, they killed 11 of this round's 19 mutants. Three new test functions, 5 cases, run a
copy of the render beside a copy of `env.sh`, with `docker` on the path and GNU time as stubs. They kill 7 of the
other 8; the last is equivalent, below.
- **The layers asked for are rendered and recorded.**
  - 18 layers flipped, and 66 unflipped when no count is given, are rendered as asked into `w001_18.zarr` and
    `w001_66.zarr`.
  - The gate records the flip and the count.
  - A count of 18 is accepted, not only the refused counts around it.
- **A missing final winding, an earlier output and another sampler image are refused** before anything is rendered.
- **A render without its level 2, or one that fails, is recorded with its exit.**

No code changed. No defect was found.

### One mutant is equivalent

**Accepting a count of 0 in `frame_index`** changes nothing. No index lies in `0 <= index < 0`, so the layer check
refuses it anyway.

## Verified, no change needed

- **Each scroll gets its own scan.** Sourced for PHerc. 0826 and 0813, `env.sh` gives 9.362 µm at 113 keV. For
  PHerc. 0800 it gives 8.640 µm at 116 keV and the CT `20250521135224-8.640um-1.2m-116keV-masked.zarr`, as the
  0800 registration names it.
- **The 18 layers are Studio's.** An 18-layer render holds layers 24 to 41 of the 66: Studio's 26 to 41 and the
  surface layer 33. #472's tests check that Studio's planes from 18 layers equal those from 66, and that the summary
  finds layer 33 in an 18-layer render. Round #203 checked the planes through `frame_index` for a 20-layer render.

## Observations for the owner (not changed)

- **The doc audit cannot resolve two commits that #524 cites.** The filing draft names `research/wrong-hand-read`
  at dc232051 and `research/studio-band-triage` at 26d5c8a5. Both are on origin: the first is on its branch, and
  the second is its branch's head. Neither branch is merged, so in a checkout of main alone the audit lists both as
  found nowhere. They resolve once the branches merge.

## Verification

- **The touched module.** `test_first_letters_thin_render.py` gives 28 passed, against 23 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #213's run.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #213's run.
  - 3,358 passed: round #213's 3,350, #524's 3 new cases in the filing draft's module and this round's 5.
  - 4 xfailed, as in round #213.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `19b11af`. Those are round #213's and
  the two commits on research branches that #524's filing draft cites, above.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`run_render.sh` and `render_frame.py` are unchanged.** Their mutants were run in a worktree. This container has
  no GNU time, so the tests' copy points its one `/usr/bin/time` at a stub, and checks that it occurs once. The
  `docker` stub answers the sampler check with the pinned sha unless told otherwise.
- **Still not reviewed from the owner's merges since round #182:** #473 to #478, #480, #483, #485, #488, #489, #493,
  #496, #505, #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 19 were run again with the new tests: 18 are killed, and the equivalent one is
  not.
