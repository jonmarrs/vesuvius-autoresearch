# Find a command and its runtime requirements

Browse reviewed primary command families before provisioning the research stack:

```sh
python scripts/list_commands.py
python scripts/list_commands.py --stack stdlib
python scripts/list_commands.py --command regional-predict
python scripts/list_commands.py --command fragment-fetch --json
```

Discovery uses only Python 3.10's standard library. It reads the bounded
[inventory](../configs/command_inventory.json), without importing command targets,
starting subprocesses, installing packages, loading model/data files or probing
CUDA. It works from another working directory when invoked by its absolute path.
The JSON reports `readiness: "not_checked"` and the identity of the exact captured
inventory bytes it parsed. Unknown command IDs, empty filter matches and invalid
inventories exit 2. The CLI does not generate caches or modify the inventory.

The inventory covers 27 reviewed entrypoints/modes, not every script or study.
Individual research reproductions retain their registration-specific instructions.
Historical sources, archived launchers and measured artifacts remain preserved.
Run displayed script prefixes from the checkout root with the appropriate
interpreter; see the guide for required arguments before executing them.

## Interpret the fields

| Field | Meaning |
| --- | --- |
| `argv` | A command prefix; supply required arguments using its guide. The catalog never executes it. |
| `stack` | A declared dependency boundary for the listed mode, as described below. |
| `layout` | `checkout` requires repository files; `wheel-or-checkout` identifies a packaged module CLI. |
| `villa` | `required`, `conditional` on recipe/mode, or `none` for the listed operation. |
| `needs` | Important data, optional package, device and platform conditions. |
| `effects` | `observe`, artifact publication, research `state`, or `interactive` annotation. Check the guide for each mode's actual writes. |
| `guide` | The authoritative usage/contract document. |

| Stack | Boundary |
| --- | --- |
| `stdlib` | No third-party Python package for the listed mode; platform conditions still apply. |
| `scientific` | Array/image/data packages without a required Torch model stack. Optional CuPy, SDK and cloud paths are described per command. |
| `torch` | Model/research stack; CPU, CUDA and native requirements depend on the recipe. |
| `gui` | Interactive GUI dependencies in addition to the data stack. |

These classifications are not minimal installation recipes, installable extras,
dependency availability checks or GPU capacity guarantees. For example:

- Production prediction imports Torch and the regional stack even for
  `--dry-run`. Planning does not imply that its imports are stdlib-only.
- The repeatability probe's default planning mode uses only stdlib; execution
  requires the training stack and a checkout lock. Its shared protocol metadata
  no longer imports NumPy. The full promotion module still uses arrays.
- The fiber filter supports `--device cpu` without CUDA probing. GPU mode needs
  CuPy and working CUDA; neither follows from the catalog entry alone.
- The scroll-frames parsing API is stdlib-only, while its live `list` CLI needs
  `s3fs` and network access. The inventory describes that CLI mode.
- Proofreader verification requires the pinned source and NumPy/Zarr. Optional
  TIFF export checks also use tifffile. GUI launch needs Napari and its GUI dependencies.
- Loop control uses Linux process facilities. A stdlib classification does not
  mean a process-control command is portable to every operating system.

Use the [package/checkout guide](PACKAGING.md) for wheel boundaries and the
[workspace diagnostic](WORKSPACE_STATUS.md) for setup observations. Neither the
catalog nor an installed wheel establishes complete experiment readiness.

## Before splitting dependency extras

The default environment still installs the existing full dependency set. The
inventory does not change `pyproject.toml`, `uv.lock`, platform support or a live
environment. A narrower environment needs a tested dependency closure for its
operations, including imports that occur before argument parsing and optional
recipe paths. A proposed split should also account for:

- The existing Python 3.10/Torch CUDA index and TensorStore constraints.
- Platform-specific WEBKNOSSOS selection and its transitive typing constraints.
- Villa-backed discovery, backbones, augmentation and GUI code supplied outside
  the wheel.
- Notebook and historical reproduction dependencies that may not belong in a
  core runtime but remain necessary for particular retained workflows.

Those installation/platform decisions remain in the
[owner-review list](REPOSITORY_AUDIT.md#items-for-owner-review). No package is
removed or upgraded based only on this metadata inventory.

## Maintain the inventory

Update the JSON when adding, moving or changing a supported entrypoint. Its
bounded schema validates command IDs, prefixes, source paths, classifications
and guide references. The regression suite checks that declared sources and
guides exist and that listing works with site packages disabled, without
imports, subprocess execution or filesystem writes. The new module is part of
both curated validation and the portable CPU profile. These checks validate
discovery and metadata consistency; they do not execute every listed workflow.
