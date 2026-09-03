# DRAFT villa issue — not posted. Slot: 2026-09-07 (1 new issue/week).

Checks done before drafting:
* prior art: no villa issue mentions `col_width_conformity`, `col_median_width`, or
  `get_ink_metrics` column scoring. Searched 2026-09-03.
* still live: `spiral-fitting/get_ink_metrics.py` is byte-identical between the ref we measured
  (`5479453a`) and current `origin/main` (`1ee7f94d3`); `COL_WIDTH_PX = 850.0`,
  `COL_WIDTH_TOL = 0.15` unchanged.
* no AI-authorship markers anywhere in the body.

Reviewer note: keep it short. Our #1621 thread was called "excessively verbose"; the body below is
deliberately under 400 words with the detail in a collapsed block.

---

**Title:** `get_ink_metrics`: detected column width is ~4x narrower than the ink's actual periodicity, so `col_width_conformity` is a tail statistic

**Body:**

`score_columns` targets `COL_WIDTH_PX = 850` +/- 15% (722-977 px). On PHercParis4 renders it reports
`col_median_width_px` of **227-406 px** (inner, w010-w019, n=7) and **225-306 px** (outer,
w120-w129, n=6) — roughly 4x narrower than the target in every strip we have.

Measuring the strips directly, without the detector, the 850 px target looks **right** and the
detector looks wrong. Column-mean ink profile, high-passed above 2500 px, band power over 100-2000
px:

| region | strips | 150-400 px | peak | 700-1000 px | peak |
|---|---:|---:|---:|---:|---:|
| inner w010-w019 | 7 | 14.5-17.2% | ~305 px | **21.5-25.5%** | **944-956 px** |
| outer w120-w129 | 5 | 8.6-9.2% | ~301 px | 5.4-6.5% | 736-825 px |

The inner windings carry a dominant ~945 px periodicity — inside your own 722-977 acceptance band,
and stable to 12 px across seven independent fits. The detector reports 227 px on those same strips.
It appears to be segmenting sub-column runs rather than columns.

Consequence for the score: `col_width_conformity` asks what fraction of detected runs land in
722-977 px while the runs are ~4x narrower by construction, so it behaves as a tail count. Across six
same-config seeds it carries essentially all of `col_score`'s variance:

```
col_score              mean 0.1823   CV 0.1877
col_width_conformity   mean 0.2248   CV 0.1871      <- all of it
col_gap_contrast       mean 0.8113   CV 0.0075      <- 25x steadier
line_score             mean 0.3497   CV 0.0405
```

Separately, the same measurement says the outer windings genuinely lack the ~945 px structure (that
band drops to a quarter of its inner power with an unstable peak), on strips 9x wider and so ~10x
better able to detect it. So a low outer `col_score` is partly real signal, not only this artefact.

We have no view on the fix — merging adjacent runs before measuring width, or weighting
`col_gap_contrast` over `col_width_conformity`, are both consistent with what we see, and you know
the detector's intent.

<details><summary>reproduction</summary>

Rendered with `render_ink.py` + `get_ink_metrics.py` at `5479453a` against the published
`representations/predictions/ink-3d/` volume, on our own spiral fits of `spiral_datasets/PHercParis4`.
Profile = column-mean of the concatenated strip; high-pass = subtract a 2500 px moving average; Hann
window; `rfft`; band power normalised over periods 100-2000 px. Inner n=7 and outer n=5 are separate
fits differing only in `optimizer_random_seed`.

</details>
