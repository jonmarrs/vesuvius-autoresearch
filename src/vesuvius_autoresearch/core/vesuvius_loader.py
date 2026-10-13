import itertools
import os
import sys
from collections import defaultdict

import numpy as np
import torch
from PIL import Image

# Add villa to path for ridge detection and official Volume class
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
VILLA_SRC = os.path.join(PROJECT_ROOT, "villa/vesuvius/src")
FIBER_TOOLS_PATH = os.path.join(
    PROJECT_ROOT, "villa/foundation/datasets/fibers-dataset"
)
# Where volume and valid_coords caches go when the caller passes no cache_dir.
DEFAULT_CACHE_DIR = os.path.join(PROJECT_ROOT, "test_cache")

for p in [VILLA_SRC, FIBER_TOOLS_PATH]:
    if p not in sys.path:
        sys.path.append(p)
from vesuvius_autoresearch.fibers import detect_ridges


def frangi_vesselness_zcollapsed(ct_np, sigma=2.0):
    """Frangi vesselness of a [Z, H, W] CT patch, z-collapsed via mean to [H, W].

    Uses skimage's CPU Frangi filter rather than the villa clone's tools.py: the
    upstream tools.py binds a single global array backend (cupy when a GPU is
    present) whose hessian path rejects numpy input AND whose cupy path hits the
    cuSolver eigvalsh failure (the bug PR #1033 fixed but upstream still carries),
    so both branches raise here and the fiber target silently fell back to zeros.
    skimage.filters.frangi is pure-CPU, dependency-light, and matches the
    original per-patch CPU intent. black_ridges=False detects bright ridges
    (fibers brighter than background in CT).
    """
    from skimage.filters import frangi

    vesselness = frangi(ct_np.astype(np.float32), sigmas=(sigma,), black_ridges=False)
    return np.nan_to_num(np.asarray(vesselness, dtype=np.float32)).mean(axis=0)


try:
    from volume_cartographer_wrapper.volume import (
        FastLocalVolume,
        VolumeCartographerVolume,
    )
except ImportError as exc:
    print(
        f"Warning: volume_cartographer_wrapper unavailable; using direct Zarr fallback: {exc}"
    )
    import zarr

    class FastLocalVolume:  # type: ignore[no-redef]
        def __init__(self, path):
            self.path = path
            self.arr = zarr.open(path, mode="r")
            self.shape = self.arr.shape
            self.backend = "zarr"

        def get_chunk(self, z, y, x, depth, height, width):
            return np.asarray(self.arr[z : z + depth, y : y + height, x : x + width])

    class VolumeCartographerVolume(FastLocalVolume):  # type: ignore[no-redef]
        def __init__(self, cache_dir=None, url=None):
            super().__init__(url or cache_dir)


Image.MAX_IMAGE_PIXELS = None
_WARNING_COUNTS = defaultdict(int)


# Largest per-axis size difference accepted between a 2D label/mask and its
# volume: export rounding, not a different crop or scale.
LABEL_SHAPE_TOLERANCE_PX = 2


def warning_counts() -> dict:
    """How often each degraded-input fallback fired in this process.

    The messages stop after a few per key; the counts do not, so a run can
    record that it trained on unwarped or zero-ridge patches.
    """
    return dict(_WARNING_COUNTS)


def _warn_limited(key, message, limit=5):
    _WARNING_COUNTS[key] += 1
    count = _WARNING_COUNTS[key]
    if count <= limit:
        print(f"Warning: {message}")
    elif count == limit + 1:
        print(f"Warning: suppressing further {key} warnings")


def _mismatch_hint(label_hw, volume_shape):
    """Why a 2D label might not fit a ``(depth, H, W)`` volume, for the error."""
    tol = LABEL_SHAPE_TOLERANCE_PX
    for a, b in itertools.permutations(range(3), 2):
        if (a, b) == (1, 2):
            continue  # (H, W) is the expected plane
        plane = (volume_shape[a], volume_shape[b])
        if all(abs(x - y) <= tol for x, y in zip(label_hw, plane, strict=True)):
            return (
                "The label matches another pair of the volume's axes (full shape "
                f"{tuple(volume_shape)}): the volume or the label is likely "
                "transposed; fix the axis order before training."
            )
    return (
        "A size difference this large is a different crop or scale, not export "
        "rounding; register the label to the volume grid before training."
    )


