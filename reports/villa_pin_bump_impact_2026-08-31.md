# Advancing the villa pin from `ced62390e` to `c935851c3`: analysis, and what it actually broke

> **The bump is DONE**, at commit `d4433fa5`. Everything from here to "The verification below was
> INCOMPLETE" was written *before* it, as a hypothetical, and is left in that tense deliberately so
> the prediction can be read against the outcome.
>
> **The pin analysed was `5479453a`; the pin actually taken was `c935851c3`.** Upstream moved three
> commits further while this was being written, so every path check below was re-run against
> `c935851c3` before the bump and gave identical answers. References to `5479453a` in the
> pre-bump text are left as written rather than retro-edited.

**2026-08-31.** Read-only analysis, no pin was moved. This exists because "bump the pin, but first
verify `ink-detection/` is untouched" has been the standing rule, and the naive form of that check
**fails**: `ink-detection/` is heavily changed across the 153 intervening commits. The rule as
written would block the bump. The real question is narrower, and the answer is that the bump is
almost entirely safe.

## The headline diff looks alarming and mostly is not

```
git diff --stat ced62390e origin/main -- ink-detection/
  111 files changed, 2 insertions(+), 19342 deletions(-)

git diff --stat ced62390e origin/main -- deprecated/
  126 files changed, 21385 insertions(+)
```

This is villa's deprecation of ink-detection: files moved to `deprecated/`, not destroyed. A
path-scoped diff cannot see a move, which is the same trap that produced the correction in commit
`ed4784e4` earlier this project. The insertions under `deprecated/` exceed the deletions, so nothing
was lost upstream.

## The ground truth is untouched, and not for the reason the rule assumes

| path | tracked at `ced62390e` | tracked at `5479453a` (re-verified identical at `c935851c3`) |
|---|---:|---:|
| `ink-detection/train_scrolls` | **0** | **0** |
| `ink-detection/eval_scrolls` | **0** | **0** |

The GT is **not tracked by villa at either commit**. It is locally downloaded data sitting inside an
ignored directory, so a submodule checkout cannot delete it: git does not remove untracked files.
The standing rule protects the right thing but names the wrong mechanism. `ink-detection/` changing
is not evidence the GT is at risk.

## What our code reads from `villa/`, and whether it survives

| path | old | new | under `deprecated/` | verdict |
|---|---:|---:|---:|---|
| `ink-detection/optimized_inference` | 26 | 26 | 0 | survives |
| `foundation/datasets/fibers-dataset` | 9 | 9 | 0 | survives |
| `foundation/volume-registration` | 7 | 7 | 0 | survives |
| `crackle-viewer` | 0 | 0 | 7 | not ours to lose |
| `discord_chatbot` | 16 | **0** | 16 | **moves to `deprecated/discord_chatbot`** |

Only one path our code names would move, and **two** scripts hardcode it, not one:
`scripts/rag_guided_search.py` and `scripts/rag_researcher.py`.

> **Corrected while acting on this report.** It originally named only `rag_guided_search.py`,
> because the grep behind it was piped through `head -5` and the second file fell off the end. A
> truncated search reported as a complete one. The same mistake in the other direction would have
> left a broken import behind after the bump.

**Both are already dead code.** They depend on a vector store at
`villa/discord_chatbot/discord_vector_store` that does not exist locally, so neither can run today
regardless of the pin. `rag_guided_search.py` was last touched 2026-06-04 and is referenced nowhere;
`rag_researcher.py` was last touched by a lint sweep on 2026-05-29 and is cited only by
`docs/VILLA_STRATEGY.md`. The bump would break something already broken.

## The verification below was INCOMPLETE, and the bump proved it

Everything above was written before the bump. Doing it broke the suite twice, and both misses
came from the same flaw in how the paths were found.

**The check grepped for literal `villa/...` strings.** It therefore could not see a path assembled
from components:

```python
_SPIRAL = os.path.join(_REPO, "villa", "volume-cartographer", "scripts", "spiral")
```

`satisfaction_metrics.py` moved from `volume-cartographer/scripts/spiral/` to `spiral-fitting/`, and
four files hardcoded the old location. Result: **19 test collection errors**. Fixed by resolving
either location and raising if neither holds the module.

**A second failure was ordering-dependent and no path check would have caught it.**
`tests/test_resnet3d_decoder.py` passed alone and failed in the suite. The repo root holds a DATA
directory `models/` with no `__init__.py`, which still shadows as a namespace package, and
`vesuvius_model.py` used `sys.path.append`, leaving villa's real `models` package last. It had only
ever worked because `benchmark_harness.py` puts `villa/ink-detection` on `sys.path` and the OLD pin
had `models/resnetall.py` there. The bump moved that into `deprecated/` and removed the accidental
fallback. Fixed by putting villa's path first and evicting any shadowing `models` for the duration
of that import, restoring both afterwards.

**And the repo already had an automated version of this audit.**
`tests/test_audit_doc_references.py` flagged five stale paths introduced by these very changes. It
does mechanically what the analysis above did by hand, and it was not consulted first.

Lesson: a path audit that greps one spelling of a path is not an audit, and no static path check
detects a dependency that resolves through `sys.path` ordering. The suite is the check that works.

| suite run | result |
|---|---|
| before the bump | 718 passed |
| after the bump | **19 collection errors** |
| after the path fix | 2 failed, 730 passed |
| after both fixes | **732 passed, 1 skipped** |

## Outcome, and what is still not done

The recommendation below was followed: both dead RAG scripts deleted, pin advanced, ground truth
verified intact (55 GB, 9 segment dirs, all three labelled segments present by name, availability
probe unchanged at `exhausted_no_candidate`). The suite went 718 passed, then 19 collection errors,
then 732 passed once both breakages were fixed.

**The GPU tests are now DONE and green.** Run once the seed fits released the card:

```
tests/test_detector_*.py tests/test_sota_*.py tests/test_vesuvius_loader.py
  -> 93 passed, EXIT=0, with CUDA available
parity tests, with GPU        -> 7 passed
parity tests, CUDA masked     -> 6 passed, 1 SKIPPED
```

So the bump is verified by the full CPU suite (732 passed) and by the GPU suites.

**A standing note is out of date, in a good way.** The record said the parity test *fails* under
CUDA masking rather than as a regression. It no longer fails: `test_cpu_gpu_vesselness_parity` now
skips with an explicit reason, `no CUDA device (absent, or masked by the shell)`. A skip that
explains itself is strictly better than a failure that has to be remembered as benign, and the note
warning about it can go.

## Recommendation (written pre-bump, followed)

The bump is safe for everything that matters: ground truth, `optimized_inference`, and `foundation`
are all unaffected. Before bumping, either repoint `rag_guided_search.py` at
`deprecated/discord_chatbot` or delete it as dead code. My preference is deletion, since it depends
on a vector store nobody has built in three months.

Still required after any bump, and **not** done here: run the detector, sota and loader tests with
the GPU. Those need the card, which is committed to the seed fits.

## And the rule itself should be reworded

"Verify `ink-detection/` is untouched" now permanently fails, so as written it forbids every future
bump. What it should say is: **verify that no path our code reads has moved or vanished, and note
that the GT under `train_scrolls` is untracked local data that a checkout cannot remove.**
