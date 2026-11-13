# Archived v3 prototype

The v3 command-line launchers are retired. This implementation belongs to the
archived April–May sprint work and has drifted from the maintained training
contracts. It has no current maintained caller. The original implementation and
YAML settings remain here for reference; they are not a supported training API.

Both `run_v3.py` and `trainer.py` explain the replacement command with `--help`.
Other CLI invocations return status 2 before importing ML packages, reading a
configuration, creating loaders or modifying training state.

Use the maintained trainer from the repository root:

```sh
uv run python scripts/training/train.py --config config.json
```

Read the [training setup](../README.md#quick-start) first. The old v3 YAML files
are not `ExperimentConfig` JSON and are not automatically converted. The v3
dataset tuples, augmentation import, teacher/loss loops and checkpoint behavior
need a dedicated port and actual training validation before this prototype
could become supported again. Retiring its CLI does not validate or reproduce
its historical LeJEPA or UA-MT methods.
