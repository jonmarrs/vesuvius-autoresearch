# Credits & Attribution

This project builds on the official Vesuvius Challenge `ScrollPrize/villa`
repository (MIT License). Original authors of the upstream components are credited
to the Villa maintainers and contributors, including **Youssef Nader, Luke
Farritor, and Julian Schilliger**.

<!--
CONFIRM BEFORE FILING (internal note, delete before submitting):
For each entry below, verify whether the villa code is (a) imported at runtime via
the `villa/` submodule, or (b) copied/adapted into this repo. For any copied/adapted
file, ensure the upstream MIT header is preserved in that file. Adjust "Usage" lines
to match reality — do not claim "imported" if code was actually vendored.
-->

## Upstream components

### Evaluation metrics — topological scoring
- **Used:** `centerline_dice`, `skeleton_distance_length`.
- **Source:** `ScrollPrize/villa` — `segmentation/evaluation/metrics`.
- **License:** MIT.
- **Usage:** model evaluation in the autoresearch loop. _[Confirm: imported via submodule vs adapted.]_

### Volume access — OME-Zarr
- **Used:** the `Volume` class for OME-Zarr loading.
- **Source:** `ScrollPrize/villa` — `vesuvius/src/vesuvius/data`.
- **License:** MIT.
- **Usage:** dataset/volume loading. Imported via the `villa/` submodule.

### Structure tensor — auxiliary supervision
- **Used:** 3D structure-tensor computation (`StructureTensorComputer`).
- **Source:** `ScrollPrize/villa` — `vesuvius/src/vesuvius/image_proc/geometry/structure_tensor.py`.
- **License:** MIT.
- **Usage:** multi-task structure-tensor targets. Imported via the `villa/` submodule.

### Augmentation recipe
- **Used:** the Scroll-2 augmentation recipe as a starting point.
- **Source:** `ScrollPrize/villa` — `ink-detection/train_timesformer_og.py`.
- **License:** MIT.
- **Usage:** adapted/extended in `scroll_augmentations.py` (tuned for local noise
  profiles). This is a derivative; preserve the upstream notice in any vendored code.

## Data

Vesuvius Challenge scroll data and labels are used under the Scroll Prize / Vesuvius
data terms. Any cleaned or regenerated label artifacts are local and are **not**
redistributed by this repository; use them only under the applicable upstream terms
and Villa license notices.

## This project

`Vesuvius AutoResearch` (codename `bountyhunter`), MIT License, © 2026 Jon Marrs.
Public since 2026-03-23 at `github.com/jonmarrs/vesuvius-autoresearch`.
