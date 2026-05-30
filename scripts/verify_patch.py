from vesuvius_loader import FastVesuviusVolume

vol = FastVesuviusVolume("local_data/PHercParis2Fr47/surface_volume.zarr")
patch = vol[0:16, 0:64, 0:64]
print(f"Patch shape: {patch.shape}")
