# River action-abstraction laboratory v1

## Purpose

R3 does not freeze bet sizes by intuition. The first laboratory is a deliberately tractable **heads-up river subgame** in which the strategic error of every candidate action set can be measured against an **exact best response**.

The lab is not the production cash-game tree. It is an oracle environment for deciding which branches buy enough strategic value to justify their CPU/memory cost.

## Game contract

`deepcash_core.river_lab.RiverGameSpec` receives:

- an exact five-card Hold'em board;
- weighted exact two-card ranges for P0 and P1;
- the exact pot entering the river;
- a finite set of exact integer bet sizes.

P0 acts first. At the first version of the lab each player may make at most one bet; the opponent may fold or call. There are no raises yet. This restriction is intentional: it keeps exact best response cheap enough to serve as an oracle while we establish the action-abstraction methodology.

The subgame is zero-sum after a constant shift of the already-built pot. A showdown with matched river bet `b` pays the winner `pot/2 + b`; a fold transfers `pot/2` to the bettor. Ties are zero under that shifted utility.

## Solver

The initial solver is synchronous full-chance **CFR+** with linear average-strategy weighting. Every compatible private-card pair is traversed; card removal is exact.

The implementation records one policy per exact private combo and infoset. There is no private-state abstraction in this R3 control.

## Exact best response

The v1 tree is small enough that best response does not need an approximate solver.

For `S` bet sizes, each private hand has `(1 + S) * 2^S` pure plans:

- choose check or one of `S` bets at its opening node;
- choose fold/call against each of the opponent's `S` bet sizes.

The lab enumerates every pure plan for each private hand against the opponent's fixed average strategy. It reports:

- policy EV;
- P0 exact best-response value;
- P0 value against P1 exact best response;
- exploitability = `(BR0 - BR1) / 2`;
- exploitability normalized by pot;
- infoset count;
- action-slot count.

This lets us compare strategy quality and structural cost using one common oracle.

## Bet-size materialization

`materialize_bet_sizes` converts candidate pot fractions into integer chip sizes, rounds half-up to the chip unit, clips to the legal `[min_bet, stack]` envelope and removes duplicates. This is a **laboratory generator**, not yet the full R3 production legalization layer.

Current benchmark candidates are intentionally diverse:

- `S1_50`: 50% pot;
- `S2_33_100`: 33%, 100%;
- `S3_25_75_150`: 25%, 75%, 150%;
- `S4_25_50_100_200`: 25%, 50%, 100%, 200%.

They are candidates, not recommendations.

## Benchmark battery

`tools/benchmark_river_action_abstraction.py` currently uses four deterministic standard-Hold'em river families:

1. A-high dry;
2. paired;
3. four-straight;
4. four-flush.

Exact-combo ranges are sampled mechanically from hand-strength quantiles with different phases for the two players. These synthetic ranges are for controlled engineering comparison only; they are not population models and do not estimate live win rate.

## Selection rule

No candidate wins merely because it has lower exploitability at one iteration count. R3 will add convergence checkpoints/equal-wall-clock comparison and then construct a Pareto frontier using at least:

- exact exploitability/pot;
- worst-board exploitability;
- wall time;
- infosets/action slots;
- later, memory and Ryzen throughput.

A richer set must justify every added branch. CPU saved by discarding strategically redundant sizings is budget that can be spent on more states, more iterations, better private-state representation or deeper resolving.

## Next gates

1. CI-gate CFR+/exact-BR correctness on small fixtures.
2. Run the deterministic v1 battery and inspect convergence, not only final snapshots.
3. Add one-raise river trees and exact-BR parity before considering re-raises.
4. Add multiple pot/stack/SPR geometries.
5. Only then precommit the R3 candidate set for larger street solvers.
