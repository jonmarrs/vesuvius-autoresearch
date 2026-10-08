# Mutex segmentation data handoff

This local research workflow pairs reviewed sheet-instance labels with an
explicit raw CT window and prepares attractive/repulsive affinity targets.
Label correctness, CT alignment, and prize eligibility require independent
evidence. Preparation success establishes a data artifact contract.

**Current runtime limitation (2026-10-08):** the pinned villa package cannot import
in this environment because `nrrd` is absent. Its Mutex dataset also incorrectly
windows channel-leading affinities and passes them to a 3D-only crop helper.
The launcher probes the actual dataset on CPU and refuses training on failure.
No working end-to-end Mutex training run is claimed. See the
[review](DESIGN_ARCHITECTURE_REVIEW_2026-10-08_MUTEX_DATA.md) for evidence.

## Prepare an explicit aligned fragment

```bash
.venv/bin/python scripts/training/prepare_mutex_training.py \
  --curated-zarr /data/reviewed_labels.zarr \
  --raw-zarr /data/ct.zarr --raw-start 200 300 400 \
  --aligned-labels --name reviewed_fragment \
  --output-dir local_data/mutex_fragments/reviewed_fragment
```

Both sources must be nonempty 3D Zarr arrays in `(z, y, x)` order, either bare
arrays or a group with an explicit array `0`. No channel or group child is
selected implicitly. Labels must contain nonnegative integer or boolean IDs;
raw CT must contain finite real intensities. Original ID and CT dtypes/values
are preserved, including IDs too large to represent exactly in float32.

`--raw-start Z Y X` selects the label-shaped window from the raw CT. Every bound
must fit the raw array. If omitted, both shapes must match and the origin is
zero. `--aligned-labels` declares that corresponding label and CT voxels are
already aligned. This tool does not register volumes, interpret arbitrary OME
transforms, or prove alignment from matching dimensions or filenames. Source
attributes are recorded for review rather than used as a registration recipe.

The default `--label-mode instances` compares the original nonzero IDs. Touching
instances retain their boundaries; disconnected pieces with one ID remain one
instance. For an intentional binary foreground mask, select
`--label-mode foreground-components`. That mode accepts at most one nonzero
source ID and uses the pinned upstream 6-connected component labeling recipe;
the graph stores both component IDs and the original mask.

Source zeros are excluded from supervision: an edge is valid only when both
endpoints have nonzero labels and are inside the fragment. Rejected curation
chunks and unevaluated regions cannot become verified negative examples.
Each target must have at least one valid edge. The pinned graph recipe provides
6 attractive and 60 repulsive offsets; `--long-range-stride` defaults to 2 and
affects only the designated long-range repulsive offsets. Exact offset order
is recorded on the graph. No graph computation is copied from villa.

The label fragment is limited to `128**3` voxels by default, before reading its
payload. Raw CT can be larger; only the selected window is requested. Affinity
generation materializes the fragment and channel arrays, so peak memory can be
substantial even at this bound. `--max-voxels` permits an explicit different
positive bound; it does not make generation streaming. Make a bounded crop
with known coordinates before preparing full-scroll sparse label outputs.

## Artifact and publication contract

```text
prepared_fragment/
  images/reviewed_fragment.zarr                 # raw 3D array
  affinity_graph/reviewed_fragment.zarr/        # matching loader stem
    labels                                    # original or component IDs
    source_labels                             # binary-component mode only
    affinities/attractive                     # uint8 (6, z, y, x)
    affinities/repulsive                      # uint8 (60, z, y, x)
    mask/attractive                           # uint8, same shape as target
    mask/repulsive                            # uint8, same shape as target
  mutex_data_completion.json
```

Completion contract 1 records source paths and attributes, raw origin and
source shape, selected shape/dtypes, label semantics, graph settings, channel
counts, and valid-edge coverage. Validation checks actual paired payloads,
finite CT values, integer labels, pinned offset sets, binary graph values/masks,
and counted coverage. It does not attest accuracy or detect every possible
in-place semantic alteration of an artifact.

Outputs must be new, disjoint from both sources, and free of resolved aliases or
ancestor/child overlap. Preparation stages the whole artifact next to its
destination and publishes only after validation succeeds. Ordinary errors leave
no final output and exit nonzero. Existing results are preserved. The legacy
`export_zarr_to_tiff()` helper follows the same new-output policy and writes
grayscale ZYX without converting IDs. TIFF is not required for preparation.

Serialize writers and keep sources stable throughout execution. A killed process
may leave a hidden staging directory. This is a local publication protocol, not
a concurrent or cryptographically attested data service.

## Plan or execute training

```bash
# Dry run: inspect the artifact and emit a config/status; no training starts.
.venv/bin/python scripts/training/launch_mutex.py \
  --data-path local_data/mutex_fragments/reviewed_fragment --patch 64

# Explicit execution first probes one real pinned dataset patch on CPU.
.venv/bin/python scripts/training/launch_mutex.py \
  --data-path local_data/mutex_fragments/reviewed_fragment --patch 64 --execute
```

Patch size and epoch count must be positive integers; the patch must fit every
fragment dimension for execution. Defaults remain patch 64 and 20 epochs.
The generated JSON is valid YAML for villa's config manager. It declares both
affinity heads with their actual channel counts and uses the loader's `invert`
setting for the attractive complement. Learning rate, weight decay, batch size,
split, smoothing, and the pinned trainer's numerical implementations are retained.

Every default launch gets a separate ignored `local_data/mutex_launch/<run>/`
directory containing `config.json` and `run.json`. Explicit `--config-out` and
`--marker-out` locations are supported and replaced atomically; they must be
separate from data and each other. Dry runs no longer rewrite a committed recipe
or the historical `reports/mutex_affinity_run.json` snapshot.

Status records distinguish artifact validation, execution requested, CPU runtime
verification, actual process start, and final exit. A refused or failed probe
has `executed: false`. Once training starts, the marker records `running` and its
PID, then `completed` or `training_failed`. `submittable` is null; the separate
`window_px_within_limit` flag only reports whether the requested patch is at most
64 voxels. The CPU probe checks loader tensors, not model accuracy, accelerator
availability, full training compatibility, or submission requirements.

The action-matrix generator reads the latest local Mutex run and preserves its
state. With custom status locations, use:

```bash
.venv/bin/python scripts/build_villa_prize_action_matrix.py \
  --mutex-marker /data/current_mutex_run.json
```

The root `train_mutex.py` shim forwards to the maintained launcher and accepts
the legacy `--data_path` spelling. Both CLIs resolve upstream paths relative to
the checkout and can be invoked by absolute path from another working directory.

## Migration

Regenerate older prepared outputs: guessed CT pairing, float32 instance IDs,
foreground relabeling, mismatched image/graph stems, and unmasked zeros cannot
be repaired reliably from an old marker. Supply both sources, verified
alignment, and a new destination. Legacy `--curated_zarr`/`--output_dir`
spellings remain accepted; the explicit raw source is newly required.

Use the maintained launcher for preflight rather than invoking the checked-in
config directly. Historical patch-size-only readiness claims and marker snapshots
are not current runtime evidence. No package installation, upstream source
change, GPU experiment, real-scroll accuracy assessment, or performance
improvement was part of this repair.
