# DeepCash finite roadmap — canonical state 2026-08-16

Final endpoint: **READY FOR TABLES = YES** only after every gate below passes. Intermediate progress never authorizes live use.

## R0 — Project foundation
Status: **PASS**

- [x] Canonical repository `pmartins87/DeepCash`.
- [x] Project principles and hardware budget documented.
- [x] Finite roadmap established.
- [x] CI and deterministic test harness.
- [x] Version/status manifests.

Exit gate: repository can reproduce tests from a clean checkout. **PASSED** — clean GitHub Actions evidence is recorded in `STATUS.json` and `docs/R1_VALIDATION_STATUS.md`.

## R1 — Exact 52-card NLHE cash engine
Status: **IN PROGRESS**

Implement and independently validate:

- [x] 52-card codec/evaluator;
- [x] 2–6 handed seating/button/blinds for stacks covering a full BB;
- [~] arbitrary effective stacks — variable stacks work; incomplete forced-blind/sub-BB edge cases remain deliberately gated;
- [x] NLHE betting with minimum full raise and configurable short-all-in reopen semantics;
- [x] fold/check/call/bet/raise/all-in legality, including dry-side-pot prevention when no opponent can contest a higher price;
- [x] multiway pots and side pots;
- [x] uncalled-bet return;
- [~] showdown/ties/odd chips — deterministic settlement exists and odd-chip allocation now fails closed unless an explicit order covers all tied winners; target-site order remains unconfirmed;
- [~] rake interface with exact units/rounding separated from rules — exact model exists; target economy remains unconfirmed;
- [x] deterministic full-hand replay and fingerprints;
- [x] exhaustive five-card distribution audit;
- [x] independent evaluator parity against pinned PokerKit;
- [x] independent full-game generic-rules parity control across 2–6 handed — fixed traces plus 25 deterministic randomized hands per player count, 125 randomized traces total, exact final-stack parity against pinned PokerKit after correcting an oracle-discovered legality bug;
- [~] adversarial/property fuzzing — cumulative short-raise boundaries, nested side pots, explicit odd-chip ordering and effectively-all-in dry-side-pot regression are covered; broader rare-state coverage remains.

Important chronology: the generalized PokerKit gate initially **failed** and exposed two separate issues — first a HU mapping error in the harness, then a real DeepCash legality error where a raise was offered although the only live opponent could not contribute above the current price. The engine was corrected and the full 2–6 handed oracle then passed. Failed oracle runs are retained as audit evidence rather than erased from project history.

Current evidence: `docs/R1_VALIDATION_STATUS.md` and `STATUS.json`.

Exit gate: exhaustive/sampled parity against independent oracles plus property/fuzz tests, with target-site-dependent rules explicitly frozen or parameterized from evidence.

## R2 — Canonical state and invariances
Status: **PASS**

Mandatory by construction, not learned by the network:

- [x] exact `HandState -> DecisionSnapshot` boundary;
- [x] hole-card order invariance;
- [x] flop simultaneous-card order invariance;
- [x] all 24 global suit permutations;
- [x] relative-chair/Button physical-seat invariance;
- [x] actor-aware ordered action history retained;
- [x] exact action monetary geometry retained (`paid`, pot/call/current-bet/commitment/min-full-raise context);
- [x] exact pot/call/stack/commitment geometry retained at the canonical-state boundary;
- [x] hidden opponent cards are not exposed to the decision representation;
- [x] deterministic randomized 2–6 handed metamorphic battery across preflop, flop, turn and river;
- [x] anti-alias tests prove one-chip strategic changes remain distinguishable.

R2 does **not** freeze the future neural/private-state encoder. Lossy representation remains an R4 problem and must be justified experimentally.

Exit gate: metamorphic tests prove equivalent physical states receive identical canonical keys while strategically different geometry remains distinct. **PASSED** — see `docs/R2_VALIDATION_STATUS.md`.

## R3 — Action abstraction laboratory
Status: **IN PROGRESS**

