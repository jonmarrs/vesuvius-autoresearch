# RETRACTED — this report measured its own filter, not the scroll

**Retracted 2026-09-03, hours after being written, before anything went outward.** Every claim below
the retraction is withdrawn. The villa issue drafted from it
(`docs/VILLA_DRAFT_column_width_4x.md`) must not be posted.

## What was claimed

That the inner windings carry a stable ~945 px column periodicity which the outer windings lack, and
that villa's detector under-measures column width by ~4x in both regions (reporting 227-406 px).

## Why it is wrong

**1. The detector measures width correctly.** Fed synthetic strips with columns of known width,
`score_columns` recovers them:

| true width | gap | detector reports |
|---:|---:|---:|
| 850 | 150 | 868 |
| 850 | 300 | 904 |
| 600 | 150 | 622 |
| 300 | 100 | 296 |
| 945 | 150 | 961 |

It also survives text-like structure: columns of pitch 945 px whose ink is broken into 100-300 px
runs separated by 30-60 px spaces are still reported at **954-965 px**. The "under-measures 4x"
claim is simply false, and one positive control would have shown that before the report was written.

**2. The ~945 px peak was an artefact of my windowing.** Across four inner strips the peak is a
*fixed fraction of strip width*:

| strip width | reported peak | peak / width |
|---:|---:|---:|
| 8810 | 944 | 0.10715 |
| 8830 | 946 | 0.10713 |
| 8840 | 947 | 0.10713 |
| 8920 | 956 | 0.10717 |

A physical column width cannot scale with the length of the strip it is measured in. This is the
residual of my own high-pass filter appearing at a fixed bin of the analysis window.

**3. The inner/outer comparison was never like-for-like.** The defect is one line:

```python
hp = min(2500, max(101, p.size // 8))     # high-pass cutoff
```

Inner strips (8810 px) got a **1101 px** cutoff; outer strips (82670 px) got **2500 px**. Two
different filters, and I attributed the difference between them to the scroll.

## What survives

* The **variance decomposition** in `reports/outer_winding_noise_floor.md` (finding 15) stands: it
  comes from villa's own `metrics.json` outputs, not from this analysis. `col_score`'s CV is
  `col_width_conformity`'s (0.1877 vs 0.1871 over six seeds) and `col_gap_contrast` is 25x steadier
  at 0.0075.
* The **new positive control** above is a real, reusable result: `score_columns` is accurate on clean
  and on text-like input, so its 227-306 px readings on real strips are telling us something about
  the strips rather than about the detector. What that something is remains **open** — which is where
  finding 15 left it, and where it goes back.

## What the method can and cannot measure, established afterwards by control

Running the same spectral method on synthetic profiles of **known** period, at each real strip
length, gives the precise reason it failed:

| true period | strip length | recovered | |
|---:|---:|---:|---|
| 300 | 8,810 (inner) | 293 | ok |
| **850** | **8,810 (inner)** | **952** | **FAIL, 12% out** |
| 945 | 8,810 (inner) | 952 | ok |
| 300 | 82,670 (outer) | 300 | ok |
| 850 | 82,670 (outer) | 854 | ok |
| 945 | 82,670 (outer) | 947 | ok |

At inner-strip length that method returns ~952 px whether the truth is 850 or 945.

**Correction to this section, same day.** I first read that as a resolution limit of an 8,810 px
strip. It is not. It was the `hp = 2500` high-pass *trimming 5,000 of 8,810 points*. A linear
detrend with a zero-padded FFT — no moving average, no trimming — recovers 300, 850 and 945 px to
within 0.6% at BOTH strip lengths. That estimator is now
`scripts/measure_strip_periodicity.py`, with the control as a test.

**And with a working estimator the answer is still no, for a better reason.** Calibrating the
band-power share of the dominant peak:

| input | share of band power |
|---|---:|
| synthetic sine, SNR 2:1 | 8.3% |
| synthetic sine, SNR 1:3 | 6.8% |
| pure noise, inner length | 0.9% |
| pure noise, outer length | 0.1% |
| **real inner strips** | **4.2-4.4%** |
| **real outer strips** | **1.1-1.2%** |

No real strip reaches the level a genuine line produces, and the inner peaks *still* sit at a fixed
fraction of strip width (0.11940, 0.11937, 0.11945 for widths 8810/8830/8840) — the signature of no
line at all, now with a validated instrument.

**So the conclusion is not "the outer windings lack column structure" but "an ink profile has no
single dominant column period to find".** Spectral periodicity is the wrong tool for finding 15.
Answering it needs positional ground truth — where the columns actually are on a strip — against
which the detector's runs can be compared. That is a labelling problem, not a signal-processing one,
and this report is a record of spending a day discovering it.

## The lesson, which is not the one I would have chosen

I did run controls. I ran them *after* writing the report and drafting an issue for publication.
The scaling check that killed it took thirty seconds and needed no new data. The trigger for running
it was "this is about to go to the people who wrote the code" -- which is far too late for a check
that cheap, and it is only luck that the trigger fired at all.

Three method errors during the analysis itself were caught and corrected in flight (an
autocorrelation band whose peaks piled at its edge, a detrend that suppressed the target scale, a
size filter that dropped every inner strip). Catching those built a false sense that the method had
been shaken out; the filter-scaling defect was of exactly the same kind and survived all three.
