# Vesuvius-C Python Bindings

This package provides highly optimized Python bindings for the official `ScrollPrize/villa/vesuvius-c` library using `ctypes`. 

It bypasses Python's internal memory management overhead to read uncompressed or Blosc2-compressed OME-Zarr blocks directly into NumPy arrays via shared memory allocation and C pointers.

## Features
- Direct C-struct parsing of `.zarray` metadata.
- Zero-copy (or single-copy) memory mapping into NumPy arrays.
- Graceful handling of OME-Zarr multiscale structure and empty dimension separators.

## Prerequisites
```bash
sudo apt-get install -y libcurl4-openssl-dev libblosc2-dev libjson-c-dev
```

## Build
```bash
chmod +x build.sh
./build.sh
```

## Usage
```python
from vesuvius_c_wrapper.vesuvius_c import FastLocalVolume

vol = FastLocalVolume('local_data/PHercParis2Fr47/surface_volume.zarr/0')
chunk = vol.get_chunk(0, 0, 0) # Grabs chunk 0/0/0
print(chunk.shape)
```
