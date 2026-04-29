import ctypes
import os
import numpy as np

# Load the shared library
_lib_path = os.path.join(os.path.dirname(__file__), 'libvesuvius.so')
_lib = ctypes.CDLL(_lib_path)

# Define structs
class ZarrCompressorSettings(ctypes.Structure):
    _fields_ = [
        ("blocksize", ctypes.c_int32),
        ("clevel", ctypes.c_int32),
        ("cname", ctypes.c_char * 32),
        ("id", ctypes.c_char * 32),
        ("shuffle", ctypes.c_int32),
    ]

class ZarrMetadata(ctypes.Structure):
    _fields_ = [
        ("shape", ctypes.c_int32 * 3),
        ("chunks", ctypes.c_int32 * 3),
        ("compressor", ZarrCompressorSettings),
        ("dtype", ctypes.c_char * 8),
        ("fill_value", ctypes.c_int32),
        ("order", ctypes.c_char),
        ("zarr_format", ctypes.c_int32),
        ("dimension_separator", ctypes.c_char),
    ]

class _Chunk(ctypes.Structure):
    _fields_ = [
        ("dims", ctypes.c_int * 3),
        # data follows...
    ]

# Function signatures
_lib.vs_zarr_parse_zarray.argtypes = [ctypes.c_char_p]
_lib.vs_zarr_parse_zarray.restype = ZarrMetadata

_lib.vs_zarr_read_chunk.argtypes = [ctypes.c_char_p, ZarrMetadata]
_lib.vs_zarr_read_chunk.restype = ctypes.POINTER(_Chunk)

_lib.vs_chunk_free.argtypes = [ctypes.POINTER(_Chunk)]
_lib.vs_chunk_free.restype = None

class FastLocalVolume:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        zarray_path = os.path.join(self.path, ".zarray")
        if not os.path.exists(zarray_path):
            raise FileNotFoundError(f"Missing .zarray at {zarray_path}")
            
        self.metadata = _lib.vs_zarr_parse_zarray(zarray_path.encode('utf-8'))
        
        self.shape = tuple(self.metadata.shape)
        self.chunks = tuple(self.metadata.chunks)
        self.sep = self.metadata.dimension_separator.decode('utf-8')
        if not self.sep or self.sep == '\x00':
            self.sep = '.'

    def get_chunk(self, z, y, x):
        """Fetch a pre-defined zarr chunk by its grid index (not voxel coordinates)."""
        chunk_name = f"{z}{self.sep}{y}{self.sep}{x}"
        chunk_path = os.path.join(self.path, chunk_name).encode('utf-8')
        
        chunk_ptr = _lib.vs_zarr_read_chunk(chunk_path, self.metadata)
        
        if not chunk_ptr:
            raise RuntimeError(f"Failed to read zarr chunk {chunk_name}")
            
        try:
            # size is the total number of elements according to chunk metadata
            depth, height, width = self.metadata.chunks
            size = depth * height * width
            
            data_addr = ctypes.addressof(chunk_ptr.contents) + ctypes.sizeof(ctypes.c_int * 3)
            float_array = (ctypes.c_float * size).from_address(data_addr)
            arr = np.ctypeslib.as_array(float_array).copy()
            
            arr = arr.reshape((depth, height, width))
            return arr
            
        finally:
            _lib.vs_chunk_free(chunk_ptr)
