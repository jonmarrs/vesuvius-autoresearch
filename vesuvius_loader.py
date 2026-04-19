import tensorstore as ts
import numpy as np
import torch
from torch.utils.data import IterableDataset, DataLoader
from PIL import Image
import os
import time

Image.MAX_IMAGE_PIXELS = None

class FastVesuviusVolume:
    """
    Highly optimized volume reader. 
    Loads TIF stack into a single memmapped .npy file for instantaneous access.
    """
    def __init__(self, volume_uri, cache_dir=None):
        self.uri = volume_uri
        
        # Determine cache location
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            # Use hash of uri to create a unique cache name if using a shared cache_dir
            import hashlib
            uri_hash = hashlib.md5(volume_uri.encode()).hexdigest()[:8]
            self.npy_path = os.path.join(cache_dir, f"volume_cache_{uri_hash}.npy")
        else:
            self.npy_path = os.path.join(volume_uri, "volume_cache.npy")
            
        self.data = None
        self.dataset = None
        
        if os.path.isdir(volume_uri) and any(f.endswith('.tif') for f in os.listdir(volume_uri)):
            if not os.path.exists(self.npy_path):
                print(f"Building fast volume cache for {volume_uri} ...")
                files = sorted([os.path.join(volume_uri, f) for f in os.listdir(volume_uri) if f.endswith('.tif')])
                
                with Image.open(files[0]) as img:
                    h, w = img.size[::-1]
                
                # Pre-allocate on disk using a temporary file for atomicity
                tmp_npy_path = self.npy_path + ".tmp"
                tmp_data = np.memmap(tmp_npy_path, dtype='uint8', mode='w+', shape=(len(files), h, w))
                for i, f in enumerate(files):
                    with Image.open(f) as img:
                        tmp_data[i] = np.array(img)
                tmp_data.flush()
                del tmp_data # Close memmap
                
                os.rename(tmp_npy_path, self.npy_path)
                print(f"Fast cache built: {self.npy_path}")
                
            # Get shape
            files = [f for f in os.listdir(volume_uri) if f.endswith('.tif')]
            with Image.open(os.path.join(volume_uri, files[0])) as img:
                h, w = img.size[::-1]
            
            self.shape = (len(files), h, w)
            self.is_zarr = False
        else:
            # For shape only. Do not save dataset to self to maintain fork safety.
            ds = ts.open({
                'driver': 'zarr',
                'kvstore': {'driver': 'file', 'path': volume_uri},
            }).result()
            self.shape = ds.shape
            self.is_zarr = True

    def _lazy_init(self):
        if self.is_zarr:
            if self.dataset is None:
                self.dataset = ts.open({
                    'driver': 'zarr',
                    'kvstore': {'driver': 'file', 'path': self.uri},
                }).result()
        else:
            if self.data is None:
                self.data = np.memmap(self.npy_path, dtype='uint8', mode='r', shape=self.shape)

    def __getitem__(self, key):
        self._lazy_init()
        if self.is_zarr:
            return self.dataset[key].read().result()
        return self.data[key]

