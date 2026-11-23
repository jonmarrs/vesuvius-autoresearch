# Design and architecture review — the owner's #463, the PHerc. 1667 renderer check

Date: 2026-11-23. Baseline: `8c3c81f` (main after round #194's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:12 UTC firing on 2026-11-23. Main had not moved since round #194's merge.

It takes **#463**, which registers a bounded check of the corrected surface renderer (contract 2) on one fixed
PHerc. 1667 crop. `repro/sota_data/revalidate_render_1667_v2.py`:
- reads a plan bound to a fixed design and to the hashes of its source files;
- captures each public source object it reads, refusing any object whose length or status is not what it should be;
- renders the crop through the production renderer;
- scores the render's centre layer against five fixed reference depths, with an NCC gate of 0.60.

`render_surface.py`'s chunk reader gains an optional `fs` argument, so the check can supply captured bytes. The
script is registered, so this round adds tests only.

It also reads #398, which adds `pynrrd` to the declared dependencies.

## What changed

### Fourteen more rules of the check are tested (`tests/test_render_revalidation.py`)

This round made 27 mutants of the script, and #463's tests killed 13. Eight new test functions, 14 cases, kill the
other 14. The rules they cover:

- **Each plan rule refuses its own edit.** The four edits are an extra key, another protocol, an upper-case commit
  and a changed design. #463's test changed only a source hash, so dropping any of the other four rules went
  unnoticed.
- **A response other than its declared whole object is refused.** That covers an empty body, a body longer than its
  `Content-Length`, and a 206 partial status.
- **An exhausted byte budget refuses before asking the server.** #463's test met the budget on the response length
  instead, which gives a different refusal.
- **A failed read raises unless the caller asks for it back.** With `on_error="return"` it is returned in place of
  the bytes.
- **A real redirect is refused, not followed.** #463's redirect case has its stub opener raise the 302 itself, so the
  script's no-redirect handler never ran. The new test serves a 302 from a local server. The read fails, nothing is
  captured, and the redirect's target is never requested. Building the opener without the handler, or emptying the
  handler, now fails.
- **A missing chunk stops the render rather than becoming fill.** The renderer fills a chunk with zeros only when
  the read raises `FileNotFoundError`. The transport reports a 404 as a plain `OSError`, so the render stops. #463's
  test accepts any `OSError`, and `FileNotFoundError` is one, so a transport that raised it would have passed while
  the render filled the chunk. The new test runs a 404 through the renderer, both after `warm` and on demand.
- **The best reference depth is the one that matches.** #463's references were all identical, so the maximum and
  the minimum were the same depth.
- **A best NCC exactly at the gate passes.**

No code changed. No defect was found.

## Verified, no change needed

- **The gate is the preregistered one.** The preregistration requires a maximum NCC `>= 0.60` without rounding. The
  script compares with `>=`, and the new test holds it there.
- **The renderer's new `fs` argument changes nothing by default.** Without it the reader still opens anonymous S3.
  #463's test shows the production chunk decoder runs on the captured transport without `s3fs`.
- **Every captured key stays inside the study's source tree.** A key outside `PHerc1667/`, or one with an empty, `.`
  or `..` part, is refused before any request. #463's test covers it.
- **The guide matches the record.** `docs/SURFACE_RENDERER.md` cites the check's maximum centre-plane NCC of 0.78897
  on a fully supported crop. It also says the historical whole-segment and depth experiments were not repeated.
- **#398's dependency is declared and locked.** It adds `pynrrd>=1.1.3`, and the lock pins 1.1.3 with its sdist and
  wheel hashes. #398's first test checks that `pynrrd` and `fft-conv-pytorch` are both declared and locked. Its
  second runs Villa's configured augmentations in a fresh process. That needs the `vesuvius` package, which this
  container lacks.

## Observations for the owner (not changed)

- **A missing chunk is an error only because of the exception's type.** The script's docstring promises that a
  missing object is an error here even though Zarr would fill it. That holds because the transport wraps every
  failed read as a plain `OSError`, and the renderer fills only on `FileNotFoundError`. Nothing in the script says
  so. The new test fails if that changes.
- **An environment installed before #398 has no `pynrrd`.** This container's is one: #398's probe records the
  `nrrd` module as absent. `uv sync` installs it from the lock.

## Verification

- **The touched module.** `test_render_revalidation.py` gives 37 passed, against 23 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #194's run. It ran with the first 11
  of the new cases. The last three were added after it, and the module and the suite guard were run again with all
  14: 44 passed.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,782 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `8c3c81f`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`repro/sota_data/revalidate_render_1667_v2.py` is registered and unchanged.** Its mutants were run in a worktree.
- **Still not reviewed from the owner's merges since round #182:** #447, #448, #450, #453, #456, #458, #461, #465,
  #468 to #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 27 were run again with the new tests, and all 27 are killed.
