# Fiber CLI streaming: one public CT cube on CPU

Checked October 30, 2026 UTC / October 29 Pacific. Both ridge and vesselness
filtering produce **byte-identical float32 NPY files** before and after the
streaming change in [PR #295](https://github.com/jonmarrs/vesuvius-autoresearch/pull/295).
All four invocations complete under a **4 GiB address-space limit**. This is
an operational check on real CT, not a model-quality or native GPU result.

| Filter | Historical CLI peak RSS | Streaming peak RSS | Historical CLI wall time | Streaming wall time |
| --- | ---: | ---: | ---: | ---: |
| Ridges | 589.8 MiB | 472.7 MiB | 30.74 s | 42.34 s |
| Vesselness | 576.3 MiB | 472.9 MiB | 27.32 s | 29.62 s |

Observed peak RSS is about 18–20% lower on this cube. Each case ran once,
historical before streaming, with caches unflushed. A CPU smoke check overlapped
part of ridge streaming. The wall times include process startup and output
writes, and exclude download and TIFF conversion. They are recorded observations,
not controlled comparative speed estimates. The streaming path does a separate
blockwise Gaussian-range pass. No general speedup or slowdown is established.
RSS is physical process memory; it is distinct from the address-space ceiling.

## Input and source identity

The input is the published 256³ uint8 Scroll-1 CT cube
`s1_00497_01497_03997_256`, at 7.91 µm, from
[Villa's fiber-skeletons Dataset001](https://dl.ash2txt.org/datasets/fiber-skeletons/Dataset001_sk-fibers-20250124/imagesTr/s1_00497_01497_03997_256_0000.tif).
The TIFF is 16,819,802 bytes, SHA-256
`0d38453cc37157f46b180e3711172e99f56eb216948eb6755eca0019ad0dbf60`.
It was downloaded once and converted losslessly to NPY before timing. Both
variants read that same NPY with `--device cpu --tiled --block-size 64 --halo 16`.
No predictions, masks or labels were substituted for CT.

Current source: `ebf29aab3eed340bf24fa70ec9f0edf7bea315dd`.
The historical variant executes the CLI body extracted from
`f2efeda9dbb246b22952744c6fdf8d849e22e94f` with the current package's
byte-identical `detection.py` and package imports. It is not a separate
historical dependency-environment reproduction. The harness refuses different
filter math. It captures source, input, CLI-body and harness hashes and checks
them again after the complete pass. No source or input changed.

Runtime: Linux x86-64, Python 3.10.21, NumPy 2.2.6, SciPy 1.15.3. CUDA was
masked, and OpenMP/OpenBLAS/MKL were each set to one thread. Each CLI ran in a
fresh measurement wrapper, so child peak RSS is not cumulative across cases.
All outputs have the required shape/dtype and finite values. Equal full-file
SHA-256 values establish identical serialization as well as voxel values.

The [JSON record](evidence/fiber_cli_public_ct_cpu_2026-10-30.json) retains all
commands, measurements and hashes. Its
[raw archive](evidence/fiber_cli_public_ct_cpu_2026-10-30_raw.zip) contains the
frozen harness, historical CLI body, download record, requests, measurements
and logs (16 files). The large input/output arrays remain in the local work
directory; the public input and hashes allow reproduction.

## Reproduce

Download the TIFF linked above to a new scratch directory. With the recorded
source and an existing environment containing NumPy, SciPy and tifffile:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-chain-env/bin/python repro/fibers/verify_filter_cli_public_ct.py \
  --repo /workspace/vesuvius-october-final \
  --tiff /workspace/shared/fiber-cli-public-ct-2026-10-30/ct.tif \
  --out /workspace/shared/fiber-cli-public-ct-2026-10-30/measured
```

The recorded run exited zero. Adapt local paths and use a new output directory. The
[frozen harness](../repro/fibers/verify_filter_cli_public_ct.py) installs nothing
and downloads nothing. A changed source/runtime needs a new dated record.
It gives each case a 180-second timeout, retains failed exits, and never retries
them to replace the recorded observation.

This check does not cover larger scans, float CT on real data, cold-cache
behavior, previews, CUDA parity, GPU allocator behavior, peak VRAM or downstream
tracing/reading quality. Synthetic regressions separately cover those CPU
artifact and dtype contracts. No active-study measurements were read, no GPU
job was started and no runtime was deployed. The two prepared October filing
answers remain unchanged; this adds no Villa merge credit.
