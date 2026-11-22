# Retired registration and nnUNet launchers

Two unimplemented prototypes retain their old argument names as compatibility
entrypoints. Execution exits **2** with an explanation. `--help` exits **0**
without loading scientific dependencies. Neither command reads inputs, creates
directories, changes configurations, launches a child or reports a result.

Their [original source](../scripts/archive/legacy_launchers/README.md) is retained
byte for byte from main `73c741a2`. No maintained workflow called them. Existing
scientific scripts, registrations, transforms and reports were not changed.

## Cross-scan registration

[The former launcher](../scripts/run_cross_scan_registration.py) accepted
`--fixed`, `--moving`, `--out` and `--auto`. It imported `align_zarrs` but never
called it. With importable dependencies it opened the volumes and printed
“Transform saved” without computing or writing any transform. It also created
the output parent before checking dependencies. Installing more packages could
therefore turn a clear dependency failure into a false success.

The pinned Villa [registration README](../villa/foundation/volume-registration/README.md)
describes the separate, interactive
[find_transform.py](../villa/foundation/volume-registration/find_transform.py)
workflow. It uses manual alignment and landmark correspondences, with explicit
voxel sizes and axis conventions. Its optional SimpleITK refinement is described
upstream as imprecise on low-resolution levels. This is not a validated automatic
alignment replacement. Inspect the residuals and resulting transform before
using it to transfer labels or compare scans.

## nnUNet bridge

[The former bridge](../scripts/run_autoresearch_nnunet_bridge.py) accepted
`--config`, `--evolve-attr`, `--evolve-val` and `--variant-name`. It only wrote a
fixed temporary YAML; trainer generation and training existed as comments.
Changing one parameter replaced the whole configurations list and discarded the
other template parameters. Supplying its fixed output as input overwrote that
input. Its default configuration file was absent from the checkout.

Villa's [model-optimization framework](../villa/segmentation/model_optimization_framework/README.md)
is a separate workflow with configuration, trainer-generation, training and
evaluation steps. The retirement does not remove it or the project's training
dependencies. Review the chosen dataset, split, parameter inheritance, output
paths and GPU requirements before using it; its example configuration requests
four GPUs and contains placeholder evaluation paths. No integration with the
maintained Autoresearch loop or validated nnUNet evolution is supplied here.

The current supported training path remains
[scripts/training/train.py](../scripts/training/train.py). A replacement bridge
would need an explicit source-bound configuration contract and end-to-end
training/evaluation validation rather than another implicit temporary file.
