# Bounty Hunter Journal

**Status:** Personal research log of bounty / prize-competition projects I've explored. Status varies per project; numbers in WIP entries are working claims from local branches and most are not independently audited. Treat the entries below as a personal index of where I've spent time, not a portfolio of shipped wins.

**Where there is verifiable public work:** Vesuvius Challenge (Project 002) has shipped artifacts in [`jonmarrs/vesuvius-autoresearch`](https://github.com/jonmarrs/vesuvius-autoresearch) plus the upstream PR stack against [`ScrollPrize/villa`](https://github.com/ScrollPrize/villa). Other projects' branches are local-only unless explicitly linked.

## Project 001: SGLang MoE Kernel Optimization
- **Bounty:** SGLang SOAR 2026 / FlashInfer AI Kernel Generation
- **Target:** `fused_moe` Triton kernel
- **Branch:** `Bounty_Hunter_2026-03-20_001_SGLang_MoE_Optimization`
- **Working claim:** ~58 TFLOPS on the fused kernel in local benchmarks; not independently audited.

## Project 002: Vesuvius Ink Detection
- **Bounty:** Vesuvius Challenge 2026 ($1M Grand Prize / $200K Kaggle Surface Detection tier, awarded March 2026; monthly Progress Prizes ongoing)
- **Target:** 3D ink detection on Herculaneum scroll CT scans (Scroll 1–3 First Letters / First Title)
- **Branch:** `Bounty_Hunter_2026-03-21_002_Vesuvius_Autoresearch`
- **Public repo:** https://github.com/jonmarrs/vesuvius-autoresearch (MIT)
- **Shipped artifacts:**
  - May 2026 Progress Prize filings ([Part 1](PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md) + [Part 2](PROGRESS_PRIZE_SUBMISSION_2026-05.md))
  - June 2026 Progress Prize draft ([doc](PROGRESS_PRIZE_SUBMISSION_2026-06.md)) anchored on upstream villa PRs [#915](https://github.com/ScrollPrize/villa/pull/915), [#916](https://github.com/ScrollPrize/villa/pull/916), [#922](https://github.com/ScrollPrize/villa/pull/922), [#923](https://github.com/ScrollPrize/villa/pull/923)
  - vesuvius-c Python wrapper measuring ~31.77M voxels/sec on local Blosc2 chunk reads
- **Current honest `val_bpb`:** 0.4145 on PHerc Paris 2 Fr 143 (in-distribution validation under the post-`c9f578f` ink-aware sampler; cross-scroll transfer is the active research target, not a measured result — see [methodology note](PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md))

## Project 003: ARC-AGI Reasoning
- **Bounty:** ARC-AGI Grand Prize ($1M+)
- **Branch:** `Bounty_Hunter_2026-03-20_003_ARC-AGI_Challenge`
- **Status:** Local exploratory branch; no submission to the public leaderboard.

## Project 004: AIMO Mathematical Reasoning
- **Bounty:** AIMO Progress Prize 3
- **Branch:** `Bounty_Hunter_2026-03-20_004_AIMO_Challenge`
- **Status:** Local exploratory branch.

## Project 005: Blackwell FP4 Kernel
- **Bounty:** FlagOS Global Challenge / OpenBMB ($250K)
- **Branch:** `Bounty_Hunter_2026-03-20_005_Blackwell_FP4_Optimization`
- **Status:** Local kernel-development branch (note: Blackwell hardware not in this workstation; testing simulates the FP4 path on Ada).

## Project 006: Web3 Security
- **Bounty:** Sherlock / Immunefi ($16M aggregate)
- **Target:** Smart-contract vulnerability detection
- **Branch:** `Bounty_Hunter_2026-03-21_006_Web3_Security`
- **Status:** Local exploratory branch.

## Project 007: XPRIZE Healthspan
- **Bounty:** XPRIZE Healthspan ($1M)
- **Target:** Longevity biomarker modeling
- **Branch:** `Bounty_Hunter_2026-03-21_007_XPRIZE_Healthspan`
- **Status:** Local exploratory branch.

## Project 008: Clay Millennium Prize
- **Bounty:** Clay Mathematics Institute ($1M per problem)
- **Target:** Formal proof generation
- **Branch:** `Bounty_Hunter_2026-03-21_008_Clay_Millennium_Prizes`
- **Status:** Local exploratory branch — no submission; "P vs NP" framing is exploratory, not a serious claim.

## Project 009: Intrinsic AI Challenge
- **Bounty:** Intrinsic AI Challenge ($180K)
- **Target:** Robotics sim-to-real RL
- **Branch:** `Bounty_Hunter_2026-03-21_009_Intrinsic_AI`
- **Status:** Local exploratory branch.

## Project 010: AgentX-AgentBeats
- **Bounty:** AgentX-AgentBeats ($150K+)
- **Target:** Research-agent efficiency
- **Branch:** `Bounty_Hunter_2026-03-21_010_AgentX-AgentBeats`
- **Status:** Local exploratory branch.

## Project 011: Anthropic Safety Bounty
- **Bounty:** Anthropic Safety Bounty ($15K per finding)
- **Target:** Jailbreak / safety-eval research
- **Branch:** `Bounty_Hunter_2026-03-21_011_Anthropic_Safety_Bounty`
- **Status:** Local exploratory branch.

## Project 012: Kaggle ML Mania 2026
- **Bounty:** Kaggle ML Mania 2026 ($50K)
- **Target:** Tournament outcome prediction
- **Branch:** `Bounty_Hunter_2026-03-21_012_Kaggle_ML_Mania`
- **Status:** Local exploratory branch.

---

**Note on the portfolio:** these 12 entries are tracking notes for projects I've started or wanted to take a swing at, not 12 wins. The Vesuvius work (Project 002) is the one with active public artifacts. The "Total Potential Value" framing that was in earlier versions of this doc was unhelpful — bounty pool size doesn't reflect either work done or expected return.
