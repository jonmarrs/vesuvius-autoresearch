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

Crop contract 1 records source shape/dtype, requested/actual origin, output shape,
and a unique generation. Tensor completion records that generation and the
effective sigma. Rebuilding a crop invalidates older tensor output. Resume checks
reject legacy marker-only output and mismatched geometry, sigma, generation, or
missing eigenanalysis components. They do not hash the full original CT volume
or scan every payload on each resume. If a source volume changes in place, rerun
with `--force`.

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
This path uses CT prediction; it does not consume a newly fitted surface. Source
and checkpoint content freshness are not cryptographically attested; use `--force`
after replacing inputs at the same paths.

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
