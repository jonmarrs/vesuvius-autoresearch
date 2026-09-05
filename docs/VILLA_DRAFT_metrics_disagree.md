# DRAFT villa issue — not posted. Slot: 2026-09-07 (1 new issue/week).

Checks re-run 2026-09-05, because the previous withdrawn draft
(`VILLA_DRAFT_column_width_4x.md`) passed every process check and was still false:

* **both instruments are byte-identical to villa `origin/main` today** (`23adee047`), checked via the
  villa submodule rather than by fetching villa-spiral, which is pinned under a running study:
  `satisfaction_metrics.py` and `get_ink_metrics.py` both match.
* **both have positive controls**: `satisfied_area` reads 0.1004 on a 100-step fit vs 0.84 converged;
  `total_fg_pixels` falls 59.5% on the same comparison. Neither is inert.
* **prior art**: no villa issue mentions the two metrics disagreeing.
* both results **pre-registered, analysis committed before the data existed**
  (`docs/preregistration/2026-09-02_gap_ink_second_look.md`, `2026-09-03_patch_bootstrap.md`).
* no AI-authorship markers.

Reviewer note: ~380 words. #1621 was called "excessively verbose"; detail stays collapsed.

---

**Title:** spiral: `satisfied_area` and `total_fg_pixels` can move independently in both directions,
so the satisfaction cross-check is uninformative about ink

**Body:**

`autoresearch.md` prescribes optimising `total_fg_pixels` with a satisfaction cross-check. We now
have two pre-registered cases where the two come apart — in opposite directions.

**Case 1 — the guard passes on a real ink regression.** Twelve fits of `spiral_datasets/PHercParis4`,
six per arm, differing only in `optimizer_random_seed` and one config flag, rendered and scored
identically on w120-w129:

| | `satisfied_area` | `total_fg_pixels` |
|---|---:|---:|
| baseline (n=6) | 0.83897 | 1,719,984 |
| changed (n=6) | 0.84764 | 1,541,596 |
| | **+1.03%, p = 3.9e-06** | **-10.35%, p = 0.0018** |

Both sets completely disjoint on both metrics. `overall_fg_fraction` agrees at -10.78%, so it is not
a strip-area artefact. The flag is `model_gap_expander_num_windings`, which #1625 already fixed and
our fits predate — **the flag is not the point**; a change that genuinely improved geometry cost 10%
of the objective, and the prescribed guard reported the improvement.

**Case 2 — the guard fires enthusiastically on no ink gain.** Six fits testing the avenue named in
`37_2026_open_problems.md` ("automatically crop 'good' regions of the spiral fit, and use these as
surface patch inputs to a subsequent run"): refit on patches the previous fit satisfied at >= 0.90,
against a control matched on total patch area.

| | `satisfied_area` | `total_fg_pixels` |
|---|---:|---:|
| area-matched control (n=3) | 0.8328 | 1,642,359 |
| refit on good patches (n=3) | 0.9799 | 1,628,729 |
| | **+17.66%, p < 1e-4** | **-0.83%, p = 0.89** |

**That +17.66% is circular by construction** — the arm was selected on satisfaction and then scored
on it. That is exactly why it is worth reporting: a loop that crops good regions and checks
satisfaction would read a 17.66% improvement and see a success, with recovered ink flat. Power here
reaches only ~10%, so this bounds rather than excludes a small ink effect.

We are not proposing a fix, and neither case alone settles how often the metrics disagree. But taken
together the guard moved confidently the wrong way once and confidently the useless way once, which
seems worth knowing if its purpose is to catch ink regressions.

<details><summary>method</summary>

`fit_spiral.py` at villa-spiral `6847063f`; `render_ink.py` + `get_ink_metrics.py` extracted at
`5479453a`; ink volume `representations/predictions/ink-3d/`. Welch two-sided. Case 1 tested at
alpha = 0.0294 (Pocock, second look). Case 2 at alpha 0.05, with the geometry-only outcome
registered in advance as a failure rather than a partial success. Per-arm `satisfied_area` quality
gates applied within arms, never pooled across them. All arms passed a registered non-blank strip
control at 47.5-48.6% nonzero, so neither comparison is one arm rendering more strip than another.

</details>
