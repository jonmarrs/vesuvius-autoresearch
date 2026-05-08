# Vesuvius-C Readiness

This report checks whether the official `ScrollPrize/villa` Vesuvius-C path is ready for prize-facing Autoresearch use.

## Summary

- Prize claim status: `fallback_only`
- Wrapper present: `True`
- Upstream present: `True`
- Native library present: `True`
- Native probe requested: `False`
- Fallback smoke: `pass`
- Sample probe: `pass`
- Sample backend: `zarr`

## Benchmark

- Command: `VESUVIUS_C_BUILD=1 /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/bin/python benchmark_vesuvius_c.py`
- Next action: Run the benchmark with VESUVIUS_C_BUILD=1 and record native speedup before a Progress Prize claim.
