
import torch
from vesuvius_loader import VesuviusLabeledDataset
import numpy as np
import zarr

def probe_coords():
    uri = 'local_data/PHercParis2Fr47/surface_volume.zarr'
    labels = 'local_data/PHercParis2Fr47/inklabels.png'
    mask = 'local_data/PHercParis2Fr47/mask.png'
    
    ds = VesuviusLabeledDataset(uri, labels, mask, patch_size=64, num_layers=16)
    
    print(f"First valid coord: {ds.valid_coords[0]}")
    y0, x0 = ds.valid_coords[0]
    
    # Directly check Zarr at this coord
    path = 'local_data/PHercParis2Fr47/surface_volume.zarr/0'
    z_vol = zarr.open(path, mode='r')
    patch = z_vol[:, y0:y0+64, x0:x0+64]
    print(f"Direct Zarr patch at first valid coord: max={patch.max()}, mean={patch.mean():.4f}")
    
    # Check mask at this coord
    mask_patch = ds.mask[y0:y0+64, x0:x0+64]
    print(f"Mask patch at first valid coord: max={mask_patch.max()}, mean={mask_patch.mean():.4f}")

    # Check ink at this coord
    ink_patch = ds.labels[y0:y0+64, x0:x0+64]
    print(f"Ink patch at first valid coord: max={ink_patch.max()}, mean={ink_patch.mean():.4f}")

if __name__ == "__main__":
    probe_coords()