Benchmark progressively richer action sets per street and geometry:

- [x] exact HU river one-bet microgame with exact combo card removal;
- [x] synchronous full-chance CFR+ control;
- [x] exact best-response controls and exact-BR value intervals;
- [x] exact exploitability/pot, infoset count and action-slot metrics;
- [x] candidate 1–4 bet-size own-tree smoke battery over multiple river board families;
- [x] cumulative/resumable CFR+ checkpoints with exact staged-vs-monolithic equivalence;
- [x] JSON checkpoint roundtrip with exact future-path equivalence;
- [x] common-reference restriction methodology `R vs R`, `C vs R`, `R vs C` so action-abstraction loss is not confused with own-tree convergence;
- [x] resumable asymmetric/common-reference CFR+;
- [x] exact one-raise river tree;
- [x] dynamic exact one-raise best response gated against independent enumeration on tractable fixtures;
- [x] package-safe shared benchmark fixtures and convergence analyzer;
- [x] multi-SPR one-bet benchmark infrastructure;
- [x] one-raise common-reference opening-size restriction smoke;
- [x] four-board one-raise common-reference battery at SPR 4 with checkpoints 250/1000/3000 and archived artifact;
- [~] opening-size candidate evidence — `O3_25_50_100` is the leading engineering candidate on the current bounded SPR-4 control battery, but is **not** frozen for production;
- [~] equal-wall-clock comparison — infrastructure works in CI, but decisive timing must be measured on the physical Ryzen 9;
- [ ] allow all-in opening nodes in the one-raise reference game to correctly have no legal raise response, enabling low-SPR one-raise tests without misrepresenting the tree;
- [ ] one-raise common-reference battery across multiple SPRs, approximately 0.5, 1, 2 and 4;
- [ ] larger held-out board/range battery;
- [ ] benchmark raise-size restriction independently from opening-size restriction;
- [ ] tighten difficult-board exact-BR intervals where necessary;
- [ ] later: richer raise depths only if measured gain justifies cost;
- [ ] final strategic-error/compute selection-rule precommit and action-family freeze.

Current one-raise SPR-4 battery (`31960177760`) at 3000 iterations reported conservative mean/worst opening-restriction upper bounds per pot:

| Candidate | Mean upper | Worst upper | Worst exact-BR interval width |
|---|---:|---:|---:|
| O1 50% | 0.026688 | 0.033807 | 0.001966 |
| O2 25/75% | 0.011250 | 0.013843 | 0.001966 |
| O3 25/50/100% | 0.001295 | 0.003167 | 0.001966 |

This is strategically informative but still insufficient for a freeze: it covers only SPR 4, deliberately tiny exact ranges, four control boards and opening-size restriction with richer raise geometry held fixed. Hosted-CI timing is also not Ryzen timing.

Candidate sizes are expressed primarily as pot fractions and geometrically clipped by stack/min-bet rules in the laboratory. Preflop will likely require blind-denominated raise-to abstractions.

Current evidence: `docs/RIVER_ACTION_ABSTRACTION_LAB_V1.md`, `docs/R3_VALIDATION_STATUS.md` and `STATUS.json`.

Exit gate: choose the smallest family on the Pareto frontier of strategic error vs CPU/memory/wall-clock cost across a multi-board/multi-SPR benchmark battery, with convergence and equal-compute evidence on the target hardware and a precommitted selection rule.

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
R0 PASS
-> R1 exact cash engine target-site/release debt (parallel)
-> R2 PASS
-> R3 one-raise low-SPR + multi-SPR + raise-size abstraction + Ryzen equal-compute gates
-> R4 state abstraction benchmarks
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

R1 site/economy debt may be closed in parallel with R3/R4 engineering, but **R9 remains blocked until every required R1–R8 exit gate passes**.

## North-star metric

The project is optimized for **practical expected value and robustness per unit of real compute**, not for the largest model, most branches, or lowest training loss in isolation.
