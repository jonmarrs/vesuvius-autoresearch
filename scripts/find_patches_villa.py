#!/usr/bin/env python3
"""
Wrapper script for Villa's intelligent patch extraction.

This script wraps Villa's intelligent patch extraction utility, which filters
patches by label density, blank fraction, and class balance.
"""

import os
import sys

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath("villa/vesuvius/src"))
    from vesuvius.models.preprocessing.patches.cli import main

    main()
