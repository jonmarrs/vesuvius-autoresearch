import tensorstore as ts
import numpy as np
import torch
from torch.utils.data import IterableDataset, DataLoader
from PIL import Image
import os
import time
import json
import sys
from collections import defaultdict

# Add villa to path for ridge detection and official Volume class
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
VILLA_SRC = os.path.join(PROJECT_ROOT, "villa/vesuvius/src")
FIBER_TOOLS_PATH = os.path.join(PROJECT_ROOT, "villa/foundation/datasets/fibers-dataset")

for p in [VILLA_SRC, FIBER_TOOLS_PATH]:
    if p not in sys.path:
        sys.path.append(p)
import tools as fiber_tools
try:
    from vesuvius_c_wrapper.vesuvius_c import VesuviusVolume, FastLocalVolume
except ImportError as exc:
    print(f"Warning: vesuvius_c_wrapper unavailable; using direct Zarr fallback: {exc}")
    import zarr

    class FastLocalVolume:
        def __init__(self, path):
            self.path = path
            self.arr = zarr.open(path, mode="r")
            self.shape = self.arr.shape

        def get_chunk(self, z, y, x, depth, height, width):
            return np.asarray(self.arr[z:z + depth, y:y + height, x:x + width])

    class VesuviusVolume(FastLocalVolume):
        def __init__(self, cache_dir=None, url=None):
            super().__init__(url or cache_dir)

Image.MAX_IMAGE_PIXELS = None
_WARNING_COUNTS = defaultdict(int)

def _warn_limited(key, message, limit=5):
    _WARNING_COUNTS[key] += 1
    count = _WARNING_COUNTS[key]
    if count <= limit:
        print(f"Warning: {message}")
    elif count == limit + 1:
        print(f"Warning: suppressing further {key} warnings")

