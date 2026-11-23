# Design and architecture review — the owner's #453 and #456, the hung-hook wait and the November filing draft

Date: 2026-11-23. Baseline: `e43d140` (main after round #198's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 07:12 UTC firing on 2026-11-23. Main had not moved since round #198's merge.

It takes two small merges of the owner's:
- **#453** fixes a race in a test helper of `tests/test_autoresearch_measurement.py`. `_alive` reads
  `/proc/PID/stat` to see whether a killed git hook is gone. A process reaped between the open and the read raises
  `ProcessLookupError`, which the helper now counts as gone, with a test.
- **#456** adds the PHerc. 211 end-to-end control, findings 118 to 121, to `docs/PRIZE_FILING_2026-11_DRAFT.md`. It
  also allows PHerc. 211's results in the filing, since its prize was announced on 2026-11-15.

## What changed

### The hung-hook wait's zombie rule is tested (`tests/test_autoresearch_measurement.py`)

This round made two mutants of `_alive`. #453's test kills the one that drops `ProcessLookupError`. The other,
which treats a zombie (`Z`) as alive, passed: the killed hook is reaped quickly, so the wait never meets a zombie.
One parametrized test reads three stubbed stat lines, `S`, `Z` and `X`, and kills it.

### Round #198's record gives the cosines that decided the flip

That record put `compare`'s cosines, −0.9962 to −0.9983, beside "The orientation was decided before any ink". The
`orient` step, which decided the flip, recorded −0.9950 to −0.9976, as finding 121's report says. The sentence now
gives both and says which is which.

No code changed. No defect was found.

## Verified, no change needed

- **The filing draft's numbers are the records'.**
  - Finding 118: r 0.53 against a largest control of 0.093, "0.09 and below".
  - Finding 119:
    - the full fit took 12,733 s, 3 h 32 min;
    - 0.8794 of the winner's 21,888 band nodes lie within 2 voxels of some winding, the 88%;
    - one winding follows the sheet for 3,640 voxels, 34 mm.
  - Finding 120: Reader V3's r is 0.6271, short of the registered margin.
  - Finding 121:
    - r 0.5194 on 0.8309 of the winner's cells;
    - 0.5388 for the winner's own surface on those cells;
    - Reader V3 0.6286 against 0.6271;
    - the chain ran from 14:15:38 to 14:57:45, 42 minutes.
  - The prize date, 2026-11-15, is the one the registrations give.
- **The failures the draft lists are in the reports.**
  - `transfer_maps.side` read the other side at depth +1 whatever depth it was given (finding 118's report).
  - The band verdict crashed on an unscored fit (#441).
  - Villa's environment could not read the winner's LZW files, and villa's `_spliced` twins were counted as windings
    (finding 119's report).
  - The windings had to be rendered flipped (finding 121's report).
- **`_alive` reads the hook's state correctly here.** The hook runs `exec sleep 600`, whose process name has no
  spaces, so the third field of its stat line is the state.

## Observations for the owner (not changed)

- **GPU memory is written as MiB divided by 1,000 and called GB.** nvidia-smi reports MiB.
  - The filing draft's three GPU figures, 12.7, 12.3 and 14.5 GB, come from records of 12,701, 12,290 and
    14,481 MiB.
  - In decimal gigabytes those are 13.3, 12.9 and 15.2 GB; in GiB, 12.4, 12.0 and 14.1.
  - The dated reports use the same conversion, so the draft repeats them faithfully.
  - For the filing, GiB with a division by 1,024, or GB with a factor of 1.048576, would be exact.
- **`_alive` reads the third space-separated field of the stat line.** A process name with a space would shift
  that field. The hung-hook test's process is `sleep`, so it does not arise. Parsing after the last `)` would hold
  for any name.

## Verification

- **The touched module.** The three new cases pass, and so does #453's. The module's other three failures here are
  among the standard suite's villa ids.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #198's run. It ran with the new test.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #198's run, and the same 3,190
  passed. One of the 24 is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `e43d140`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Two small merges make one round.** #453 changes 16 lines of a test, and #456 adds 34 lines to a draft.
- **Still not reviewed from the owner's merges since round #182:** #458, #461, #465, #468 to #478, #480, #483, #485,
  #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** Both were run again with the new test, and both are killed.
