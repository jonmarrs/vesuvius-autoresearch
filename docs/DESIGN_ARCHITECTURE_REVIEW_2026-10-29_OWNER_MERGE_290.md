# Design and architecture review — the owner's #290 (seed-heading trace completion)

Date: 2026-10-29. Baseline: `337dd1be` (main after #290).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 20:12 UTC firing. #290 makes the seed-heading re-run launcher end in `CHAIN_FAILED` and exit 1
when a trace fails or leaves incomplete outputs. A new standard-library helper, `scripts/seed_heading_chain_status.py`,
decides completion from each run's latest logged attempt and its outputs, for both the launcher and the comparison.
A `chain.lock` lease serializes a work directory. The comparison publishes its record with an exclusive hard link.

#290 answers two observations in the #278 and #281–#284 review:
- a failed re-run ended with `CHAIN_COMPLETE` and exit 0;
- no test ran the comparison's `main()`.

I reviewed it myself; it is one launcher, one helper and their tests. Nothing needed a change.

## Verified, no change needed

- **The completion rule matches the real tracer.** #290's tests use a stub tracer, so I read villa's `volume.py` at
  39a8cf3a, the commit the re-run traces. It writes the three outputs the helper requires:
  - `run.json` at the start;
  - a `tiles.jsonl` line per finished tile;
  - each tile to `tiles/<name>.partial.npz`, renamed to `.npz` when finished.

  Rerunning with the same `--out` resumes and keeps finished tiles, which is what a retry after `FAILED` relies on.
  A successful real trace therefore passes `outputs`, and an interrupted one leaves a `.partial.npz` or no
  finished tile.
- **The latest attempt decides.** A later `TRACE` or `FAILED` overrides an earlier `DONE`, and `SKIP_DONE` is ignored.
  A run whose outputs were deleted is traced again. Malformed event lines, unreadable logs and vanished files give
  exit 2, which the launcher turns into a setup refusal (exit 3).
- **The launcher's control flow.**
  - In the `else` branch, `$?` is the status check's own exit code.
  - Under `set -u`, an empty `FORMAT_ARGS` expands to nothing on bash 5.2.
  - The lease is taken before the villa commit record and before source extraction, so two launches cannot extract
    or record at once.
  - `--require-afv` is passed only in the legacy `.afv` mode.
  - Import probes must now exit 0 as well as print the right path.
- **The comparison.** It refuses an incomplete run before importing ScrollGT. The record goes to a temporary file in
  the same directory, which is fsynced and given the mode `replacement_mode` computes (0666 less the umask for a
  new file), then hard-linked to its name. An existing record or a dangling symlink at the target is kept.
- **The tests.** On the launcher and comparison before #290 (`33aea5c7`), 17 of the 33 tests in its two files fail.
  #290's record names eight. Here they give 64 passed, with the draft, file-mode and suite-guard tests. The 2 the
  owner's run skipped pass: this container has the Villa checkout.
- **The checks.**
  - Ruff 0.9.10 `check` and `format` are clean on its five Python files.
  - Mypy is clean over the whole repository (833 files), and `bash -n` passes on the launcher.
  - The test runs leave the checkout unchanged.

## Observations for the owner (not changed)

- **Run events share `chain.log` with free-form output.** The import probes' stderr and `patch`'s output are
  appended to the same file. A stray line whose first word is `TRACE`, `DONE` or `FAILED` (for example "FAILED to
  load …") makes the status helper report UNKNOWN (exit 2). The launcher then refuses every run until the line is
  removed. It fails closed. None of the probes or `patch` would plausibly print such a line.
- **`status --work W` does not check a legacy `.afv` export unless given `--require-afv`.** The launcher passes it
  in `.afv` mode, and the draft's command is for the 39a8cf3a chain, which writes no export.
- **The comparison still calls `logged_done` inside its scoring loop**, after the up-front check of all four runs.
  It is redundant and harmless.

## Verification

- **#290's test files**, with the draft, file-mode and suite-guard tests, give 64 passed.
- **The standard suite**: pending.
- **The doc audit**: pending.
