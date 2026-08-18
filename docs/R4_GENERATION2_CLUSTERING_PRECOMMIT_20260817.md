# R4 Generation-2 clustering precommit — 2026-08-17

Status: **FROZEN CANDIDATE POOL / DEVELOPMENT NOT RUN / HELD-OUT-V2 UNSEEN**

Generation-1 held-out-v1 is permanently consumed. This document freezes the next R4 representation experiment before any Generation-2 development result is consumed.

## Goal

Test whether a deterministic clustering representation can improve the fidelity/compression frontier beyond the Generation-1 deterministic feature buckets while preserving the same strict information boundary.

`equity8` remains the Generation-1 deterministic accuracy anchor. Generation-2 adds only clustering candidates. A counterfactual-value family is **not** silently introduced here: it is deferred unless a legal, runtime-computable construction is frozen in a separate future generation before numerical use.

## Information boundary

Generation-2 clustering may use only:

- public board cards;
- the acting player's own exact private combo;
- the modelled opponent range and combo weights;
- exact card-removal compatibility;
- exact showdown outcome against range support.

It may not use:

- the realized opponent private hand;
- solved opponent policy;
- future sampled actions;
- privileged hidden state;
- held-out-v2 results;
- post-hoc feature tuning after development consumption.

The exact game/chance/payoff state remains uncompressed. Only solver information-state identity is aliased.

## Frozen candidate pool

1. `equity8` — unchanged Generation-1 accuracy anchor;
2. `matchup_cluster4` — deterministic weighted k-medoids over exact matchup-profile distance, nominally four buckets;
3. `matchup_cluster8` — same construction, nominally eight buckets;
4. `equity4_matchup2` — product of four exact card-removal equity quantiles and two matchup clusters.

No candidate may be added to this generation after the first development result is consumed.

### Matchup-profile distance

For each exact private combo, construct its showdown profile against every combo in the modelled opponent range. An opponent combo contributes:

- exact showdown score `0 / 0.5 / 1` when compatible;
- an explicit incompatibility state when blocked by the player's private cards.

Distance between two private combos is the opponent-weighted mean disagreement across this profile. A compatible/incompatible mismatch counts as full disagreement. This lets the clustering observe strategically relevant card removal without learning or receiving the realized opponent hand.

Clustering is deterministic weighted k-medoids:

- global weighted medoid initialization;
- deterministic farthest-first medoid expansion;
- deterministic medoid refinement;
- stable tie-breaking;
- fewer materialized buckets allowed when the range contains fewer distinct matchup profiles.

## Frozen stack/action geometry

Generation-1 audit found that its nominal SPR2 and SPR4 jobs materialized the same one-bet action set. Generation-2 fixes that experimental weakness before numerical use.

Pot = `100`; min bet = `20`; stack = `100 / 200 / 400`; frozen reference fractions:

`25%, 50%, 100%, 200%, 400%`.

Therefore the physical action sets are intentionally distinct:

- SPR1: `[25, 50, 100]`;
- SPR2: `[25, 50, 100, 200]`;
- SPR4: `[25, 50, 100, 200, 400]`.

This remains a tractable river one-bet laboratory, not a production street tree. Physical production selection still requires street/stack-compatible Ryzen evidence.

## Frozen development coordinates

Development uses eight already-seen/consumed boards only. It does not consume any Generation-2 unseen board.

- range combos/player: `8`;
- phase A: `p0=0.19`, `p1=0.47`;
- phase B: `p0=0.58`, `p1=0.83`;
- SPR: `1 / 2 / 4`;
- checkpoints: `300 / 1200 / 3600`;
- exact-combo common reference;
- one-sided private-state restriction loss before joint compression metrics.

The machine-readable freeze is `deepcash_core/data/r4_representation_generation2_v1.json`.

## Held-out-v2 firewall

Eight new boards are frozen in `deepcash_core/river_representation_gen2_fixtures.py` before the development run. They are disjoint from earlier R4 boards by both name and physical five-card set.

Held-out-v2 status: **FROZEN_UNSEEN_DO_NOT_RUN**.

After development:

1. inspect every development cell and artifact;
2. select at most three finalists under conservative fidelity/compression/compute Pareto evidence;
3. record a finalist freeze;
4. only then permit held-out-v2 consumption.

No post-hoc scalar score will be invented to force a winner.

## Development selection metrics

At the shared final checkpoint, audit at least:

- worst conservative restriction-loss upper bound / pot;
- mean upper bound / pot;
- P90 upper bound / pot;
- value-interval width / pot;
- materialized bucket compression;
- action-slot ratio;
- wall-clock training time;
- per-board/per-phase/per-SPR paired behavior;
- checkpoint convergence.

`equity8` is the fixed accuracy anchor. A clustering candidate must provide a meaningful fidelity/compression or fidelity/compute advantage to survive.

## Production boundary

Even a successful Generation-2 held-out-v2 remains engineering evidence. R4 cannot PASS until serious finalists receive physical Ryzen equal-wall-clock comparison on a representative street/stack architecture and one production representation is explicitly frozen.

R9 remains BLOCKED until R1-R8 PASS.
