# DeepCash finite roadmap — canonical state 2026-08-16

Final endpoint: **READY FOR TABLES = YES** only after every required gate below passes. Intermediate progress never authorizes live use.

## R0 — Project foundation
Status: **PASS**

- [x] Canonical repository `pmartins87/DeepCash`.
- [x] Project principles and Ryzen-9 budget documented.
- [x] Finite roadmap, CI, deterministic tests and status manifests.
- [x] Clean-checkout reproducibility gate.

## R1 — Exact 52-card NLHE cash engine
Status: **IN PROGRESS**

Generic engine already implemented/validated:

- [x] exact 52-card codec/evaluator;
- [x] 2–6 handed seating/button/blinds, including sub-BB forced blinds;
- [x] exact fold/check/call/raise-to/all-in legality;
- [x] minimum full raise and explicit short-all-in/reopen policy;
- [x] prevention of raises that create uncontestable side-pot tranches;
- [x] side pots, ties, uncalled returns and deterministic settlement;
- [x] deterministic hand replay;
- [x] exhaustive five-card distribution audit and independent PokerKit evaluator parity;
- [x] independent 2–6 handed full-game parity, including shallow/sub-BB stacks;
- [x] bidirectional legal-action oracle — run `31963863819`: 120 hands / 592 live states / exactly one documented pinned-PokerKit blind-epoch divergence.

Remaining R1 debt is target-dependent rather than generic-engine uncertainty:

Reference/deployment contract:

- **GGPoker is the initial rules/economy reference model**;
- the exact NLHE 6-max engine and strategic core remain site-agnostic;
- conventional-site differences are isolated behind explicit rules, economy and runtime adapters;
- rake/caps/rounding, reopen/min-raise, odd chips, forced bets, currency/table metadata and scraper/tablemap behavior must be measured and parameterized rather than assumed identical;
- supporting another site must not require a separate strategic core unless a measured rule difference changes the game itself.

- [ ] authoritative target-site short-all-in/reopen semantics;
- [ ] target-site odd-chip order;
- [ ] rake eligibility/cap/rounding/timing;
- [ ] straddle/ante/other forced-bet variants if present;
- [ ] later native/cross-language evaluator parity before production performance freeze.

Implementation checkpoint (2026-08-17): the typed universal site-rule contract and
GGPoker 6-max reference profile are implemented on `agent/r1-site-rule-contract`
and passed structural CI run `31985349633`. Published rake rows and eligibility
are recorded exactly; unresolved cumulative reopen,
odd-chip and rake-rounding/timing facts fail closed. This is engineering progress,
not R1 acceptance. Evidence: `docs/R1_GGPOKER_SITE_RULE_CONTRACT_20260817.md`.

Implementation checkpoint (2026-08-17): a strict evidence-fixture harness is
implemented on `agent/r1-evidence-fixtures` and passed CI run `31986987358`. It rejects retained
personal identifiers, ambiguous short-all-in geometry, inconsistent odd-chip
remainders, broken rake chip conservation and non-canonical source provenance.
This enables deterministic evidence admission; it does not resolve any outstanding
GGPoker fact by itself. Validated head: `9ff89f4f192148179dab8916d433680298ab5e19`. Evidence:
`docs/R1_GGPOKER_EVIDENCE_CAPTURE_20260817.md`.

Current evidence: `docs/R1_VALIDATION_STATUS.md` and `STATUS.json`.

## R2 — Canonical state and invariances
Status: **PASS**

Guaranteed by construction/test rather than learned:

- [x] exact `HandState -> DecisionSnapshot` boundary;
- [x] hole-card order invariance;
- [x] simultaneous flop-card order invariance;
- [x] all 24 global suit permutations;
- [x] button-relative physical-chair invariance;
- [x] actor-aware ordered action history;
- [x] exact pot/call/stack/commitment/min-raise geometry retained;
- [x] opponent private cards excluded from decision representation;
- [x] randomized 2–6 handed metamorphic tests and one-chip anti-alias tests.

Lossy compression remains an R4-only concern; the game engine stays exact.

## R3 — Action abstraction laboratory
Status: **IN PROGRESS**

### Infrastructure — PASS

