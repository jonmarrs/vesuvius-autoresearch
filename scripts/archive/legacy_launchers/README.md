# Retained unimplemented launcher source

These two files are byte-identical snapshots from main `73c741a2`:

- `run_cross_scan_registration.py` opened inputs and reported a saved transform,
  but never called its imported alignment function or wrote the transform.
- `run_autoresearch_nnunet_bridge.py` only wrote a fixed temporary YAML. Its
  mutation dropped the other template parameters and could overwrite the input
  when that input had the same path. No trainers or training were launched.

The root scripts now retain their argument names and refuse execution before
scientific imports, input reads or output writes. No maintained workflow called
either launcher. These snapshots are historical source for inspection; do not
execute them. They are not measured registration/training evidence.

See [migration and scope](../../../docs/UNSUPPORTED_LAUNCHERS.md). The upstream
tools remain separate workflows and are not executed by the compatibility stubs.

Pre-commit hooks and default Ruff directory discovery exclude these Python
snapshots. The [preservation-policy checks](../../../tests/test_preserved_source_policy.py)
also require that active code and these explanatory notes retain checks.
