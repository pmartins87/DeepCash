# R5 exact tabular solver comparison — precommit 2026-08-16

R5 algorithm engineering may begin in parallel while R3/R4 finish, but **no production solver selection is permitted before the earlier representation/action gates and target-Ryzen equal-compute evidence are available**.

This precommit freezes the first exact small-game comparison before its numerical results are accepted.

## Purpose

Establish a deterministic correctness/performance control for regret-update and average-strategy choices on the already-audited exact HU river laboratory.

The first generation compares only synchronous full-chance tabular variants. It does not yet compare MCCFR, Deep CFR or neural value/regret methods.

## Frozen variants

1. `CFR_UNIFORM`
   - ordinary cumulative regrets, no non-negative clipping;
   - uniform average-strategy weight per iteration.

2. `CFR_LINEAR`
   - ordinary cumulative regrets;
   - linear average-strategy weight `t`.

3. `CFR_PLUS_UNIFORM`
   - cumulative regrets clipped at zero after every global iteration;
   - uniform average-strategy weight.

4. `CFR_PLUS_LINEAR`
   - cumulative regrets clipped at zero;
   - linear average-strategy weight `t`;
   - must reproduce the existing DeepCash river CFR+ implementation exactly at equal iteration count.

No variant may be removed after seeing results without recording the failed/weak result as seen evidence.

## Frozen development battery

- board set: the four existing R3 control boards only;
- pot: 100;
- stack: 400 (SPR 4);
- action family: fixed 25% / 50% / 100% river bet sizes, geometrically materialized once and shared by every solver variant;
- 6 exact combos/player from deterministic quantile ranges;
- range phases 0.00 / 0.27;
- checkpoints 100 / 400 / 1200;
- exact compatible-card chance enumeration;
- exact best-response evaluation after each checkpoint.

## Measurements

Per variant / board / checkpoint record:

- exploitability per pot;
- policy EV;
- BR0 / BR1 values and interval width;
- cumulative training seconds;
- exact-BR evaluation seconds;
- infosets and action slots.

The first run is a **development control**, not held-out evidence. Hosted-CI timing is useful for gross algorithmic cost only; target-Ryzen timing remains mandatory later.

## Correctness gates before interpreting speed

- `CFR_PLUS_LINEAR` must equal the legacy `solve_river_cfr_plus` result on frozen fixtures;
- staged training must equal monolithic training for every variant;
- JSON checkpoint roundtrip must preserve the exact future path for every variant;
- resuming a checkpoint on the wrong game or wrong variant must fail closed;
- finite/non-finite state corruption must not be silently accepted.

## Selection discipline

This generation may rank the four tabular controls for further R5 engineering, but it cannot choose the production algorithm. Later R5 generations must still include sampled methods and neural candidates where justified, all evaluated by strategic error reduction per real Ryzen CPU-hour.

`R5 engineering = PRECOMMITTED`

`R5 production selection = NOT AUTHORIZED`
