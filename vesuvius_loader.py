import tensorstore as ts
import numpy as np
import torch
from torch.utils.data import IterableDataset, DataLoader
from PIL import Image
import os
import time
import json
import sys

# Add villa to path for ridge detection
VILLA_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "villa/vesuvius/src"))
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)

try:
    from vesuvius.image_proc.features.ridges_vessels import detect_ridges_3d
except ImportError:
    detect_ridges_3d = None

Image.MAX_IMAGE_PIXELS = None

class FastVesuviusVolume:
    """
    Highly optimized volume reader. 
    Loads TIF stack into a single memmapped .npy file for instantaneous access.
    Now supports optional 3D ridge detection (Frangi filters) for enhanced structural awareness.
    """
    def __init__(self, volume_uri, cache_dir=None, use_ridges=False, ridge_sigma=2.0):
        self.uri = volume_uri
        self.use_ridges = use_ridges
        self.ridge_sigma = ridge_sigma

        # Determine cache location
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            import hashlib
            uri_hash = hashlib.md5(volume_uri.encode()).hexdigest()[:8]
            self.npy_path = os.path.join(cache_dir, f"volume_cache_{uri_hash}.npy")
            self.ridge_path = os.path.join(cache_dir, f"ridge_cache_{uri_hash}_{self.ridge_sigma}.npy")
        else:
            self.npy_path = os.path.join(volume_uri, "volume_cache.npy")
            self.ridge_path = os.path.join(volume_uri, f"ridge_cache_{self.ridge_sigma}.npy")            
        self.stats_path = self.npy_path.replace(".npy", "_stats.json")
        self.data = None
        self.ridge_data = None
        self.dataset = None
        self.mean = 128.0
        self.std = 70.0
        
        if os.path.isdir(volume_uri) and any(f.endswith('.tif') for f in os.listdir(volume_uri)):
            if not os.path.exists(self.npy_path):
                print(f"Building fast volume cache for {volume_uri} ...")
                files = sorted([os.path.join(volume_uri, f) for f in os.listdir(volume_uri) if f.endswith('.tif')])
                
                with Image.open(files[0]) as img:
                    h, w = img.size[::-1]
                
                tmp_npy_path = self.npy_path + ".tmp"
                tmp_data = np.memmap(tmp_npy_path, dtype='uint8', mode='w+', shape=(len(files), h, w))
                for i, f in enumerate(files):
                    with Image.open(f) as img:
                        tmp_data[i] = np.array(img)
                tmp_data.flush()
                del tmp_data 
                
                os.rename(tmp_npy_path, self.npy_path)
                print(f"Fast cache built: {self.npy_path}")
                
            files = [f for f in os.listdir(volume_uri) if f.endswith('.tif')]
            with Image.open(os.path.join(volume_uri, files[0])) as img:
                h, w = img.size[::-1]
            
            self.shape = (len(files), h, w)
            self.is_zarr = False
        else:
            ds = ts.open({
                'driver': 'zarr',
                'kvstore': {'driver': 'file', 'path': volume_uri},
            }).result()
            self.shape = ds.shape
            self.is_zarr = True
            if not os.path.exists(self.stats_path):
                self.stats_path = os.path.join(os.path.dirname(volume_uri.rstrip('/')), "volume_stats.json")

        if os.path.exists(self.stats_path):
            try:
                with open(self.stats_path, 'r') as f:
                    stats = json.load(f)
                    self.mean = stats.get('mean', 128.0)
                    self.std = stats.get('std', 70.0)
            except Exception: pass
        else:
            self._calculate_stats()

        if self.use_ridges and detect_ridges_3d:
            self._init_ridges()

    def _init_ridges(self):
        if not os.path.exists(self.ridge_path):
            print(f"Computing Ridge Map (Frangi filters) for {self.uri} ... This may take a while.")
            self._lazy_init()
            
            # For large volumes, we compute ridges in blocks to avoid OOM
            # But for now, let's assume a straightforward implementation or block-wise
            D, H, W = self.shape
            tmp_ridge_path = self.ridge_path + ".tmp"
            # Ridge maps are floats (0.0 to 1.0)
            tmp_ridges = np.memmap(tmp_ridge_path, dtype='float32', mode='w+', shape=(D, H, W))
            
            # Simple block-wise processing
            step_z = 32
            if D < 3:
                print(f"Volume too small for 3D ridges (D={D}). Skipping.")
                return

            for z in range(0, D, step_z):
                z_start = z
                z_end = min(z + step_z + 4, D) # overlap for Hessian
                if z_end - z_start < 3:
                    z_start = max(0, z_end - 3)
                
                vol_slice = np.array(self[z_start:z_end])
                if vol_slice.shape[0] < 3:
                    # Final fallback if something went wrong with the range logic
                    continue
                    
                print(f"z_start={z_start}, z_end={z_end}, vol_slice.shape={vol_slice.shape}")
                ridge_slice = detect_ridges_3d(vol_slice, sigma=self.ridge_sigma)
                # handle overlap
                actual_end = min(z + step_z, D)
                tmp_ridges[z:actual_end] = ridge_slice[(z - z_start):((z - z_start) + (actual_end - z))]
                tmp_ridges.flush()
                print(f"Ridge progress: {actual_end}/{D} slices")

            del tmp_ridges
            os.rename(tmp_ridge_path, self.ridge_path)
            print(f"Ridge cache built: {self.ridge_path}")
        
    def _calculate_stats(self):
        print(f"Calculating stats for {self.uri} ...")
        try:
            self._lazy_init()
            # Sample 32 slices for better Z-score accuracy
            indices = np.linspace(0, self.shape[0]-1, 32, dtype=int)
            samples = []
            for idx in indices:
                samples.append(np.array(self[idx]))
            samples = np.array(samples)
            self.mean = float(samples.mean())
            self.std = float(samples.std())
            
            with open(self.stats_path, 'w') as f:
                json.dump({'mean': self.mean, 'std': self.std}, f)
        except Exception as e:
            print(f"Warning: Could not calculate/save stats: {e}")

    def normalize(self, patch):
        """Automated Z-scoring based on stored volume stats. Supports multi-channel input."""
        if isinstance(patch, np.ndarray):
            patch = torch.from_numpy(patch.copy()).float()
        elif not isinstance(patch, torch.Tensor):
            patch = torch.tensor(np.array(patch, copy=True), dtype=torch.float32)
        
        if self.use_ridges and len(patch.shape) == 4 and patch.shape[0] == 2:
            # Multi-channel [C=2, Z, H, W]
            ct = (patch[0] - self.mean) / (self.std + 1e-5)
            ridges = patch[1] # Ridges are already 0-1
            return torch.stack([ct, ridges], dim=0)
        
        return (patch - self.mean) / (self.std + 1e-5)

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
                try:
                    if hasattr(os, 'posix_fadvise'):
                        with open(self.npy_path, 'rb') as f:
                            os.posix_fadvise(f.fileno(), 0, os.path.getsize(self.npy_path), os.POSIX_FADV_SEQUENTIAL)
                except Exception: pass

        if self.use_ridges and self.ridge_data is None and os.path.exists(self.ridge_path):
            self.ridge_data = np.memmap(self.ridge_path, dtype='float32', mode='r', shape=self.shape)

    def __getitem__(self, key):
        self._lazy_init()
        if self.is_zarr:
            ct = self.dataset[key].read().result()
        else:
            ct = self.data[key]
        
        if self.use_ridges:
            if self.ridge_data is not None:
                ridges = self.ridge_data[key]
            else:
                # Fallback: Return zeros for ridges if not computed/loaded
                ridges = np.zeros_like(ct, dtype='float32')
            
            return np.stack([ct, ridges], axis=0)
            
        return ct

