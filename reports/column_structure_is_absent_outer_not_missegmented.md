# The outer windings genuinely lack column structure, and villa's detector under-measures it everywhere

**2026-09-03.** Answers the question `reports/outer_winding_noise_floor.md` (finding 15) left open:
are the ~270 px columns the scorer reports on w120-w129 real, or is the detector mis-segmenting out
there? **Neither, quite.** The structure is genuinely absent in the outer windings, and separately the
detector under-reports column width by about 4x in *both* regions.

Measured without the detector: the column-mean ink profile of each rendered strip, high-passed to
remove drift slower than 2500 px, then compared across two period bands by spectral power.

## Result

| region | strips | 150-400 px band | peak | 700-1000 px band | peak |
|---|---:|---:|---:|---:|---:|
| **inner** w010-w019 | 7 | 14.5 - 17.2% | 301-315 px | **21.5 - 25.5%** | **944-956 px** |
| **outer** w120-w129 | 5 | 8.6 - 9.2% | 299-302 px | **5.4 - 6.5%** | 736-825 px |

Two things separate cleanly.

**1. The inner windings carry a strong, very stable ~945 px periodicity. The outer windings do not.**
Across seven independent inner strips the 700-1000 px band is the *dominant* one and its peak sits
between 944 and 956 px — a 12 px spread. Across five outer arms the same band collapses to roughly a
quarter of that power and its peak wanders over 736-825 px, which is what a spectrum does when there
is no line to find.

This is not a resolution artefact, and the direction matters: the outer strips are **82,670 px wide
against the inner 8,810**, so they contain about 87 cycles of a 945 px period where the inner strips
contain 9. The outer measurement has nearly ten times the power to detect that periodicity, and finds
less of it. A short strip could fake a peak; a long one cannot easily hide it.

**So the answer to finding 15 is "the data, not the detector".** villa's column score is low and noisy
on w120-w129 because the column structure it looks for is genuinely weaker there, not because the
detector fails in that region.

**2. villa's 850 px expectation is well calibrated — for the inner windings.** The measured 944-956 px
sits inside its own acceptance band of 722-977 px (850 +/- 15%). That is a point in the metric's
favour and worth stating, since this project has mostly catalogued the ways it misleads.

**3. But the detector reports widths about 4x too small, in both regions.** It gives
`col_median_width_px` = 227 on the inner strips where the dominant periodicity is ~945 px, and
240-293 on the outer ones. Whatever it is segmenting, it is not the ~945 px unit; it is finding
sub-column runs and measuring those.

That explains finding 15 mechanically. `col_width_conformity` asks what fraction of detected runs fall
in 722-977 px while the runs it detects are ~4x narrower **by construction**, so the term is a tail
count in *both* regions — it merely has less to work with in the outer one. `col_gap_contrast`, which
does not depend on run width, is correspondingly stable (CV 0.0082).

## Limits

Spectral power at a period is not proof of text columns; it is evidence of a repeating intensity
structure at that scale, which is what a column layout produces but not only what produces it. The
inner strips are all from one ROI and the outer from another, so region and dataset position are
confounded with each other -- this compares two places on one scroll, not two scrolls. The 9-cycle
inner window is thin, which is why the stability of the peak across seven independent fits carries
the argument rather than any single spectrum. Nothing here says the outer windings contain no text;
it says they contain no *periodic column-scale structure* the profile can see.

## Reproduce

Column-mean profile per strip, `np.convolve` high-pass at 2500 px, Hann window, `rfft`, band power
normalised over 100-2000 px. Inner strips: `spiral_out/seedarm_*/meshes/ink`. Outer:
`spiral_out/outer_*/meshes/ink`.
