# RETRACTED: "the published spiral dataset cannot run the fit's default mode"

**Retracted 2026-08-28, the same day it was written, before it was reported anywhere.** The claim
was false. The original text is summarised below rather than preserved, since nothing in it survived.

## What was claimed, and why it was wrong

The claim: `dense_spacing_mode` defaults to `"phase"`, phase mode requires the surf-SDT source
OME-Zarr, that store is not published, therefore the published dataset cannot run the default
configuration.

Two independent errors, either of which alone breaks it.

**1. The default is not `"phase"`.** I read this line

```python
mode = str(config.get("dense_spacing_mode", "phase"))     # fit_session.py:259
```

and took `"phase"` for the default. It is the fallback for an *absent* key. The key is never absent:
`Config().as_dict()["dense_spacing_mode"]` is **`"winding_model"`**. I read a default out of a
`.get()` fallback instead of instantiating the config and looking.

**2. Even under phase mode, the SDT is off by default.** `_phase_bundle_enabled` is a conjunction:

```python
return (_dense_spacing_mode(config) == "phase"
        and input_source_enabled(config, "normals")
        and input_source_enabled(config, "surf_sdt"))
```

and `input_use_surf_sdt` is `False` in the default config. I quoted the first clause of a
three-clause `and` and stopped reading.

Evaluated rather than read:

```
dense_spacing_mode      : winding_model
input_use_surf_sdt      : False
_phase_bundle_enabled() : False        <- so use_sdt is False
_winding_model_enabled(): True
```

`use_sdt` passed to `ensure_fit_sparse_stores` is `_phase_bundle_enabled(config)`, so **the
`os.path.exists(sdt_zarr_path)` check never runs on the default config.** The absent source zarr
blocks nothing.

## What is actually true

* The surf-SDT source OME-Zarr genuinely is not published (that part was checked correctly: a bare
  `las_008_surf_sdt.ome.zarr`, its `.zattrs` and its `zarr.json` all 404). It is simply **not
  required**, because the SDT input is disabled by default.
* The **32.58 GiB SDT sidecar we downloaded is not needed for the default configuration.** It was
  69% of the payload. Harmless, and required if anyone enables phase mode, but it was not necessary
  for this.
* The asymmetry between the stores is real and still worth knowing: normals and grad_mag read
  geometry from the sidecar's `meta.json`, while surf_sdt opens the raw zarr. It is just not a
  blocker.
* The real gap for the default mode is a **naming mismatch, not a missing file.** The default mode
  is `winding_model`, which requires the `winding_inference` input at conventional relative
  `winding_inference`. The dataset publishes that content as `winding_model/` (seven shards plus
  `manifest.json`). `path_overrides` in `spiral-scroll.json` exists for exactly this.

## The lesson, which is the reason this file still exists

Both errors are the same move: **reading a default off a fallback expression, and reading one clause
of a conjunction.** In both cases the correct action was to instantiate the object and print the
value, which took one command and immediately contradicted the write-up.

This is the sixth instance today of a check that could not see what it was being used for, and the
first where I was the check. The others were tools; this was reasoning. It reached a committed
report because it was plausible, internally consistent, and never executed.

The rule that would have caught it: **a claim about runtime behaviour gets evaluated at runtime
before it gets written down**, not read out of source. The commit that introduced it did note "no
fit has been run" and deferred reporting upstream for that reason, which is the only thing that kept
it off villa.
