#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Tifxyz Surface Wrapper
Provides a bridge to official Villa Tifxyz data formats for volumetric coordinate handling.
"""

import os
import sys

import numpy as np

try:
    from vesuvius.tifxyz import Tifxyz, read_tifxyz

    TIFXYZ_AVAILABLE = True
except ImportError:
    TIFXYZ_AVAILABLE = False


def load_tifxyz_surface(path: str):
    """
    Loads an official Tifxyz surface from a directory.
    """
    if not TIFXYZ_AVAILABLE:
        print("Error: 'vesuvius' package with Tifxyz support not found.")
        return None

    return read_tifxyz(path)


def extract_patch_coords(surface: Tifxyz, y: int, x: int, h: int, w: int):
    """
    Extracts the (X, Y, Z) world coordinates for a 2D patch on the surface.
    Useful for mapping 2D model predictions back to the 3D volume.
    """
    if surface is None:
        return None

    # Returns (x, y, z, valid) as a tuple of 2D arrays
    coords = surface[y : y + h, x : x + w]
    return coords


if __name__ == "__main__":
    if TIFXYZ_AVAILABLE:
        print("Tifxyz module is available.")
        # Example: surface = load_tifxyz_surface("local_data/segments/segment1")
    else:
        print(
            "Tifxyz module NOT available. Please run 'uv pip install ./villa/vesuvius'."
        )
