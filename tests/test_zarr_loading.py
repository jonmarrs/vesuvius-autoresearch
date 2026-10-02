import os

import numpy as np
import pytest
import tensorstore as ts


@pytest.mark.skipif(os.environ.get("VESUVIUS_TEST_S3") != "1", reason="set VESUVIUS_TEST_S3=1 for the live S3 integration test")
def test_load():
    # Attempt to open the Vesuvius Zarr volume from S3
    # Based on metadata, the bucket is vesuvius-challenge-open-data
    # Path: samples/PHercParis4/volumes/20230206171837-7.910um-54keV-masked.zarr/

    bucket = "vesuvius-challenge-open-data"
    path = "PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/"

    print(f"Opening s3://{bucket}/{path} ...")

    dataset = ts.open(
        {
            "driver": "zarr",
            "kvstore": {
                "driver": "s3",
                "bucket": bucket,
                "path": path,
                "aws_region": "us-east-1",
                "aws_credentials": {"type": "anonymous"},
            },
        }
    ).result(timeout=30)

    print("Dataset opened successfully!")
    print(f"Shape: {dataset.shape}")
    print(f"Dtype: {dataset.dtype}")

    # Read a small 3D chunk from the middle
    # Z, Y, X
    z_mid, y_mid, x_mid = [s // 2 for s in dataset.shape]
    chunk_size = 16

    print(f"Reading chunk at Z={z_mid}, Y={y_mid}, X={x_mid} ...")
    chunk = (
        dataset[
            z_mid : z_mid + chunk_size,
            y_mid : y_mid + chunk_size,
            x_mid : x_mid + chunk_size,
        ]
        .read()
        .result(timeout=30)
    )

    print(f"Chunk read successfully! Shape: {chunk.shape}")
    print(f"Mean value: {np.mean(chunk):.4f}")

    assert chunk.shape == (chunk_size,) * 3


def test_tensorstore_local_zarr_roundtrip(tmp_path):
    data = np.arange(4 * 6 * 8, dtype=np.uint8).reshape(4, 6, 8)
    dataset = ts.open({
        "driver": "zarr",
        "kvstore": {"driver": "file", "path": str(tmp_path / "volume")},
        "metadata": {"shape": list(data.shape), "chunks": [2, 3, 4], "dtype": "|u1"},
        "create": True,
    }).result(timeout=10)
    dataset.write(data).result(timeout=10)
    np.testing.assert_array_equal(dataset[1:3, 2:5, 3:7].read().result(timeout=10), data[1:3, 2:5, 3:7])


if __name__ == "__main__":
    test_load()
