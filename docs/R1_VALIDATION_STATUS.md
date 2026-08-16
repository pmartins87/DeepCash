# R1 validation status — 2026-08-16

R1 is **IN PROGRESS**, not PASS.

## Accepted evidence

### General deterministic CI

- run `31948882362` on commit `acd390baa75cd4f94b7bf8894ef075c1cc691152`: **PASS**;
- includes canonicalization/action tests, exact-engine foundation tests, state-machine tests, deterministic full-hand replay, randomized legal-hand chip conservation and explicit multiway side-pot regressions.

### Evaluator oracle gate

- run `31948656185` on commit `7022abd66bd57b9a7fea103b38596f18ab6d60cc`: **PASS**;
- exhaustive category audit enumerated all **2,598,960** five-card combinations and matched the known standard Hold'em distribution;
- independent deterministic cross-check used pinned PokerKit commit `5841c0afe4d6eb71ae5db0f8a6a376ee3e329afb` and `StandardHighHand`.

### State-machine correction gate

- run `31948857753` on commit `45c4e03d42d068df5371f604f5b77edefaf3c1d4`: **PASS**;
- short all-in reopening is now an explicit configurable rule instead of a hidden assumption;
- a prior actor can regain raise rights under the configured cumulative policy, but the engine independently forbids a raise into a dry side pot when no opponent with chips can respond;
- a full raise starts a new raise-right epoch for the other live players.

## Why R1 is not PASS yet

The evaluator is independently gated, but the **complete game lifecycle** is not yet independently cross-checked against an external rules engine. Target-site-dependent facts also remain intentionally unresolved:

1. short-all-in/reopen behavior;
2. odd-chip allocation order;
3. rake eligibility, cap and rounding/timing;
4. incomplete blind/straddle/ante behavior if relevant to the selected games.

The Core must not convert these unknowns into silent defaults for production.

## Next R1 work

- add independent full-game trace/oracle fixtures;
- increase adversarial/property testing of multiway all-ins, folds, side pots and cumulative short raises;
- freeze target cash-game economy from authoritative/client evidence when selected;
- only after those gates consider native evaluator acceleration and R1 PASS.
