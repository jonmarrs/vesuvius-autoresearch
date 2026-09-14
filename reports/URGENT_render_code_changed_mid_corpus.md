# The render code changed mid-corpus, and two published nulls may be masking real effects

**2026-09-13, written the moment it was found, while `curbase_s6` is still running.**
**This is not yet a retraction — it is a confound with a decisive test not yet run.**

## What is established

`repro/spiral_render/setup_workdir.sh:19` builds every render work dir from the villa submodule's
**`origin/main`**:

```bash
git -C "$VILLA" archive origin/main spiral-fitting lasagna vesuvius/src | tar -x -C "$W"
```

Our submodule pin advanced **`d8c5f488a` → `be09a8503` at 2026-09-11 13:22** (commit `0242fd99`,
whose message asserted "baselines remain valid"). Render times split the corpus exactly across it:

| arm | rendered | render code |
|---|---|---|
| `curbase_s1–s3` | 09-07 23:31 – 09-08 09:43 | **`d8c5f488a`** |
| `nosamecur_s1–s3` | 09-11 19:01 – 09-12 04:55 | `be09a8503` |
| `anchor10cov_*` | 09-12 23:57 – 09-13 07:45 | `be09a8503` |
| `curbase_s4/s5` | 09-13 18:52 – 23:41 | `be09a8503` |

The diff across those pins, restricted to the render path, is **678 insertions** — `lasagna/fit.py`
(the flatten, +33), `lasagna/fit_data.py` (+136), `sparse_tensorstore_cache.py` (+39) and
`vesuvius/src/vesuvius/tifxyz/reader.py` (+144). **That is not inert.**

## The measurement that raised it

`curbase_s4` and `s5` are the **same configuration** as `s1–s3` — same dataset, same tree, same
30,000 steps, differing only by seed. They land **+4.3% higher in ink**:

| arm | `total_fg_pixels` | vs s1–s3 mean |
|---|---:|---:|
| s1 / s2 / s3 | 2,904,520 / 2,901,177 / 2,841,071 | — |
| **s4** | **3,019,583** | **+3.85 sd** |
| **s5** | **2,992,717** | **+3.09 sd** |

Their `satisfied_area` is unremarkable (84.8%, 85.2% against 84.7–85.0%), so the fits are normal. The
difference appears **after** the fit — which is where the render sits.

## Why this matters beyond the study in flight

**Every comparison in this corpus against `curbase_s1–s3` crosses that boundary**, because those three
are the only arms rendered with the old code:

* **Same-winding ablation** (`reports/decoupling_does_not_cleanly_reproduce.md`): reported
  **+0.28%, CI [−2.56%, +3.13%]**, a null.
* **Anchor ablation** (`reports/anchor_ablation_verdict.md`): reported **−0.86%**, a null.

If the render change alone adds ~+4%, then both ablated arms — rendered with the *new* code — were
compared against baselines rendered with the *old* one, and **a real negative effect of roughly −4%
would appear as a null.** That is the arithmetic; whether it is what happened is not established.

## What is NOT established

**That the render change caused the +4.3%.** The alternative is ordinary seed variation: `s1–s3` span
only 63,449 (CV 0.0124) on three fits, and a df=2 spread has already been shown twice today to be
unreliably tight. Two arms landing 3–4 sd out of an underestimated spread is possible.

Two observations cut *against* the render explanation and are recorded because they are inconvenient
for the alarming reading: `nosamecur` (2,890,443) and `anchor10cov` (2,857,571) were **also rendered
with the new code** and sit within 1% of the old-code baselines, not 4% above. If the new render added
4% unconditionally, they should be high too.

## The decisive test, which is cheap

**Re-render `curbase_s1` with the current submodule and re-score it.** Same fit, same seed, same
everything — only the render code differs. Its original ink is 2,904,520.

* comes back near **2,904,520** → the render change is inert, the +4.3% is seed variation, and both
  published nulls stand;
* comes back near **3,020,000** → the render change adds ~4%, and the same-winding and anchor verdicts
  must be recomputed against a re-rendered baseline before either is trusted.

Cost: one render plus one score, ≈2 hours, no new fit. **Queued behind `curbase_s6`**, which is
mid-flight and whose box cannot be shared.

## Immediate consequences

