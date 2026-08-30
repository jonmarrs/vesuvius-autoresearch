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

---

## Follow-up, same day: the signal survives, and the innocent explanation does not

**Restricting to quads the metric ACCEPTS changes almost nothing.**

| | all targeted quads | satisfied quads only |
|---|---:|---:|
| patches | 38,195 | 35,318 |
| 1 winding | 92.4% | 92.5% |
| 2 windings | 7.4% | 7.4% |
| minority fraction p99 | 0.4273 | 0.4250 |
| minority > 0.20 | 3.76% | 3.74% |

So this is not assignment noise in unfitted regions: the satisfaction metric **accepts** quads sitting
on two different windings inside one patch.

**The distribution is bimodal, which retires run length as the statistic.** 90% of patches have zero
minority quads; when a patch does split, the minority side is typically 10 to 45% of it. That is why
the pre-registered boundary-length sweep barely moved the flag rate (7.6% to 6.2% across
`L in {1..16}`): the split is not a thin filament to filter away, it is two large coherent regions.
Minority fraction is the right measure and boundary length was the wrong one.

**The obvious innocent explanation is largely ruled out.** `target_raw_shifted_all` carries
`branch_offset`, so a patch wrapping past the theta=0 cut legitimately spans two winding indices,
which would produce exactly this bimodality. But a branch cut partitions a patch along a curve
spanning its full extent, so it should appear as a full-height band:

```
winding span (max-min) among 2+ winding patches   span 1 = 98.2%
minority region spans a contiguous column range    95.2%
minority region covers ALL rows (full-height band)  0.6%   <- decisive
median coverage                                    27% of columns, 48% of rows
```

**Only 0.6% are full-height bands.** The minority regions are localized blobs, which is not a branch
cut and is what a local sheet switch looks like.

## What is and is not established

**Established:** a converged fit contains ~7.4% of patches where the satisfaction metric accepts
quads on two adjacent windings, in localized regions rather than full-extent partitions, and this is
not explained by the theta=0 branch cut or by unfitted-region assignment noise.

**Not established:** that these are sheet switches. Localized two-winding regions are *consistent*
with switches and inconsistent with the one innocent mechanism tested, which is weaker than a
positive identification. Other mechanisms have not been enumerated, let alone excluded.

**Method note.** Everything after the first flag-rate table is exploratory analysis on the same fit
the detector will later be validated against. It informed the design (minority fraction rather than
boundary length), which is legitimate development, but it means the design was chosen with these
distributions in view. The design must be frozen before the injection study runs, and the write-up
must say that the statistic was selected after seeing baseline data.
