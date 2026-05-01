import tensorstore as ts
import numpy as np
import torch
from torch.utils.data import IterableDataset, DataLoader
from PIL import Image
import os
import time
import json
import sys

# Add villa to path for ridge detection and official Volume class
VILLA_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "villa/vesuvius/src"))
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)

try:
    from vesuvius.image_proc.features.ridges_vessels import detect_ridges_3d
    from vesuvius.data.volume import Volume
except ImportError:
    detect_ridges_3d = None
    Volume = None

Image.MAX_IMAGE_PIXELS = None

class FastVesuviusVolume:
    """
    Adapter for the official villa Volume class.
    Provides a compatible interface for the rest of the loader.
    """
    def __init__(self, volume_uri, cache_dir=None, use_ridges=False, ridge_sigma=2.0):
        self.uri = volume_uri
        self.use_ridges = use_ridges
        self.ridge_sigma = ridge_sigma
        
        if Volume is None:
            raise ImportError("Official vesuvius Volume class not found. Check villa submodule.")
            
        # Initialize official volume
        self.official_vol = Volume(
            type="zarr",
            path=volume_uri,
            normalization_scheme="instance_zscore",
            return_as_tensor=True,
            verbose=False
        )
        self.shape = self.official_vol.shape()

        # We still maintain our own ridge cache logic for now
        if cache_dir:
            import hashlib
            uri_hash = hashlib.md5(volume_uri.encode()).hexdigest()[:8]
            self.ridge_path = os.path.join(cache_dir, f"ridge_cache_{uri_hash}_{self.ridge_sigma}.npy")
        else:
            self.ridge_path = volume_uri.replace(".zarr", f"_ridges_{self.ridge_sigma}.npy")
            
        self.ridge_data = None
        if self.use_ridges and detect_ridges_3d:
            self._init_ridges()

    def _init_ridges(self):
        if not os.path.exists(self.ridge_path):
            print(f"Computing 3D ridges for {self.uri} (sigma={self.ridge_sigma}) ...")
            D, H, W = self.shape
            tmp_ridge_path = self.ridge_path + ".tmp"
            tmp_ridges = np.memmap(tmp_ridge_path, dtype='float32', mode='w+', shape=(D, H, W))
            
            step_z = 32
            for z in range(0, D, step_z):
                z_start = max(0, z - 4)
                z_end = min(z + step_z + 4, D)
                
                vol_slice = self.official_vol[z_start:z_end, :, :].cpu().numpy()
                if vol_slice.shape[0] < 3: continue
                
                ridge_slice = detect_ridges_3d(vol_slice, sigma=self.ridge_sigma)
                
                actual_start = z
                actual_end = min(z + step_z, D)
                tmp_ridges[actual_start:actual_end] = ridge_slice[(actual_start - z_start):(actual_end - z_start)]
                
            tmp_ridges.flush()
            del tmp_ridges
            os.rename(tmp_ridge_path, self.ridge_path)
            print(f"Ridge cache built: {self.ridge_path}")

        self.ridge_data = np.memmap(self.ridge_path, dtype='float32', mode='r', shape=self.shape)

    def normalize(self, patch):
        # Volume class already normalizes to z-score
        if isinstance(patch, torch.Tensor):
             return patch.float()
        return torch.from_numpy(patch).float()

    def __getitem__(self, key):
        ct = self.official_vol[key]
        if self.use_ridges and self.ridge_data is not None:
            ridges = torch.from_numpy(self.ridge_data[key]).to(ct.device)
            return torch.stack([ct, ridges], axis=0)
        return ct

