"""Download the objects listed in plan files from the public open-data bucket. Anonymous HTTPS GET only.

Usage: s3_fetch.py STRIP_PREFIX DEST_DIR PLAN.tsv [PLAN.tsv ...] [--meta KEY ...]

Each plan line is "key<TAB>size". An object lands at DEST_DIR/<key without STRIP_PREFIX>. A file already present
with the listed size is kept. --meta keys are small metadata objects; one that does not exist is reported and skipped.
Exit status 1 if any listed object could not be fetched at its listed size.
"""

import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BUCKET = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"
THREADS = 12
local = threading.local()


def target(dest, strip, key):
    if not key.startswith(strip):
        raise SystemExit(f"key outside the prefix: {key}")
    path = os.path.normpath(os.path.join(dest, key[len(strip) :]))
    if not path.startswith(os.path.abspath(dest) + os.sep):
        raise SystemExit(f"key escapes the destination: {key}")
    return path


def fetch(dest, strip, key, size):
    path = target(dest, strip, key)
    if size is not None and os.path.exists(path) and os.path.getsize(path) == size:
        return "kept", 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    error = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(
                BUCKET + urllib.parse.quote(key), timeout=120
            ) as response:
                data = response.read()
            if size is not None and len(data) != size:
                raise OSError(f"{len(data)} bytes, listed {size}")
            part = f"{path}.part{threading.get_ident()}"
            with open(part, "wb") as handle:
                handle.write(data)
            os.replace(part, path)
            return "got", len(data)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return "missing", 0
            error = exc
        except OSError as exc:
            error = exc
        time.sleep(2 * (attempt + 1))
    return f"failed: {error}", 0


def main():
    args = sys.argv[1:]
    meta = []
    if "--meta" in args:
        cut = args.index("--meta")
        args, meta = args[:cut], args[cut + 1 :]
    strip, dest, plans = args[0], os.path.abspath(args[1]), args[2:]
    jobs = [(key, None) for key in meta]
    for plan in plans:
        with open(plan) as handle:
            for line in handle:
                key, size = line.rstrip("\n").split("\t")
                jobs.append((key, int(size)))
    print(
        f"{len(jobs)} objects, {sum(s or 0 for _, s in jobs) / 1e9:.3f} GB listed",
        flush=True,
    )
    counts, total, bad, start = {}, 0, [], time.time()
    with ThreadPoolExecutor(THREADS) as pool:
        results = pool.map(lambda job: (job, fetch(dest, strip, *job)), jobs)
        for done, ((key, size), (status, got)) in enumerate(results, 1):
            name = status.split(":")[0]
            counts[name] = counts.get(name, 0) + 1
            total += got
            if name == "failed" or (name == "missing" and size is not None):
                bad.append((key, status))
            elif name == "missing":
                print(f"no such metadata object: {key}", flush=True)
            if done % 2000 == 0:
                print(
                    f"{done}/{len(jobs)} {counts} {total / 1e9:.2f} GB {time.time() - start:.0f} s",
                    flush=True,
                )
    print(
        f"DONE {counts} {total / 1e9:.3f} GB downloaded in {time.time() - start:.0f} s",
        flush=True,
    )
    for key, status in bad[:20]:
        print(f"BAD {key} {status}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