class VesuviusLabeledDataset(torch.utils.data.Dataset):
    def __init__(self, volume_uri, labels_path, mask_path=None, patch_size=64, num_layers=16, seed=None, cache_dir=None, use_ridges=False, ridge_sigma=2.0, is_unlabeled=False):
        self.volume = FastVesuviusVolume(volume_uri, cache_dir=cache_dir, use_ridges=use_ridges, ridge_sigma=ridge_sigma)
        self.patch_size = patch_size
        self.num_layers = num_layers
        self.shape = self.volume.shape
        self.seed = seed
        self.use_ridges = use_ridges
        self.is_unlabeled = is_unlabeled
        
        # Load Labels (2D PNG)
        if labels_path and os.path.exists(labels_path):
            with Image.open(labels_path) as img:
                self.labels = np.array(img).astype(np.float32) / 255.0
        else:
            self.labels = None
            
        if mask_path and os.path.exists(mask_path):
            with Image.open(mask_path) as img:
                self.mask = np.array(img).astype(np.float32) / 255.0
        else:
            self.mask = None
            
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
            self.valid_coords = np.load(cache_path)
        else:
            print(f"Finding valid coordinates in mask...")
            self.valid_coords = []
            H, W = (self.mask.shape if self.mask is not None else (self.shape[1], self.shape[2]))
            
            # Simple grid-based valid coordinates
            for y in range(0, H - self.patch_size, stride):
                for x in range(0, W - self.patch_size, stride):
                    if self.mask is None or self.mask[y:y+self.patch_size, x:x+self.patch_size].mean() > 0.05:
                        self.valid_coords.append((y, x))
            
            self.valid_coords = np.array(self.valid_coords, dtype=np.int32)
            np.save(cache_path, self.valid_coords)
        
        print(f"Initialized Dataset: Volume {self.shape}, Valid Patches {len(self.valid_coords)}, is_unlabeled={self.is_unlabeled}")

    def __len__(self):
        return len(self.valid_coords)

    def get_labeled_unlabeled_patch_indices(self):
        """Standard method for semi-supervised batch samplers."""
        indices = list(range(len(self)))
        if self.is_unlabeled:
            return [], indices
        return indices, []

    def __getitem__(self, idx):
        y0, x0 = self.valid_coords[idx]
        
        # Small deterministic jitter based on index
        rng = np.random.RandomState(idx + (self.seed or 0))
        y0 = max(0, min(self.shape[1] - self.patch_size, y0 + rng.randint(-4, 5)))
        x0 = max(0, min(self.shape[2] - self.patch_size, x0 + rng.randint(-4, 5)))
        z0 = rng.randint(0, self.shape[0] - self.num_layers)
        
        try:
            patch_vol = self.volume[z0:z0+self.num_layers, y0:y0+self.patch_size, x0:x0+self.patch_size]
            patch_vol = self.volume.normalize(patch_vol)
            if not self.use_ridges:
                patch_vol = patch_vol.unsqueeze(0) # [1, Z, H, W]
            
            if self.labels is not None and not self.is_unlabeled:
                patch_label = torch.tensor(np.array(self.labels[y0:y0+self.patch_size, x0:x0+self.patch_size], copy=False), dtype=torch.float32)
            else:
                patch_label = torch.zeros((self.patch_size, self.patch_size), dtype=torch.float32)
                
            return patch_vol, patch_label
            
        except Exception:
            # Fallback for errors during loading
            c = 2 if self.use_ridges else 1
            return torch.zeros(c, self.num_layers, self.patch_size, self.patch_size), torch.zeros(self.patch_size, self.patch_size)

