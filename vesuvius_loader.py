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
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
VILLA_SRC = os.path.join(PROJECT_ROOT, "villa/vesuvius/src")
FIBER_TOOLS_PATH = os.path.join(PROJECT_ROOT, "villa/foundation/datasets/fibers-dataset")

for p in [VILLA_SRC, FIBER_TOOLS_PATH]:
    if p not in sys.path:
        sys.path.append(p)
import tools as fiber_tools
from vesuvius_c_wrapper.vesuvius_c import VesuviusVolume, FastLocalVolume

Image.MAX_IMAGE_PIXELS = None

class FastVesuviusVolume:
    """
    Optimized volume loader using Vesuvius-C for zero-copy data-on-demand
    and roadmap-Priority-A CuPy tools for on-the-fly ridge detection.
    """
    def __init__(self, volume_uri, cache_dir=None, use_ridges=False, ridge_sigma=2.0):
        self.uri = volume_uri
        self.use_ridges = use_ridges
        self.ridge_sigma = ridge_sigma

        # Priority B Integration: 
        # Use FastLocalVolume for local files (bypasses curl)
        # Use VesuviusVolume for remote URLs (supports caching)
        if os.path.exists(volume_uri):
            # Auto-detect OME-Zarr resolution levels
            local_path = volume_uri
            if not os.path.exists(os.path.join(local_path, ".zarray")):
                # Check for OME-Zarr structure (level 0 is full res)
                level0_path = os.path.join(local_path, "0")
                if os.path.exists(os.path.join(level0_path, ".zarray")):
                    local_path = level0_path
                    print(f"Detected OME-Zarr: Using level 0 at {local_path}")
            self.vol = FastLocalVolume(local_path)
        else:
            self.vol = VesuviusVolume(cache_dir=cache_dir or "test_cache", url=volume_uri)
            
        self.shape = self.vol.shape


    def normalize(self, patch):
        if isinstance(patch, torch.Tensor):
             return patch.float()
        return torch.from_numpy(patch).float()

    def __getitem__(self, key) -> torch.Tensor:
        """
        Supports slicing like [z0:z1, y0:y1, x0:x1]
        Computes ridges on-the-fly if enabled.
        """
        z_slice, y_slice, x_slice = key
        
        depth = z_slice.stop - z_slice.start
        height = y_slice.stop - y_slice.start
        width = x_slice.stop - x_slice.start

        # Fetch raw CT data via Vesuvius-C
        ct = self.vol.get_chunk(
            z_slice.start, y_slice.start, x_slice.start,
            depth, height, width
        )
        ct_tensor = torch.from_numpy(ct).float() / 255.0

        if self.use_ridges:
            # Priority A Integration: CuPy-accelerated ridges on-the-fly
            try:
                import cupy as cp
                ct_gpu = cp.asarray(ct.astype(np.float32) / 255.0)
                # Use our newly ported CuPy function in villa
                ridges_gpu = fiber_tools.detect_ridges(ct_gpu, sigma=self.ridge_sigma)
                ridges = cp.asnumpy(ridges_gpu)
                ridges_tensor = torch.from_numpy(ridges).float()
            except Exception:
                ridges_tensor = torch.zeros_like(ct_tensor)
            return torch.stack([ct_tensor, ridges_tensor], dim=0)
            
        return ct_tensor

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
            # Clean URI for filename usage
            clean_uri = volume_uri.replace("/", "_").replace(".", "_")
            cache_path = f"valid_coords_{clean_uri}_{self.patch_size}_{stride}_{mask_mtime}.npy"

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
        
        z_depth = self.shape[0]
        z_request = min(self.num_layers, z_depth)
        z_range = z_depth - z_request
        z0 = rng.randint(0, z_range + 1) if z_range > 0 else 0
        
        try:
            patch_vol = self.volume[z0:z0+z_request, y0:y0+self.patch_size, x0:x0+self.patch_size]
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
        z_depth = self.shape[0]
        z_request = min(self.num_layers, z_depth)
        z_range = z_depth - z_request
        z0 = rng.randint(0, z_range + 1) if z_range > 0 else 0
        
        try:
            patch = self.volume[z0:z0+z_request, y0:y0+self.patch_size, x0:x0+self.patch_size]
            if not self.use_ridges:
                patch = patch.unsqueeze(0)
            return patch, torch.zeros((self.patch_size, self.patch_size), dtype=torch.float32)
        except Exception:
            c = 2 if self.use_ridges else 1
            return torch.zeros(c, self.num_layers, self.patch_size, self.patch_size), torch.zeros(self.patch_size, self.patch_size)
