# November 2026 Progress Prize: submission draft

**Draft only. Not submitted.** Deadline: **November 30, 2026, 11:59 p.m. Pacific**.
Use the [official rules](https://scrollprize.org/prizes#progress-prizes) and the
[November submission form](https://docs.google.com/forms/d/e/1FAIpQLSeB6MC_--4UCCEGc3zalX57-uE4puRcE_vJoYJCrEt4uYaaaw/viewform).
This is a narrow bundle of two shipped Villa fixes, not a First Letters submission.

## URL field

The form allows multiple URLs. Try one per line. If the field won't accept both
that way, put the lead PR in the URL field and include the supporting PR URL in
the contribution answer rather than making a second entry.

```text
https://github.com/ScrollPrize/villa/pull/2463
https://github.com/ScrollPrize/villa/pull/2258
```

## Contribution field

I’m submitting two small, merged fixes to Villa’s fitting and fiber-seeding tooling.

1. **Data and inputs.** Villa #2463 was checked at configuration load with Villa's
   two shipped FlowSnap-only presets and focused regression fixtures. No full
   scroll dataset was fitted. Villa #2258 was checked at the CPU fiber-seeding
   stage on published ScrollGT v0.8.1 masks from Scrolls 1, 3 and 5.

2. **Relevance to reading.** A reported error prevented both shipped FlowSnap-only
   presets from starting optimization. Villa #2463 removes that configuration
   blocker in the unwrapping workflow. Villa #2258 corrects seed placement when
   fractional plane spacing is needed across scan resolutions. These checks do
   not establish an improvement in fitting quality, tracing, ink detection,
   or readability.

3. **What works now.** Both FlowSnap-only presets load their intended `snap` loss
   with compatible initialization. The plain preset still needs a non-default
   compatible initialization, and both presets still require a prediction field
   with `pred_dt`. The flag moved from loss weights to arguments; the fitting
   algorithm did not change. Fractional seeding follows the requested global
   grid across tile boundaries. At 52.7333 voxels on one Scroll 1 mask, the
   first three planes changed from z0, z52, z104 to z0, z52, z105. Default
   64-voxel seeding was unchanged.

4. **Evidence.** The Villa review reproduced the old configuration rejection,
   checked both presets and the flag override, and reported seven focused tests
   passing, including two new regressions. It did not run a full fit or export.
   For Villa #2258, the three masks yielded seed counts of 1,589 → 1,590,
   11,213 → 11,175 and 1,154 → 1,151 (at most 0.34% change). The linked PR
   records the CPU comparison, hashes and reproduction steps. On the original
   comparison, the regression suite went from 3 of 20 passing to 20 of 20.

## Review notes (not for pasting)

- [Villa #2463](https://github.com/ScrollPrize/villa/pull/2463) (merged 2026-11-24 Pacific;
  `2026-11-24T14:10:01Z`) is the lead. See the [reported issue](https://github.com/ScrollPrize/villa/issues/2458)
  and the [focused review](https://github.com/ScrollPrize/villa/pull/2463#issuecomment-7049875312).
- [Villa #2258](https://github.com/ScrollPrize/villa/pull/2258) (merged 2026-11-01 Pacific;
  `2026-11-01T14:56:47Z`) is supporting evidence only. It merged after the October
  deadline. Its personal-verification box was unchecked when reviewed; this
  draft does not supply a personal attestation.
- Recheck the current rules and merge states before filing. Keep out unpublished
  or still-eligible research results, mixed reports, and unmerged work. The
  organizers decide whether the evidence meets their impact criteria.
- Jon supplies the personal and team fields, decides what he can attest to,
  accepts the terms, and submits if he chooses.
