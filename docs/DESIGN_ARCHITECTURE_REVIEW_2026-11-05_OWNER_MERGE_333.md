# Design and architecture review — the owner's #333

Date: 2026-11-05. Baseline: `10423ea3` (main after #334, which follows #333).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 00:13 UTC firing. #333 landed during the previous round, after its review had started, and was
left for this one.
- **#333** pins detector report markers by a recorded SHA-256 and rejects ambiguous marker JSON. It takes up three
  observations from the review of #317 (`DESIGN_ARCHITECTURE_REVIEW_2026-11-01_OWNER_MERGES_305_318.md`):
  - a deeply nested marker raised `RecursionError`;
  - the scorecard's own fields were not hashed;
  - the guide's example named the tracked legacy scorecard.

No change was needed. This record is the round's only change.

## Verified, no change needed

- **The parser.** One decoder now serves both the checker and publication. It refuses:
  - duplicate members at any level;
  - nonfinite numbers, including `1e999`;
  - more than 64 nested containers, counting the root.
  - Recursion errors from the decoder and the encoder become `ValueError`, so the CLI reports them and exits 1.
- **Publication** decodes its own encoded marker with the same rules before staging or touching the previous report.
  That catches dictionary keys that collide once JSON makes them strings.
- **The pin.**
  - The expected hash is validated before any file is read. It is compared with the same captured bytes that are
    parsed.
  - Matching it skips none of the status, schema, payload and readback checks.
  - Uppercase is accepted, and the CLI reports it in lowercase. A pinned partial measurement still exits 1.
- **Each new guard is reached.** Removing any of the following fails a test:
  - the depth check, or moving its bound by one;
  - the duplicate hook or the finite-float hook;
  - either recursion handler;
  - publication's self-check;
  - the hash comparison, the lowercasing, or the hex pattern.
- **The record's counts.**
  - The module gains 21 test IDs; one replaces an existing test, a net 20.
  - On #333's parent they give 19 failed and 2 passed: the record's 18 failed and 2 passed, plus the readback-race
    case added afterwards.
  - The five modules the record names give 193 passed: detector contracts, report artifacts, prediction artifacts,
    metrics and file modes.
- **The checker** still imports no ML or image package, pinned or not (its test).

## Observations for the owner (not changed)

- **A malformed `--expected-sha256` exits 1, not 2.** The guide reserves 2 for usage errors. The new section says a
  malformed hash exits 1, so the two passages differ. The value is checked by `check_report`, not by argparse.
- **Two observations on #317 still stand.**
  - The 64 MiB total-payload check cannot fire, since there are two payloads of at most 32 MiB each.
  - Report-path errors from `eval` and `infer` still escape as `ValueError` tracebacks.

## Verification

- **#333's module** gives 90 passed. Its one warning is Torch's deprecation of `torch.jit.interface`.
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on #333's three Python files. Mypy is clean over the
  whole repository (880 files).
- **The standard suite** gives the same failures as round #143:
  - the 43 standing failures;
  - the 25 SDK cases that need `s3fs`;
  - the 2 modules that cannot be collected.
- **The 237 test modules outside the suite** give 2,231 passed, 80 skipped, 13 failed and 21 collection errors: the
  same failures as round #143.
- **The doc audit**, run alone, finds no new unresolved reference.
