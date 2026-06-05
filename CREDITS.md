# Credits & Attribution

This project builds on the official Vesuvius Challenge `ScrollPrize/villa`
repository (MIT License), authored by the Villa maintainers and contributors
(including Youssef Nader, Luke Farritor, and Julian Schilliger).

All Villa components listed below are used by **importing** them from the `villa/`
git submodule at runtime; no Villa source is copied or vendored into this
repository, so there is no separately-licensed code redistributed here. Use of
Villa code remains under its upstream MIT License.

## Villa components used (imported, not copied)

- **Evaluation metrics** — `centerline_dice` and `skeleton_distance_length`,
  from `villa/segmentation/evaluation/metrics`. Used as the topological scoring
  signals in the search loop's evaluation step (logged as `avg_centerline_dice`
  and `avg_skel_dist` in `results.tsv`).
- **Structure-tensor computation** — `StructureTensorComputer`, from
  `vesuvius.image_proc.geometry.structure_tensor`. Used to build auxiliary
  multi-task targets.
- **Primus / LeJEPA backbone** — `PrimusNetwork` from
  `vesuvius.models.build.primus_wrapper`, imported for the optional LeJEPA-based
  architecture.

## Original work (offered toward Villa, not borrowed from it)

- `scroll_augmentations.py` — original GPU-native scroll augmentations written for
  Villa issue #201 (scroll-specific 3D augmentations). Pure-function transforms with
  no project-internal dependencies, structured for porting into Villa's
  `batchgeneratorsv2`. This is a contribution, not a borrowing.

## Data

Vesuvius Challenge scroll data and labels are used under the Scroll Prize / Vesuvius
data terms. Any cleaned or regenerated label artifacts are local and are **not**
redistributed by this repository.

## This project

`Vesuvius AutoResearch` (codename `bountyhunter`), MIT License, © 2026 Jon Marrs.
Public since 2026-03-23 at `github.com/jonmarrs/vesuvius-autoresearch`.
