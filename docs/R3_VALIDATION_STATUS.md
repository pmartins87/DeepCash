# R3 action-abstraction validation status — 2026-08-16

R3 is **IN PROGRESS**.

The exact river laboratory now has deterministic resumable CFR+, cumulative convergence checkpoints, rich common-reference restriction games, a one-raise tree, a dynamic exact best-response oracle gated against enumeration, and a four-board one-raise restriction battery. **No production bet-size set has been selected.**

## Accepted controls

The current R3 stack contains:

- `deepcash_core.river_lab` — exact-card HU river one-bet microgame;
- synchronous full-chance CFR+ with linear average strategy;
- exact compatible-card chance enumeration;
- exact best responses and exploitability/value intervals;
- exact infoset/action-slot accounting;
- resumable deterministic CFR+ checkpoints with exact staged-vs-monolithic equivalence;
- `deepcash_core.river_reference_lab` / `river_reference_training` — asymmetric common-reference games;
- `deepcash_core.river_raise_reference_lab` / `river_raise_reference_training` — asymmetric one-raise common-reference games;
- dynamic exact BR for the one-raise reference tree, independently gated against the older enumerative oracle on tractable fixtures;
- package-safe benchmark fixtures and convergence analysis under `deepcash_core`;
- multi-board and multi-SPR one-bet benchmark infrastructure;
- CI regression and archived benchmark artifacts.

There is still no private-state abstraction in these controls. Exact combos remain separate.

## Methodological correction — own-tree exploitability is not abstraction loss

A smaller action family and a larger action family define **different games**. Therefore a candidate cannot be judged by comparing only its exploitability inside its own restricted tree.

A tiny tree can be easier to solve and can show lower own-tree exploitability precisely because strategically useful opponent actions have been removed. That number remains useful as a convergence diagnostic, but it is **not** the primary measure of action-abstraction quality.

R3 now uses a richer common reference game. For reference action set `R` and candidate subset `C`, it solves:

1. `R vs R`;
2. `C vs R` — only P0 is restricted;
3. `R vs C` — only P1 is restricted.

Every finite CFR policy has an exact-BR value interval `BR1 <= V <= BR0`. Restriction-loss bounds are propagated from those intervals rather than treating finite-iteration policy EV as the exact game value.

No strategic PASS threshold is being invented after seeing the numbers. The analyzers report interval tightening and conservative restriction-loss bounds; any production selection criterion must be precommitted and then validated on the target Ryzen hardware.

## Initial one-bet controls

Workflow run `31949683719` on commit `2640371563cd40067eb5f370af30ee123aaddb21`: **PASS**.

At 120 CFR+ iterations and 6 exact combos/player, own-tree exploitability/pot was:

| Board | S1 50% | S2 33/100% | S3 25/75/150% | S4 25/50/100/200% |
|---|---:|---:|---:|---:|
| A-high dry | 0.002324 | 0.004596 | 0.006590 | 0.005061 |
| Paired | 0.002087 | 0.005830 | 0.006172 | 0.008407 |
| Four-straight | 0.002529 | 0.008423 | 0.010329 | 0.009817 |
| Four-flush | 0.002639 | 0.005544 | 0.005175 | 0.005755 |

These numbers were **not** used to select S1. They primarily demonstrated that richer trees converge more slowly under equal iteration count.

Resumable one-bet CFR+ run `31949968733`: **PASS**. Artifact `9264366421`, SHA-256 `47d83b15555c934bd9eee4ac739cebf2a0069664ec1dd287ce61279629c446fa`.

The checkpoint gate proves exact staged-vs-monolithic training equivalence, exact JSON resume continuity, spec mismatch rejection and refusal to evaluate untrained states.

## Common-reference one-bet infrastructure

The asymmetric/reference solver and common-reference restriction methodology are operational and resumable. Workflow `31950481366`: **PASS**.

The original tiny common-reference smoke intentionally produced very wide exact-BR intervals; that result was treated as a warning that finite-iteration upper bounds cannot be interpreted before convergence, not as evidence for or against a candidate sizing family.

The common-reference implementation has since been made package-safe, and the same convergence analyzer is shared by the one-bet and one-raise reference schemas.

## One-raise exact-reference gate

The river reference tree now supports one opening bet followed by fold/call/raise, then fold/call after the raise. Opening action sets may differ by player so only one side can be restricted while the opponent keeps the rich reference tree.