1. **The consensus forward test is compromised as designed.** Its two triplets differ in render code,
   not only in seed. Its registered cross-triplet validity gate may catch this; if it does, the result
   is VOID and will be reported as such rather than as a number.
2. **No published verdict is withdrawn yet.** The confound is real, its effect is unmeasured, and the
   test that would settle it takes two hours.
3. **`0242fd99`'s claim that "baselines remain valid" was asserted, not tested.** Bumping a submodule
   mid-corpus is exactly the kind of change that needs a re-render check, and it did not get one.

---

# It happened again, twelve hours later, from a background job

**2026-09-14 01:13.** A monitor watching villa upstream fetched, and the submodule's `origin/main`
moved from `be09a8503` to `38c2b4278` — **while `curbase_s6` was mid-fit and had not yet rendered.**
s6 would have been rendered with a *third* villa version while s4 and s5 used the second.

**Caught and prevented:** `origin/main` was reset to `be09a8503` before s6's render began, verified
identical to what s4 and s5 used.

**As it happens, `38c2b4278` was harmless** — its 660 insertions are entirely in
`volume-cartographer/` (C++), and the diff restricted to what `setup_workdir.sh` extracts
(`spiral-fitting`, `lasagna`, `vesuvius/src`) is **empty**. The monitor's own verdict said so, and
checking confirmed it. Pinning first was still right: the cost of pinning is nothing, the cost of
being wrong is a corrupted study, and a commit titled `fix(render)` is not one to take on trust.

## The part that matters

`setup_workdir.sh` already carried this comment, in capitals, before either incident:

> *"do NOT fetch it mid-study: every arm of a comparison must be built from the same tree, and a
> fetch silently changes what future work dirs get."*

**It was addressed to a human, and a background monitor does not read comments.** The first incident
was a submodule bump I made; the second was an automated job. The warning was correct, prominent, and
useless both times.

## The structural fix

`setup_workdir.sh` now resolves the ref to a SHA **once**, archives that SHA rather than a moving ref,
writes it to `<workdir>/VILLA_SHA`, and accepts `VILLA_REF` so a study can pin one commit for all its
arms.

Behaviour today is unchanged — `origin/main` currently *is* `be09a8503`, so s6 renders exactly as s4
and s5 did — but from now on **a work dir states its own provenance**. The 09-11 split took
reconstructing render order from file mtimes to find; the next one is a `cat`.

`tests/test_render_provenance_is_recorded.sh` pins all of that.

## Two more upstream moves, both verified inert (2026-09-14 01:13 and 01:43)

The monitor fetched twice more, moving `origin/main` to `38c2b4278` and then `bfef6abe0`. **Both are
inert for rendering**, verified rather than assumed:

| from `be09a8503` to | files changed in `spiral-fitting`, `lasagna`, `vesuvius/src` | total files changed |
|---|---:|---:|
| `38c2b4278` | **0** | 8 (660 insertions, all `volume-cartographer/`) |
| `bfef6abe0` | **0** | 8 (660 insertions, all `volume-cartographer/`) |

`setup_workdir.sh` extracts only those three paths, so a render from any of the three refs produces
byte-identical code. Both commits are titled `fix(render)`, which is why the check was run rather than
the titles trusted — villa's `render` there means the C++ volume-cartographer renderer, not the
spiral ink render this pipeline uses.

`origin/main` has been re-pinned to `be09a8503` anyway, so all three arms of the triplet **record the
same SHA**. That is cosmetic given the paths are identical, but a future auditor reading
`VILLA_SHA` should not have to repeat this diff to find out that two different values meant the same
code.

**The monitor's own verdict said "render path identical" both times and was right both times.** It is
doing exactly the right check; the failure on 09-11 was a submodule bump *I* made, which no monitor
was watching for.

## The provenance record earned its keep on its first use (2026-09-14 03:13)

`curbase_s6` rendered from **`bfef6abe0`**, not `be09a8503` — a monitor fetch undid the 01:43 re-pin
before the render began at 02:37. `<workdir>/VILLA_SHA` says so, which is the entire point: this is
now a fact read from the artifact rather than reconstructed from mtimes.

**And it does not matter, provably.** Comparing *tree objects* rather than diffs, the three paths
`setup_workdir.sh` extracts are the same object in both commits:

