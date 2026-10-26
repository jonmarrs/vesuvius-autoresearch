# October 2026 Progress Prize — fiber benchmark research form answers

**Prepared 2026-10-25; not submitted.** This is an optional separate research
submission covering October's ScrollGT releases and measurements. The
[engineering bundle](PRIZE_FILING_2026-10_FORM_ANSWERS.md) covers the three
merged Villa fixes; those fixes are not credited again here. Earlier benchmark
releases are background, not new October work.

The rules permit multiple submissions and ask for substantial independent
contributions to be filed separately. Review this answer before deciding to
file it. Complete personal fields and terms in the current October form;
save the receipt and exact submitted answers. Deadline: **October 31, 2026,
11:59 p.m. Pacific**. Target filing on October 29.

## URL field

```text
https://github.com/jonmarrs/scrollgt/tree/v0.9.0
https://github.com/jonmarrs/scrollgt/pull/14
https://github.com/jonmarrs/vesuvius-autoresearch/blob/b808f3d3fe208440137022bfc63039829c92d613/reports/neural_tracer_ct_context.md
https://github.com/jonmarrs/vesuvius-autoresearch/blob/b808f3d3fe208440137022bfc63039829c92d613/reports/neural_tracer_ct_context_512.md
https://github.com/jonmarrs/vesuvius-autoresearch/blob/b808f3d3fe208440137022bfc63039829c92d613/reports/neural_tracer_heading_residual.md
https://github.com/jonmarrs/vesuvius-autoresearch/blob/4f35917240f6b359f674e8fe457f8c3c18cbd919/reports/neural_tracer_steep_heading.md
```

## What is your contribution?

**(1) Which scroll data.** Twenty-one published fiber cubes from Scrolls 1,
3 and 5 at 7.91 µm: ten 256³ cubes and eleven 512³ cubes, with Villa's
human-traced skeletons and public model predictions. Eleven cubes are in the
reference mask model's training set; ten are held out from that mask. An
entrant trained on those ten would need its own disclosure.

**(2) How this helps reading.** October's ScrollGT releases make fiber
comparisons harder to misinterpret. Version 0.6 adds the held-out split and
refuses to average it with in-sample scores. Version 0.7 fixes an ERL
denominator that rewarded deleting short fragments: deleting our tracer's
instances under 400 voxels raised the old ERL from 35.39 to 41.46 while
coverage fell from 0.62 to 0.38. The corrected score counts the fiber a
labelling misses; all 126 published rows were re-scored, with their old
values reproduced under the old definition.

Version 0.9 adds real scan context around each cube and a separate neural
tracer row. The earlier cube-only protocol dropped seed dots near CT edges.
Giving the same tracer real CT around its unchanged tracing box increases
coverage 1.76–2.78× on all ten 256³ cubes and 1.19–1.35× on all eleven 512³
cubes. At tolerance 2 it ranks first on merge-penalized ERL on 10 of 21,
against 8 with the cube alone. This is a protocol correction, not a new model.
The mask and other entrants remain cube-only, so it is not a matched-context
comparison between every entrant.

The registered follow-up, Finding 100, traced previously skipped seeds from
the presence direction projected into the CT sheet. It adds 1.20–1.43×
coverage on the two held-out Scroll-5 cubes. On Scroll 3 the median is only
1.017×, below the registered 1.05×, so that prediction failed. Precision
stays within 0.017 of baseline on the ten held-out cubes; the ranking against
our tracer changes on none. One checkpoint, two Scroll-5 cubes, and no
manipulation of tilt: this does not establish tilt as the cause.

**(3) What this enables.** Readers can score their own instance labels on
public data, reproduce built-in baselines on CPU, distinguish held-out from
in-sample results, and choose explicitly between cube-only and scan-context
inputs. Old scorer versions are refused when comparing with current floors.
The code is MIT licensed; annotation and model sources are attributed.

A CPU reproduction follow-up (ScrollGT #14) fixes a whole-volume distance
transform allocation failure: the 512³ example completes at 2.57 GiB peak
RSS under a 7 GiB address-space budget. Both checked examples reproduce all
15 fields of their published rows. The v0.9.0 tag identifies the released
benchmark; the PR identifies this later usability patch.

**(4) Evidence.** The released targets include provenance, scorer versions,
baseline rows and commands. The linked context studies were pre-registered
and retain their identity checks and outcomes. The broader reports preserve
failed predictions and label exploratory analyses. Finding 99, exploratory
and not pre-registered, identifies CT-axis disagreement in every classified
heading failure, with all small-cube dots and sampled large-cube dots
analysed separately. It suggests testing the H/V-axis assumption. Finding
100's measured policy results have the limited scope given above;
production Villa and the published benchmark rows are unchanged.

Luke Finigan's earlier outside contribution fixed edge-order sensitivity in
the scorer; that work is credited to him. It is evidence of outside use and
is not claimed as my October implementation.
