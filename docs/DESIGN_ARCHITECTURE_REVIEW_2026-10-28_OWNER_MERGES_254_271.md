# Design and architecture review — the owner's #254 and #256–#271 (readout, promotion, live rule, control, filing)

Date: 2026-10-28. Baseline: `f87ba484` (main after the owner's #271).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the firings from 17:13 UTC on 10-27 to 13:25 UTC on 10-28. Main moved from `3a04216d` (#254) to
`fe9e58e3` (#267) before it started and to `f87ba484` (#268–#271) during it; this branch merges #268–#271. Four
read-only reviews ran beside mine, one each on the loop code, the registered analyses, the filing and ScrollGT, and
#268–#271. I checked every finding of theirs that this record uses before acting on it.
- **#254** reads the batchgeneratorsv2 confirmation: the registered command gives no reading (its join left 7 cycles
  unmatched); with each run pinned by its log header, all four predictions hold.
- **#256** adds a manual promotion of a kept candidate; **#262** uses it to promote batchgeneratorsv2's 6th window
  cycle. **#257** is the confirmation's Amendment 2.
- **#258** puts the replicate rule in the live loop beside the 0.01 margin; **#259** adds a no-change control to the
  sampler; **#263** records each cycle's code and configuration identities.
- **#260** fixes the registered scripts' 8th-cycle cut and adds a header join; **#264** and **#265** register and
  review the unchanged-control window.
- **#261**, **#266**, **#267** and **#269** update the October filing: the ranking metric, the ScrollGT corpus
  check, the v0.9.1 release and the annotation audit.
- **#268** verifies the Villa fiber export; **#270** hardens research execution and adds workspace diagnostics;
  **#271** makes worker startup cancellation safe and adds handoff deadlines.

## What changed

- **The replicate rule never promotes the no-change control** (`run_autoresearch_loop.py`,
  `replicate_rule_promotion`).
  - The rule promotes a cycle when its tweak's cycles beat the other tweaks' by t > 4.5 on val_f1 and ROC AUC
    (#258). The control (#259) changes no setting, so that evidence says nothing about it. A firing on it promoted
    one cycle's retrain of `config.json` on any gain over the incumbent, without train.py's 0.01 margin. The
    promotion also started every tweak's evidence over and rewarded the control's family.
  - Through the loop's own `main()`, with 6 control cycles about 0.004 above the other tweaks, the rule promoted a
    control cycle at val_f1 0.2716, below the margin's bar of 0.275762.
  - The firing is now recorded with `refused` and the cycle reverts. `tests/test_replicate_rule_live.py` runs that
    cycle through `main()`; the test fails on the old loop.
  - Train.py's margin can still promote a control cycle. Whether it should is the owner's call.
  - The fix reaches the loop only with a pull, and a pull into the loop's checkout ends the unchanged-control
    window. Until then the running loop can still promote a control cycle by the rule, which would end that window
    as "a promotion".
- **A manual promotion no longer leaves the new checkpoint beside the old config** (`scripts/promote_loop_candidate.py`).
  - `apply` wrote `config.json` and the history after the checkpoint and the logs, outside `promote_files`'
    rollback. A failure there left the promotion half applied, and a restart would train the new checkpoint with
    the old config.
  - Such a failure now puts all five files back, as a failure inside `promote_files` does. A failed `git add` now
    says where the old files are, as a failed commit does. Three tests in `tests/test_promote_loop_candidate.py`
    fail on the old script.
- **The readout's daily-gap figure** (#254, `reports/loop_confirmation_readout_2026-10-27.md`). It said sysstat
  leaves 23:50–00:10 unsampled each day. Cycles that start at 00:01 and 00:02 have a load, so the gap ends at 00:00,
  as #252's report says. Corrected in place and marked; a test in `tests/test_loop_confirmation_audit.py` binds it.
- **The readout's faults section notes #260.** #260 made the three registered functions cut at exactly 8 standing
  cycles too. `registered_verdict` still counts the join's unmatched cycles before the cut, so with an `--until`
  past the 8th standing cycle's end a later cycle without its run still gives UNMATCHED_RUNS. A synthetic window
  with 8 standing cycles and 60 others gives CONFIRMED at the 8th's end, and UNMATCHED_RUNS at
  `--until 2026-10-29T16:00:00` when one of 3 later cycles has no run.
- **The filing's corpus-check and 0.9.1 figures are bound** (`tests/test_filing_2026_10_numbers.py`). The draft says
  every figure in it is bound by a test. #266's (21 rows, 315 field values, a 7 GiB limit) and #267's (scoring
  version 3, Python 3.10–3.14 CI) were not. The new test fails on each of four altered figures.
- **The corpus record's expected rows are tied to published ones** (`tests/test_scrollgt_corpus_reproduction.py`).
  The record checked each scorecard only against its own `expected`. All 21 equal the connected-components rows
  finding 91 committed (`reports/neural_tracer_entrant.json`).

## Verified, no change needed

- **#254's records regenerate.**
  - The registered replicate-rule record is byte-identical, and so is the host-load window.
  - The corrected one differs only in 969 floats of the centred null, at most 9.6e-13 relative. Its counts,
    readings and first promotion (the 6th standing cycle, 10-26 18:33:16, score 7.1689) are the same.
  - The registered and corrected verdicts, recomputed with today's functions, differ at most 2.7e-15 relative.
  - The steps adjustment is equal.
  - The audit itself cannot be rebuilt here: the October run logs are absent.
- **The audit pins runs correctly.** All 128 registered matches pass the header check, and each of the 7 unmatched
  cycles has exactly one run that passes. Dropping the 7 instead gives CONFIRMED with 120 others.
- **#256 and #262.**
  - The manual promotion requires `.loop_paused`, no lock holder, no run and no held incumbent. It takes the lock
    and re-checks the config, incumbent and input bytes. It backs up all five files and commits only the three
    promotion files.
  - The committed `best_model.pt` is sha256 `c80885969cc5b3d4…`: val_f1 0.2710039, ROC AUC 0.5884, AP lift 1.2379,
    complete 400/400 validation, as the readout says. Its saved config equals `config.json`.
  - The commit's +0.005242 is over the previous incumbent's 0.265762.
- **#258's live rule is the frozen one.** It imports `scripts/loop_replicate_rule.scores` at its registered values.
  A score depends only on earlier rows, so taking each cycle's last score equals the frozen first-firing replay.
  - It reads only scored cycles that faced the same checkpoint bytes, budget, protocol, inputs, patch counts and
    baseline, with full identities. Crashed, blocked, NaN-AUC and pre-#263 records are left out.
  - Any promotion changes the incumbent's sha256, so the rule starts over.
  - `promote` re-checks that `last_model.pt` is this cycle's candidate and that the incumbent is unchanged. It
    restores the old files on a failed append and never raises into the loop.
- **#260's header join and cut.**
  - `--registered` forces the val_f1 join and refuses `--join header`.
  - The header join requires one run matching shift, number, tweak, val_f1 and incumbent.
  - The `>=` cut is right in all three functions.
- **#264/#265's script implements its registration's table.** It has the ≤ thresholds and INCOMPLETE below 6, and
  freezes at the first cycle that completes both 10-cycle quotas. The arm checks match how `cycle_config` builds
  the control and the reverse arm.
- **#261's figures hold:**
  - first on merge-penalized ERL on 10 with the scan and 8 cube-only;
  - finding 100's precision range, −0.0171 to +0.0068;
  - its coverage overtakes, 1 at tolerance 2 and 4 at tolerance 4;
  - the Scroll-5 figures;
  - all 7 source hashes.
- **#266 and #267 hold.**
  - All 21 targets exited 0, with every row at scoring version 3 and tolerance 2.0.
  - The times and peak RSS match the record: 0.57 GiB at 256³, 2.55–2.57 GiB at 512³.
  - The archive's hash matches, and it holds 84 files.
  - The harness sets `RLIMIT_AS` in a fresh child per target and refuses an output inside the source checkout.
  - The release record has five CI jobs on 3.10–3.14, all successful.
- **The standard suite lists every new test file.** At `fe9e58e3`, `tests/test_loop_unchanged_control.py` imported
  the live rule's module but was not in `VALIDATION_TESTS`, so the suite guard failed. #270 added it.
- **The checks pass.**
  - Ruff 0.9.10 `check` and `format` are clean on the seven changed Python files.
  - Mypy, with the pre-commit hook's flags, is clean over the whole repository (814 files).

## Observations for the owner (not changed)

- **The unchanged-control `read` can run before the window's last cycle is recorded** (`scripts/loop_unchanged_control.py`,
  registered, so not changed here).
  - Once the wall clock passes the deadline, `status` calls the window complete. A cycle that started before the
    deadline is in the window, but it is recorded only when it ends, 15–20 minutes later.
  - A synthetic journal read at the deadline plus 1 s gave INCOMPLETE (6 control, 5 reverse cycles). With the last
    cycle's record it gave BEATS_UNCHANGED. The output does not record the time it was read.
  - Until the script changes, run `read` only once `cycles.jsonl` holds a cycle that started at or after
    23:00 UTC on Nov 3, or once the window has ended another way.