| path | `be09a8503` | `bfef6abe0` | |
|---|---|---|---|
| `spiral-fitting` | `bd5a462d9` | `bd5a462d9` | identical |
| `lasagna` | `16da5ceb9` | `16da5ceb9` | identical |
| `vesuvius/src` | `d856e9407` | `d856e9407` | identical |

Identical tree hashes are stronger than an empty diff: they mean the extracted content is the same
object, so the archive is byte-identical. **s6's render code is the same as s4's and s5's.** The same
holds for `3b398f7cc`, four commits past our pin.

So the second triplet is internally consistent and the forward test is not compromised by *these*
moves. The 09-11 split, which crossed a real change in `lasagna/fit.py` and the tifxyz reader, is a
different matter and still needs the re-render test.

**Method note worth keeping: compare tree objects, not diffs.** `git rev-parse <ref>:<path>` answers
"is the extracted content identical" in one step, with no chance of a diff filter quietly omitting a
file. It is also the check that should have been run at the 09-11 bump, and would have failed there.

## Pre-result observation: the flatten demonstrably differs on identical input (2026-09-14 09:30)

Recorded **while the re-render is still at band 9 of 35**, before its ink number exists, so it cannot
be shaped by the outcome.

`curbase_s1`'s meshes flattened under the two code versions:

| | pre-trim grid | post-trim | bands |
|---|---|---|---:|
| original, `d8c5f488a` | 9143 × **451** | 8982 × 449 | 36 |
| re-render, `d82e13edf` | 9143 × **449** | 8990 × 446 | 35 |

**Identical input meshes, different output grid.** The pre-trim width matches exactly (9143), so this
is not a different fit being read — it is the same surface flattened differently. Strip area moves
from 4,032,918 to 4,009,540 cells, **-0.58%**.

So the 09-11 change is **not inert for rendering**, which the earlier tree-object comparison already
implied and this now demonstrates end to end on real data.

**It does not yet say the ink moves.** A 0.58% area change cannot by itself produce
the ~4% ink excess that raised this. The registered endpoint is `total_fg_pixels` against 2,904,520
with a ±2% band, and that number is still ~1 hour away.

## Correction to my own alarm: most of the "+4%" is strip area, not detector output

**Recorded 2026-09-14 09:50, while the re-render is at band 12 of 35** — before its ink number exists.

When `curbase_s4` came in high I raised this on `total_fg_pixels` alone. **I did not decompose it**,
and the decomposition changes the picture:

| comparison | ink | strip area | **density** |
|---|---:|---:|---:|
| triplet B vs A, all six | +9.49% | +1.83% | +7.54% |
| **B vs A, excluding `s6`** | **+4.30%** | +2.21% | **+2.02%** |

Per-arm density tells it more plainly:

| arm | density |
|---|---:|
| s1 / s2 / s3 | 0.00720 / 0.00709 / **0.00681** |
| **s4** | **0.00713** — inside the baseline range |
| **s5** | **0.00722** — 0.3% above the baseline max |
| s6 | **0.00834** — the only genuine outlier |

**s4 and s5's ink excess is roughly half larger strips and half density variation that sits within
the baselines' own spread.** The baselines themselves span 5.7% in density (0.00681–0.00720), so a
0.00713 and a 0.00722 are unremarkable.

### What this does to the alarm

It **weakens it substantially**. The headline that prompted this report — "the second triplet is 4.3%
higher, and it was rendered with different code" — is mostly a strip-size difference plus ordinary
density variation, not the detector firing more per pixel.

**The confound is still real**: the extracted trees genuinely differ, the flatten genuinely produces a
different grid on identical input (−0.58% area), and `curbase_s1–s3` really are the only arms rendered
before the change. Those facts stand. What is weaker is my inference that a ~4% ink bias follows from
them.

**The re-render test remains the right test** and is unaffected by this — it measures the render
effect directly on one fit rather than inferring it from a triplet comparison. Its ±2% band was
registered before any of this and is not being revised.

### The process failure worth naming

I escalated to a report titled URGENT on a difference in a *count*, having spent the previous day
establishing that `total_fg_pixels` is the wrong quantity to reason about placement with, and having
written that "the count is measurable because it is insensitive to placement". **The decomposition
into area and density takes one command and I ran it eighteen hours late.**
