# R3 action-abstraction validation status — 2026-08-16

R3 is **IN PROGRESS**.

The first exact river laboratory is built and CI-gated. No production bet-size set has been selected.

## Accepted v1 laboratory

Components:

- `deepcash_core.river_lab` — exact-card HU river microgame;
- synchronous full-chance CFR+ with linear average strategy;
- exact compatible-card chance enumeration;
- exact pure-plan best response for both players;
- exploitability and exploitability/pot;
- exact infoset/action-slot accounting;
- `tools/benchmark_river_action_abstraction.py` — deterministic multi-board sizing battery;
- `.github/workflows/river-lab.yml` — regression + smoke benchmark artifact.

The v1 microgame permits one bet and a fold/call response. Raises are intentionally deferred so the oracle remains exact and inexpensive while the methodology is established.

## CI evidence

River-lab workflow run `31949683719` on commit `2640371563cd40067eb5f370af30ee123aaddb21`: **PASS**.

The workflow first passed the exact-BR regression tests, then ran four river board families against four candidate sizing sets and uploaded artifact `9264288209`.

Smoke configuration:

- 120 CFR+ iterations;
- 6 exact range combos per player;
- pot 100;
- stack 300;
- minimum bet 20.

### Smoke results

| Board | S1 50% | S2 33/100% | S3 25/75/150% | S4 25/50/100/200% |
|---|---:|---:|---:|---:|
| A-high dry | 0.002324 | 0.004596 | 0.006590 | 0.005061 |
| Paired | 0.002087 | 0.005830 | 0.006172 | 0.008407 |
| Four-straight | 0.002529 | 0.008423 | 0.010329 | 0.009817 |
| Four-flush | 0.002639 | 0.005544 | 0.005175 | 0.005755 |

Values are **exact exploitability / pot of the policy after only 120 iterations**, not estimates of live EV.

Structural cost in the same smoke:

| Candidate | Bet sizes | Infosets | Action slots | Approx. wall time per board |
|---|---|---:|---:|---:|
| S1 | 50 | 24 | 48 | 0.13 s |
| S2 | 33, 100 | 36 | 84 | 0.24–0.25 s |
| S3 | 25, 75, 150 | 48 | 120 | 0.42–0.44 s |
| S4 | 25, 50, 100, 200 | 60 | 156 | 0.80–0.84 s |

## Correct interpretation

The current smoke **does not show that one sizing is strategically superior**.

At a fixed tiny iteration count, the larger action spaces are less converged and therefore often show greater measured exploitability. Selecting S1 from these numbers would repeat exactly the kind of error this laboratory exists to prevent: confusing easier optimization with a better final abstraction.

The next comparison must separate:

1. approximation error from removing actions;
2. solver convergence error;
3. real wall-clock/CPU cost.

That requires cumulative convergence curves and equal-wall-clock budgets.

## Next R3 gates

1. convert CFR+ training into resumable/cumulative checkpoints so convergence is measured without restarting;
2. build equal-wall-clock comparison across S1–S4;
3. expand board/range and pot/stack/SPR battery;
4. add a one-raise tree and gate its exact best response against enumerative controls;
5. only after those results precommit a candidate action family for turn/flop work;
6. run physical Ryzen calibration before any production action abstraction is frozen.

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