- **#260 changed registered functions without an amendment.**
  - The confirmation's registration says nothing else in the script may change, and the replicate rule's freezes
    `window_test`.
  - The changes are written up in the October plan and an evidence JSON; neither registration has an amendment.
  - The committed outputs are unchanged.
  - #238's documented exploratory command now runs the header join, so it no longer gives #238's committed bytes.
    `--join val_f1` does.
- **#265 moved the deadline an hour earlier than #264's code.** #264's code compared naive Pacific strings: 16:00
  PST on Nov 3. #265 keeps the registration's "PDT" literally: 23:00 UTC, 15:00 PST. Its implementation review says
  so.
- **The filing's URL field cites ScrollGT v0.9.0, and its checklist says it cites the newest tag.**
  - v0.9.1 is now published. `test_scrollgt_cite_is_its_newest_tag` checks only that the newest tag's URL is
    somewhere in the draft, and #267's body link satisfies it.
  - `test_scrollgt_0_9_0_is_described_as_released` pins `tree/v0.9.0`. The research answers say the v0.9.0 tag
    identifies the released benchmark.
  - Either the URL field or the checklist sentence needs to change; which is the owner's call.
- **The plan's "All 12 URLs return HTTP 200" predates #261's steep-heading link.** The recorded check covers the
  older link. At 08:21 UTC the new one (`blob/2fb41b27…`) returned 200 here. The Villa and ScrollGT links return
  403 from this environment, so I could not recheck them.
