# Candidate CT preprocessing and structure tensor measurement

`scripts/execute_lasagna_pipeline.py` prepares local ranked candidates as bounded
CT crops and structure tensor groups. The default run performs those two stages.
Its `PASS` means that the requested preprocessing completed; the execution report
states this scope explicitly.

```sh
.venv/bin/python scripts/execute_lasagna_pipeline.py \
  --ranked reports/scroll23_ranked_candidates.tsv --limit 3 \
  --output-root reports/lasagna_fiber_candidates \
  --report reports/lasagna_pipeline_execution.json --gpus 0
```

The worklist preserves both the processing priority (`rank`) and the original TSV
row (`candidate_index`). Evidence commands use the original index and the actual
ranked file. Candidate geometry must contain nonnegative integer x/y/z coordinates,
positive integer dimensions, and a safe artifact name. Invalid eligible candidates
fail before execution. Relative input and mask paths resolve from the caller's
working directory; generated helper commands use absolute script paths.

## Crop and tensor publication

Crop origins that overrun a positive source boundary are clamped to fit, preserving
the existing crop behavior. Saved `source_start_zyx` is the actual origin and
`source_requested_zyx` is the requested origin. Downstream geometry must use the
actual origin. The source and destination cannot alias or contain one another.

Crops copy at most 64³ requested voxels per Python read. Their source dtype,
compression, filters, order, and fill value are retained. This does not cap the
memory used to decode an underlying source chunk. A staged directory is published
after all writes and provenance succeed. Failed reads/writes retain the prior
output. Existing-directory replacement uses two renames and attempts rollback
on publication errors; serialize writers and readers during replacement. A killed
process may leave a hidden staging directory or a recoverable `previous` backup.

Crop contract 2 records source shape/dtype, requested/actual origin, output shape,
a unique generation and a content fingerprint. Resume compares both the saved
crop and the selected source region with that fingerprint. Tensor completion
contract 2 binds its source crop, sigma and all eleven output arrays to their
decoded content. Changed, deleted or corrupt payloads therefore require
recomputation even when their metadata stays the same. Rebuilding a crop still
invalidates older tensors through its generation record.

Resume scans the selected crop region and stored tensor outputs in fixed 64³
spatial blocks; it reads additional CPU data compared with the former metadata
check. It hashes no whole-scroll volume. Changes outside the crop leave its
fingerprint valid. Zarr's valid fill-value behavior still applies to chunks
absent at initial creation; these checks establish content identity from that
point onward. Contract-1 artifacts lack the new fingerprints and need one
recomputation before automatic reuse. Previous outputs are retained if a
replacement fails.

The tensor wrapper runs villa's `run_create_st.py` with the active interpreter,
resolved repository paths, and the upstream source path in `PYTHONPATH`. It
validates the six-channel floating tensor, all first/second/normal vector axes,
and confidence output, including readable payloads, before publishing completion.
The legacy `--rho` option now fails explicitly: the pinned runner has no rho
setting, and the old wrapper silently ignored it. `--sigma` and `--gpus` are
supported and validated.

```sh
.venv/bin/python scripts/compute_structure_tensors.py \
  --input path/to/candidate_crop.zarr --output path/to/tensors.zarr \
  --sigma 2 --gpus 0
```

## Surface fitting and optional CT evidence

Surface fitting needs an explicit upstream configuration and its own input
manifest. Follow [villa's Lasagna guide](../villa/lasagna/README.md) for that work.
The former automation called `lasagna_analyze.py`, which visualizes an already
fitted model, with unsupported fitting arguments. It also called batch refinement
with the wrong argument order and without parameters. Those calls have been
removed. This command does not claim to fit, refine, or evaluate a surface.

`--with-evidence` additionally runs the separate CT prediction/evidence chain
after preprocessing. Each selected TSV row must supply `train_mask_path` and
`predict_mask_path` in the same coordinate frame. Both files must exist at
preflight; the evidence validator checks their content and alignment afterward.
The chosen checkpoint must match the existing evidence before reuse.
New single-model predictions record the SHA-256 of the exact bytes loaded;
replacing a checkpoint at the same path invalidates reuse. Legacy prediction
metadata without that digest needs fresh inference. A rebuilt crop also
refreshes requested CT evidence.

```sh
.venv/bin/python scripts/execute_lasagna_pipeline.py \
  --ranked path/to/candidates_with_masks.tsv --limit 1 \
  --with-evidence --checkpoint best_model.pt
```

A previous `PASS` report alone is insufficient. Resume revalidates the separate
`evidence_metadata.json` and its current image, masks, and export declarations.
A crop or tensor failure blocks dependent stages for that candidate. Other
candidates can finish, but any failed candidate makes the overall exit status 1.
A new attempt invalidates the old execution report before processing begins.

See [Submission evidence](SUBMISSION_EVIDENCE.md) for the evidence contract.
This path uses CT prediction; it does not consume a newly fitted surface. The
evidence checks cover local artifact mechanics and the checkpoint identity.
Complete prediction inputs, any context beyond the candidate crop and training
exposure require a separate audit. Use `--force` when intentionally refreshing
those inputs. Capturing checkpoint bytes also needs one checkpoint-sized CPU
buffer while loading; this is separate from GPU memory.

## Verify existing outputs before scheduling work

```sh
.venv/bin/python scripts/execute_lasagna_pipeline.py \
  --ranked reports/scroll23_ranked_candidates.tsv --limit 3 \
  --output-root reports/lasagna_fiber_candidates --verify-only \
  --report reports/lasagna_pipeline_verification.json
```

This reads existing artifact content and writes the verification report. It
launches no crop, tensor or inference commands and preserves artifact bytes and
modification times. The report uses `mode: verify_only` and stage states
`VERIFIED`, `STALE_OR_MISSING` or a dependency-blocked state. Exit 0 means all
requested checks passed; exit 1 identifies stale, missing or failed checks.
Rerun without `--verify-only` to rebuild required stages. `--force` and
`--verify-only` cannot be combined. Add `--with-evidence` only when the selected
rows supply the masks required for the separate CT evidence check.

Report paths are checked before publication, protecting ranked inputs,
checkpoints, supplied source/mask paths, artifact directories and the research
lock from direct or resolved overlap. The path check is a snapshot; serialize
concurrent writers as with directory publication.

## Measuring stored tensors

`scripts/evaluate_deformation_metric.py` now measures its input rather than
generating simulated eigenvalues. It accepts a six-channel floating array, the
official `structure_tensor` group member, or a six-channel array at `0`.
Packed channels follow upstream order: zz, zy, zx, yy, yx, xx.

```sh
.venv/bin/python scripts/evaluate_deformation_metric.py \
  --st-zarr path/to/tensors.zarr --subsample 2 \
  --output reports/tensor_anisotropy.json
```

Reads are bounded in sampled voxel space, with subsampling anchored at zero
across blocks. Nonfinite and materially non-positive-semidefinite tensors fail.
Negative eigenvalues within 1e-6 of the per-voxel normalized tensor scale are
clipped as roundoff and counted. Fractional anisotropy is scale invariant;
zero tensors contribute zero and their count is disclosed, alongside the mean
over nonzero tensors.

FA measures local anisotropy. It is invariant to rotation and does not measure
neighborhood orientation agreement or prove that registration flattened a
scroll. The earlier “Coherence Score” and its unsupported registration
interpretation have been removed.