class FastVesuviusVolume:
    """
    Optimized volume loader using Vesuvius-C for zero-copy data-on-demand
    and roadmap-Priority-A CuPy tools for on-the-fly ridge detection.
    """
    def __init__(self, volume_uri, cache_dir=None, use_ridges=False, ridge_sigma=2.0):
        self.uri = volume_uri
        self.cache_dir = cache_dir
        self.use_ridges = use_ridges
        self.ridge_sigma = ridge_sigma

        self._init_vol()
        self.shape = self.vol.shape

    def _init_vol(self):
        # Priority B Integration: 
        # Use FastLocalVolume for local files (bypasses curl)
        # Use VesuviusVolume for remote URLs (supports caching)
        if os.path.exists(self.uri):
            # Auto-detect OME-Zarr resolution levels
            local_path = self.uri
            if not os.path.exists(os.path.join(local_path, ".zarray")):
                # Check for OME-Zarr structure (level 0 is full res)
                level0_path = os.path.join(local_path, "0")
                if os.path.exists(os.path.join(level0_path, ".zarray")):
                    local_path = level0_path
                    print(f"Detected OME-Zarr: Using level 0 at {local_path}")
            self.vol = FastLocalVolume(local_path)
        else:
            self.vol = VesuviusVolume(cache_dir=self.cache_dir or "test_cache", url=self.uri)

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('vol', None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._init_vol()


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
            if depth < 3:
                _warn_limited("ridge_thin_volume", f"Volume too thin ({depth} slices) for ridge detection; using zero ridges.")
                ridges_tensor = torch.zeros_like(ct_tensor)
            else:
                try:
                    import cupy as cp
                    ct_gpu = cp.asarray(ct.astype(np.float32) / 255.0)
                    # Use our newly ported CuPy function in villa
                    ridges_gpu = fiber_tools.detect_ridges(ct_gpu, sigma=self.ridge_sigma)
                    ridges = cp.asnumpy(ridges_gpu)
                    ridges_tensor = torch.from_numpy(ridges).float()
                except Exception as exc:
                    _warn_limited(
                        "ridge_fallback",
                        f"ridge detection failed for {self.uri}; using zero ridge channel: {type(exc).__name__}: {exc}",
                    )
                    ridges_tensor = torch.zeros_like(ct_tensor)
            return torch.stack([ct_tensor, ridges_tensor], dim=0)
            
        return ct_tensor

class VesuviusLabeledDataset(torch.utils.data.Dataset):
    def __init__(self, volume_uri, labels_path, mask_path=None, patch_size=64, num_layers=16, seed=None, cache_dir=None, use_ridges=False, ridge_sigma=2.0, use_lasagna=False, is_unlabeled=False, require_ink=False):
        self.volume = FastVesuviusVolume(volume_uri, cache_dir=cache_dir, use_ridges=use_ridges, ridge_sigma=ridge_sigma)
        self.patch_size = patch_size
        self.num_layers = min(num_layers, self.volume.shape[0])
        self.shape = self.volume.shape
        self.seed = seed
        self.use_ridges = use_ridges
        self.use_lasagna = use_lasagna
        self.is_unlabeled = is_unlabeled
        self.require_ink = require_ink
        # ... (rest of init) ...

    def _apply_lasagna_flattening(self, patch_vol):
        if not self.use_lasagna:
            return patch_vol
        try:
            D, H, W = patch_vol.shape[-3:]
            grid_z, grid_y, grid_x = torch.meshgrid([torch.linspace(-1, 1, D), torch.linspace(-1, 1, H), torch.linspace(-1, 1, W)], indexing='ij')
            grid = torch.stack([grid_x, grid_y, grid_z], dim=-1).unsqueeze(0)
            grid[..., 2] = grid[..., 2] * 0.1 
            return torch.nn.functional.grid_sample(patch_vol.unsqueeze(0), grid, mode='bilinear', padding_mode='border', align_corners=True).squeeze(0)
        except Exception:
            return patch_vol
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
        labels_mtime = int(os.path.getmtime(labels_path)) if labels_path and os.path.exists(labels_path) else 0
        
        if cache_dir:
            import hashlib
            uri_hash = hashlib.md5(volume_uri.encode()).hexdigest()[:8]
            cache_path = os.path.join(cache_dir, f"valid_coords_cache_{uri_hash}_{self.patch_size}_{stride}_{mask_mtime}_{labels_mtime}_{1 if require_ink else 0}.npy")
        else:
            # Clean URI for filename usage
            clean_uri = volume_uri.replace("/", "_").replace(".", "_")
            cache_path = f"valid_coords_{clean_uri}_{self.patch_size}_{stride}_{mask_mtime}_{labels_mtime}_{1 if require_ink else 0}.npy"

        if os.path.exists(cache_path):
            self.valid_coords = np.load(cache_path)
        else:
            print(f"Finding valid coordinates (require_ink={require_ink}) for {volume_uri}...")
            self.valid_coords = []
            
            H, W = self.shape[1], self.shape[2]
                
            for y in range(0, H - self.patch_size, stride):
                for x in range(0, W - self.patch_size, stride):
                    # Mask check
                    if self.mask is not None:
                        if not self.mask[y:y+self.patch_size, x:x+self.patch_size].any():
                            continue
                    
                    # Ink check
                    if self.require_ink and self.labels is not None:
                        if not self.labels[y:y+self.patch_size, x:x+self.patch_size].any():
                            continue
                            
                    self.valid_coords.append((y, x))
            
            if not self.valid_coords:
                print(f"  WARNING: No patches found. Retrying with any non-zero pixels...")
                # Fallback to just anything in the volume if nothing matches
                for y in range(0, H - self.patch_size, stride * 4):
                    for x in range(0, W - self.patch_size, stride * 4):
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
            
            # Priority J: Apply Lasagna flattening
            patch_vol = self._apply_lasagna_flattening(patch_vol)
            
            if not self.use_ridges:
                patch_vol = patch_vol.unsqueeze(0) # [1, Z, H, W]
            
            if self.labels is not None and not self.is_unlabeled:
                patch_label = torch.tensor(np.array(self.labels[y0:y0+self.patch_size, x0:x0+self.patch_size], copy=False), dtype=torch.float32)
            else:
                patch_label = torch.zeros((self.patch_size, self.patch_size), dtype=torch.float32)
            return patch_vol, patch_label
        except Exception as e:
            _warn_limited(
                "labeled_zero_patch",
                f"returning zero labeled patch for sample {idx} from {self.volume.uri}: {type(e).__name__}: {e}",
            )
            c = 2 if self.use_ridges else 1
            return torch.zeros(c, self.num_layers, self.patch_size, self.patch_size), torch.zeros(self.patch_size, self.patch_size)

class VesuviusS3Dataset(torch.utils.data.Dataset):
    def __init__(self, uri, patch_size=32, num_layers=16, seed=None, cache_dir=None, use_ridges=False, ridge_sigma=2.0, is_unlabeled=True):
        self.uri = uri
        self.patch_size = patch_size
        self.seed = seed
        self.cache_dir = cache_dir
        self.use_ridges = use_ridges
        self.ridge_sigma = ridge_sigma
        self.is_unlabeled = is_unlabeled
        
        self.volume = FastVesuviusVolume(uri, cache_dir=cache_dir, use_ridges=use_ridges, ridge_sigma=ridge_sigma)
        self.shape = self.volume.shape
        self.num_layers = min(num_layers, self.shape[0])
        
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
        except Exception as exc:
            _warn_limited(
                "s3_zero_patch",
                f"returning zero S3 patch for sample {idx} from {self.uri}: {type(exc).__name__}: {exc}",
            )
            c = 2 if self.use_ridges else 1
            return torch.zeros(c, self.num_layers, self.patch_size, self.patch_size), torch.zeros(self.patch_size, self.patch_size)
