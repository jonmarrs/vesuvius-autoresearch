# Duplicated coverage is worth as much as real coverage to the spiral ink objective

**2026-08-31.** Pre-registered in `docs/preregistration/2026-08-31_duplicate_coverage_cost.md` and
its addendum, both committed before any arm was rendered. **Verdict: SUPPORTED**, by the rule fixed
in advance, and by a wider margin than predicted.

## Result

Three arms off one 30,000-step fit, identical render and scoring settings, lasagna path:

| arm | meshes | occupied cells | gap>=2 dup | total_fg_pixels | total_pixels | fg_fraction | line | column |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A baseline, 10 distinct | 10 | 206,321 | 0.00% | 240,088 | 26,754,900 | 0.00897 | 0.438 | 0.232 |
| B duplicate, 10 + copy of w015 | 11 | **206,321** | **10.32%** | 270,314 | 29,792,000 | 0.00907 | 0.436 | 0.209 |
| C honest, 11 distinct | 11 | 234,495 | 0.00% | 270,899 | 30,704,000 | 0.00882 | 0.388 | 0.161 |

Relative to A:

```
B (duplicate)   total_fg +12.59%   fg_fraction +0.00010   line -0.002   column -0.024
C (honest)      total_fg +12.83%   fg_fraction -0.00015   line -0.050   column -0.072
```

**Arm B has byte-identical occupied cells to arm A: it adds zero new papyrus.** Its eleventh mesh is
a copy of w015's geometry carried at index 20. It still gains 30,226 ink pixels, 12.59% on the
objective, against the 30,811 pixels that arm C gains from a genuinely new winding.

## The decision rule, applied

`dT(B) = +0.1259 > +0.02` and `|dF(B)| = 0.00010 < 0.02`, so the registered verdict is **SUPPORTED**:
duplicated coverage produces exactly the signature `autoresearch.md` calls a real win, "lifts total
while holding fraction roughly steady", while recovering no new text.

The comparison that matters is not the threshold but B against C. **They are interchangeable.**
`total_fg_pixels` differs by 585 pixels out of ~270,000, and `fg_fraction` by 0.00025. Nothing in
the metric pair separates re-counting ink already counted from reading ink for the first time.

## The structure metrics do not help, and this cuts against my own suggestion

I asked in villa#1658 whether the loop should be told to read `overall_line_score` and
`overall_column_score`, which the scorer already writes and `autoresearch.md` never mentions. They do
not catch this. Both fall for both arms, and they fall **further for the honest arm**: line -0.050
against -0.002, column -0.072 against -0.024. On every one of the four numbers, the duplicate arm
looks equal to or better than the arm that genuinely read more papyrus.

The likely reason is that these metrics reward self-similar layout, and duplication is maximally
self-similar, while a genuinely new winding brings new line spacing and column placement that
disturbs the periodicity. So on this evidence they are not the missing guard. That is worth saying
plainly, since it weakens a suggestion I made upstream.

## Controls, all pre-registered, all passed

* duplicate integrity: B shows 10.32% of cells claimed by windings >=2 apart, against 0.00% for A;
* arm separation: C stays at 0.00%, so it is real growth and not more duplication;
* alignment: every arm rendered non-blank, p95 8.0 / 8.0 / 10.0, so no arm is a silent frame failure;
* lasagna converged in all three, 74 to 95 seconds.

## What this does not show

**It does not show villa's loop has ever done this.** Nothing here observes their optimiser. It
shows the metric pair cannot price the difference if it ever did.

**The satisfaction metrics are genuinely untested here, and that is a real limit.**
`autoresearch.md` also directs the loop to watch `fit_spiral.py`'s satisfaction numbers as a
cross-check. My manipulation is post-fit: I copied a mesh folder, so the fit and therefore its
satisfaction metrics are unchanged by construction. An optimiser that produced duplicate coverage
*through the fit* would move those numbers, and they might well catch it. This experiment cannot
say. Testing that needs a fit driven to duplicate, not a duplicated mesh.

One fit, one ten-winding span, one scroll, no repeats. A single duplicated winding is a crude stand
in for what an optimiser would find.

## Reproducing

`repro/spiral_render/` for the render path. Arms are built by copying `w015_spliced_*` to
`w020d_spliced_*`; overlap is checked with `scripts/measure_winding_overlap.py --quant 4`.