class VesuviusLabeledDataset(IterableDataset):
    def __init__(self, volume_uri, labels_path, mask_path=None, patch_size=64, num_layers=16, seed=None, cache_dir=None):
        self.volume = FastVesuviusVolume(volume_uri, cache_dir=cache_dir)
        self.patch_size = patch_size
        self.num_layers = num_layers
        self.shape = self.volume.shape
        self.seed = seed
        
        # Load Labels (2D PNG)
        with Image.open(labels_path) as img:
            self.labels = np.array(img).astype(np.float32) / 255.0
            
        if mask_path and os.path.exists(mask_path):
            with Image.open(mask_path) as img:
                self.mask = np.array(img).astype(np.float32) / 255.0
        else:
            self.mask = np.ones_like(self.labels)
            
        # Pre-calculate valid coordinates
        stride = 16
        mask_mtime = int(os.path.getmtime(mask_path)) if mask_path and os.path.exists(mask_path) else 0
        
        if cache_dir:
            import hashlib
            uri_hash = hashlib.md5(volume_uri.encode()).hexdigest()[:8]
            cache_path = os.path.join(cache_dir, f"valid_coords_cache_{uri_hash}_{self.patch_size}_{stride}_{mask_mtime}.npy")
        else:
            cache_path = os.path.join(volume_uri, f"valid_coords_cache_{self.patch_size}_{stride}_{mask_mtime}.npy")

        if os.path.exists(cache_path):
            self.valid_coords = np.load(cache_path).tolist()
            # If the mask happens to be empty or list empty, valid_coords could be empty. But we trust the cache.
        else:
            print(f"Finding valid coordinates in mask (mean={self.mask.mean():.4f})...")
            self.valid_coords = []
            H, W = self.mask.shape
            for y in range(0, H - self.patch_size, stride):
                for x in range(0, W - self.patch_size, stride):
                    if self.mask[y:y+self.patch_size, x:x+self.patch_size].mean() > 0.05:
                        self.valid_coords.append((y, x))
            
            if not self.valid_coords:
                for y in range(0, H - self.patch_size, stride * 4):
                    for x in range(0, W - self.patch_size, stride * 4):
                        if self.mask[y:y+self.patch_size, x:x+self.patch_size].any():
                            self.valid_coords.append((y, x))
            np.save(cache_path, np.array(self.valid_coords, dtype=np.int32))
        
        print(f"Initialized Labeled Dataset: Volume {self.shape}, Valid Patches {len(self.valid_coords)}")

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        seed_base = self.seed if self.seed is not None else 0
        worker_id = worker_info.id if worker_info is not None else 0
        
        # Robust seeding strategy
        seed = (seed_base + worker_id + (os.getpid() % 1000)) % 4294967295
        ss = np.random.SeedSequence(seed)
        np.random.seed(ss.generate_state(1)[0])

        while True:
            if not self.valid_coords:
                yield torch.zeros(1, self.num_layers, self.patch_size, self.patch_size), torch.zeros(self.patch_size, self.patch_size)
                continue

            idx = np.random.randint(0, len(self.valid_coords))
            y0, x0 = self.valid_coords[idx]
            
            # Small jitter
            y0 = max(0, min(self.shape[1] - self.patch_size, y0 + np.random.randint(-8, 9)))
            x0 = max(0, min(self.shape[2] - self.patch_size, x0 + np.random.randint(-8, 9)))
            z0 = np.random.randint(0, self.shape[0] - self.num_layers)
            
            try:
                patch_vol = self.volume[z0:z0+self.num_layers, y0:y0+self.patch_size, x0:x0+self.patch_size]
                patch_vol = torch.tensor(np.array(patch_vol, copy=False), dtype=torch.float32).div_(255.0).unsqueeze(0)
                patch_label = torch.tensor(np.array(self.labels[y0:y0+self.patch_size, x0:x0+self.patch_size], copy=False), dtype=torch.float32)
                
                yield patch_vol, patch_label
                
            except Exception:
                continue

class VesuviusS3Dataset(IterableDataset):
    """Fallback for Zarr/S3 data."""
    def __init__(self, uri, patch_size=32, num_layers=16, seed=None, cache_dir=None):
        self.uri = uri
        self.patch_size = patch_size
        self.num_layers = num_layers
        self.seed = seed
        self.cache_dir = cache_dir
        self.dataset = None
        if uri.startswith("s3://"):
            raise ValueError("S3 Streaming disabled. Use local paths.")
            
        ds = ts.open({
            'driver': 'zarr',
            'kvstore': {'driver': 'file', 'path': uri},
        }).result()
        self.shape = ds.shape

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        seed_base = self.seed if self.seed is not None else 0
        worker_id = worker_info.id if worker_info is not None else 0
        
        # Robust seeding strategy
        seed = (seed_base + worker_id + (os.getpid() % 1000)) % 4294967295
        ss = np.random.SeedSequence(seed)
        np.random.seed(ss.generate_state(1)[0])
            
        if self.dataset is None:
            self.dataset = ts.open({
                'driver': 'zarr',
                'kvstore': {'driver': 'file', 'path': self.uri},
            }).result()

        block_z, block_hw = 128, 256
        while True:
            z0 = np.random.randint(0, self.shape[0] - block_z)
            y0 = np.random.randint(0, self.shape[1] - block_hw)
            x0 = np.random.randint(0, self.shape[2] - block_hw)
            
            try:
                block = self.dataset[z0:z0+block_z, y0:y0+block_hw, x0:x0+block_hw].read().result()
                for _ in range(64):
                    pz = np.random.randint(0, block_z - self.num_layers)
                    py = np.random.randint(0, block_hw - self.patch_size)
                    px = np.random.randint(0, block_hw - self.patch_size)
                    
                    patch = block[pz:pz+self.num_layers, py:py+self.patch_size, px:px+self.patch_size]
                    tensor = torch.tensor(np.array(patch, copy=False), dtype=torch.float32).div_(255.0).unsqueeze(0)
                    yield tensor, torch.empty(0)
            except Exception:
                continue
