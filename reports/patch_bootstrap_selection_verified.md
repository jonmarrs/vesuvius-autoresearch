# The patch-bootstrap arms are what the registration says they are

**2026-09-04, written while arms 2-6 were still fitting.** Everything below is an *input*
property -- which patches went in, and how good the reference fit judged them. No endpoint was
read. `scripts/check_patch_selection.py`, tested in `tests/test_check_patch_selection.py`.

The datasets were built hours before the first fit started, and "the builder printed the right
number once" is not the same as "the directory on disk is still right". Reference fit:
`2026-08-28_s1_slice-13056-18432_38442-patch_baseline01/satisfied_fitted.json`.

## Enforced invariants: all hold

| set | n | mean | median | p25 | area-weighted mean |
|---|---:|---:|---:|---:|---:|
| BOOTSTRAP | 26,728 | 0.9908 | 0.9995 | 0.9922 | 0.9921 |
| RANDOM | 30,071 | 0.7986 | 0.9938 | 0.7492 | 0.8351 |
| ALL (reference) | 38,439 | 0.8003 | 0.9940 | 0.7557 | 0.8398 |

* **Both arms are subsets of the reference fit.** Zero patches in either arm are unknown to it.
* **The threshold did not leak.** The lowest satisfied fraction in BOOTSTRAP is exactly **0.9000**.
* **The arms are area-matched: 76.36% vs 76.37%**, a gap of 0.01 points. This is the invariant the
  control exists for. The first, count-matched build left them at 76.4% vs 70.0%, which would have
  confounded evidence *quality* with evidence *quantity* -- so this is checked, not assumed.

## The manipulation is real

BOOTSTRAP mean satisfied fraction **0.9908** against RANDOM **0.7986**; 9,235 of RANDOM's patches
(30.7%) sit below the 0.90 threshold. The two arms overlap in 20,836 patches, so RANDOM is not a
near-copy of BOOTSTRAP: it holds 9,235 that BOOTSTRAP excludes and omits 5,892 that it keeps.

Had the arms turned out similar in quality, a null result would have been uninformative -- no
manipulation, nothing to detect. They are not.

## A pre-flagged limitation, partly discharged

The registration recorded, before any data existed, that "RANDOM is one draw, not a distribution
over draws... an unusually good or bad draw would bias it."

**RANDOM's quality profile tracks the full population almost exactly: mean 0.7986 vs 0.8003, a
difference of 0.0017** (area-weighted 0.8351 vs 0.8398). On the selection variable, this draw is
demonstrably not extreme.

That is a partial discharge and should not be read as more. It constrains the draw on *the variable
it was drawn against* and says nothing about any other dimension -- spatial position, winding,
trace provenance -- on which this particular subset could still be unrepresentative. The registered
follow-up if the result is close remains a second RANDOM draw, not more seeds.

## What this does not tell you

Nothing about the outcome. The endpoints stay unread until all six arms exist, because
`scripts/analyse_patch_bootstrap.py` refuses a partial sample and the decision rule -- including
that a geometry-only gain is a **FAILURE**, not a partial success -- was committed before any arm
produced a number.
