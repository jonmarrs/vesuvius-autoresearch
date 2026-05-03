
import torch
from vesuvius_loader import VesuviusLabeledDataset
import numpy as np

def scan_val_dataset():
    uri = 'local_data/PHercParis2Fr143/surface_volume.zarr'
    labels = 'local_data/PHercParis2Fr143/inklabels.png'
    mask = 'local_data/PHercParis2Fr143/mask.png'
    
    ds = VesuviusLabeledDataset(uri, labels, mask, patch_size=64, num_layers=16)
    
    ink_counts = 0
    data_counts = 0
    
    for i in range(min(1000, len(ds))):
        x, target = ds[i]
        if target.sum() > 0:
            ink_counts += 1
        if x.mean() > 0.01:
            data_counts += 1
            
    print(f"In 1000 val samples (Fr 143):")
    print(f"  Samples with ink: {ink_counts}")
    print(f"  Samples with CT data: {data_counts}")

if __name__ == "__main__":
    scan_val_dataset()