_CUPY_UNSET = object()
_CUPY = _CUPY_UNSET


def _cupy():
    """CuPy when the fibers backend can use it and a device is present, else None.

    Decided once per process. Uses fibers.detection's own check (CuPy and
    cupyx.scipy.ndimage), so this never hands CuPy arrays to a detect_ridges that
    would treat them as NumPy, and asks for a device like fibers.cli does: CuPy
    is a hard dependency, so importable is not the same as usable.
    """
    global _CUPY
    if _CUPY is _CUPY_UNSET:
        _CUPY = None
        from vesuvius_autoresearch.fibers import detection

        if detection.HAS_CUPY:
            try:
                if detection.cp.cuda.runtime.getDeviceCount() > 0:
                    _CUPY = detection.cp
            except Exception:
                pass
    return _CUPY


def ridge_channel(ct, sigma, uri, strict=False) -> torch.Tensor:
    """The ridge channel for a ``[Z, H, W]`` CT patch, as float32 on the CPU.

    The single implementation behind both datasets: CuPy when it imports, the
    CPU otherwise. Two diverging copies were how one of them came to discard
    every GPU result (``.to(self.device)``, an attribute never set). A failure
    is an error under ``strict`` and otherwise a counted warning with a zero
    channel, which is a different input, never a quiet substitute.
    """
    ct = np.asarray(ct, dtype=np.float32)
    # Input problems are the data's, not the GPU's: report them once instead of
    # failing on the GPU, counting a GPU fallback, and failing again on the CPU.
    if min(ct.shape) < 3:
        return _ridge_failure(
            ct, uri, strict, f"a {ct.shape} patch is too small for ridge detection"
        )
    if not np.isfinite(ct).all():
        return _ridge_failure(ct, uri, strict, "non-finite CT values")

    def checked(ridges):
        # A result of the wrong shape or with non-finite values is a failure,
        # not a feature (from #48's strict-preprocessing contract).
        ridges = np.asarray(ridges, dtype=np.float32)
        if ridges.shape != ct.shape or not np.isfinite(ridges).all():
            raise ValueError("ridge detection returned invalid shape or values")
        return torch.from_numpy(ridges)

    cp = _cupy()
    if cp is not None:
        try:
            return checked(cp.asnumpy(detect_ridges(cp.asarray(ct), sigma=sigma)))
        except Exception as exc:
            _warn_limited(
                "ridge_gpu_fallback",
                f"GPU ridge detection failed for {uri}; using the CPU: "
                f"{type(exc).__name__}: {exc}",
            )
    try:
        return checked(detect_ridges(ct, sigma=sigma))
    except Exception as exc:
        return _ridge_failure(
            ct, uri, strict, f"ridge detection failed: {type(exc).__name__}: {exc}", exc
        )


def _ridge_failure(ct, uri, strict, reason, cause=None):
    if strict:
        raise RuntimeError(f"{uri}: {reason}") from cause
    _warn_limited("ridge_fallback", f"{uri}: {reason}; using zero ridges")
    return torch.zeros(ct.shape, dtype=torch.float32)


