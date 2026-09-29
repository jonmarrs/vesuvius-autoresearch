# Villa catalogue listing for inkdelta (option B). POSTED 2026-09-29 as ScrollPrize/villa#1928

**POSTED 2026-09-29: https://github.com/ScrollPrize/villa/pull/1928** (branch `jonmarrs:community-projects-inkdelta`,
commit 430020259 on upstream 417199cc5, +2/−0, via the GitHub API; no local villa checkout touched). Checks
re-run that morning: the duplicate search was clean (new #1916 Volumen, unrelated, inserts at line 77); 0 of our
PRs open; all 5 cited URLs returned 200; there were no AI markers in the body or the commit. One body sentence was
tightened before posting ("five matched as registered; the sixth after its direction was corrected"). **Do not
nudge.** The bot auto-closes after 14 days idle, around 10-13; if that happens, record it and let it go.

**Original instructions:** post no earlier than 2026-09-29 (weekly new-item slot). **Prerequisites:**

1. `jonmarrs/inkdelta` is public on GitHub.
2. `reports/inkdelta_validation.md` and the step-2 report are on this repo's `main`, so the README's
   links resolve.
3. A duplicate search of villa PRs and issues for "inkdelta", "total_fg_pixels" and "autoresearch
   metric".

Villa PR SOP: small, evidence in the body, **no AI markers**. #901 (May) was closed without comment.
Recent third-party listings (#1896, #1718) merged as plain one-entry PRs, so this follows that shape.

**Checked 2026-09-28 (read-only):**
- Duplicate search for "inkdelta", "total_fg_pixels", "autoresearch metric" and "community projects" found no
  overlap. The `total_fg_pixels` hits are our own #1842/#1728/#1866 and @ItIsCuthNotCup's #1886.
- The four closed catalogue PRs (#1635, #1677, #1546, #1469) were not rejected. Three were closed by the bot
  after 14 days without activity ("repository PR time limits"), and #1469 has no closing comment. What decides
  merge vs close is whether a maintainer looks within 14 days. **Do not nudge**
  ([[no-reviewer-nudges-quality-over-volume]]); if it auto-closes, record that and let it go.
- The entry takes a runnable command and a licence from #1896's merged format. Author placement follows the
  adjacent spiralcheck entry ("[name](url) by Author."), because consistency within the section beats
  another section's style.
- `pip install git+https://github.com/jonmarrs/inkdelta` was tested in a fresh venv on 2026-09-28, and
  `inkdelta check` on a real run dir worked.
- Re-run the duplicate search on the day, and read the catalogue's Segmentation → Tools section as it stands
  then; it moves.

## The entry (one bullet, `scrollprize.org/docs/20_community_projects.md`, Segmentation → Tools, after spiralcheck)

```markdown
- [inkdelta](https://github.com/jonmarrs/inkdelta) by Jon Marrs. Checks whether a `total_fg_pixels` difference between `spiral-fitting` runs is real before the autoresearch loop keeps it. From the files a run already leaves, it refuses a score that re-used old slices (`all slices exist, skipping`) or rendered an all-zero strip, flags runs scored by different models or sampled by different `vc_render_tifxyz` builds, and reports the difference with an interval: Welch from seed replicates, never narrower than the run-to-run CV you measure with `inkdelta noise` (three seeds can land tight by chance). Measured on PHercParis4: the published image and a post-#1146 source build differ by +5.0% to +9.2% on the same surface, and one run per side cannot resolve an effect that size. `pip install git+https://github.com/jonmarrs/inkdelta`, `inkdelta noise --group out/*_base_s?` to measure your CV, then `inkdelta compare --a out/*_base_s? --b out/*_change_s? --cv <that CV>`. Validated on six pre-registered known-answer cases and reproduces seven previously registered intervals exactly. Standard library only, MIT.
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
> - **Noise.** It reports an interval, not a win, and never one narrower than your measured run-to-run
>   CV allows. In our corpus three control seeds landed at CV 0.0124 against a floor of 0.0536, which
>   made a ±9% null look like a ±3% one
>   (https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/control_sensitivity.md).
>
> Validation: six known-answer cases from our corpus, registered before the tool ran on real data. It
> reproduces a registered interval exactly and correctly calls a real +6.45% build effect unresolved
> from single runs.
> (https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/inkdelta_validation.md)
> A second pass re-derived the six other registered Welch intervals in our corpus. Five matched as
> registered, to 4 d.p. The sixth failed only because our pre-registration had the comparison's
> direction reversed; in the registered direction it matches too. The miss is disclosed
> (https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/inkdelta_registered_intervals.md).
>
> On our own 102 scored runs it found exactly two stale renders: the one behind a claim we had already
> withdrawn, and one deliberate re-score. It found no empty renders
> (https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/corpus_integrity_audit.md).
