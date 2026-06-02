import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import smoke test
import scripts.smoke_test as st

for name, fn in st.TESTS:
    print(f"Running {name}...")
    try:
        t0 = time.perf_counter()
        fn()
        print(f"PASS: {name} ({time.perf_counter() - t0:.2f}s)")
    except Exception as e:
        print(f"FAIL: {name}: {e}")