class FastVesuviusVolume:
    """
    Optimized volume loader aligned with Villa Volume Cartographer / VC3D
    OME-Zarr conventions plus CuPy tools for on-the-fly ridge detection.
    """

    def __init__(self, volume_uri, cache_dir=None, use_ridges=False, ridge_sigma=2.0):
        self.uri = volume_uri
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.use_ridges = use_ridges
        self.ridge_sigma = ridge_sigma

        self._init_vol()
        self.shape = self.vol.shape

    def _init_vol(self):
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
            self.backend = "zarr"
        else:
            self.vol = VolumeCartographerVolume(cache_dir=self.cache_dir, url=self.uri)
            self.backend = "volume-cartographer"

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("vol", None)
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

        # Fetch raw CT data through the Volume Cartographer-aligned local
        # OME-Zarr compatibility layer.
        ct = self.vol.get_chunk(
            z_slice.start, y_slice.start, x_slice.start, depth, height, width
        )
        # Normalize to [0, 1] based on dtype. Previously hardcoded `/ 255.0`
        # assumed uint8; uint16 / float32 zarrs would silently miscalibrate.
        if ct.dtype == np.uint8:
            ct_norm = ct.astype(np.float32) / 255.0
        elif ct.dtype == np.uint16:
            ct_norm = ct.astype(np.float32) / 65535.0
        elif np.issubdtype(ct.dtype, np.floating):
            ct_norm = ct.astype(np.float32)
        else:
            _warn_limited(
                "ct_unknown_dtype",
                f"unknown CT dtype {ct.dtype} for {self.uri}; falling back to /255.0 normalization.",
            )
            ct_norm = ct.astype(np.float32) / 255.0
        ct_tensor = torch.from_numpy(ct_norm)

        if self.use_ridges:
            ridges_tensor = ridge_channel(ct_norm, self.ridge_sigma, self.uri)
            return torch.stack([ct_tensor, ridges_tensor], dim=0)

        return ct_tensor

    def get_raw_patch(self, z, y, x, d, h, w) -> torch.Tensor:
        ct = self.vol.get_chunk(z, y, x, d, h, w)
        if not ct.dtype.isnative:  # e.g. a big-endian zarr; torch needs native
            ct = ct.astype(ct.dtype.newbyteorder("="))
        if ct.dtype == np.uint16:
            ct = ct.astype(np.int32)
        return torch.from_numpy(ct)


