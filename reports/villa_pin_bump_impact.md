# What advancing the villa pin from `ced62390e` to `5479453a` would actually do

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

| path | tracked at `ced62390e` | tracked at `5479453a` |
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

Only one path our code names would move. `scripts/rag_guided_search.py` hardcodes
`villa/discord_chatbot` in five places.

**It is already dead code.** Nothing in the repo references `rag_guided_search`, its vector store
`villa/discord_chatbot/discord_vector_store` does not exist locally, so the script cannot run today
either, and it was last touched 2026-06-04. The bump would break something already broken.

## Recommendation

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