class VesuviusLabeledDataset(torch.utils.data.Dataset):
    def __init__(self, volume_uri, labels_path, mask_path=None, patch_size=64, num_layers=16, seed=None, cache_dir=None, use_ridges=False, ridge_sigma=2.0, is_unlabeled=False):
        self.volume = FastVesuviusVolume(volume_uri, cache_dir=cache_dir, use_ridges=use_ridges, ridge_sigma=ridge_sigma)
        self.patch_size = patch_size
        self.num_layers = min(num_layers, self.volume.shape[0])
        self.shape = self.volume.shape
        self.seed = seed
        self.use_ridges = use_ridges
        self.is_unlabeled = is_unlabeled
        
        # Load Labels (2D PNG)
        if labels_path and os.path.exists(labels_path):
            with Image.open(labels_path) as img:
                img_arr = np.array(img).astype(np.float32)
                if img_arr.max() > 1.0:
                    img_arr /= 255.0
                self.labels = img_arr
        else:
            self.labels = None

        if mask_path and os.path.exists(mask_path):
            with Image.open(mask_path) as img:
                img_arr = np.array(img).astype(np.float32)
                if img_arr.max() > 1.0:
                    img_arr /= 255.0
                self.mask = img_arr
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
            # Fallback if no cache_dir
            cache_path = volume_uri.replace(".zarr", f"_valid_coords_{self.patch_size}_{stride}_{mask_mtime}.npy")

        if os.path.exists(cache_path):
            self.valid_coords = np.load(cache_path)
        else:
            print(f"Finding valid coordinates in mask for {volume_uri}...")
            self.valid_coords = []
            if self.mask is not None:
                H, W = self.mask.shape
                print(f"  Mask shape: {H}x{W}, Mean: {self.mask.mean():.4f}")
            else:
                H, W = self.shape[1], self.shape[2]
                print(f"  No mask, using volume shape: {H}x{W}")
                
            for y in range(0, H - self.patch_size, stride):
                for x in range(0, W - self.patch_size, stride):
                    if self.mask is None or self.mask[y:y+self.patch_size, x:x+self.patch_size].mean() > 0.05:
                        self.valid_coords.append((y, x))
            
            if not self.valid_coords:
                print(f"  WARNING: No patches found with threshold 0.05. Retrying with any non-zero pixels...")
                for y in range(0, H - self.patch_size, stride):
                    for x in range(0, W - self.patch_size, stride):
                        if self.mask is None or self.mask[y:y+self.patch_size, x:x+self.patch_size].any():
                            self.valid_coords.append((y, x))

            self.valid_coords = np.array(self.valid_coords, dtype=np.int32)
            print(f"  Found {len(self.valid_coords)} valid patches.")
            np.save(cache_path, self.valid_coords)
        
        print(f"Initialized Dataset: Volume {self.shape}, Valid Patches {len(self.valid_coords)}, is_unlabeled={self.is_unlabeled}")

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
        y0 = max(0, min(self.shape[1] - self.patch_size, y0 + rng.randint(-4, 5)))
        x0 = max(0, min(self.shape[2] - self.patch_size, x0 + rng.randint(-4, 5)))
        
        z_range = self.shape[0] - self.num_layers
        z0 = rng.randint(0, z_range + 1) if z_range > 0 else 0
        
        try:
            patch_vol = self.volume[z0:z0+self.num_layers, y0:y0+self.patch_size, x0:x0+self.patch_size]
            if not self.use_ridges:
                patch_vol = patch_vol.unsqueeze(0) # [1, Z, H, W]
            
            if self.labels is not None and not self.is_unlabeled:
                patch_label = torch.tensor(np.array(self.labels[y0:y0+self.patch_size, x0:x0+self.patch_size], copy=False), dtype=torch.float32)
            else:
                patch_label = torch.zeros((self.patch_size, self.patch_size), dtype=torch.float32)
            return patch_vol, patch_label
        except Exception:
            c = 2 if self.use_ridges else 1
            return torch.zeros(c, self.num_layers, self.patch_size, self.patch_size), torch.zeros(self.patch_size, self.patch_size)

class VesuviusS3Dataset(torch.utils.data.Dataset):
    def __init__(self, uri, patch_size=32, num_layers=16, seed=None, cache_dir=None, use_ridges=False, ridge_sigma=2.0, is_unlabeled=True):
        self.uri = uri
        self.patch_size = patch_size
        self.num_layers = num_layers
        self.seed = seed
        self.cache_dir = cache_dir
        self.use_ridges = use_ridges
        self.ridge_sigma = ridge_sigma
        self.is_unlabeled = is_unlabeled
        
        self.volume = FastVesuviusVolume(uri, cache_dir=cache_dir, use_ridges=use_ridges, ridge_sigma=ridge_sigma)
        self.shape = self.volume.shape
        
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
            if not self.use_ridges:
                patch = patch.unsqueeze(0)
            return patch, torch.zeros((self.patch_size, self.patch_size), dtype=torch.float32)
        except Exception:
            c = 2 if self.use_ridges else 1
            return torch.zeros(c, self.num_layers, self.patch_size, self.patch_size), torch.zeros(self.patch_size, self.patch_size)
