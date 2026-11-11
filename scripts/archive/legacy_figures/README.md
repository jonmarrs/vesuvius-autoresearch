# Retained figure-generator source

These two files are byte-identical copies from main `90a1f029`. They used old
Villa/CuPy imports, fixed data paths and fixed report destinations. The synthetic
generator ran during import and referenced CuPy even when importing it failed.
No maintained command calls either generator.

The root entrypoints now refuse execution before scientific imports or writes.
The files here are historical source for inspection; do not run them to
regenerate or overwrite retained evidence. Existing figures and reports were
not changed. Use the maintained [fiber workflow](../../../docs/FIBER_DETECTION.md)
for new explicitly sourced artifacts. A vesselness visualization alone does not
establish ink, text or prize eligibility.
