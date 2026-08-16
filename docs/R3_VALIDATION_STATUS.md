# R3 action-abstraction validation status — 2026-08-16

R3 is **IN PROGRESS**.

The exact river laboratory now has deterministic resumable CFR+, cumulative convergence checkpoints, a one-raise exact tree, and a common-reference action-restriction oracle. No production bet-size set has been selected.

## Accepted controls

The current R3 stack contains:

- `deepcash_core.river_lab` — exact-card HU river one-bet microgame;
- synchronous full-chance CFR+ with linear average strategy;
- exact compatible-card chance enumeration;
- exact pure-plan best response for both players;
- exploitability and exploitability/pot inside a fixed tree;
- exact infoset/action-slot accounting;
- `deepcash_core.river_training` — resumable CFR+ state with exact staged-vs-monolithic equivalence;
- `deepcash_core.river_raise_lab` — exact river tree with one explicit raise depth and enumerative best response;
- `deepcash_core.river_reference_lab` — asymmetric P0/P1 action sets for common-reference restriction measurement;
- `deepcash_core.river_reference_training` — resumable CFR+ for asymmetric/reference games;
- cumulative convergence, Pareto/equal-compute and common-reference benchmark tools;
- CI regression + archived benchmark artifacts.

There is still no private-state abstraction in these controls. Exact combos remain separate.

## Methodological correction — own-tree exploitability is not abstraction loss

A smaller action family and a larger action family define **different games**. Therefore a candidate cannot be judged by comparing only its exploitability inside its own restricted tree.

A tiny tree can be easier to solve and can show lower own-tree exploitability precisely because strategically useful opponent actions have been removed. That number remains useful as a convergence diagnostic, but it is **not** the primary measure of action-abstraction quality.

R3 now uses a richer common reference game. For reference action set `R` and candidate subset `C`, it solves:

1. `R vs R`;
2. `C vs R` — only P0 is restricted;
3. `R vs C` — only P1 is restricted.

Every finite CFR policy has an exact-BR value interval `BR1 <= V <= BR0`. Restriction-loss bounds are propagated from those intervals rather than treating finite-iteration policy EV as the exact game value.

Current rich one-bet reference fractions are 25%, 33%, 50%, 75%, 100%, 150% and 200% pot. This is an engineering reference, not a production action set.

## Initial fixed-iteration own-tree smoke

Workflow run `31949683719` on commit `2640371563cd40067eb5f370af30ee123aaddb21`: **PASS**.

At 120 CFR+ iterations and 6 exact combos/player:

| Board | S1 50% | S2 33/100% | S3 25/75/150% | S4 25/50/100/200% |
|---|---:|---:|---:|---:|
| A-high dry | 0.002324 | 0.004596 | 0.006590 | 0.005061 |
| Paired | 0.002087 | 0.005830 | 0.006172 | 0.008407 |
| Four-straight | 0.002529 | 0.008423 | 0.010329 | 0.009817 |
| Four-flush | 0.002639 | 0.005544 | 0.005175 | 0.005755 |

These values are own-tree exploitability/pot after a tiny fixed iteration budget. They were **not** used to select S1.

Structural cost in that smoke:

| Candidate | Bet sizes | Infosets | Action slots | Approx. wall time per board |
|---|---|---:|---:|---:|
| S1 | 50 | 24 | 48 | 0.13 s |
| S2 | 33, 100 | 36 | 84 | 0.24–0.25 s |
| S3 | 25, 75, 150 | 48 | 120 | 0.42–0.44 s |
| S4 | 25, 50, 100, 200 | 60 | 156 | 0.80–0.84 s |

## Resumable one-bet CFR+ gate

Workflow run `31949968733` on commit `b916b33ac7f51b82530cea7a6b505e8704a81b86`: **PASS**.

Artifact:

- ID `9264366421`;
- ZIP SHA-256 `47d83b15555c934bd9eee4ac739cebf2a0069664ec1dd287ce61279629c446fa`.

Regression gates proved:

