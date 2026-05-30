import zarr


def check_zarr():
    path = "local_data/PHercParis2Fr47/surface_volume.zarr/0"
    z_vol = zarr.open(path, mode="r")
    print(f"Shape: {z_vol.shape}")

    # Check a chunk from the middle
    mid_y, mid_x = z_vol.shape[1] // 2, z_vol.shape[2] // 2
    patch = z_vol[:, mid_y : mid_y + 64, mid_x : mid_x + 64]
    print(
        f"Middle patch max: {patch.max()}, min: {patch.min()}, mean: {patch.mean():.4f}"
    )


if __name__ == "__main__":
    check_zarr()
