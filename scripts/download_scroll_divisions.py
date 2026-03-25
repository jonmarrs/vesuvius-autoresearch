import os
import boto3
import json
import zarr
import math
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
bucket = 'vesuvius-challenge-open-data'

# We will focus on:
# - PHerc0332 (Scroll 3)
# - PHerc0172 (Scroll 5)
# - PHerc0139 (Scroll 1)
# (Note: PHerc1667 volumes are missing from the public bucket, but we will still check for it just in case)
target_scrolls = ['PHerc0332', 'PHerc0172', 'PHerc0139', 'PHerc1667']

def get_volume_prefix(scroll_id):
    volumes_prefix = f"{scroll_id}/volumes/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=volumes_prefix, Delimiter='/')
    for obj in resp.get('CommonPrefixes', []):
        vol_prefix = obj['Prefix']
        if vol_prefix.endswith('masked.zarr/'):
            return f"{vol_prefix}0/"
            
    # Try samples directory
    volumes_prefix = f"samples/{scroll_id}/volumes/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=volumes_prefix, Delimiter='/')
    for obj in resp.get('CommonPrefixes', []):
        vol_prefix = obj['Prefix']
        if vol_prefix.endswith('masked.zarr/'):
            return f"{vol_prefix}0/"
    return None

def download_divisions(scroll_id):
    print(f"\n--- Processing {scroll_id} ---")
    prefix = get_volume_prefix(scroll_id)
    if not prefix:
        print(f"Skipping {scroll_id}: No masked.zarr volume found in public bucket.")
        return
        
    print(f"Found volume prefix: {prefix}")
    
    # 1. Download and parse the .zarray metadata to get the shape and chunks
    try:
        zarray_obj = s3.get_object(Bucket=bucket, Key=f"{prefix}.zarray")
        zarray_data = json.loads(zarray_obj['Body'].read().decode('utf-8'))
        shape = zarray_data['shape']
        chunks = zarray_data['chunks']
        print(f"Volume Shape (Z,Y,X): {shape}")
        print(f"Chunk Size (Z,Y,X): {chunks}")
    except Exception as e:
        print(f"Failed to read .zarray for {scroll_id}: {e}")
        return
        
    # We want 11 divisions: 0%, 10%, ..., 100%
    # We will slice along the Z-axis (depth) to get different cross-sections of the scroll.
    # The max Z index is shape[0]
    z_max = shape[0]
    z_chunk = chunks[0]
    
    # Target 1GB per division.
    # Assuming each chunk is roughly 2MB (128x128x128 uint8), we need ~512 chunks.
    # We will form a block of chunks. e.g., an 8x8x8 grid of chunks = 512 chunks = ~1GB.
    target_chunks = 512
    grid_size = math.ceil(target_chunks**(1/3)) # ~8
    
    divisions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    
    for div in divisions:
        div_name = f"div_{int(div*100)}"
        print(f"\n  Downloading Division {div_name} ({div*100}% along Z-axis)...")
        
        # Calculate the starting Z chunk index
        # 1.0 division should be shifted back so the block fits within bounds
        start_z_idx = int((z_max - (grid_size * z_chunk)) * div) // z_chunk
        start_z_idx = max(0, min(start_z_idx, (z_max // z_chunk) - grid_size))
        
        # Pick a middle point for Y and X so we are likely to hit actual scroll data (not empty space)
        mid_y_idx = (shape[1] // chunks[1]) // 2
        mid_x_idx = (shape[2] // chunks[2]) // 2
        
        # Shift back by half the grid size to center the block
        start_y_idx = max(0, mid_y_idx - (grid_size // 2))
        start_x_idx = max(0, mid_x_idx - (grid_size // 2))
        
        out_dir = f"local_data/{scroll_id}_Divisions/{div_name}/0/"
        os.makedirs(out_dir, exist_ok=True)
        
        # Save metadata
        for meta in ['.zarray', '.zgroup', '.zattrs']:
            key = f"{prefix}{meta}"
            out_path = os.path.join(out_dir, meta)
            try:
                s3.download_file(bucket, key, out_path)
            except:
                pass
                
        downloaded = 0
        for z in range(start_z_idx, start_z_idx + grid_size):
            for y in range(start_y_idx, start_y_idx + grid_size):
                for x in range(start_x_idx, start_x_idx + grid_size):
                    chunk_key = f"{prefix}{z}/{y}/{x}"
                    out_path = os.path.join(out_dir, f"{z}/{y}/{x}")
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    
                    try:
                        s3.download_file(bucket, chunk_key, out_path)
                        downloaded += 1
                    except Exception as e:
                        # Chunk might not exist (empty space padding)
                        pass
        
        print(f"  Downloaded {downloaded} chunks for {div_name}.")

for scroll in target_scrolls:
    download_divisions(scroll)
    
print("\nAll division downloads finished.")