1. `37 + 63 + 200` staged iterations equal one monolithic 300-iteration solve exactly;
2. JSON checkpoint roundtrip preserves the exact subsequent training path;
3. a checkpoint refuses a different game spec;
4. an untrained checkpoint cannot masquerade as a strategy.

## Cumulative own-tree convergence

The same run measured 20/60/120 checkpoints. A-high dry, for example:

| Candidate | iter 20 | iter 60 | iter 120 | cumulative train sec @120 |
|---|---:|---:|---:|---:|
| S1 50% | 0.019494 | 0.006590 | 0.003185 | 0.065 |
| S2 33/100% | 0.039527 | 0.013706 | 0.004525 | 0.107 |
| S3 25/75/150% | 0.040603 | 0.010387 | 0.004500 | 0.151 |
| S4 25/50/100/200% | 0.053339 | 0.012424 | 0.004163 | 0.200 |

This demonstrated that equal iteration count is not equal optimization quality or equal compute.

## One-raise exact tree gate

`deepcash_core.river_raise_lab` now allows one opening bet, one raise-to and then fold/call. The tree remains small enough for enumerative exact best response.

The regression suite covers:

- exact tree/action-slot structure;
- raise target legality;
- exact-BR bounds around average-policy EV;
- deterministic repeatability;
- convergence from a small to larger iteration budget;
- a known-nuts sanity game.

The one-raise tests passed as part of river workflow run `31950253074` and remained green in subsequent river-lab workflows.

This is a structural control only. One-raise action families have not yet been promoted into the common-reference sizing battery.

## Common-reference restriction oracle gate

`deepcash_core.river_reference_lab` was added specifically to measure one-sided action restriction against a richer common game.

Workflow run `31950310169`: **PASS**.

The first intentionally tiny smoke used 80 iterations, 3 combos/player, A-high dry and S1 against the seven-size reference. It reported:

- `worst_loss_upper_per_pot = 0.232342`;
- reference own-tree exploitability/pot about `0.09296`;
- P0-restricted exploitability/pot about `0.10913`;
- P1-restricted exploitability/pot about `0.12313`.

**The 0.232342 value is not an estimate that S1 loses 23.2% of a pot.** The exact-BR value intervals are still extremely wide at 80 iterations, so the upper bound is dominated by numerical uncertainty. The smoke proved the wiring and, usefully, showed that interpreting restriction bounds before convergence would be invalid.

## Resumable common-reference convergence gate

The asymmetric/reference solver now has its own deterministic checkpoint state:

- staged training preserves global linear-average iteration weights;
- JSON roundtrip preserves the exact future path;
- checkpoints are tied to the exact asymmetric game/action sets;
- finite-state results are always evaluated with exact best response.

Workflow run `31950481366` on head `8fea4f1566539787e892b9f0747c0fe20c9f615d`: **PASS**.

Its river test suite passed **23 tests**, including exact staged-vs-monolithic equivalence for asymmetric games. The workflow also ran a cumulative common-reference smoke at 20/80/200 iterations and archived the resulting reference-convergence JSON with the other river artifacts.

This closes the infrastructure gap that previously forced the rich reference game to restart from zero at every checkpoint.

## What equal-compute now means

R3 separately tracks:

- cumulative training time;
- exact-BR evaluation time;
- own-tree convergence error;
- common-reference one-sided restriction-loss bounds;
- infosets/action slots;
- eventually memory and Ryzen throughput.

Hosted-CI wall time is engineering evidence only. The decisive equal-wall-clock comparison must be run on the physical Ryzen 9 before action-family freeze.

## Next R3 gates

1. extend common-reference checkpoints until exact-BR value intervals are tight enough that restriction-loss bounds become informative;
2. expand to multiple pot/stack/SPR geometries and a larger held-out board/range battery;
3. integrate the one-raise control into the common-reference methodology;
4. run equal-wall-clock evidence on the physical Ryzen 9;
5. only then precommit/freeze an action family for larger turn/flop work.

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
