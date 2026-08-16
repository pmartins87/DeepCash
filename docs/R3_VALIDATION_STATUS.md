# R3 action-abstraction validation status — 2026-08-16

R3 is **IN PROGRESS**.

The exact river laboratory now has deterministic resumable CFR+, cumulative convergence checkpoints and Pareto/equal-compute analysis infrastructure. No production bet-size set has been selected.

## Accepted v1 laboratory

Components:

- `deepcash_core.river_lab` — exact-card HU river microgame;
- synchronous full-chance CFR+ with linear average strategy;
- exact compatible-card chance enumeration;
- exact pure-plan best response for both players;
- exploitability and exploitability/pot;
- exact infoset/action-slot accounting;
- `deepcash_core.river_training` — resumable CFR+ state with spec signature and JSON checkpoint schema;
- `tools/benchmark_river_action_abstraction.py` — deterministic multi-board sizing battery;
- `tools/benchmark_river_action_convergence.py` — cumulative checkpoints with training time separated from exact-BR evaluation time;
- `tools/analyze_river_action_convergence.py` — aggregate mean/worst error, Pareto frontier and equal-compute snapshots;
- `.github/workflows/river-lab.yml` — regression, battery, convergence analysis and archived artifacts.

The v1 microgame permits one bet and a fold/call response. Raises remain a separate next gate so the current exact oracle stays small and auditable.

## Initial fixed-iteration smoke

River-lab workflow run `31949683719` on commit `2640371563cd40067eb5f370af30ee123aaddb21`: **PASS**.

The workflow ran four river board families against four candidate sizing sets and uploaded artifact `9264288209`.

Smoke configuration:

- 120 CFR+ iterations;
- 6 exact range combos per player;
- pot 100;
- stack 300;
- minimum bet 20.

### Fixed-iteration results

| Board | S1 50% | S2 33/100% | S3 25/75/150% | S4 25/50/100/200% |
|---|---:|---:|---:|---:|
| A-high dry | 0.002324 | 0.004596 | 0.006590 | 0.005061 |
| Paired | 0.002087 | 0.005830 | 0.006172 | 0.008407 |
| Four-straight | 0.002529 | 0.008423 | 0.010329 | 0.009817 |
| Four-flush | 0.002639 | 0.005544 | 0.005175 | 0.005755 |

Values are **exact exploitability / pot of the policy after only 120 iterations**, not estimates of live EV.

Structural cost in that smoke:

| Candidate | Bet sizes | Infosets | Action slots | Approx. wall time per board |
|---|---|---:|---:|---:|
| S1 | 50 | 24 | 48 | 0.13 s |
| S2 | 33, 100 | 36 | 84 | 0.24–0.25 s |
| S3 | 25, 75, 150 | 48 | 120 | 0.42–0.44 s |
| S4 | 25, 50, 100, 200 | 60 | 156 | 0.80–0.84 s |

These numbers were explicitly **not** used to select S1. At a fixed tiny iteration count, richer action spaces are harder to optimize, so this snapshot mixes abstraction quality with convergence error.

## Resumable CFR+ gate

Workflow run `31949968733` on commit `b916b33ac7f51b82530cea7a6b505e8704a81b86`: **PASS**.

Artifact:

- ID `9264366421`;
- ZIP SHA-256 `47d83b15555c934bd9eee4ac739cebf2a0069664ec1dd287ce61279629c446fa`.

Regression gates proved:

1. `37 + 63 + 200` staged iterations produce **exactly the same final policy/result** as one monolithic 300-iteration legacy solve;
2. JSON serialize/deserialize of a checkpoint preserves the exact subsequent training path;
3. a checkpoint refuses to resume on a different `RiverGameSpec`;
4. untrained checkpoints cannot be evaluated as if they were valid strategies.

This closes the first reproducibility debt before any long river benchmark is attempted.

## Cumulative convergence smoke

The same run measured 20/60/120 cumulative checkpoints, 4 exact range combos/player, on all four board families. Training wall time excludes exact-BR evaluation time.

Representative A-high dry curve:

| Candidate | iter 20 | iter 60 | iter 120 | cumulative train sec @120 |
|---|---:|---:|---:|---:|
| S1 50% | 0.019494 | 0.006590 | 0.003185 | 0.065 |
| S2 33/100% | 0.039527 | 0.013706 | 0.004525 | 0.107 |
| S3 25/75/150% | 0.040603 | 0.010387 | 0.004500 | 0.151 |
| S4 25/50/100/200% | 0.053339 | 0.012424 | 0.004163 | 0.200 |

The other board families also showed substantial convergence from 20 to 120 iterations. This confirms why the original 120-iteration cross-tree comparison could not be interpreted as abstraction error alone.

The CI smoke Pareto analyzer currently leaves only S1 checkpoints on the observed tiny-budget frontier. **This is an engineering smoke result, not a production action-selection result.** Hosted-CI timing is machine-specific, ranges are tiny/synthetic, raise branches do not exist yet, and the candidates are not trained to a common low-error regime.

## What equal-compute now means

The analyzer does not pretend equal iteration count means equal compute. For each candidate/checkpoint it aggregates:

- cumulative training seconds across the battery;
- mean exact exploitability/pot;
- worst-board exact exploitability/pot;
- infosets/action slots;
- exact-BR evaluation cost separately.

It can select the latest checkpoint each candidate reached under the same observed training-second budget and construct a Pareto frontier. The decisive version of this comparison must be rerun on the physical Ryzen 9 before action-family freeze.

## Next R3 gates

1. add a one-raise river tree and gate its exact best response against an enumerative control;
2. expand board/range and pot/stack/SPR battery;
3. extend convergence checkpoints until candidates enter a genuinely comparable error regime;
4. run equal-wall-clock evidence on the physical Ryzen 9;
5. only then precommit/freeze an action family for larger turn/flop work.

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
