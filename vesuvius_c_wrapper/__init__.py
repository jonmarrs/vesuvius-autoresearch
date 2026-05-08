"""Compatibility hooks for the official ScrollPrize/villa Vesuvius-C code."""

from .vesuvius_c import FastLocalVolume, VesuviusCUnavailable, VesuviusVolume

__all__ = ["FastLocalVolume", "VesuviusCUnavailable", "VesuviusVolume"]
