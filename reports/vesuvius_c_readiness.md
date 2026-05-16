# Vesuvius-C Readiness

This report checks whether the official `ScrollPrize/villa` Vesuvius-C path is ready for prize-facing Autoresearch use.

## Summary

- Prize claim status: `blocked`
- Wrapper present: `True`
- Upstream present: `False`
- Native library present: `True`
- Native probe requested: `False`
- Fallback smoke: `not_run`
- Loader slice smoke: `not_run`
- Sample probe: `not_run`
- Sample backend: `n/a`

## Benchmark

- Command: `VESUVIUS_C_BUILD=1 /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python benchmark_vesuvius_c.py`
- Next action: Restore wrapper and upstream Villa checkout.
