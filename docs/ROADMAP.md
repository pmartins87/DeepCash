# DeepCash finite roadmap — canonical state 2026-08-16

Final endpoint: **READY FOR TABLES = YES** only after every gate below passes. Intermediate progress never authorizes live use.

## R0 — Project foundation
Status: **IN PROGRESS**

- [x] Canonical repository `pmartins87/DeepCash`.
- [x] Project principles and hardware budget documented.
- [x] Finite roadmap established.
- [ ] CI and deterministic test harness.
- [ ] Version/status manifests.

Exit gate: repository can reproduce tests from a clean checkout.

## R1 — Exact 52-card NLHE cash engine
Status: **PENDING**

Implement and independently validate:

- 52-card codec/evaluator;
- 2–6 handed seating/button/blinds;
- arbitrary effective stacks;
- NLHE betting with minimum raise/reopen rules;
- fold/check/call/bet/raise/all-in legality;
- multiway pots and side pots;
- uncalled-bet return;
- showdown/ties/odd chips;
- rake interface with exact units/rounding separated from rules;
- deterministic full-hand replay.

Exit gate: exhaustive/sampled parity against an independent oracle plus property/fuzz tests.

## R2 — Canonical state and invariances
Status: **FOUNDATION STARTED**

Mandatory by construction, not learned by the network:

- hole-card order invariance;
- flop simultaneous-card order invariance;
- global suit-permutation invariance;
- relative-chair/button rotation invariance;
- action-history equivalence where semantics are identical;
- no loss of exact pot/call/stack/SPR geometry at the canonical-state boundary.

Exit gate: metamorphic tests prove equivalent states receive identical canonical keys/features.

## R3 — Action abstraction laboratory
Status: **PENDING**

Benchmark progressively richer action sets per street and geometry:

- fold/check/call;
- 1–4 bet sizes;
- 1–4 raise sizes;
- all-in as explicit terminal sizing where strategically distinct;
- later: multiple raise depths.

Candidate sizes should be expressed primarily as pot fractions and geometrically clipped by stack/min-raise rules. Preflop may require blind-denominated raise-to abstractions.

Exit gate: choose the smallest family on the Pareto frontier of strategic error vs CPU/memory cost across a multi-board/multi-SPR benchmark battery.

## R4 — Private/public state abstraction laboratory
Status: **PENDING**

Compare:

- exact combo identity controls;
- equity/range features;
- hand category + draw structure;
- blocker/nutness features;
- board texture ontology;
- counterfactual value embeddings/clustering;
- learned embeddings only after deterministic baselines exist.

Compression is allowed only at the solver/encoder observation boundary; the game engine remains exact.

Exit gate: selected representation beats simpler candidates on held-out strategic error per wall-clock and does not violate invariances.

## R5 — Solver correctness and algorithm selection
Status: **PENDING**

Build exact small-game oracles and compare:

- vanilla CFR;
- CFR+ / RM+;
- external/outcome sampling MCCFR;
- Deep CFR or neural regret/value variants;
- discounting/linear weighting;
- deterministic checkpoint/resume.

Exit gate: algorithms reproduce exact solutions in tractable games and the production candidate wins on reduction of exploitability/error per Ryzen CPU-hour.

## R6 — Street solvers and local resolving
Status: **PENDING**

Order of attack:

1. river subgames;
2. turn+river;
3. flop+turn+river;
4. preflop-to-river integration.

Develop safe/local resolving with blueprint priors, range consistency and bounded decision latency.

Exit gate: resolving demonstrably improves held-out EV/exploitability over blueprint-only without strategy discontinuities or illegal range updates.

## R7 — 6-max blueprint architecture
Status: **PENDING**

Construct a tractable full-game blueprint using:

- canonical state;
- selected action abstraction;
- selected representation;
- sampled chance/opponent trajectories;
- street decomposition where beneficial;
- neural/tabular hybrids if they improve CPU efficiency.

Important: do not attempt to enumerate the literal complete 6-max game tree.

Exit gate: stable held-out performance across positions, stack depths, board families and seeds; no representation/action-abstraction debt remains open.

## R8 — Ryzen 9 physical calibration
Status: **PENDING**

Measure on the actual target machine:

