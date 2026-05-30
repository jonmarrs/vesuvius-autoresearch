import numpy as np
from scipy.ndimage import gaussian_filter


def hessian_curvature_3d(volume, gauss_sigma=2, sigma=6):
    volume_smoothed = gaussian_filter(volume, sigma=gauss_sigma)
    print(f"volume_smoothed.shape: {volume_smoothed.shape}")
    Dz = np.gradient(volume_smoothed, axis=0, edge_order=2)
    joint_hessian = np.zeros(
        (volume.shape[0], volume.shape[1], volume.shape[2], 3, 3), dtype=float
    )
    joint_hessian[:, :, :, 2, 2] = np.gradient(Dz, axis=0, edge_order=2)
    return joint_hessian


# Reproduce the loader logic
D = 33
step_z = 32
for z in range(0, D, step_z):
    z_start = z
    z_end = min(z + step_z + 4, D)
    if z_end - z_start < 3:
        z_start = max(0, z_end - 3)
    print(f"z={z}, z_start={z_start}, z_end={z_end}")
    vol_slice = np.random.rand(z_end - z_start, 64, 64)
    hessian_curvature_3d(vol_slice)
