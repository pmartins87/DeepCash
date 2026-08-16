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
- [x] 2–6 handed seating/button/blinds;
- [x] generic arbitrary effective stacks including forced blinds below one nominal BB, shallow stacks and all-in calls for less;
- [x] NLHE betting with minimum full raise and configurable short-all-in reopen semantics;
- [x] fold/check/call/bet/raise/all-in legality, including dry-side-pot prevention when no opponent can contest a higher price;
- [x] multiway pots and side pots;
- [x] uncalled-bet return;
- [~] showdown/ties/odd chips — deterministic settlement exists and odd-chip allocation fails closed unless an explicit order covers all tied winners; target-site order remains unconfirmed;
- [~] rake interface with exact units/rounding separated from rules — exact model exists; target economy remains unconfirmed;
- [x] deterministic full-hand replay and fingerprints;
- [x] exhaustive five-card distribution audit;
- [x] independent evaluator parity against pinned PokerKit;
- [x] independent full-game generic-rules parity across 2–6 handed, including an expanded 200-trace battery with sub-BB and shallow stacks;
- [x] bidirectional legal-action boundary oracle across 2–6 handed, with actor/call/fold/check/raise and raise-to boundary probes;
- [~] adversarial/property fuzzing — cumulative short-raise boundaries, preflop live-BB short-all-in reopening, nested side pots, explicit odd-chip ordering and effectively-all-in dry-side-pot regressions are covered; broader rare-state coverage remains.

Important chronology: the generalized PokerKit gates were required to fail loudly and did so several times. They exposed a HU mapping error in the harness, a real DeepCash legality error where a raise was offered although no opponent could contest a higher price, a zero-chip bookkeeping CHECK difference during automatic runout, and finally one narrow pinned-PokerKit blind-epoch reopening divergence. The first three were corrected/normalized only after root-cause analysis. The fourth is intentionally **not copied into DeepCash**: when a player has already faced a live 100 BB and later faces a first short all-in to 180, the generic DeepCash `CUMULATIVE_FULL_RAISE` contract keeps reraise rights closed because the increase is only 80. The v3 oracle isolates precisely that upstream divergence and treats every other mismatch as a hard failure.

Accepted latest generic evidence:

- sub-BB full-game oracle run `31961946231`: **PASS**, 40 deterministic randomized hands per player count from 2 through 6, **200 traces total**, exact final-stack parity;
- legal-action oracle v3 run `31963863819` on commit `5e6c46349980b9a6e861b69736a3d7c49bb7f686`: **PASS**, **120 hands / 592 live decision states**, exactly one documented pinned-PokerKit blind-epoch divergence;
- broad general CI run `31963863833` on the same commit: **PASS**.

Current evidence: `docs/R1_VALIDATION_STATUS.md` and `STATUS.json`.

Exit gate: exhaustive/sampled parity against independent oracles plus property/fuzz tests, with target-site-dependent rules explicitly frozen or parameterized from evidence. Target-site short-all-in/reopen, odd-chip, rake and optional forced-bet semantics remain release debt.

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
- [x] exact all-in opening semantics: opening retained, response fold/call, no fabricated raise branch;
- [x] one-raise opening-size common-reference control across SPR 0.5, 1, 2 and 4;
- [x] automatic geometric clipping proven to collapse nominal candidates when their materialized action sets become identical at low SPR;
- [x] independent raise-size restriction laboratory with fixed opening sizes;
- [x] raise-size single-board convergence smoke — useful as wiring/convergence evidence but too uncertain for selection;
- [x] separate held-out board registries and alternate deterministic range phases precommitted before accepting held-out results;
- [x] complete non-empty proper subset lattice of `{25,50,75,100}%` opening sizes, so the old O3 hypothesis is no longer privileged by construction;
- [x] deterministic selector/precommit that chooses one champion at each 1/2/3-size complexity before a second unseen opening generation is consumed;
- [x] independent raise-size held-out generation separated from the opening-size held-out sets;
- [~] opening-size candidate evidence — `O3_25_50_100` led the original four-board control SPR range, but is **not** frozen and must survive the larger subset lattice plus unseen generations;
- [~] opening subset-lattice -> unseen-v2 workflow — running/unaccepted until workflow evidence and artifacts are inspected;
- [~] independent raise-size held-out workflow — running/unaccepted until workflow evidence and artifacts are inspected;
- [~] equal-wall-clock comparison — infrastructure works in CI, but decisive timing must be measured on the physical Ryzen 9;
- [ ] tighten difficult-board exact-BR intervals where necessary;
- [ ] expand held-out evidence only if the precommitted batteries expose unresolved geometry-specific behavior;
- [ ] final action-family freeze from control + held-out + physical-Ryzen evidence;
- [ ] later: richer raise depths only if measured gain justifies cost.

Accepted multi-SPR opening-size control (`31960758207`) at the 3000-iteration checkpoint:

| SPR | O1 mean/worst upper | O2 mean/worst upper | O3 mean/worst upper | worst exact-BR interval |
|---:|---:|---:|---:|---:|
| 0.5 | 0.001768 / 0.004225 | 0.000839 / 0.000900 | 0.000839 / 0.000900 | 0.001154 |
| 1 | 0.018995 / 0.023405 | 0.008197 / 0.010410 | 0.001510 / 0.001630 | 0.001860 |
| 2 | 0.026965 / 0.033987 | 0.011181 / 0.013935 | 0.001587 / 0.003729 | 0.002940 |
| 4 | 0.026688 / 0.033807 | 0.011250 / 0.013843 | 0.001295 / 0.003167 | 0.001966 |

