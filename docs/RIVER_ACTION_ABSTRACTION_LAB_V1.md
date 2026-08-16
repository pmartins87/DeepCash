# River action-abstraction laboratory v1

## Purpose

R3 does not freeze bet sizes by intuition. The first laboratory is a deliberately tractable **heads-up river subgame** used to separate three different quantities that must not be conflated:

1. **solver convergence error** inside a chosen game tree;
2. **structural compute cost** of that tree;
3. **strategic loss caused by restricting actions** relative to a richer common reference game.

The lab is not the production cash-game tree. It is an oracle environment for deciding which branches buy enough strategic value to justify CPU/memory cost.

## Game contract

`deepcash_core.river_lab.RiverGameSpec` receives:

- an exact five-card Hold'em board;
- weighted exact two-card ranges for P0 and P1;
- the exact pot entering the river;
- a finite set of exact integer bet sizes.

P0 acts first. In the first tree each player may make at most one bet; the opponent may fold or call. A separate `river_raise_lab` now extends this to one raise, but the one-bet tree remains the smallest auditable control.

The subgame is zero-sum after a constant shift of the already-built pot. A showdown with matched river bet `b` pays the winner `pot/2 + b`; a fold transfers `pot/2` to the bettor. Ties are zero under that shifted utility.

## Solver

The control solver is synchronous full-chance **CFR+** with linear average-strategy weighting. Every compatible private-card pair is traversed; card removal is exact.

`deepcash_core.river_training` adds deterministic resumable state. Staged training is gated to be exactly equal to a monolithic run with the same global iteration count, including linear averaging weights. JSON checkpoint roundtrip must preserve the exact subsequent training path.

There is no private-state abstraction in this R3 control.

## Exact best response inside a fixed tree

For `S` bet sizes in the one-bet game, each private hand has `(1 + S) * 2^S` pure plans:

- choose check or one of `S` bets at its opening node;
- choose fold/call against each of the opponent's `S` bet sizes.

The lab enumerates every pure plan for each private hand against the opponent's fixed average strategy and reports:

- policy EV;
- P0 exact best-response value;
- P0 value against P1 exact best response;
- exploitability = `(BR0 - BR1) / 2`;
- exploitability normalized by pot;
- infoset count;
- action-slot count.

These values are excellent **convergence diagnostics for a fixed game tree**.

## Methodological correction: own-tree exploitability is not abstraction error

A smaller action set and a larger action set define **different games**. Therefore comparing each policy's exploitability only inside its own restricted tree does **not** tell us how much strategic value was lost by removing actions.

A restricted game can even look easier to solve precisely because important opponent actions no longer exist. That can make its own-tree exploitability smaller while its strategy is strategically poorer in the richer game.

No DeepCash action-family decision may therefore be based on cross-candidate own-tree exploitability alone.

## Common-reference restriction oracle

`deepcash_core.river_reference_lab` fixes this by allowing P0 and P1 to have different action sets.

For a rich reference set `R` and candidate subset `C`, R3 solves three zero-sum games:

1. `R vs R` — common reference;
2. `C vs R` — only P0 is action-restricted;
3. `R vs C` — only P1 is action-restricted.

This measures the value lost when **one player at a time** is denied the omitted actions while the opponent retains the richer set. It avoids the cancellation that can occur when both players are restricted in the same way.

Each finite CFR solution has an exact-BR value interval:

`BR1 <= true game value <= BR0`.

The restriction-loss oracle propagates these intervals rather than pretending the finite-iteration policy EV is the exact equilibrium value. For P0 restriction:

`loss = V(R,R) - V(C,R)`.

For P1 restriction, expressed as value gained by P0 because P1 was restricted:

`loss = V(R,C) - V(R,R)`.

The benchmark reports lower/upper bounds for both and a conservative `worst_loss_upper_per_pot`.

This common-reference metric, not own-tree exploitability, is the primary R3 abstraction-quality signal.

## Bet-size materialization

`materialize_bet_sizes` converts candidate pot fractions into integer chip sizes, rounds half-up to the chip unit, clips to the legal `[min_bet, stack]` envelope and removes duplicates. This is a **laboratory generator**, not yet the full production legalization layer.

Current candidate families remain deliberately diverse:

- `S1_50`: 50% pot;
- `S2_33_100`: 33%, 100%;
- `S3_25_75_150`: 25%, 75%, 150%;
- `S4_25_50_100_200`: 25%, 50%, 100%, 200%.

The current common reference is the materialized union of 25%, 33%, 50%, 75%, 100%, 150% and 200% pot. This reference itself is not frozen as production truth; it is a richer control.

## Benchmark batteries

`tools/benchmark_river_action_abstraction.py` measures own-tree convergence/structure.

`tools/benchmark_river_action_convergence.py` measures cumulative training curves and separates training wall time from exact-BR evaluation time.

`tools/analyze_river_action_convergence.py` builds mean/worst-error Pareto and equal-compute views. Hosted-CI time is engineering evidence only; physical Ryzen time is required before freeze.

`tools/benchmark_river_reference_restriction.py` measures one-sided action-restriction loss against the richer common game.

Current deterministic standard-Hold'em river families include:

1. A-high dry;
2. paired;
3. four-straight;
4. four-flush.

Exact-combo ranges are sampled mechanically from hand-strength quantiles with different phases for the two players. These synthetic ranges are engineering controls, not population models and not estimates of live win rate.

## One-raise control

`deepcash_core.river_raise_lab` now contains a second exact tree in which either player's opening bet may face one explicit raise-to and then fold/call. Its exact best response is still enumerative because the control tree remains small.

This is a structural gate for raise-depth engineering; it is not yet integrated into the production candidate battery.

## Selection rule

An action family can advance only after it is judged on all of the following:

- convergence under cumulative training;
- common-reference restriction-loss bounds;
- worst-board restriction loss;
- wall time on the physical Ryzen 9;
- infosets/action slots and later memory;
- multiple pot/stack/SPR geometries;
- behavior after adding at least one raise depth.

A richer set must justify every branch. CPU saved by discarding strategically redundant sizings can instead buy more states, more iterations, better private-state representation or deeper resolving.

## Next gates

1. CI-gate the common-reference restriction benchmark and archive smoke evidence.
2. Expand it across all boards/candidates and multiple pot/stack/SPR geometries.
3. Extend convergence until the exact-BR intervals are tight enough that candidate loss bounds are informative.
4. Integrate the one-raise control into the same common-reference methodology.
5. Run physical equal-wall-clock evidence on the Ryzen 9.
6. Only then precommit/freeze the R3 action family for larger street solvers.
