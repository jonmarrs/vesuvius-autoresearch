import os
import sys

VILLA_SRC = os.path.abspath("villa/vesuvius/src")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)

from vesuvius.data.volume import Volume

uri = "local_data/PHercParis2Fr47/surface_volume/"
print(f"Testing Volume with uri: '{uri}'")
try:
    vol = Volume(
        type="zarr",
        path=uri,
        normalization_scheme="instance_zscore",
        return_as_tensor=True,
        verbose=True,
    )
    print("Success!")
    print(f"Shape: {vol.shape()}")
except Exception as e:
    print(f"Failed: {e}")
    import traceback

    traceback.print_exc()
