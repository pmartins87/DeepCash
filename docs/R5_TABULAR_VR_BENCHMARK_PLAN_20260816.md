# R5 cheap tabular VR benchmark — frozen plan 2026-08-16

Purpose: determine whether the legal-information running baseline can recover useful variance reduction at far lower cost than `INFOSET_EXACT`.

The candidate implementation already has a dedicated structural gate. This document freezes the numerical comparison **before** its result is consumed.

## Compared modes

1. `ZERO` — ordinary external-sampling identity control;
2. `TABULAR_RUNNING` — running-mean control variate keyed only by traverser private combo + public opponent node + action;
3. `INFOSET_EXACT` — expensive legal-information hidden-support integration target.

`PERFECT_HISTORY` is not rerun here. Its corrected privileged-oracle result is already accepted in `docs/R5_VR_MODE_BENCHMARK_V2_ACCEPTED_20260816.md` and remains ineligible for production.

## Frozen battery

- board set: existing four river control boards;
- range combos: 8 per player;
- p0 phase: 0.13;
- p1 phase: 0.61;
- pot: 100;
- bet sizes: 25/50/100;
- regret variant: `ES_CFR_PLUS_LINEAR`;
- seeds: `101,211,307,401,503`;
- cumulative checkpoints: `500,2000,10000` iterations;
- same initialized seed per board/mode;
- exact best response at every checkpoint;
- hosted wall-clock is engineering evidence only.

For each board × mode × seed × checkpoint record:

- exploitability per pot;
- policy EV / BR0 / BR1;
- cumulative train seconds;
- terminal visits;
- for `TABULAR_RUNNING`: baseline action slots, sampled-update count and fraction of slots ever visited.

## Frozen aggregate reporting

At each checkpoint and mode report globally and per board:

- mean / median / min / max exploitability per pot;
- sample standard deviation across the 20 board-seed cells;
- mean cumulative train seconds;
- paired win count versus ZERO;
- paired mean and median exploitability difference versus ZERO.

At checkpoint 10000 additionally report:

- time multiplier versus ZERO;
- mean exploitability reduction versus ZERO;
- gap to `INFOSET_EXACT` in mean exploitability;
- tabular baseline coverage.

## Interpretation rule

No post-hoc absolute PASS threshold is permitted.

`TABULAR_RUNNING` remains a serious engineering candidate only if it occupies a useful Pareto position relative to ZERO and INFOSET_EXACT: the strategic gain must be considered together with its actual CPU overhead. A candidate that is both strategically worse and slower than another mode is dominated and retained as negative evidence.

The running mean may become stale as the policy changes. If that appears to be the limiting mechanism, a later EMA/recency-weighted candidate may be designed, but its schedule must be frozen before its own numerical comparison; it cannot be retroactively tuned inside this run.

Physical Ryzen equal-wall-clock selection remains an R8 requirement.
