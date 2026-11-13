"""Write the <name>__stats.json that make_submission_image.py reads, from the published sidecar.

Usage: stats_from_sidecar.py SIDECAR.json SURFACE_NAME OUT.json

The repo's ensemble_maps.py pools these numbers over 31 depths (496 GPU jobs). The sidecar records
every one of them, so the d = +1 image can be rebuilt with the published normalisation from the
d = +1 maps alone. Schema as ensemble_maps.py writes it.
"""

import json
import sys

sidecar = json.load(open(sys.argv[1]))
norm = sidecar["ink"]["normalisation"]
depths = list(range(-15, 16))
models = {
    name: {
        "model": name,
        "depths": depths,
        **{k: m[k] for k in ("p1", "p99_5", "mean", "sd")},
    }
    for name, m in norm["per_model"].items()
}
shape = sidecar["ct"]["shape"]
stats = {
    "surface": sys.argv[2],
    "H": shape[1],
    "W": shape[2],
    "ct": {
        "p1": sidecar["ct"]["stretch"]["lo"],
        "p99_5": sidecar["ct"]["stretch"]["hi"],
        "layers": [18, 48],
    },
    "models": models,
    "ensemble": {
        "models": norm["models"],
        "depths": depths,
        "p1": norm["ensemble_stretch"]["p1"],
        "p99_5": norm["ensemble_stretch"]["p99_5"],
    },
    "source": "published sidecar values (kill test stage A), not a depth sweep run here",
}
json.dump(stats, open(sys.argv[3], "w"), indent=1)
print(json.dumps({k: v for k, v in stats.items() if k != "models"}))