class VesuviusLabeledDataset(torch.utils.data.Dataset):
    """CT patches and labels, with optional preprocessing.

    ``strict_reads=True`` requires requested preprocessing to succeed as well as
    the source read. It is used for measurements: substituted features or an
    unwarped patch cannot represent the requested input configuration. A working
    CPU ridge implementation remains a valid fallback from an unavailable GPU.
    The default permissive mode retains warning-and-fallback behavior.
    """

    def __init__(
        self,
        volume_uri,
        labels_path,
        mask_path=None,
        patch_size=64,
        num_layers=16,
        seed=None,
        cache_dir=None,
        use_ridges=False,
        ridge_sigma=2.0,
        use_lasagna=False,
        is_unlabeled=False,
        require_ink=False,
        target_fiber_source="sobel_z",
        target_fiber_sigma=2.0,
        min_mask_ratio=0.05,
        min_ink_ratio=0.01,
        patches_json=None,
        jitter=True,
        strict_reads=False,
    ):
        self.volume = FastVesuviusVolume(
            volume_uri,
            cache_dir=cache_dir,
            use_ridges=use_ridges,
            ridge_sigma=ridge_sigma,
        )
        self.patch_size = patch_size
        self.num_layers = min(num_layers, self.volume.shape[0])
        self.shape = self.volume.shape
        # __getitem__ normalises uint8 (/255) and uint16 (read as int32, /65535)
        # and passes floats through; any other dtype reached the model raw.
        # Checked from the array's metadata, without reading CT.
        vol = self.volume.vol
        dtype = getattr(vol, "dtype", None) or getattr(
            getattr(vol, "arr", None), "dtype", None
        )
        dtype = None if dtype is None else np.dtype(dtype)
        if dtype is not None and not (
            (dtype.kind == "u" and dtype.itemsize in (1, 2)) or dtype.kind == "f"
        ):
            raise ValueError(
                f"unsupported CT dtype {dtype} for {volume_uri}; the labeled "
                "dataset normalises uint8 and uint16 volumes and passes floats through"
            )
        self.seed = seed
        self.jitter = jitter
        self.strict_reads = strict_reads
        self.use_ridges = use_ridges
        self.use_lasagna = use_lasagna
        self.is_unlabeled = is_unlabeled
        self.require_ink = require_ink
        self.min_mask_ratio = min_mask_ratio
        self.min_ink_ratio = min_ink_ratio
        # target_fiber_source: "sobel_z" (default — train.py computes Sobel-Z
        # of CT inline, dataloader returns a zero placeholder for the 3rd
        # tuple element) or "frangi" (dataloader computes Frangi vesselness
        # via fiber_tools.detect_vesselness on the CT patch, ~86ms/patch
        # CPU, parallelized by num_workers).
        self.target_fiber_source = target_fiber_source
        self.target_fiber_sigma = target_fiber_sigma

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

        # Guard: the 2D label/mask must spatially correspond to the volume's
        # (H, W) plane (self.shape == (depth, H, W)). Some fragments store their
        # CT as (H, depth, W) instead, so a naive load silently misaligns labels
        # against transposed CT — the model then trains on garbage and scores
        # ~chance, with the only visible symptom a downstream collate crash. Fail
        # loudly here instead. Exports of the same segment differ by rounding
        # (0-1 px across the registered segments in reports/scorer_vs_labels.json);
        # anything larger is a different crop or scale. The tolerance used to be
        # 20% of each side (~1,600 px on an 8,181 px fragment), which let a
        # misregistered label train and validate silently.
        vol_hw = (self.shape[1], self.shape[2])
        coords_from_json = bool(patches_json and os.path.exists(patches_json))
        for _name in ("labels", "mask"):
            _arr = getattr(self, _name)
            if _arr is None or (_name == "mask" and coords_from_json):
                continue  # a mask only places patches; patches.json replaces it
            if _name == "labels" and _arr.ndim != 2:
                # Labels are cut into patches: an RGB(A) PNG passed the old
                # (H, W)-only check and produced [p, p, C] label patches. A mask
                # may keep its channels; villa's patch finder collapses them.
                raise ValueError(
                    f"labels for {volume_uri} must be a single-channel image; "
                    f"got array shape {_arr.shape}"
                )
            lh, lw = _arr.shape[:2]
            if (
                abs(lh - vol_hw[0]) > LABEL_SHAPE_TOLERANCE_PX
                or abs(lw - vol_hw[1]) > LABEL_SHAPE_TOLERANCE_PX
            ):
                raise ValueError(
                    f"{_name} shape {(lh, lw)} does not match volume (H, W)="
                    f"{vol_hw} for {volume_uri} (tolerance "
                    f"{LABEL_SHAPE_TOLERANCE_PX} px). "
                    + _mismatch_hint((lh, lw), tuple(self.shape))
                )
            if (lh, lw) != vol_hw:
                # Within tolerance, put it on the volume grid: crop the extra
                # row/column, or pad a missing one with zeros. A label 1-2 px
                # short otherwise gave edge patches a shorter label than
                # patch_size, and collation failed.
                fitted = np.zeros(vol_hw + _arr.shape[2:], dtype=_arr.dtype)
                h, w = min(lh, vol_hw[0]), min(lw, vol_hw[1])
                fitted[:h, :w] = _arr[:h, :w]
                setattr(self, _name, fitted)

        # Pre-calculate valid coordinates
        mask_mtime = (
            int(os.path.getmtime(mask_path))
            if mask_path and os.path.exists(mask_path)
            else 0
        )
        labels_mtime = (
            int(os.path.getmtime(labels_path))
            if labels_path and os.path.exists(labels_path)
            else 0
        )

        import hashlib

        # Never a bare relative filename: that saved the cache into whatever
        # directory the process was launched from.
        uri_hash = hashlib.md5(volume_uri.encode()).hexdigest()[:8]
        cache_path = os.path.join(
            self.volume.cache_dir,
            # "grid": computed on the label/mask as fitted to the volume grid; older
            # caches came from the unfitted arrays.
            f"valid_coords_villa_grid_{uri_hash}_{self.patch_size}_{mask_mtime}_{labels_mtime}_{1 if require_ink else 0}_{self.min_mask_ratio}_{self.min_ink_ratio}.npy",
        )

        if patches_json and os.path.exists(patches_json):
            print(f"Loading valid coordinates from JSON patch catalog: {patches_json}")
            import json

            with open(patches_json) as f:
                patch_data = json.load(f)
            self.valid_coords = np.array(
                [[p["y"], p["x"]] for p in patch_data.get("patches", [])]
            )
        elif os.path.exists(cache_path):
            self.valid_coords = np.load(cache_path)
        else:
            print(
                f"Finding valid coordinates (require_ink={require_ink}) for {volume_uri} using Villa find_valid_patches..."
            )

            from .patch_catalog import find_valid_patches

            # If require_ink is True, use labels for both bbox and fraction
            # If require_ink is False, use mask to find foreground patches
            if self.require_ink and self.labels is not None:
                target_array = self.labels
                lbl_thresh = self.min_ink_ratio
            elif self.mask is not None:
                target_array = self.mask
                lbl_thresh = self.min_mask_ratio
            else:
                target_array = np.ones((self.shape[1], self.shape[2]), dtype=np.uint8)
                lbl_thresh = 0.0

            results = find_valid_patches(
                label_arrays=[target_array],
                label_names=[volume_uri],
                patch_size=(self.patch_size, self.patch_size),
                bbox_threshold=self.min_mask_ratio,
                label_threshold=lbl_thresh,
                valid_patch_find_resolution=0,  # Use full-res in-memory arrays directly
            )

            self.valid_coords = []
            for patch in results["fg_patches"]:
                pos = patch["start_pos"]
                if len(pos) == 3:
                    z, y, x = pos
                    self.valid_coords.append((y, x))
                elif len(pos) == 2:
                    y, x = pos
                    self.valid_coords.append((y, x))

            if not self.valid_coords:
                print(
                    "  WARNING: No patches found. Retrying with any non-zero pixels..."
                )
                results_fallback = find_valid_patches(
                    label_arrays=[target_array],
                    label_names=[volume_uri],
                    patch_size=(self.patch_size, self.patch_size),
                    bbox_threshold=0.01,
                    label_threshold=0.01,
                    valid_patch_find_resolution=0,
                )
                for patch in results_fallback["fg_patches"]:
                    pos = patch["start_pos"]
                    if len(pos) == 3:
                        z, y, x = pos
                        self.valid_coords.append((y, x))
                    elif len(pos) == 2:
                        y, x = pos
                        self.valid_coords.append((y, x))

                # No silent (0, 0) stand-in: it was cached, and 203 logged runs
                # validated (and selected models) on that single corner patch.
                if not self.valid_coords:
                    raise ValueError(
                        f"no {self.patch_size}px patch of {volume_uri} has "
                        f"{'ink' if self.require_ink and self.labels is not None else 'mask'} "
                        "coverage, even at the relaxed 1% thresholds; check the "
                        "label/mask alignment and require_ink"
                    )

            self.valid_coords = np.array(self.valid_coords, dtype=np.int32)
            print(f"  Found {len(self.valid_coords)} valid patches.")
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            np.save(cache_path, self.valid_coords)

        print(
            f"Initialized Dataset: Volume {self.shape}, Valid Patches {len(self.valid_coords)}, is_unlabeled={self.is_unlabeled}"
        )

    def _apply_lasagna_flattening(self, patch_vol):
        """Per-pixel surface flattening for papyrus CT patches.

        For each (y, x) column, estimate the local Z-position of the
        papyrus surface as a softmax-weighted argmax of intensity along
        Z, smooth the surface, then 3D-grid_sample so every column is
        re-centered on its local surface. This reduces inter-column Z
        misalignment that confuses ink models trained on flat-2D labels.

        Accepts [Z, H, W] (3D) or [C, Z, H, W] (4D) tensors and returns
        the same shape. Falls back to the unmodified patch_vol if
        use_lasagna is False, the volume is too thin (D < 3), or the
        warp raises an exception. Strict reads reject a requested warp that
        cannot run instead of returning an unwarped sample.
        """
        if not self.use_lasagna:
            return patch_vol
        if patch_vol.shape[-3] < 3:
            if getattr(self, "strict_reads", False):
                raise RuntimeError("Lasagna flattening requires at least 3 slices")
            return patch_vol
        try:
            is_3d = patch_vol.dim() == 3
            vol = patch_vol.unsqueeze(0) if is_3d else patch_vol  # [C, Z, H, W]
            C, Z, H, W = vol.shape
            device, dtype = vol.device, vol.dtype

            # 1. Surface estimation: softmax-weighted Z index, averaged across channels.
            vol_f = vol.float() if dtype == torch.uint8 else vol
            intensity = vol_f.mean(dim=0)  # [Z, H, W]
            z_indices = torch.arange(Z, device=device, dtype=torch.float32).view(
                Z, 1, 1
            )
            weights = torch.nn.functional.softmax(intensity, dim=0)  # [Z, H, W]
            z_surface = (weights * z_indices).sum(dim=0)  # [H, W]

            # Smooth surface to suppress pixel-level noise from CT artifacts.
            z_surface = z_surface.view(1, 1, H, W)
            z_surface = torch.nn.functional.avg_pool2d(
                z_surface, kernel_size=5, stride=1, padding=2
            ).view(H, W)

            z_center = (Z - 1) / 2.0

            if dtype == torch.uint8:
                # By absolute path, not a relative sys.path entry: that only resolved
                # from the repository root (elsewhere the except below silently
                # disabled flattening) and shadowed ~90 generic module names.
                from vesuvius_autoresearch.core.villa_modules import load_villa_leaf

                grid_sample_3d_u8 = load_villa_leaf(
                    "lasagna/grid_sample_3d_u8.py"
                ).grid_sample_3d_u8

                z_offset = z_surface - z_center  # absolute coords
                z_offset = z_offset.unsqueeze(0).expand(Z, -1, -1)  # [Z, H, W]

                z_grid, y_grid, x_grid = torch.meshgrid(
                    torch.arange(Z, device=device, dtype=torch.float32),
                    torch.arange(H, device=device, dtype=torch.float32),
                    torch.arange(W, device=device, dtype=torch.float32),
                    indexing="ij",
                )
                new_z = z_grid + z_offset
                grid = torch.stack([x_grid, y_grid, new_z], dim=-1).unsqueeze(0)

                offset = torch.tensor(
                    [0.0, 0.0, 0.0], device=device, dtype=torch.float32
                )
                inv_scale = torch.tensor(
                    [1.0, 1.0, 1.0], device=device, dtype=torch.float32
                )

                warped = grid_sample_3d_u8(vol, grid, offset, inv_scale)
            else:
                # 2. Build sampling grid in normalized [-1, 1] coords.
                z_offset = (z_surface - z_center) * (2.0 / max(1, Z - 1))  # [H, W]
                z_offset = z_offset.unsqueeze(0).expand(Z, -1, -1)  # [Z, H, W]

                z_grid, y_grid, x_grid = torch.meshgrid(
                    torch.linspace(-1.0, 1.0, Z, device=device, dtype=dtype),
                    torch.linspace(-1.0, 1.0, H, device=device, dtype=dtype),
                    torch.linspace(-1.0, 1.0, W, device=device, dtype=dtype),
                    indexing="ij",
                )
                new_z = z_grid + z_offset
                # grid_sample expects (x, y, z) order in the last dim.
                grid = torch.stack([x_grid, y_grid, new_z], dim=-1).unsqueeze(
                    0
                )  # [1, Z, H, W, 3]

                warped = torch.nn.functional.grid_sample(
                    vol.unsqueeze(0),
                    grid,
                    mode="bilinear",
                    padding_mode="border",
                    align_corners=True,
                ).squeeze(0)  # [C, Z, H, W]

            if (
                not isinstance(warped, torch.Tensor)
                or warped.shape != vol.shape
                or warped.dtype != vol.dtype
                or warped.device != vol.device
                or not torch.isfinite(warped).all()
            ):
                raise ValueError("Lasagna warp returned invalid shape, dtype or values")
            if is_3d:
                warped = warped.squeeze(0)
            return warped
        except Exception as exc:
            if getattr(self, "strict_reads", False):
                raise RuntimeError(
                    f"Lasagna flattening failed for {self.volume.uri}: {type(exc).__name__}: {exc}"
                ) from exc
            _warn_limited(
                "lasagna_warp_failed",
                f"Lasagna flattening failed for {self.volume.uri}; returning unwarped patch: {type(exc).__name__}: {exc}",
            )
            return patch_vol

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
        if getattr(self, "jitter", True):
            # Large jitter so non-overlapping grid centers from Villa provide continuous coverage
            half_p = self.patch_size // 2
            y0 = max(
                0,
                min(
                    self.shape[1] - self.patch_size,
                    y0 + rng.randint(-half_p, half_p + 1),
                ),
            )
            x0 = max(
                0,
                min(
                    self.shape[2] - self.patch_size,
                    x0 + rng.randint(-half_p, half_p + 1),
                ),
            )

        z_depth = self.shape[0]
        z_request = min(self.num_layers, z_depth)
        z_range = z_depth - z_request
        z0 = rng.randint(0, z_range + 1) if z_range > 0 else 0

        try:
            if isinstance(self.volume, FastVesuviusVolume):
                patch_vol = self.volume.get_raw_patch(
                    z0, y0, x0, z_request, self.patch_size, self.patch_size
                )
            else:
                patch_vol = self.volume[
                    z0 : z0 + z_request,
                    y0 : y0 + self.patch_size,
                    x0 : x0 + self.patch_size,
                ]

            # patch_vol = patch_vol.to(self.device, non_blocking=True)

            # Priority J: Apply Lasagna flattening
            patch_vol = self._apply_lasagna_flattening(patch_vol)

            # Normalize after flattening
            if patch_vol.dtype == torch.uint8:
                patch_vol = patch_vol.float() / 255.0
            elif patch_vol.dtype == torch.int32:  # previously uint16
                patch_vol = patch_vol.float() / 65535.0
            else:
                patch_vol = patch_vol.float()  # floating volumes (checked in __init__)

            if self.use_ridges:
                patch_vol = self._compute_ridges(patch_vol)
            else:
                patch_vol = patch_vol.unsqueeze(0)  # [1, Z, H, W]

            if self.labels is not None and not self.is_unlabeled:
                patch_label = torch.tensor(
                    np.array(
                        self.labels[
                            y0 : y0 + self.patch_size, x0 : x0 + self.patch_size
                        ],
                        copy=False,
                    ),
                    dtype=torch.float32,
                )
            else:
                patch_label = torch.zeros(
                    (self.patch_size, self.patch_size), dtype=torch.float32
                )
            # 3rd return: per-patch fiber target. Always [1, 1, H, W] (z is
            # singleton — train.py expects target_fiber to be z-collapsed to
            # match `torch.mean(out_fiber, dim=2, keepdim=True)`). For
            # source="sobel_z" this is a zero placeholder; train.py computes
            # the real Sobel-Z target on the GPU side. For source="frangi"
            # we compute Frangi vesselness on the CT channel (CPU, ~86ms/patch
            # parallelized by dataloader workers) and z-mean to collapse.
            patch_fiber = self._compute_fiber_target(patch_vol)
            return patch_vol, patch_label, patch_fiber
        except Exception as e:
            if getattr(self, "strict_reads", False):
                raise RuntimeError(
                    f"failed to read labeled patch {idx} from {self.volume.uri}: {e}"
                ) from e
            _warn_limited(
                "labeled_zero_patch",
                f"returning zero labeled patch for sample {idx} from {self.volume.uri}: {type(e).__name__}: {e}",
            )
            c = 2 if self.use_ridges else 1
            return (
                torch.zeros(c, self.num_layers, self.patch_size, self.patch_size),
                torch.zeros(self.patch_size, self.patch_size),
                torch.zeros(1, 1, self.patch_size, self.patch_size),
            )

    def _compute_fiber_target(self, patch_vol):
        """Return [1, 1, H, W] fiber target. Sobel-Z source = zeros (train.py
        will compute the real Sobel-Z on GPU); Frangi source = on-the-fly
        Frangi vesselness z-collapsed via mean."""
        if self.target_fiber_source != "frangi":
            return torch.zeros(
                (1, 1, self.patch_size, self.patch_size), dtype=torch.float32
            )
        try:
            # Take CT channel only (index 0): patch_vol is [C, Z, H, W] or [Z, H, W]
            ct = patch_vol[0] if patch_vol.dim() == 4 else patch_vol
            ct_np = ct.detach().cpu().numpy().astype(np.float32)
            v_2d = frangi_vesselness_zcollapsed(ct_np, sigma=self.target_fiber_sigma)
            if (
                v_2d.shape != (self.patch_size, self.patch_size)
                or not np.isfinite(v_2d).all()
            ):
                raise ValueError("Frangi target returned invalid shape or values")
            return torch.from_numpy(v_2d).unsqueeze(0).unsqueeze(0)  # [1, 1, H, W]
        except Exception as exc:
            if getattr(self, "strict_reads", False):
                raise RuntimeError(
                    f"Frangi target compute failed for {self.volume.uri}: {type(exc).__name__}: {exc}"
                ) from exc
            _warn_limited(
                "frangi_target_failed",
                f"Frangi target compute failed for {self.volume.uri}; using zeros: {type(exc).__name__}: {exc}",
            )
            return torch.zeros(
                (1, 1, self.patch_size, self.patch_size), dtype=torch.float32
            )

    def _compute_ridges(self, patch_vol):
        ridges = ridge_channel(
            patch_vol.cpu().numpy(),
            self.volume.ridge_sigma,
            self.volume.uri,
            strict=getattr(self, "strict_reads", False),
        )
        return torch.stack([patch_vol, ridges.to(patch_vol.dtype)], dim=0)


