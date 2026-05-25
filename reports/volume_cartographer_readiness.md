# Volume Cartographer Readiness

This report checks whether Autoresearch is aligned with Villa's maintained `volume-cartographer` path instead of deprecated `vesuvius-c`.

## Summary

- Prize claim status: `volume_cartographer_aligned`
- Wrapper present: `True`
- Official component present: `True`
- Volume API header present: `True`
- VC3D launcher present: `True`
- Local volume smoke: `pass`
- Loader slice smoke: `pass`
- Sample probe: `pass`
- Sample backend: `volume-cartographer-zarr`

## Next Action

- Keep VC3D overlay validation in the prize handoff gate; add native C++ bridge only if Python training needs it.