At SPR 0.5, `O2` and `O3` clip to the same materialized action set and therefore produce identical results. At SPR >= 1, O3 is materially closer to the richer opening reference than O1/O2 on the original control battery. This remains development evidence, not a production freeze.

Candidate sizes are expressed primarily as pot fractions and geometrically clipped by stack/min-bet rules in the laboratory. Preflop will likely require blind-denominated raise-to abstractions.

Current evidence: `docs/RIVER_ACTION_ABSTRACTION_LAB_V1.md`, `docs/R3_VALIDATION_STATUS.md`, the R3 precommit files, `docs/ACTIVE_GATES_20260816.md` and `STATUS.json`.

Exit gate: choose the smallest family on the Pareto frontier of strategic error vs CPU/memory/wall-clock cost across control + held-out multi-board/multi-SPR batteries, with converged exact-BR intervals, independent opening/raise-size evidence, and equal-compute evidence on target hardware. No action family may be frozen merely because it led development controls.

## R4 — Private/public state abstraction laboratory
Status: **IN PROGRESS**

R4 engineering has started in parallel with the final R3 evidence collection, but **no representation has been selected**.

Architecture rule: exact cards, card removal, pot, stack, action geometry and payoffs remain in the game engine. Lossy compression is permitted only in the solver/encoder information-set representation.

Implemented/gated infrastructure:

- [x] exact-combo private-infoset control;
- [x] representation-aware river CFR+ that aliases only private infoset identity while leaving chance/payoff/action trees exact;
- [x] candidate policies expand back to exact combo keys before exact best-response evaluation;
- [x] one-sided common-reference methodology: candidate P0 vs exact P1 and exact P0 vs candidate P1;
- [x] exact control must reproduce the original river CFR+ solver bit-for-bit on the frozen unit fixture;
- [x] deterministic interpretable candidate generation before learned embeddings;
- [x] exact showdown-equity features use conditional opponent ranges with exact card removal;
- [x] blocker features measure opponent range mass removed by each private combo;
- [x] weighted quantile bucketization never splits exact feature ties by incidental combo enumeration order;
- [x] hole-card-order invariance tests for every current deterministic candidate;
- [x] resumable representation CFR+ state with staged-vs-monolithic exact equivalence;
- [x] JSON checkpoint roundtrip with exact future-path equivalence;
- [x] development and held-out board registries separated explicitly;
- [x] independent R4 held-out v1 precommitted **before any R4 numerical result is accepted**;
- [x] general CI containing the new R4 machinery passed in run `31963863833`;
- [ ] run and inspect development numerical battery;
- [ ] freeze a deterministic development selection procedure before touching R4 held-out v1;
- [ ] global suit-permutation/metamorphic invariance tests at the representation level;
- [ ] counterfactual-value features/clustering after deterministic controls are understood;
- [ ] learned embeddings only if they beat deterministic candidates per real compute;
- [ ] held-out v1 evaluation on the precommitted independent boards/ranges/SPR cells;
- [ ] physical Ryzen equal-wall-clock comparison;
- [ ] final representation freeze.

Current deterministic candidates:

- `category` — final hand category only;
- `strength4` — four weighted quantiles of exact river hand strength;
- `equity4` / `equity8` — exact showdown-equity quantiles versus the supplied opponent range with exact card removal;
- `category_equity4` — category crossed with equity quantile;
- `equity4_blocker2` / `equity8_blocker2` — equity quantile crossed with opponent-range blocker-mass quantile.

These are intentionally simple baselines, not a production shortlist.

The independent R4 held-out v1 generation is frozen in `docs/R4_HELDOUT_PRECOMMIT_20260816.md`: eight board families unique to R4, two range-phase pairs, 8 exact combos/player, SPR 1/2/4 and checkpoints 300/1200/3600. It remains **NOT RUN** until development selection is frozen. If a later candidate is designed using those held-out results, it must receive a new unseen generation.

Current evidence: `deepcash_core/river_representation_lab.py`, `deepcash_core/river_representation_training.py`, `deepcash_core/river_representation_fixtures.py`, `tools/benchmark_river_representation_reference.py`, `tests/test_river_representation_lab.py`, `docs/R4_RIVER_REPRESENTATION_LAB_V1.md` and `docs/R4_HELDOUT_PRECOMMIT_20260816.md`.

Exit gate: selected representation beats simpler candidates on held-out strategic error per wall-clock, preserves all required invariances and survives physical-Ryzen equal-compute comparison.

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
-> R1 target-site/release debt (parallel)
-> R2 PASS
-> R3 action abstraction held-out/lattice/Ryzen evidence (in progress)
-> R4 representation engineering and development evidence (in progress, parallel where independent)
-> R3 action freeze + R4 representation freeze
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

R1 site/economy debt may be closed in parallel with R3/R4 engineering. R3 and R4 may also progress in parallel only where their evidence sets are explicitly separated. **R9 remains blocked until every required R1–R8 exit gate passes**.

## North-star metric

The project is optimized for **practical expected value and robustness per unit of real compute**, not for the largest model, most branches, or lowest training loss in isolation.
