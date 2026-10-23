# October 2026 Progress Prize — concise form answers

**Prepared 2026-10-23; not submitted.** This is one bundle of small Villa fixes.
The detailed [evidence draft](PRIZE_FILING_2026-10_DRAFT.md) retains the separate
research results and disclosures. Do not paste its entire research narrative
into this engineering submission. The current rules ask for small fixes to
be bundled and substantial independent contributions to be filed separately.

Deadline: **11:59 p.m. Pacific, October 31, 2026**. Form:
https://docs.google.com/forms/d/e/1FAIpQLSc4flEfgK2nyjoczz2_U_XrIGMlgrnSknWatLqrFPnbtKfZwg/viewform

On filing day, recheck the rules, form, PR states and links. Complete email,
full name, team description, optional Discord display name and terms yourself.
Copy the answer sections from the file, not terminal-wrapped output. Preserve
the receipt and exact submitted text afterward; no submission tag exists yet.

## URL field

```text
https://github.com/ScrollPrize/villa/pull/2022
https://github.com/ScrollPrize/villa/pull/2044
https://github.com/ScrollPrize/villa/pull/2155
https://github.com/jonmarrs/vesuvius-autoresearch
```

## What is your contribution?

**(1) Which scroll data.** PHerc. Paris 4 / Scroll 1, using Villa's published
spiral-fitting data and ink scorer, including the outer w120–w129 strip and
a smaller w010–w019 strip. The measured scorer runs used one RTX 4090.

**(2) How this helps people read the scrolls.** Three fixes merged into Villa
this month make the existing spiral-fitting workflow usable and reproducible:

- **#2022 (merged 2026-10-11):** correct the autoresearch runner instructions
  to use the shipped CLI's flags. The old instructions failed to launch and
  could silently drop a requested configuration change or GPU selection.
- **#2044 (merged 2026-10-11 Pacific):** add opt-in `--sequential-folds` and
  average fold probabilities in place. On the real outer strip, stock scoring
  was OOM-killed 70 seconds in, at a peak of at least 27.6 GB; sequential
  scoring completed at 13.8 GB in 1,009 seconds under a 26 GiB memory limit.
  It allows that strip to be scored on the tested workstation without changing
  the scoring method.
- **#2155 (merged 2026-10-21):** fix the spiral-fitting README's NVIDIA pip
  command to install `--group cuda`. The old command installed neither track
  extraction backend on Linux x86-64; the corrected command selects the CUDA
  dependencies already used by the documented uv route.

**(3) What this enables.** Users can launch the documented runner with the
intended variant and devices, score a large outer-winding strip within the
measured memory limit, and install the GPU track-extraction dependencies by
following the pip instructions. Sequential folds are optional and slower;
the default concurrency is preserved.

**(4) Evidence.** The three linked PRs contain the reproduction commands and
before/after evidence. #2022 checked the runner's generated commands and
environment with its expensive subprocesses stubbed. #2044 ran the actual
scorer on published scroll data: on the smaller strip, the three modes'
counts agree within 0.005%, consistent with measured run-to-run variation.
The averaging step itself was checked for bit-identical output; that is not
a claim that the complete GPU scorer is deterministic. #2155 verified package
selection with pip dry runs rather than claiming a new extraction benchmark.

The public Autoresearch repository preserves the patches and measurement
records. The upstream fixes are released in Villa under its existing license.
These changes use published models and data and introduce no new trained
model or dataset requiring a separate release.
