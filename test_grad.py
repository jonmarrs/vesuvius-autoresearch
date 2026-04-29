import numpy as np
try:
    x = np.random.rand(2, 64, 64)
    np.gradient(x, axis=0, edge_order=2)
except ValueError as e:
    print(f"Caught expected error: {e}")
