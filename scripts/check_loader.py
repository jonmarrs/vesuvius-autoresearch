import os
import sys

# Add villa to path
VILLA_SRC = os.path.abspath("villa/vesuvius/src")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)

from vesuvius.data.volume import Volume

vol_path = "local_data/PHercParis2Fr47/surface_volume.zarr"
print(f"Checking path: {os.path.abspath(vol_path)}")

vol = Volume(
    type="zarr",
    path=os.path.abspath(vol_path),
    normalization_scheme="instance_zscore",
    return_as_tensor=True,
    verbose=True,
)
print("Volume loaded successfully!")
