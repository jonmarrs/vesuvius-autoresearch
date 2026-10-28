# Verify finished fiber tiles through current Villa's object-store export

**Prepared October 27 Pacific / October 28 UTC; native integration not run here.**
Villa `39a8cf3a` replaces the fiber tracer's AFV export with `vc_object_store`.
The seed-heading proposal's recorded two-cube GPU re-run remains at
`322cb0899`. This replay check prepares one part of the required current-main
verification without repeating inference or borrowing the active training GPU.

Use an already configured Villa environment, a **separate clean checkout**,
and a closed real-data tracer run containing `run.json` and finished
`tiles/*.npz`. The configured Python must import Villa and the actual native
`vc_object_store` bindings. Their package currently requires Python 3.14 and
native build dependencies; this script installs nothing. The cached cloud
environment lacks those bindings. A plan or passing verifier tests does not
establish that the native integration works.

First independently check the scan's volume ID and the run's `grid_scale`.
Set the four paths/identities below for that host. The output directory must
be new and outside both the Villa checkout and the original run. Ensure enough
space for a copy of the finished tile archives and one exported store.

```sh
AGENTS_AGENT_MODE=1 python /path/to/vesuvius-autoresearch/repro/fibers/verify_villa_object_store_export.py \
  --villa /path/to/separate-clean-villa \
  --run /path/to/closed-real-data-tracer-run \
  --out /path/to/new-export-check \
  --volume EXPECTED_NATIVE_VOLUME_ID
```

This prints a **PLANNED** record and creates no output directory. Review it,
then repeat the same command with `--execute` in the configured environment.
Execution copies the input records, calls Villa's real `tracing.volume_store`
CLI twice, and checks each export by reading it through Villa's native reader.
Each invocation has a 30-minute timeout. Export time includes the native writer;
this is a correctness check, not a performance comparison. Do not use it on a
live run, and do not pull into the research checkout while its registered
unchanged-control window is open.

For an old run with no recorded CT path, supply `--ct` with its actual public
CT store. It is passed to the export command, without editing the original
record. The verifier refuses the exporter's checkpoint fallback, avoiding a
checkpoint lookup or download just to recover that path. A run that recorded
its CT keeps it: `--ct` cannot replace it, since the exporter writes the traced
CT's coordinates unchanged and naming another store would bind them to that
volume. Villa's exporter finds the volume only from a Vesuvius open-data store,
or from a fiber store of the same scan (`--template`, not passed here). A run
traced on a local crop therefore has no truthful export through this check:
on October 28 every closed run on the tracing host (`ct/`, `ct_9p6/` resampled
to 9.6 µm, and the context crops) was one. If its run predates
`fiber_namespace`, the check derives a deterministic
namespace from the input hashes and adds it **only to the export copy**. That
copy is an export fixture: never use it to resume tracing or treat its added
namespace as an identity recorded by the historical tracer. A run with an
existing namespace keeps it.

An **EXACT** report requires every exported fiber's native xyz coordinates,
UUID, name, family, point count, volume binding, seed, plane, stop reasons and
link UUIDs to match the finished tiles on both exports. The comparison uses
exact arrays, not a coordinate tolerance. It checks geometry in batches of at
most 256 fibers, decodes each tile member once per pass, rejects extra or
missing fibers, ignores incomplete `.partial.npz` tiles, and refuses an empty
verification. The original record and tile hashes, source commit and Python
source hashes must remain unchanged; the export copy and verifier are checked
for changes too. Logs and a FAILED report remain after an export or comparison
failure. A missing native dependency fails before creating the output directory.

Keep `report.json`, both `export-*.log` files and the copied input/export files
with the original real-data provenance. The report retains source and input
identities and counts. It deliberately does not serialize the process
environment. A new source revision or data change needs a new output directory.

The local verifier tests use small fixtures and injected reader/CLI failures.
They cover wrong axis order, scale, family, volume, links, missing/extra fibers,
unsafe output paths, record hash/parse consistency and input/snapshot drift.
The independent decoder also matches the actual pinned `39a8cf3a` tile iterator,
loaded without native dependencies. **These are tests of this verification
tool, not real-data evidence for an upstream PR.**

Even a successful real-data export replay will verify only export and readback.
Before posting the seed-heading proposal, run the current volume-tracing CLI
on the retained two Scroll-5 inputs and compare its before/after paths with
the recorded traces. Preserve the existing AFV launcher and measurements.
The upstream PR cap and required owner-written motivation still apply.
Neither this preparation nor a future replay adds a merged Villa contribution
to the October filing. File the completed engineering and optional research
submissions independently of this integration work.
