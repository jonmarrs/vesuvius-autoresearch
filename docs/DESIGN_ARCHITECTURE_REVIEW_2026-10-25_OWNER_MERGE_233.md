# Design and architecture review — the owner's #233 (finding 100 in the October draft)

Date: 2026-10-25. Baseline: `5fe8f07f` (main after the owner's #233).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 20:13 UTC firing. The 16:12–19:12 firings found main unmoved after #234. #233 folds finding 100
into `docs/PRIZE_FILING_2026-10_DRAFT.md`:
- it adds a part-(2) bullet with finding 100's results;
- its failed P2 joins the registered tally, which becomes twenty-three;
- the "does not claim" list now scopes "following the sheet adds coverage" to the two held-out Scroll-5 cubes.

## What changed

- **One sentence in the draft said the two arms traced the same dots.**
  - The draft said that, traced from villa's own CT axis, "the same dots cover less than along the sheet on 9 of the
    10".
  - Finding 100 says otherwise. Each arm traces the dots it skips as they are offered, and each arm's new traces
    change which later dots are already owned. On the ten held-out cubes, sheet traced 4,135 of them and keep 4,727.
  - The sentence now says "the skipped dots". `tests/test_filing_2026_10_numbers.py` binds the new wording, and the
    figures in the sentence are unchanged.

## Verified, no change needed

- **The bullet's figures are finding 100's.** #233's test computes each one from the JSON:
  - coverage 0.333 → 0.399 and 0.268 → 0.382 (1.20× and 1.43×), with precision moving −0.013 and +0.007;
  - Scroll 3's 1.003–1.024× and median 1.017×;
  - precision within 0.017 on all ten held-out cubes;
  - keep below sheet on 9 of 10, with 1.11× and 1.28× on the two Scroll-5 cubes;
  - the in-sample 0.995–1.015×;
  - no change in ranking against our tracer at either tolerance.
- **The tally is the list.** The test counts the list's entries against its table, and the table sums to 23. No other
  copy of the count is in the repository's documents.
- **The scope matches the report:**
  - two cubes of one scroll, both cubes on which the reference mask also fails;
  - tilt was not varied;
  - one checkpoint, with villa unchanged.
- **Finding 99's bullet still ends "nothing was traced again".** It describes finding 99, and the next bullet,
  finding 100, says what tracing them did.

## Verification

- **Tests:** the filing, form-answer, withdrawn-claims, source-number and quotation tests give 116 passed and 5
  skipped, before and after the change. The skips are sibling checkouts absent from this container.
- **Perturbation:** restoring "the same dots" in the draft fails the filing test.
- **Ruff** 0.9.10 `check` and `format` are clean on the test file.
- **No independent review this round.** The change is one word in the draft and its binding.
