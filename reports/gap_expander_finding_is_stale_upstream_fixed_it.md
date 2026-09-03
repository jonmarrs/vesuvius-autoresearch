# The gap-expander finding is STALE: upstream fixed it on 2026-08-27, and our provenance was wrong

**2026-09-03.** Found while checking for duplicates before an outward post, which is the only reason
it was found at all. Two separate errors, one about villa and one about our own records.

## 1. villa already fixed the default. Do not report it.

The finding as published says villa's shipped spiral config "warns about itself on every run":
`shell_outer_winding_idx` = 130 requires `model_gap_expander_num_windings >= 133`, and the default is
130.

**That was true. It is not true now.** Commit `61a62c445`, "Spiral gap expander fix" (#1625), merged
**2026-08-27**, split the parameter in two:

* `model_gap_expander_capacity_windings` — "Allocated gap-lattice capacity... Must be at least
  `shell_outer_winding_idx + 3`", default **`DEFAULT_GAP_EXPANDER_CAPACITY = 144`**;
* `model_gap_expander_num_windings` — now documented as "Legacy/fallback physical winding-count
  estimate used by exporters; **it does not allocate the gap lattice**", still 130.

144 >= 133, so **the shipped default is consistent and the warning no longer fires**. Every consumer
now reads `config.get('capacity_windings', config['num_windings'])`, so the legacy key is inert
wherever capacity is present.

The related upstream issue #1220 (closed 2026-07-29) is adjacent but distinct — it concerns the
dense losses being silently disabled with no shell — and was itself fixed by #1279. Its author
already knew the `<= gap_expander - 3` relationship.

**Consequence: there is no live villa-facing bug here, and posting one would report an
already-fixed issue.** This was caught by the pre-post duplicate search, which is the entire reason
that step exists.

## 2. Our own tooling provenance was wrong, twice

Worse, and entirely ours. I have repeatedly recorded that this work's tooling is villa `5479453a`,
including a commit yesterday that "corrected" an earlier claim of `c935851c3` to `5479453a`. **That
correction was also wrong**, because fits and renders do not come from the same place:

| stage | how it is invoked | ref actually used |
|---|---|---|
| **fit** | `cd villa-spiral/spiral-fitting && uv run python fit_spiral.py` | the **working tree**, `6847063f` (2026-08-26) |
| **render + score** | `git -C villa-spiral archive origin/main ...` | **`origin/main`**, `5479453a` (2026-08-30) |

Two different refs in one pipeline, and every document quoting a single one is wrong.

The decisive evidence is in our own checkpoints: `model_gap_expander_capacity_windings` is **ABSENT**
from the resolved config of every fit, while `model_gap_expander_num_windings` is present at 130
(base) or 133 (gap). The capacity key cannot be absent at `5479453a`, which defines it with a
default — but it does not exist at all at `6847063f`, which predates #1625.

## 3. What this does and does not invalidate

**The measurements stand.** Every arm was fitted by the same code and rendered by the same code, so
the comparisons remain internally valid:

* the geometry effect (5 gap seeds vs 6 base, +1.034%, p = 3.9e-06, completely disjoint) is real
  **for villa as of 2026-08-26**;
* the ink arms, the outer noise floor and the column decomposition are unaffected, since none of them
  depends on which villa the code came from — only on all arms sharing it.

**The framing changes completely.** At `6847063f` the shortfall was genuine: with no capacity key,
`num_windings` *is* the lattice allocator via the fallback at `transforms.py`, the code emits
`WARNING: shell_outer_winding_idx 130 requires ... >= 133`, and raising it to 133 measurably improved
the fit. So the result is not "villa should change its default". It is:

> **Upstream's #1625 was worth about +1% `satisfied_area`, measured on 11 fits.**

That is a smaller and more honest claim, and it is a *validation of someone else's fix* rather than a
discovery of a live defect.

## 4. What should have caught this earlier

The pre-post duplicate search did catch it, one step before an outward post — but only because that
step is mandatory. Three cheaper checks would have caught it weeks earlier:

1. **Read the resolved config, not the script.** The checkpoint records what the fitter actually
   used. One `torch.load` would have shown `capacity_windings` absent and prompted the question.
2. **Pin the fit ref explicitly.** `cd <dir> && uv run python` executes whatever the working tree
   happens to be. Renders are extracted from a named ref and were therefore knowable; fits were not.
3. **Re-check a finding about upstream against current upstream before building on it.** This one was
   four days stale when the six-fit arm was registered against it.