The exact best response used for larger one-raise batteries is dynamic rather than pure-plan enumeration. The dynamic oracle is gated against the independent enumerative control on small fixtures before it is trusted for larger trees.

A first resumable one-raise common-reference convergence smoke passed in workflow `31951341083`. At 1000 iterations on A-high dry, 3 combos/player, pot 100, stack 400 (SPR 4), conservative restriction-loss upper bounds/pot were approximately:

- `O1_50`: 0.037924;
- `O2_25_75`: 0.017274;
- `O3_25_50_100`: 0.001947.

That single-board smoke was not used to freeze an action set.

## One-raise multi-board battery v2

Workflow run `31960177760` on commit `430e876e9844478ca95c5f233e60d17b544b2347`: **PASS**.

Configuration:

- exact HU river one-raise common-reference tree;
- pot 100, stack 400, therefore **SPR 4**;
- 4 exact range combos/player;
- four board families: A-high dry, paired, four-straight and four-flush;
- checkpoints 250, 1000 and 3000;
- opening candidates `O1_50`, `O2_25_75`, `O3_25_50_100`;
- reference opening sizes 25%, 50%, 75%, 100% pot;
- rich raise-response geometry held fixed while only opening sizes are restricted;
- dynamic exact BR intervals propagated into restriction-loss bounds.

Artifact:

- ID `9267050257`;
- ZIP SHA-256 `7e88e66c97cfb27c82ca8de9d6a4567fa252b6347425449bb37592b64c784d0e`.

At the 3000-iteration checkpoint:

| Candidate | mean conservative loss upper / pot | worst-board loss upper / pot | worst exact-BR interval width / pot |
|---|---:|---:|---:|
| O1 50% | 0.026688 | 0.033807 | 0.001966 |
| O2 25/75% | 0.011250 | 0.013843 | 0.001966 |
| O3 25/50/100% | 0.001295 | 0.003167 | 0.001966 |

Per-board final upper bounds for `O3_25_50_100` were:

- A-high dry: 0.000689;
- paired: 0.000661;
- four-flush: 0.000661;
- four-straight: 0.003167.

All twelve board/candidate curves tightened their exact-BR interval substantially from 250 to 3000 iterations. The four-straight board remains the hardest fixture in this battery, with final interval width about 0.001966/pot.

### Interpretation

This is the first one-raise result strong enough to be strategically informative rather than merely a wiring smoke. It says the three-opening-size candidate can be certified much closer to the four-opening-size reference **on this specific SPR-4, four-board, four-combo control battery** than the one- or two-opening-size candidates.

It still does **not** justify freezing `O3` for production because:

1. the worst O3 restriction upper bound (0.003167/pot) is of the same order as the remaining worst exact-BR interval width (0.001966/pot);
2. only SPR 4 has been measured in the one-raise battery;
3. the range samples remain deliberately small controls;
4. only opening sizes were restricted — raise-size abstraction itself has not yet been benchmarked;
5. hosted GitHub Actions timing is not target-Ryzen timing;
6. flop/turn/preflop may require different action families.

Therefore `O3` is a **leading engineering candidate**, not a frozen production decision.

## Equal-compute discipline

R3 separately tracks:

- cumulative training time;
- exact-BR evaluation time;
- own-tree convergence error;
- common-reference one-sided restriction-loss bounds;
- exact-BR interval width;
- infosets/action slots;
- board/SPR geometry;
- eventually memory and target-Ryzen throughput.

Hosted-CI wall time is engineering evidence only. The decisive equal-wall-clock comparison must be run on the physical Ryzen 9 before action-family freeze.

## Remaining R3 gates

1. support one-raise reference states where an opening is all-in and therefore correctly has **no legal raise response**, instead of excluding that low-SPR geometry;
2. run the one-raise common-reference battery across multiple SPRs, including approximately 0.5, 1, 2 and 4;
3. expand board/range coverage and add held-out fixtures rather than tuning to the current four controls;
4. benchmark **raise-size restriction** independently from opening-size restriction;
5. tighten difficult-board exact-BR intervals further where needed;
6. run equal-wall-clock evidence on the physical Ryzen 9;
7. precommit the selection rule and only then freeze the smallest action family on the strategic-error/compute Pareto frontier.

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
