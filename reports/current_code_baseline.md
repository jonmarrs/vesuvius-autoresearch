# Current villa recovers 68% more ink than the code our corpus was built on

**2026-09-08.** Three baselines on current villa (`d8c5f488a`), seeds 1-3, 30,000 steps, fit and
render/score. Established because `spiral-fitting` had moved 35 files / +3,385 lines past our pin
(`reports/corpus_is_on_superseded_code.md`), and villa's own loop doc requires a baseline first.

## Result

| arm | `satisfied_area` | `total_fg_pixels` | strip px | `fg_fraction` |
|---|---:|---:|---:|---:|
| curbase_s1 | 0.8472 | 2,904,520 | 403,291,800 | 0.00720 |
| curbase_s2 | 0.8494 | 2,901,177 | 409,365,000 | 0.00709 |
| curbase_s3 | 0.8503 | 2,841,071 | 417,105,600 | 0.00681 |
| **mean** | **0.8490** | **2,882,256** | 409,920,800 | **0.00703** |
| old-corpus mean (n=6, pinned code) | 0.8390 | 1,720,000 | ~360,000,000 | 0.00475 |

**+67.6% on the objective. +48% on ink density.**

## It is not a bigger-strip artefact, and not a changed scorer

The strip is 14% larger, which alone cannot explain a 68% count. **`fg_fraction` rises 48%**, so the
ink is genuinely denser, not merely more numerous.

And the instrument is unchanged. Between the old corpus's render ref (`5479453a`) and these
baselines' (`d8c5f488a`):

| file | status |
|---|---|
| `spiral-fitting/render_ink.py` | **identical** |
| `spiral-fitting/get_ink_metrics.py` | **identical** |
| `spiral-fitting/tifxyz.py` | **identical** |
| `lasagna/fit.py` (the flatten) | changed |

The renderer, the scorer and the mesh loader are byte-identical. What changed is the **geometry** —
the fit and the flatten. So this is villa's fitting work recovering more ink through the same
measuring apparatus, which is the strongest form the claim can take.

## Validity

* all three passed the registered non-blank control (47.5%, 47.9%, 47.3% nonzero), consistent with
  every previously measured arm (44.8-48.6%);
* arms differ only in `optimizer_random_seed`; same dataset, same 30,000 steps, same z-ROI;
* seed spread on ink is 2.2% (2,841,071 to 2,904,520), far tighter than the 68% effect;
* the pinned tree is untouched and `tests/test_villa_spiral_refs_pinned.py` still passes, so the old
  corpus remains reproducible.

## What this does to our earlier results

**The four decoupling findings were measured on materially worse geometry.** They stand as
measurements of that code — the arithmetic is unchanged — but whether `satisfied_area` and
`total_fg_pixels` still come apart *on current code* is now an open question, and the corpus
correlation (r = -0.121 over 24 fits) describes the old tree only.

**The bar for an optimisation attempt moved from ~1.72M to ~2.88M.** Any change we propose must beat
a baseline that is 68% higher than the one we had been implicitly targeting.

## Not claimed

Which specific upstream change produced the gain. Twelve commits touched the fit and one touched the
flatten; this measures their combined effect, not an attribution.