- [x] exact HU river one-bet and one-raise microgames;
- [x] exact best-response controls and conservative restriction-loss intervals;
- [x] resumable/checkpointed CFR+ reference solvers;
- [x] common-reference `candidate vs exact` methodology;
- [x] geometric clipping/all-in action semantics;
- [x] separate development, held-out-v1 and unseen-v2 generations.

### Opening-size complete subset search — ACCEPTED

Every non-empty proper subset of `{25,50,75,100}%` was tested. Frozen seen-data cardinality champions:

- 1 size: `L1_100`;
- 2 sizes: `L2_50_100`;
- 3 sizes: `L3_25_50_100`.

### Opening-size unseen-v2 — PASS

The independently precommitted six-board, 8-combo/player, SPR 1/2/4 unseen generation completed after selection.

Checkpoint-3600 cross-SPR mean/worst conservative upper loss per pot:

| candidate | mean | worst |
|---|---:|---:|
| L1_100 | 0.00589680 | 0.01368868 |
| L2_50_100 | 0.00114458 | 0.00267837 |
| **L3_25_50_100** | **0.00097338** | **0.00168981** |

At SPR 2, L3's extra 25% branch has a resolved strategic advantage over L2. Therefore:

- **25/50/100 = leading river opening-size strategic finalist**;
- **50/100 = compute-efficient opening finalist**;
- 100-only is rejected as too coarse.

Evidence: `docs/R3_OPENING_LATTICE_SELECTION_ACCEPTED_20260816.md` and `docs/R3_OPENING_HELDOUT_V2_ACCEPTED_20260816.md`.

### Raise-size unseen evidence — ACCEPTED

Across SPR 1/2/4, the leading engineering family is **50/100**. Removing 50% causes material deeper-SPR loss; adding 150% has not shown a resolved incremental benefit sufficient to justify extra cost.

Evidence: `docs/R3_RAISE_SIZE_HELDOUT_ACCEPTED_20260816.md`.

### R3 exit debt

- [ ] tighten exact-BR intervals only where the final L2/L3 decision remains resolution-limited;
- [ ] physical Ryzen equal-wall-clock comparison of serious finalists — **PENDING_NOT_STARTED; no R3 workload is currently running on the Ryzen and no physical R3 evidence exists yet**;
- [ ] define street/SPR-dependent abstraction rather than extrapolating one river grid blindly to flop/turn/preflop;
- [ ] preserve geometric action deduplication when nominal sizes clip to the same physical action.

R3 cannot PASS from hosted-CI strategic evidence alone.

## R4 — Private/public state abstraction laboratory
Status: **IN PROGRESS**

Architecture rule: exact cards, chance, payoff, stack/pot and action tree remain exact. Compression aliases only solver/encoder information-state identity.

Implemented correctness infrastructure:

- [x] exact-combo control reproduces original river solver;
- [x] one-sided candidate-vs-exact restriction evaluation;
- [x] candidate policies expanded to exact combo keys before BR evaluation;
- [x] resumable deterministic representation CFR+;
- [x] JSON checkpoint future-path equivalence;
- [x] hole-card-order and all-24-suit-permutation invariance;
- [x] deterministic feature candidates and exact card-removal equity/blocker features;
- [x] precommitted development selector and independent heldout-v1 firewall.

Current deterministic candidates:

`category`, `strength4`, `equity4`, `equity8`, `category_equity4`, `equity4_blocker2`, `equity8_blocker2`.

Corrected bucket-constrained-BR development run `31976302604` completed successfully. Artifact `9274193444` was fully audited; ZIP SHA-256 `b1edea689f1d7417f80b2f77d8ec8241042cde81a75eb5f632eea8af38d8fd3e`.

Frozen deterministic finalists:

- `equity8`;
- `equity4_blocker2`;
- `category_equity4`.

Freeze: `configs/r4_representation_finalists_v1.json` and `docs/R4_REPRESENTATION_FINALIST_FREEZE_20260817.md`.

Next R4 gates:

- [x] complete corrected development battery and inspect all 24 cells;
- [x] freeze at most three deterministic finalists;
- [ ] merge the freeze after CI;
- [ ] manually run the precommitted independent heldout-v1 from merged `main`;
- [ ] inspect every held-out cell and artifact before promotion;
- [ ] add counterfactual-value/clustering candidates only as a separately frozen generation;
- [ ] learned embeddings only if they beat deterministic baselines per real compute;
- [ ] physical Ryzen equal-wall-clock comparison;
- [ ] production representation freeze.

