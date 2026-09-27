# Draft: villa catalogue listing for inkdelta (option B). NOT POSTED

**Post no earlier than 2026-09-29** (weekly new-item slot). **Prerequisites:**

1. `jonmarrs/inkdelta` is public on GitHub.
2. `reports/inkdelta_validation.md` and the step-2 report are on this repo's `main`, so the README's
   links resolve.
3. A duplicate search of villa PRs and issues for "inkdelta", "total_fg_pixels" and "autoresearch
   metric".

Villa PR SOP: small, evidence in the body, **no AI markers**. #901 (May) was closed without comment.
Recent third-party listings (#1896, #1718) merged as plain one-entry PRs, so this follows that shape.

## The entry (one bullet, `scrollprize.org/docs/20_community_projects.md`, Segmentation → Tools, after spiralcheck)

```markdown
- [inkdelta](https://github.com/jonmarrs/inkdelta) by Jon Marrs. Checks whether a `total_fg_pixels` difference between `spiral-fitting` runs is real before the autoresearch loop keeps it. From the files a run already leaves, it refuses a score that re-used old slices (`all slices exist, skipping`) or rendered an all-zero strip, flags runs scored by different models or sampled by different `vc_render_tifxyz` builds, and reports the difference with an interval (Welch from seed replicates, or a supplied CV). Measured on PHercParis4: the published image and a post-#1146 source build differ by +5.0% to +9.2% on the same surface, and one run per side cannot resolve an effect that size. Standard library only; validated on six pre-registered known-answer cases.
```

## PR title

`community projects: add inkdelta (is a total_fg_pixels difference real?)`

## PR body

> Adds one entry under Segmentation → Tools for [inkdelta](https://github.com/jonmarrs/inkdelta), a
> small CPU-only checker for the spiral-fitting autoresearch loop's objective.
>
> It checks three things, each from a measurement, not an assumption:
>
> - **Stale renders.** When per-slice TIFFs already exist, the published `vc_render_tifxyz` skips
>   sampling and exits 0, so a copied run dir re-scores an old render.
> - **Install route.** Since #1146, source builds step one level-g voxel along the normal, and the
>   05-13 image steps one level-0 voxel. On four surfaces that moves `total_fg_pixels` +5.0% to +9.2%
>   (reported on #1588).
> - **Noise.** It reports an interval, not a win.
>
> Validation: six known-answer cases from our corpus, registered before the tool ran on real data. It
> reproduces a registered interval exactly and correctly calls a real +6.45% build effect unresolved
> from single runs.
> (https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/inkdelta_validation.md)
