# Baseline signal for a sheet-switch detector: recoverable, and not yet conservative

**2026-08-29.** Measured on the converged baseline fit
(`..._baseline01/checkpoint_fitted.ckpt`), before any injection.

## Feasibility: settled

`satisfaction_metrics.get_patch_satisfied_areas` returns `target_winding_idx_per_patch`, a per-quad
integer winding index that the fit computes on every run and **never persists**. It recovers cleanly
offline from a finished checkpoint, reusing upstream's own loaders
(`load_checkpoint_cpu`, `build_fit_inputs`, `build_transform`) with nothing reimplemented.

```
patches                                        38,442
winding-idx arrays populated                   38,442  (all)
satisfaction pass                              7.99 s
dr per winding (fitted)                        16.173
internal winding discontinuities (4-adjacent)  115,493
patches with >=1 internal jump                 2,914 / 38,442 = 7.6%
```

Arrays are cached (533 MB) so detector iterations do not re-pay the ~130 s load.

Three interface facts cost a spike each, and are recorded so nobody pays for them twice:
`context.verified_patches` is a **dict** keyed by patch id, while `get_patch_satisfied_areas` wants a
**list of patch objects**; input paths must be resolved through `load_scroll_spec` +
`conventional_input_paths` on the dataset root, since `find_inconsistent_windings`'s patches-dir
resolution does not find `outer_shell`; and the parallel patch loader needs
`FIT_SPIRAL_PATCH_LOAD_WORKERS=1` here to avoid a forkserver `ConnectionResetError`.

## The signal clusters, which is the encouraging part

115,493 discontinuities across 2,914 patches is roughly **40 per flagged patch**. Jumps are not
scattered singletons; they form runs, which is what a real switch boundary should look like and what
a run-length filter can exploit.

## But it does not clear the pre-registered bar

Flag rate against minimum connected-boundary size `L`:

| L | patches flagged | rate |
|---:|---:|---:|
| 1 | 2,914 | 7.6% |
| 2 | 2,914 | 7.6% |
| 4 | 2,851 | 7.4% |
| 8 | 2,712 | 7.1% |
| 16 | 2,367 | 6.2% |
| 32 *(not pre-registered)* | 1,665 | 4.3% |

The pre-registered sweep is `L in {1,2,4,8,16}`. **None of those reaches the 5% conservativeness
bar.** `L = 32` does, was not pre-registered, and is **not adopted**: extending a sweep after seeing
the registered values fail is the exact failure the pre-registration exists to prevent.

## A flaw in our own rule, recorded rather than fixed

Rule 3 calls the un-injected flag rate a **false-alarm** rate, which assumes flagged patches are
clean. Sheet switches are a real failure mode corrected by hand in VC3D today, so some of those
2,914 patches are plausibly genuine. With no labelled switches in public data, true and false
detections are not separable in that number: **7.6% is an upper bound on false alarms, not a
measurement of them.**

The rule stands as written. The flaw was found after seeing the baseline, so amending it now would
be tuning the standard to the result. See the post-observation note in
`docs/preregistration/2026-08-29_sheet_switch_detector.md`.

## Where this leaves the September bet

Honestly: **worse than when the plan was written, and known three weeks before the gate.**

The raw within-patch winding-jump signal is recoverable and clusters sensibly, but at every
pre-registered operating point it flags more patches than a tool advertised as *conservative* should.
Either a better signal is needed (the jump geometry, not merely its length), or the honest outcome is
the negative result rule 2 already commits us to publishing.

That is the plan working as intended. The go/no-go gate is 2026-09-15 and this is 2026-08-29.
