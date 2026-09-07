# Upstream contribution SOP: small surgical PRs

**Adopted 2026-09-07.** Replaces report-only engagement with villa.

## Why

Eleven PRs to `ScrollPrize/villa`, all closed, none merged. They were `feat(...)` additions and
self-listings. Meanwhile the August 2026 prize winners merge 4-25 line fixes to defects in villa's
*existing* code — `+4/-0` "Fix ConvBlock encoder ignoring pool_type", `+7/-1` "Fix ZarrDataset
calling a method that does not exist", `+0/-2` "Remove unused view menu entries".

**We were reporting defects; they were fixing them.** Our issues are good bug reports nobody
actioned.

First PR in the new shape — [#1721](https://github.com/ScrollPrize/villa/pull/1721), `+4/-4`,
documentation only — merged in about an hour.

## Where candidates come from

| source | status |
|---|---|
| our open villa issues | 6 open, each an already-diagnosed defect; #1658 yielded two PRs |
| [`repro/spiral_render/README.md`](../repro/spiral_render/README.md) | nine obstacles hit running villa from published data; several we already solved, so the patch predates the PR |
| anything that breaks while running their code | every hour lost to an undocumented obstacle |

## Verify before writing, every time

**Check current upstream, never our own notes.** Our README records that `lasagna/fit.py` imports a
module absent from `lasagna/` and calls it undocumented. The import defect is still live, but
`lasagna/README.md` now documents the requirement in two places — a PR built on the stale note would
have been wrong in public.

1. Is the defect still present at `origin/main`?
2. Is it already documented or fixed?
3. Can you prove it in one command a reviewer can paste?

## Shape

- **One defect, 4-25 lines.** Nothing the reviewer must verify on your behalf.
- **Evidence in the body**, pasteable.
- **State what you did not touch, and why.** #1721 left an adjacent suspect log path alone and said
  so; that is what makes a small diff read as careful rather than careless.
- **Do not smuggle in a recommendation.** #1722 documented that two metrics exist and explicitly
  declined to promote them to a guard — that judgement belongs to the maintainers.
- **No AI-authorship markers**, in commits or PR bodies, including `Co-Authored-By` trailers. This
  overrides the repo's own commit convention for villa-facing work: PRs #922 and #923 were rejected
  over exactly that.

## Cadence

Fixes are not governed by the new-issue backlog gate. Still one thing per PR, and do not batch-dump
a backlog in a day.