## R5 — Solver correctness, traversal and algorithm selection
Status: **IN PROGRESS**

R5 now treats solver choice as an empirical hierarchy rather than assuming vanilla CFR+/Deep CFR is sufficient.

### Exact synchronous controls — ACCEPTED

First synchronous battery established `CFR_PLUS_LINEAR` as the best initial synchronous control: checkpoint-1200 mean/worst exploitability per pot about `0.000398 / 0.000455`.

### Corrected alternating exact controls — ACCEPTED

A literature/source audit forced a correction to player-local alternating average timing before result consumption. Corrected run `31966030278` showed enormous gains.

The strongest tested exact control is currently the explicitly named historical/OpenSpiel-style post-update discounted algorithm:

`OPEN_SPIEL_STYLE_POST_DCFR_150_0_2`

Checkpoint-1200 mean/worst exploitability per pot ~`0.00000587 / 0.00000767`.

### DCFR semantic split — AUDITED

DeepCash deliberately distinguishes:

1. historical/OpenSpiel-style **add instantaneous regret, then discount updated cumulative regret**;
2. 2026 paper-equation **discount old cumulative regret, then add instantaneous regret**.

They are not silently called the same algorithm.

### Paper-equation DCFR / HS schedules — ACCEPTED NEGATIVE EVIDENCE

Run `31966914580` tested paper-equation DCFR(1.5/0/2) and HS-DCFR(30/15) with frozen horizon/schedules. On this exact river microgame they remained around `~0.002–0.004` exploitability/pot and were dramatically weaker than corrected alternating CFR+ and the historical post-update discounted control.

The negative result is retained; no post-hoc parameter tuning was used to force the literature method to win.

### Sampling decomposition — ACCEPTED

- external sampling: useful scaling candidate but poor tiny-tree convergence;
- IID chance sampling: materially better than external sampling at the same sampled-iteration scale;
- analytical test proves the chance-sampled one-step regret estimator is unbiased;
- correlated chance sampling (persistent randomized golden-ratio Weyl stream): **strong paired result**, better than IID chance sampling in 16/16 frozen board-seed cells at 1k, 5k and 20k;
- alternating external LCFR: competitive only late and only marginally better than uniform alternating external CFR; not decisive.

Current leading sampling primitive: **correlated chance allocation**, not yet a production solver.

### Sampling scaling audit — ACTIVE

The first range-support crossover was invalidated for timing before acceptance because the sampled hot path rebuilt the entire compatible-deal support on every chance draw.

Corrected implementation:

- exact weighted compatible-deal CDF built once per training batch;
- O(log N) repeated draws;
- 10,000-draw regression proves identical deal sequence and final PRNG state against the legacy sampler.

Corrected crossover v2 run `31967392548` is active and must pass semantic replay before timing conclusions are accepted.

### Modern candidate funnel

Research registry: `docs/R5_MODERN_ALGORITHM_CANDIDATE_REGISTRY_20260816.md`.

High-value remaining candidates include:

- variance-reduced MCCFR baselines;
- discounted/predictive regret methods with precisely frozen update semantics;
- regret-based pruning;
- block-coordinate/treeplex methods when public-state architecture exists;
- neural discounted/regret/value approximation only after R4 finalists and trustworthy sampled traversal.

R5 exit gate:

- exact small-game correctness;
- deterministic checkpoint/resume;
- held-out strategic validation;
- scaling/memory evidence;
- physical Ryzen equal-compute comparison;
- one production solver/traversal architecture frozen only after R3/R4 representations are compatible.

## R6 — Street solvers and local resolving
Status: **PENDING**

Order:

1. river subgames;
2. turn+river;
3. flop+turn+river;
4. preflop-to-river integration.

Build blueprint-consistent local resolving with exact range updates and bounded latency.

Exit gate: resolving improves held-out EV/exploitability over blueprint-only without illegal/discontinuous range behavior.

## R7 — 6-max blueprint architecture
Status: **PENDING**