class VesuviusS3Dataset(torch.utils.data.Dataset):
    def __init__(
        self,
        uri,
        patch_size=32,
        num_layers=16,
        seed=None,
        cache_dir=None,
        use_ridges=False,
        ridge_sigma=2.0,
        use_lasagna=False,
        is_unlabeled=True,
    ):
        # use_lasagna accepted for API parity with VesuviusLabeledDataset
        # (train.py's get_dataloader passes it unconditionally). The S3Dataset
        # is used for unlabeled volumes (UA-MT) where surface flattening
        # wasn't wired in. Real Lasagna lives only in the labeled dataset.
        self.uri = uri
        self.patch_size = patch_size
        self.seed = seed
        self.cache_dir = cache_dir
        self.use_ridges = use_ridges
        self.ridge_sigma = ridge_sigma
        self.use_lasagna = use_lasagna
        self.is_unlabeled = is_unlabeled

        self.volume = FastVesuviusVolume(
            uri, cache_dir=cache_dir, use_ridges=use_ridges, ridge_sigma=ridge_sigma
        )
        self.shape = self.volume.shape
        self.num_layers = min(num_layers, self.shape[0])

        stride = patch_size // 2
        self.valid_coords = []
        for y in range(0, self.shape[1] - patch_size, stride):
            for x in range(0, self.shape[2] - patch_size, stride):
                self.valid_coords.append((y, x))
        self.valid_coords = np.array(self.valid_coords, dtype=np.int32)
        print(
            f"Initialized S3 Dataset: Volume {self.shape}, Patches {len(self.valid_coords)}, is_unlabeled={self.is_unlabeled}"
        )

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
            patch = self.volume[
                z0 : z0 + z_request,
                y0 : y0 + self.patch_size,
                x0 : x0 + self.patch_size,
            ]
            if not self.use_ridges:
                patch = patch.unsqueeze(0)
            return patch, torch.zeros(
                (self.patch_size, self.patch_size), dtype=torch.float32
            )
        except Exception as exc:
            _warn_limited(
                "s3_zero_patch",
                f"returning zero S3 patch for sample {idx} from {self.uri}: {type(exc).__name__}: {exc}",
            )
            c = 2 if self.use_ridges else 1
            return torch.zeros(
                c, self.num_layers, self.patch_size, self.patch_size
            ), torch.zeros(self.patch_size, self.patch_size)