class VesuviusS3Dataset(torch.utils.data.Dataset):
    """Fallback for Zarr/S3 data (Map-style)."""
    def __init__(self, uri, patch_size=32, num_layers=16, seed=None, cache_dir=None, use_ridges=False, ridge_sigma=2.0, is_unlabeled=True):
        self.uri = uri
        self.patch_size = patch_size
        self.num_layers = num_layers
        self.seed = seed
        self.cache_dir = cache_dir
        self.use_ridges = use_ridges
        self.ridge_sigma = ridge_sigma
        self.is_unlabeled = is_unlabeled
        
        if uri.startswith("s3://"):
            raise ValueError("S3 Streaming disabled. Use local paths.")
            
        self.volume = FastVesuviusVolume(uri, cache_dir=cache_dir, use_ridges=use_ridges, ridge_sigma=ridge_sigma)
        self.shape = self.volume.shape
        
        # Grid-based patches
        stride = patch_size // 2
        self.valid_coords = []
        for y in range(0, self.shape[1] - patch_size, stride):
            for x in range(0, self.shape[2] - patch_size, stride):
                self.valid_coords.append((y, x))
        self.valid_coords = np.array(self.valid_coords, dtype=np.int32)
        print(f"Initialized S3 Dataset: Volume {self.shape}, Patches {len(self.valid_coords)}, is_unlabeled={self.is_unlabeled}")

    def __len__(self):
        return len(self.valid_coords)

    def get_labeled_unlabeled_patch_indices(self):
        indices = list(range(len(self)))
        if self.is_unlabeled:
            return [], indices
        return indices, []

    def __getitem__(self, idx):
        y0, x0 = self.valid_coords[idx]
        rng = np.random.RandomState(idx + (self.seed or 0))
        z0 = rng.randint(0, self.shape[0] - self.num_layers)
        
        try:
            patch = self.volume[z0:z0+self.num_layers, y0:y0+self.patch_size, x0:x0+self.patch_size]
            tensor = self.volume.normalize(patch)
            if not self.use_ridges:
                tensor = tensor.unsqueeze(0)
            return tensor, torch.zeros((self.patch_size, self.patch_size), dtype=torch.float32)
        except Exception:
            c = 2 if self.use_ridges else 1
            return torch.zeros(c, self.num_layers, self.patch_size, self.patch_size), torch.zeros(self.patch_size, self.patch_size)