- worker count;
- batch size;
- RAM footprint;
- checkpoint cadence;
- disk throughput;
- contention;
- throughput by street/module;
- equal-wall-clock comparison of candidate algorithms.

Freeze a three-month production budget with reserve for reruns/refinement rather than spending 100% on one monolithic run.

Exit gate: immutable production profile and estimated completion envelope.

## R9 — Production training (~3 months maximum envelope)
Status: **BLOCKED UNTIL R1–R8 PASS**

Recommended budget philosophy:

- majority: blueprint training;
- meaningful reserve: river/turn resolving tables/models and high-value rare states;
- reserve: failed-seed reruns, validation and targeted refinements.

Checkpoints are evaluated continuously; continuation is based on marginal strategic gain per CPU-hour.

Exit gate: frozen base policy with reproducible hashes, training provenance and held-out validation.

## R10 — Strategic audit
Status: **PENDING**

Audit:

- positional frequencies;
- sizing distributions;
- range monotonicity/sanity where applicable;
- strategically equivalent state consistency;
- out-of-distribution behavior;
- adversarial policies;
- self-play cross-seed stability;
- regression sentinels.

Exit gate: no unexplained high-impact strategic anomalies.

## R11 — Opponent/pool data pipeline
Status: **PENDING**

Adapt lessons from AoF while recognizing cash complexity:

- persistent player aliases/identity;
- action-level hand reconstruction with uncertainty;
- stats by position/street/node/size/stack/board family;
- pool priors;
- Bayesian/shrinkage estimates;
- confidence intervals/effective sample size;
- no invented actions when snapshots are ambiguous.

Exit gate: replayed hand histories reconstruct with audited precision sufficient for exploitation.

## R12 — Safe exploitation layer
Status: **PENDING**

Unlike AoF, exploitation cannot be represented by one scalar shove-frequency deviation. Use a hierarchical opponent model:

- preflop frequencies/ranges by node;
- bet/raise/check frequencies by street and sizing bucket;
- showdown-informed range updates;
- pool prior -> player posterior;
- confidence-weighted deviation from blueprint.

Candidate exploit mechanisms:

1. blueprint range/opponent-policy perturbation;
2. local best response / subgame resolving against posterior opponent model;
3. exploit budget/regularization limiting departure from the robust base;
4. automatic fallback when confidence or state matching is insufficient.

Exit gate: exploitation gains EV in held-out synthetic/realistic opponent tests while bounded-adversary tests show acceptable robustness loss.

## R13 — OpenHoldemCash observe/replay runtime
Status: **PENDING**

Create a dedicated runtime/fork for conventional Hold'em cash rather than overloading AoF formulas:

- scrape exact cards/chips/button/actions;
- preserve raw evidence;
- reconstruct temporal state conservatively;
- canonical C++/Python contract;
- player identity/database integration;
- decision logging without clicking first.

Exit gate: long observe-only sessions have zero unexplained state/action mismatches.

## R14 — Autoplayer integration and safety
Status: **PENDING**

- legal-action translation to site controls;
- arbitrary bet sizing entry;
- min/max clipping;
- timeout handling;
- stale-state prevention;
- duplicate-click prevention;
- fail-closed behavior;
- full decision provenance in logs.

Exit gate: simulator/replay and controlled table tests show exact intended action execution.

## R15 — Operational homologation
Status: **PENDING**

Final checks:

- target site/economy frozen;
- rake/rounding validated from real hand records;
- runtime hash matches strategy hash;
- database schema/version checks;
- rollback package;
- session watchdogs;
- strategic sentinels;
- human-readable incident logs.

Only this gate may set:

`READY FOR TABLES = YES`

## Immediate critical path

```text
R0 finish CI/status
-> R1 exact cash engine
-> R2 invariance gates
-> R3/R4 action + state abstraction benchmarks
-> R5 solver selection
-> R6 street resolving
-> R7 full blueprint prototype
-> R8 physical Ryzen calibration
-> R9 production training
-> R10 audit
-> R11/R12 exploitation
-> R13/R14 OpenHoldemCash
-> R15 homologation
-> READY FOR TABLES
```

## North-star metric

The project is optimized for **practical expected value and robustness per unit of real compute**, not for the largest model, most branches, or lowest training loss in isolation.
