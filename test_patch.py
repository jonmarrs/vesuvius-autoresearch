import os
import sys

import numpy as np

_VILLA_VESUVIUS_SRC = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "villa",
        "vesuvius",
        "src",
    )
)
if _VILLA_VESUVIUS_SRC not in sys.path:
    sys.path.insert(0, _VILLA_VESUVIUS_SRC)

from vesuvius.models.datasets.find_valid_patches import find_valid_patches

# Fake 2D label array
labels = np.zeros((1000, 1000), dtype=np.uint8)
labels[100:200, 100:200] = 1

results = find_valid_patches(
    label_arrays=[labels],
    label_names=["test"],
    patch_size=(64, 64),
    bbox_threshold=0.5,
    label_threshold=0.01,
    valid_patch_find_resolution=0,  # Full resolution since it's a numpy array
)

print(results)
