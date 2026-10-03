# DRAFT (not posted): measurements of #1818's `--surface-interpolation smooth` against villa's ink labels

**Status:** draft, 2026-10-03. **Not posted, and not to be posted without the user's explicit approval.**

* **Venue:** a reply on the merged PR #1818 (replies are capped at one a day, no new item needed), or
  nothing.
* **Gates:** the user's approval; a check that nobody has already posted the same; re-run the numbers
  against the committed JSON on the day.
* **Consider first:** pmh47 closed #1866 ("not valuable information for autoresearch agents") about
  noise-source notes. This is a different kind of item: a render option's effect measured against villa's
  own labels, addressed to the option's author. The judgement is the user's.

## Text (as it would be posted)

> Measured `--surface-interpolation smooth` against the ink labels villa publishes on the 2.4 µm frame
> (8 PHercParis4 segments, `ink-labels/.../20260918`), rendering the `v3-78k-fullsup` 3D ink prediction
> through each segment's mesh. Default (`linear`) output is byte-identical to the pre-#1818 build.
>
> Results:
>
> * **Agreement with the labels barely moves.** On the segment meshes as published (~20-voxel grid
>   cells), the rendered prediction's AP against the labels is unchanged by smooth (|ΔAP| ≤ 0.0001). On
>   meshes subsampled 4× to ~80-voxel cells, smooth is slightly more faithful: ΔAP > 0 resolved in 6 of
>   8 segments, about +1–2% relative.
> * **`render_ink` + `get_ink_metrics` moves a lot more on coarse grids.** Through that pipeline the
>   `total_fg_pixels` change is −3.6% to +4.1% per segment on 20-voxel meshes, and −7.9% to +19.4% per
>   segment (−32% to +42% per 2048-px window) on 80-voxel grids. The scorer's own agreement with the
>   labels does not consistently change in either case.
>
> The effect scales with grid cell size. The fitted spiral surfaces we measured are ~80-voxel. If smooth
> is ever used for spiral renders, comparisons across modes will move by more than typical
> keep/discard margins. Method, pre-registrations and data: <link to reports/coarse_grid_interpolation.md>.

## Notes

* Every number is in `reports/scorer_vs_labels_surface_interpolation.md`,
  `reports/surface_interpolation_vs_labels.md` and `reports/coarse_grid_interpolation.md`, and
  test-bound via the October draft.
* No AI markers. Do not nudge.
