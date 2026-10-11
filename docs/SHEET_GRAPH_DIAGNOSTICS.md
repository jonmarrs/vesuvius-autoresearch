# Sheet-graph diagnostics

This tool estimates relative, unwrapped angles in a small explicit graph. It
does not stitch surfaces, convert a Thaumato graph, generate meshes, render CT,
measure legibility or establish ground truth/prize eligibility. Graph confidence
factors and walk statistics are descriptive heuristics.

## Explicit input

Provide UTF-8 JSON with exactly these fields:

~~~json
{
  "schema_version": 1,
  "angle_unit": "degrees",
  "nodes": [{"id": "anchor"}, {"id": "sheet"}, {"id": "unreachable"}],
  "edges": [{"u": "anchor", "v": "sheet", "weight": 0.9, "angle_delta": 20}]
}
~~~

Units must be declared as `degrees` or `radians`; values are never inferred from
an upstream offset or reduced modulo a turn. Each edge states
`f(v) - f(u) = angle_delta`. Its reverse has the negative delta and the same
weight. All endpoints must be declared. This is a simple undirected graph:
duplicate nodes, self edges and duplicate/parallel endpoint pairs are rejected.

Node IDs are nonempty strings of at most 256 characters or integers with
absolute value at most 2^53-1. Booleans and floats are not IDs. Integer `1` and
string `"1"` remain distinct in the output's node list. Node records contain
only `id`; edges require all four fields shown above. Unknown fields, duplicate
JSON keys, empty graphs, malformed records and nonfinite/nonnumeric values fail.

Weights must be real confidence factors in [0, 1]. Zero disables an edge for
reachability and estimation while retaining it in the diagnostic report.
These factors are not calibrated probabilities. Source files must be regular
JSON files, not symlinks. Hard limits: 16 MiB source bytes, 4,096 nodes and 16,384
undirected edges; input is checked before graph construction/estimation.

## Estimate and inspect

~~~bash
.venv/bin/python scripts/sheet_stitcher.py --input-graph my_graph.json --out reports/my_graph_diagnostic --start-node '"anchor"' --start-angle 0 --algorithm max_product
~~~

The anchor fixes the relative gauge; its angle is not an absolute physical
registration. The start-node argument is a JSON ID literal: `7` selects an
integer, while `'"7"'` selects a string. If omitted, the first canonical ID is
the anchor (integers before strings, then ascending numeric/lexicographic order).
An explicitly unknown or null anchor is an error.

The maximum-product estimator runs Dijkstra on negative log weights. It finalizes
a node when the strongest route is popped, allowing a better route to replace
a weaker first discovery. Log costs avoid product underflow. Canonical neighbor
ordering and separate heap ranks make ties deterministic even with mixed ID
types. Angles sum signed deltas along the chosen path. A chosen path can disagree
with other graph edges; residuals expose that disagreement rather than calling
the graph solved.

The bundle contains the exact `source.json` bytes and `estimates.json`. JSON
records source path/stat signature/byte count/SHA-256, source-copy hash, units,
anchor, actual recipe, hard limits, node reachability and estimates, strongest
path cost/parent, and each edge's residual `f(v)-f(u)-angle_delta`. Unreachable
angles and path metadata are null, not zero. Nodes/edges preserve typed IDs;
output edge orientation is canonical and its delta is reversed when needed.

The absolute residual tolerance defaults to 1e-6 in the declared angle unit and
can be set with `--tolerance`. It must be finite and nonnegative. Status is
`inconsistent_reachable_constraints`, `partial_reachability`, or
`consistent_relative_constraints`; counts separately report all nodes, edges,
unreachable nodes, disabled/unreachable/checked edges and violations. These
statuses describe the reachable relative graph constraints, not physical
registration, complete coverage or successful stitching.

## Exploratory random walks

~~~bash
.venv/bin/python scripts/sheet_stitcher.py --input-graph my_graph.json --out reports/my_walk_diagnostic --start-node '"anchor"' --algorithm random_walk --walks 2000 --walk-length 20 --seed 0
~~~

Walks start at the fixed anchor and choose positive edges proportionally to
their weights. Returning to the anchor resets the running angle to the reference;
the reported anchor stays fixed. Each sampled node receives the lower observed
median, using order index floor((n-1)/2). Its descriptive IQR is the difference
between order indices floor(3(n-1)/4) and floor((n-1)/4). Order statistics avoid
overflow from averaging extreme finite values. Counts and methods distinguish
sampled estimates from the maximum-product fallback for reachable unsampled
nodes. Structurally unreachable nodes remain unknown.

Inconsistent cycles can bias these estimates. Correlated walk visits do not
yield independent measurements, calibrated uncertainty or guaranteed outlier
rejection. Residuals are computed from the resulting walk estimates, not from
the fallback tree. A local NumPy generator preserves caller RNG state; seed and
canonical graph ordering make runs reproducible.

Defaults are 2,000 walks, 20 steps each, seed 0. Hard limits are 10,000 walks,
1,024 steps per walk and 1,000,000 requested total steps. Seed must be an integer
in [0, 2^32-1]. Walk/seed options require `--algorithm random_walk`. Angle sums
or residual/statistic arithmetic that cannot remain finite fail the report.

## Publication and legacy migration

Outputs are new bundle directories, disjoint from the input file. Omitting
`--out` selects a timestamped `sheet_graph` directory under `reports` relative
to the working directory. Existing files/directories, valid/broken symlinks and
source/output aliases are rejected. Absolute inputs/outputs work outside the
checkout. Source copy and finite JSON are staged and read back, then source
bytes/identity are rechecked before one directory rename publishes the bundle.
Failures roll back staging and preserve prior artifacts. Keep sources stable
and serialize writers; this is not an adversarial filesystem snapshot or a
concurrent-writer API.

A valid diagnostic report exits zero, including one that explicitly records
inconsistent constraints or partial reachability. Invalid/missing input,
settings, failed reads/writes, changed sources or an appearing destination exit
nonzero and publish no bundle. There is no implicit dummy/demo graph.

The underscore aliases `--input_graph` and `--output` remain available. The
legacy `viterbi` algorithm/function names alias the corrected maximum-product
diagnostic; metadata uses the actual algorithm name. `SheetGraph` remains
available from the CLI module for Python callers; its construction now enforces
the graph contract. An empty graph raises an error rather than yielding a
successful empty solution.

PKL/bin input/output and the legacy solver sweep are retired. The vendored
Thaumato graph stores edges by node pair with multiple `sheet_offset_k` variants,
unbounded certainty factors and separate degree/turn conventions. The old
adapter treated this as adjacency, guessed missing fields and wrote a nonexistent
node-angle member. No implicit conversion is valid. The old sweep also selected
the newest mesh folder without proving it came from the attempted solver, and
ranked texture variance as if it established winding correctness. Its retained
entry point now returns an explicit failure and launches no producers. Rebuild
any physical integration separately with verified formats, units, provenance
and evaluation; these JSON diagnostics are not solved Thaumato graphs.
