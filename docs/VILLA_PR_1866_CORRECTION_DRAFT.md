# Draft correction comment for villa PR #1866 — NOT POSTED

**Status: draft only.** Posting is an outward action and needs the owner's approval. Under the
standing rules it is a reply in an existing thread (allowed up to one per day), it must carry no
AI-authorship markers, and it should go out only if the PR is still open.

**Why it is worth posting:** the PR body says the two flattened surfaces "sit 7.15 vx apart" and
that a deterministic flatten "lands 6.6–7.3 vx from both stock surfaces". A maintainer reading that
would take it as geometric instability of the output surface, which it is not. The substance of the
PR — where the non-determinism lives, the 3.04%, and how to switch it off — is unaffected.

---

**Proposed comment text:**

> A correction to one number in the description, found while checking it.
>
> The "7.15 vx apart" (and "6.6–7.3 vx" for the deterministic run) is a nearest-neighbour distance
> between the two flattened tifxyz point sets. The flat grid is spaced ~20 vx, so two samplings of
> the *same* sheet with a random in-plane offset read ~7.7–8 vx apart that way. Splitting each
> nearest-neighbour vector along the reference surface's own grid normal:
>
> | pair | NN p50 | along the normal, p50 | in-plane p50 |
> |---|---:|---:|---:|
> | a surface shifted 4 vx radially (control) | 4.00 | 3.58 | 1.75 |
> | two stock flattens, same meshes, w120–w129 | 7.39 | **0.25** | 7.07 |
> | two stock flattens, same meshes, w010–w019 | 0.25 | **0.01** | 0.25 |
>
> So the flatten lands on the same surface and **re-parametrises** it, rather than moving it. The
> 3.04% change in `total_fg_pixels` is real; it comes from how the sheet is laid out in the strip,
> not from where the surface sits. The deterministic switch is unaffected: it makes the layout
> reproducible.

---

Source: `reports/the_flatten_moves_the_grid_not_the_surface.md`,
`scripts/measure_flatten_normal_offset.py`, `reports/flatten_normal_offset/*.json`.