Construct a tractable full-game blueprint using:

- exact canonical game state;
- R3-selected action abstraction;
- R4-selected representation;
- R5-selected solver/traversal;
- sampled chance/opponent trajectories where justified;
- street/public-state decomposition;
- neural/tabular hybrid only where measured CPU efficiency warrants it.

Never enumerate the literal full 6-max game tree.

Exit gate: stable held-out performance across positions, stack depths, boards and seeds with no unresolved representation/action debt.

## R8 — Physical Ryzen 9 calibration
Status: **PENDING**

No R3/R4/R5 physical selection workload is currently running on the Ryzen. Hosted GitHub Actions evidence does not satisfy this gate.

Measure on the actual target machine:

- worker count and contention;
- batch size;
- RAM footprint;
- disk/checkpoint throughput;
- per-module throughput;
- equal-wall-clock R3/R4/R5 finalist comparisons.

Freeze a production budget with reserve for validation/reruns rather than consuming the full three-month envelope in one monolithic run.

## R9 — Production training
Status: **BLOCKED UNTIL R1–R8 PASS**

Maximum intended envelope: approximately three months on the Ryzen 9.

Production checkpoints are continuously evaluated by marginal strategic gain per CPU-hour. Final policy/model hashes and provenance are immutable artifacts.

## R10 — Strategic audit
Status: **PENDING**

Audit positional/action frequencies, sizing distributions, equivalent-state consistency, OOD behavior, adversarial policies, self-play cross-seed stability and regression sentinels.

Exit gate: no unexplained high-impact strategic anomaly.

## R11 — Opponent/pool data pipeline
Status: **PENDING**

Adapt AoF lessons to cash complexity:

- persistent identity/aliases;
- uncertainty-preserving action reconstruction;
- stats by position/street/node/size/stack/board family;
- pool priors and player posteriors;
- shrinkage/effective sample/confidence;
- never invent ambiguous actions.

## R12 — Safe exploitation layer
Status: **PENDING**

Use hierarchical opponent models and confidence-gated local exploitation rather than one scalar frequency deviation.

Candidate mechanisms:

- range/policy perturbation;
- posterior-aware local best response/resolving;
- explicit exploit budget/regularization;
- automatic robust-blueprint fallback on insufficient confidence/state match.

Exit gate: held-out EV gain with bounded robustness loss.

## R13 — OpenHoldemCash observe/replay runtime
Status: **PENDING**

Dedicated conventional-Hold'em cash runtime/fork:

- exact scrape of cards/chips/button/actions;
- raw evidence preservation;
- conservative temporal reconstruction;
- canonical C++/Python decision contract;
- identity/database integration;
- decision logging before clicking.

Exit gate: long observe-only sessions with zero unexplained state/action mismatches.

## R14 — Autoplayer integration and safety
Status: **PENDING**

- arbitrary legal bet sizing;
- min/max clipping;
- stale-state prevention;
- duplicate-click prevention;
- timeout handling;
- fail-closed behavior;
- full decision provenance.

Exit gate: simulator/replay and controlled tests execute exactly the intended action.

## R15 — Operational homologation
Status: **PENDING**

Final freeze:

- target site/economy;
- real-hand rake/rounding validation;
- strategy/runtime/database hashes and schema versions;
- rollback package;
- watchdogs and strategic sentinels;
- incident logs.

Only R15 may set:

`READY FOR TABLES = YES`

## Immediate critical path

```text
R0 PASS
-> R1 GGPoker-reference rules/economy + universal site adapter contract (parallel)
-> R2 PASS
-> R3 strategic finalists -> physical Ryzen action comparison -> action freeze
-> R4 development -> frozen finalists -> heldout -> Ryzen -> representation freeze
-> R5 corrected sampling scaling + variance reduction -> Ryzen -> solver/traversal freeze
-> R6 resolving
-> R7 full blueprint
-> R8 physical production calibration
-> R9 production training
-> R10 audit
-> R11/R12 data + exploitation
-> R13/R14 runtime/autoplayer
-> R15 homologation
-> READY FOR TABLES
```

## North-star metric

DeepCash optimizes **practical expected value and robustness per unit of real compute**. More branches, a larger model, lower training loss or a fashionable solver are not goals by themselves.