- **The live loop:**
  - **A torn last line in `cycles.jsonl` turns the rule off.** The rule refuses a corrupt journal, as designed and
    tested. But the next record is appended to the torn line, so it is lost too, until the file is repaired.
  - **The live code epoch is finer than the frozen record's.** Live, it is the commit, its status lines and a
    content digest. Frozen, it is the merges that touched the loop's code. Any pull splits a live epoch. That costs
    power, not validity.
  - **The live rule tests every cycle for as long as an incumbent stands.** The frozen false-promotion rate was
    measured per window.
  - **The control's weight does not decay during its cooldown.** After a control promotion its weight of 2.0
    would hold, because a cooling family is not among those decayed.
  - **`decide`'s `tweak_cycles` counts cycles the score leaves out** (fewer than 10 others), so the "over N of its
    cycles" in a commit can overstate the t statistic's n.
  - **The manual promotion's `--family` is not checked** against the loop's templates.
- **The unchanged-control script imports two private helpers of the live rule** (`_provenance`, `_validation_key`).
  A later change to the live module changes the registered analysis. This round's change touches neither.
- **The unchanged-control power table is bound by no test.** It is right: from the corrected confirmation, SDs
  0.00137 and 0.00668 (batchgeneratorsv2) and 0.00192 and 0.0063 (pooled, df 103).
- **The repeatability probe's contract 2 is not in its doc.** `docs/REPEATABILITY_PROBE.md` does not list its new
  requirements (an applied step, a complete strict warm start, distinct seeds). `noise_probe_pooled` will not pool
  a contract-2 batch with the contract-1 batches.
- **The ScrollGT records.**
  - The corpus record's `release_data_unchanged`, `measurement_scope` and four other keys are not written by the
    harness. The 21 skeleton hashes and the two 10-25 targets' files do match the earlier records.
  - The release record carries flags (`scoring_modules_identical_to_corpus_check`, `data_unchanged_from_v0_9_0`)
    without the hashes behind them.
- **Doc audit entries are external.**
  - `139c6873` is the loop checkout's commit (the readout).
  - `38496eb8…` is ScrollGT's (the corpus report).
  - `21b068d5…` is a Villa blob (#271's review).

## Verification

- **The changed test files**, with the guard set and the new tests of #256–#271, give 927 passed and 14 skipped.
  The one failure is the standing `test_live_documents_stay_clean`.
- **Doc audit:** against `fe9e58e3`, the merged branch adds one entry, the Villa blob above. Two `39a8cf3a` entries
  are gone. This record adds no entries.
