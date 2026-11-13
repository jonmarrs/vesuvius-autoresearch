"""Regional sharding preserves coverage/order without allocating the full grid."""

import tracemalloc
from types import SimpleNamespace

import pytest

from vesuvius_autoresearch.core.inference import region_tiles


def _args(height, width, stride, parts=1, part=0):
    return SimpleNamespace(
        height=height, width=width, stride=stride, num_parts=parts, part_id=part
    )


def _expected(height, width, size, stride):
    # A complete regular grid plus an explicit final edge, in row-major order.
    ys = sorted({*range(0, height - size + 1, stride), height - size})
    xs = sorted({*range(0, width - size + 1, stride), width - size})
    return [(y, x) for y in ys for x in xs]


@pytest.mark.parametrize("shape,stride", [((8, 8), 8), ((11, 13), 4), ((19, 25), 3)])
@pytest.mark.parametrize("parts", [1, 2, 5])
def test_shards_preserve_row_major_order_and_partition_every_tile(shape, stride, parts):
    height, width = shape
    full = _expected(height, width, 8, stride)
    observed = {}
    for part in range(parts):
        args = _args(height, width, stride, parts, part)
        expected = full[part::parts]
        if not expected:
            with pytest.raises(ValueError, match="no tiles"):
                region_tiles(args, 8)
            continue
        tiles = region_tiles(args, 8)
        assert list(tiles) == expected
        assert len(tiles) == len(expected) == args.tiles_processed
        assert args.tiles_total == len(full)
        assert tiles[0] == expected[0]
        assert tiles[-1] == expected[-1]
        assert list(tiles[1::2]) == expected[1::2]
        with pytest.raises(IndexError):
            _ = tiles[len(expected)]
        observed.update({part + i * parts: tile for i, tile in enumerate(tiles)})
    assert [observed[i] for i in range(len(full))] == full


def test_shard_planning_has_a_small_memory_footprint():
    args = _args(2000, 2000, 8, 5, 2)
    tracemalloc.start()
    try:
        tiles = region_tiles(args, 32)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert args.tiles_total == 61_009
    assert len(tiles) == len(range(2, 61_009, 5))
    assert peak < 256 * 1024, f"tile planning allocated {peak:,} traced bytes"
