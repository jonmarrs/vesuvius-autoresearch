# Research-test inputs and strict runs

The portable CPU profile is the bounded developer check described in
[CONTRIBUTING.md](../CONTRIBUTING.md#development). Historical and scientific
integration tests have different prerequisites. A skip is missing coverage,
not a passing scientific claim.

Selected probe checks now declare `research_input("spiral_patches")` or
`research_input("spiral_rays")`. Historical source checks declare
`villa_history(*commit_ids)`. Prerequisites are checked when a selected test
runs, not when its module imports. Unmarked synthetic and report/source guards
in the same modules continue to execute without these inputs.

Missing declared inputs skip by default, with their paths or commit IDs in the
reason. Require them for an intentional integration run:

```sh
uv run python -m pytest tests/test_probe_real_patch_scatter.py \
  tests/test_check_render_equivalence.py tests/test_villa_preserved.py \
  --require-research-inputs -q -rs
```

To select only the declared checks across the test tree:

```sh
uv run python -m pytest tests -m 'research_input or villa_history' \
  --require-research-inputs -q -rs
```

The strict flag fails selected tests whose declared prerequisites are absent.
It does not require inputs for deselected tests, turn other legacy skip policies
into errors, or provision dependencies and data. Missing original inputs, damaged
payloads and failed scientific assertions must be resolved separately. Presence
checks do not decode, hash or establish the provenance of the study corpus.
Existing assertion thresholds and numerical test bodies are unchanged.

## Original study corpus

Restore the original study inputs into these checkout-relative paths:

| Marker input | Required files and original scope |
| --- | --- |
| `spiral_patches` | `local_data/spiral_patches_phercparis4/umbilicus.json` and the original patch directories containing matching `x.tif`, `y.tif`, `z.tif` coordinate grids. The existing presence assertion still requires at least five patches; other checks retain their original extent/sampling rules. |
| `spiral_rays` | `local_data/spiral_winding_model_phercparis4/shard_0/{ray_origin_zyx,ray_step_zyx,crossing_t,crossing_level,crossing_offsets}.npy`, from the original measured crossing shard. |

The fixture checks the umbilicus file or all five shard files. Geometry readers
and the test assertions still decide whether the supplied contents are usable.
Empty files, fabricated grids, or another scroll's data are not replacements for
the original study corpus. Use retained authorized copies and preserve their
source records. This repository has no verified download manifest or public
replacement for those originals; no scientific rerun is claimed when they are
unavailable.

## Villa history

An initialized checkout of the current pinned Villa commit is insufficient for
historical comparisons. The render checks require these historical commits:

```text
be09a8503 38c2b4278 bfef6abe0 3b398f7cc d82e13edf
d9d70bef1 d8c5f488a 1f544fa71 0e01fe1c7
```

The preserved-source checks additionally require `ced62390e` and its original
`ink-detection/` blobs. That is a historical source pin, not the current
submodule pin. Its later move to `deprecated/ink-detection/` does not authorize
comparing different source versions or rewriting the preserved copies.

Provision history explicitly on an idle developer checkout:

```sh
git submodule update --init villa
git -C villa rev-parse --is-shallow-repository
# If the previous command prints true:
git -C villa fetch --unshallow origin
# Otherwise, fetch the available remote history normally:
git -C villa fetch origin
```

These fetches do not change the checked-out Villa commit. If the historical
objects are absent from the remote history you fetched, restore them from the
original retained repository; do not substitute another ref. A blob-filtered
clone may also need its source blobs hydrated explicitly before running tests.
For example, `git -C villa show ced62390e:ink-detection/train_timesformer_og.py`
should succeed before attempting the preserved-source comparison.

The fixture verifies that `villa/` is its own repository rather than accepting
the parent's refs, and requires the resolved commit hash to match each declared
prefix. A hexadecimal branch name cannot substitute for a different commit.
Its Git probes prohibit
transport and have ten-second timeouts. Git probes and temporary-repository
operations ignore inherited repository/index selectors from hooks while
retaining authentication and guard settings. Marked tests inherit
`GIT_NO_LAZY_FETCH=1` (verified with Git 2.52) so assertions do not implicitly
download missing promisor objects. Use a Git version supporting that variable
or a complete, non-filtered checkout for offline history checks. Missing blobs
after commit preflight fail the actual assertions; the preserved-source loop
no longer turns such a failure into a late skip.

The recovery script's ref-acceptance test uses a temporary local repository.
Its precheck invocations force an unattainable capacity threshold so they never
advance into rendering, including on a large research host.

## Coverage limits

The declarations cover the missing corpus/history cases identified in the
repository audit and the existing patch-corpus guards in fifteen probe modules.
They are not a claim that every research test is portable, that all legacy
skip conditions were migrated, or that the underlying studies were revalidated.
The [audit](REPOSITORY_AUDIT.md) retains the independent data-onboarding and
scientific-rerun decisions. Always report selected modules, skips and missing
inputs alongside passing results.
