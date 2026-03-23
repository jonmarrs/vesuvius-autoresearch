import tensorstore as ts
import numpy as np
import torch
from torch.utils.data import IterableDataset, DataLoader

class VesuviusS3Dataset(IterableDataset):
    def __init__(self, uri, patch_size=32, num_layers=16, anonymous=True):
        self.uri = uri
        self.patch_size = patch_size
        self.num_layers = num_layers
        
        # Parse URI if it's an s3:// link
        if uri.startswith("s3://"):
            parts = uri.replace("s3://", "").split("/")
            bucket = parts[0]
            path = "/".join(parts[1:])
            kvstore = {
                'driver': 's3',
                'bucket': bucket,
                'path': path,
                'aws_region': 'us-east-1',
                'aws_credentials': {'type': 'anonymous'} if anonymous else {}
            }
        else:
            kvstore = {'driver': 'file', 'path': uri}

        # Open the dataset
        self.dataset = ts.open({
            'driver': 'zarr',
            'kvstore': kvstore,
        }).result()
        
        self.shape = self.dataset.shape
        print(f"Initialized VesuviusS3Dataset from {uri}: {self.shape} {self.dataset.dtype}")

    def __iter__(self):
        # Optimized loading: Fetch a larger block and yield multiple patches from it
        block_z = 128 # Matching chunk size
        block_hw = 256
        
        while True:
            # Randomly sample a LARGE block
            z0 = np.random.randint(0, self.shape[0] - block_z)
            y0 = np.random.randint(0, self.shape[1] - block_hw)
            x0 = np.random.randint(0, self.shape[2] - block_hw)
            
            try:
                # Async read using TensorStore
                block = self.dataset[
                    z0:z0+block_z,
                    y0:y0+block_hw,
                    x0:x0+block_hw
                ].read().result()
                
                # Yield multiple patches from this block
                for _ in range(128): # 128 patches per block fetch
                    pz = np.random.randint(0, block_z - self.num_layers)
                    py = np.random.randint(0, block_hw - self.patch_size)
                    px = np.random.randint(0, block_hw - self.patch_size)
                    
                    patch = block[pz:pz+self.num_layers, py:py+self.patch_size, px:px+self.patch_size]
                    tensor = torch.from_numpy(patch.astype(np.float32) / 255.0).unsqueeze(0)
                    yield tensor
                
            except Exception as e:
                print(f"Error loading block: {e}")
                continue

def make_s3_loader(uri, batch_size=4, patch_size=32, num_layers=16):
    dataset = VesuviusS3Dataset(uri, patch_size, num_layers)
    return DataLoader(dataset, batch_size=batch_size)

if __name__ == "__main__":
    # Test the loader
    uri = 's3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/'
    
    loader = make_s3_loader(uri, batch_size=2)
    print("Fetching first batch from middle of volume...")
    ts_dataset = loader.dataset.dataset if hasattr(loader.dataset, 'dataset') else loader.dataset
    z_mid, y_mid, x_mid = [s // 2 for s in ts_dataset.shape]
    
    # Manually fetch a chunk from middle
    chunk = ts_dataset[z_mid:z_mid+16, y_mid:y_mid+32, x_mid:x_mid+32].read().result()
    print(f"Manual middle chunk shape: {chunk.shape}")
    print(f"Manual middle chunk mean: {np.mean(chunk):.4f}")
    print(f"Manual middle chunk max: {np.max(chunk)}")
    
    # Iterate a few times to see if random samples get data
    print("\nRandomly sampling batches:")
    for i, batch in enumerate(loader):
        print(f"Batch {i}: mean={batch.mean():.4f}, max={batch.max():.4f}")
        if i >= 5: break
