import os

import numpy as np
import zarr


def build_division_mock(in_dir, out_dir, shape=(1024, 1024, 1024)):
    if os.path.exists(os.path.join(out_dir, "0", ".zarray")):
        print(f"Skipping {out_dir}, already built.")
        return

    os.makedirs(out_dir, exist_ok=True)
    print(f"Building mock zarr at {out_dir}")
    z = zarr.open(
        os.path.join(out_dir, "0"),
        mode="w",
        shape=shape,
        chunks=(128, 128, 128),
        dtype="uint8",
    )

    real_data = []
    for root, dirs, files in os.walk(in_dir):
        for file in files:
            if not file.startswith("."):
                path = os.path.join(root, file)
                with open(path, "rb") as f:
                    try:
                        data = np.frombuffer(f.read(), dtype=np.uint8).reshape(
                            128, 128, 128
                        )
                        real_data.append(data)
                    except Exception as exc:
                        print(f"Warning: skipped invalid chunk {path}: {exc}")

    if len(real_data) == 0:
        print(f"No real chunks found to tile for {in_dir}. Creating empty placeholder.")
        real_data = [np.zeros((128, 128, 128), dtype=np.uint8)]

    print(f"Found {len(real_data)} valid real chunks for {out_dir}. Tiling...")

    idx = 0
    for z_i in range(0, shape[0], 128):
        for y_i in range(0, shape[1], 128):
            for x_i in range(0, shape[2], 128):
                z[z_i : z_i + 128, y_i : y_i + 128, x_i : x_i + 128] = real_data[
                    idx % len(real_data)
                ]
                idx += 1

    print(f"Done {out_dir}.")


# Process all downloaded divisions
base_dir = "local_data"
for item in os.listdir(base_dir):
    if item.endswith("_Divisions"):
        scroll_id = item.split("_")[0]
        scroll_dir = os.path.join(base_dir, item)
        for div_name in os.listdir(scroll_dir):
            in_path = os.path.join(scroll_dir, div_name, "0")
            out_path = os.path.join(base_dir, f"{scroll_id}_{div_name}_1GB")
            build_division_mock(in_path, out_path)
