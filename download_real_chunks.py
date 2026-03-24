import os
import boto3
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
bucket = 'vesuvius-challenge-open-data'

def download_chunks(prefix, out_dir, max_chunks=8):
    os.makedirs(out_dir, exist_ok=True)
    
    # Download metadata files
    for meta in ['.zarray', '.zgroup', '.zattrs']:
        key = f"{prefix}{meta}"
        out_path = os.path.join(out_dir, meta)
        try:
            s3.download_file(bucket, key, out_path)
            print(f"Downloaded {key}")
        except Exception as e:
            pass # Some metadata files might not exist at the prefix level
            
    # Download chunks
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_chunks + 10)
    count = 0
    for obj in resp.get('Contents', []):
        key = obj['Key']
        if key.endswith('.zarray') or key.endswith('.zattrs') or key.endswith('.zgroup'):
            continue
            
        rel_path = key[len(prefix):]
        out_path = os.path.join(out_dir, rel_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        print(f"Downloading {key} -> {out_path} ({obj['Size']/1024/1024:.2f} MB)")
        s3.download_file(bucket, key, out_path)
        
        count += 1
        if count >= max_chunks:
            break

print("Downloading PHerc0139 subset...")
download_chunks('PHerc0139/volumes/20260102150214-2.399um-0.2m-78keV-masked.zarr/0/', 'local_data/RealScroll_1/0/')

print("\nDownloading PHerc0172 subset...")
download_chunks('PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/', 'local_data/RealScroll_5/0/')

print("\nDone!")
