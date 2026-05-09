import os
import zarr
import numpy as np

# We have 36 scrolls with 1GB of downloaded chunk data in local_data/{scroll}_Large.
# Let's tile them all into offline 1GB continuous Zarr datasets.

def build_large_mock(in_dir, out_dir, shape=(1024, 1024, 1024)):
    if os.path.exists(os.path.join(out_dir, '0', '.zarray')):
        print(f"Skipping {out_dir}, already built.")
        return
        
    os.makedirs(out_dir, exist_ok=True)
    print(f'Building large mock zarr at {out_dir}')
    z = zarr.open(os.path.join(out_dir, '0'), mode='w', shape=shape, chunks=(128, 128, 128), dtype='uint8')
    
    real_data = []
    for root, dirs, files in os.walk(in_dir):
        for file in files:
            if not file.startswith('.'):
                path = os.path.join(root, file)
                with open(path, 'rb') as f:
                    try:
                        data = np.frombuffer(f.read(), dtype=np.uint8).reshape(128, 128, 128)
                        real_data.append(data)
                    except Exception as exc:
                        print(f"Warning: skipped invalid chunk {path}: {exc}")

    if len(real_data) == 0:
        print(f'No real chunks found to tile for {in_dir}.')
        return
        
    print(f'Found {len(real_data)} valid real chunks for {out_dir}. Tiling...')
    
    idx = 0
    for z_i in range(0, shape[0], 128):
        for y_i in range(0, shape[1], 128):
            for x_i in range(0, shape[2], 128):
                z[z_i:z_i+128, y_i:y_i+128, x_i:x_i+128] = real_data[idx % len(real_data)]
                idx += 1
                
    print(f'Done {out_dir}.')

# Scan local_data for downloaded Large chunks
for item in os.listdir('local_data'):
    if item.endswith('_Large'):
        scroll_id = item.replace('_Large', '')
        in_path = f"local_data/{item}/0/"
        out_path = f"local_data/{scroll_id}_1GB"
        
        # Don't rebuild if already built
        if not os.path.exists(os.path.join(out_path, '0', '.zarray')):
            build_large_mock(in_path, out_path)
