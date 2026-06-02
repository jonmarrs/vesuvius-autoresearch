import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import tifffile

try:
    import cupy as cp
except ImportError:
    pass

sys.path.insert(0, os.path.abspath("villa/foundation/datasets/fibers-dataset"))
import tools

# Create a synthetic "scroll-like" volume or load a small chunk if available
# We'll just generate an image from a small synthetic chunk with some tubular structures
z, y, x = np.mgrid[-32:32, -32:32, -32:32]
# A tubular structure (line)
tube = np.exp(-(x**2 + y**2) / 10.0)
# A blob structure
blob = np.exp(-(x**2 + y**2 + z**2) / 10.0)
# Some background noise
noise = np.random.rand(64, 64, 64) * 0.1
volume = (tube + blob + noise).astype(np.float32)

volume_cp = cp.array(volume)
res_cp = tools.detect_vesselness(volume_cp)
res_np = cp.asnumpy(res_cp)

fig, axes = plt.subplots(1, 2, figsize=(10, 5))
axes[0].imshow(volume[32, :, :], cmap="gray")
axes[0].set_title("Original Slice")
axes[0].axis("off")

axes[1].imshow(res_np[32, :, :], cmap="inferno")
axes[1].set_title("Frangi Vesselness Output")
axes[1].axis("off")

os.makedirs("reports/figures", exist_ok=True)
plt.savefig("reports/figures/sprint033_fiber_vesselness_demo.png", bbox_inches="tight")
print("Image generated at reports/figures/sprint033_fiber_vesselness_demo.png")
