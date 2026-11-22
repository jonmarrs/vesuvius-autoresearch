"""List the chunks of one zarr array in the public open-data bucket for a range of z chunk indices.

Usage: s3_plan.py KEY_PREFIX_OF_ARRAY Z_CHUNK_LO Z_CHUNK_HI [OUT.tsv]
Anonymous HTTPS listing only. Prints the count and total bytes; with OUT.tsv writes "key<TAB>size" lines.
"""

import re
import sys
import urllib.parse
import urllib.request

BUCKET = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"


def list_prefix(prefix):
    token = None
    while True:
        query = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            query["continuation-token"] = token
        with urllib.request.urlopen(
            BUCKET + "?" + urllib.parse.urlencode(query), timeout=60
        ) as response:
            text = response.read().decode()
        for key, size in re.findall(r"<Key>([^<]+)</Key>.*?<Size>(\d+)</Size>", text):
            yield key, int(size)
        match = re.search(
            r"<NextContinuationToken>([^<]+)</NextContinuationToken>", text
        )
        if not match:
            return
        token = match.group(1)


def main():
    prefix, lo, hi = sys.argv[1].rstrip("/") + "/", int(sys.argv[2]), int(sys.argv[3])
    rows = []
    for z in range(lo, hi + 1):
        got = list(list_prefix(f"{prefix}{z}/"))
        rows.extend(got)
        print(
            f"z chunk {z}: {len(got)} chunks, {sum(s for _, s in got) / 1e9:.3f} GB",
            flush=True,
        )
    print(f"TOTAL {len(rows)} chunks, {sum(s for _, s in rows) / 1e9:.3f} GB")
    if len(sys.argv) > 4:
        with open(sys.argv[4], "w") as handle:
            for key, size in rows:
                handle.write(f"{key}\t{size}\n")


if __name__ == "__main__":
    main()
