# R1 validation status — 2026-08-16

R1 is **IN PROGRESS**, not PASS.

The important change from the first status is that the game lifecycle now has a real independent rules-engine gate; the remaining debt is broader coverage and site/economy facts, not absence of an external full-game oracle.

## Accepted evidence

### General deterministic CI

- run `31948882362` on commit `acd390baa75cd4f94b7bf8894ef075c1cc691152`: **PASS**;
- includes exact-engine foundation tests, state-machine tests, deterministic full-hand replay, randomized legal-hand chip conservation and explicit multiway side-pot regressions.

Latest integrated CI at the beginning of R3:

- run `31949683720` on commit `2640371563cd40067eb5f370af30ee123aaddb21`: **PASS**.

### Evaluator oracle gate

- run `31948656185` on commit `7022abd66bd57b9a7fea103b38596f18ab6d60cc`: **PASS**;
- exhaustive category audit enumerated all **2,598,960** five-card combinations and matched the known standard Hold'em distribution;
- independent deterministic cross-check used pinned PokerKit commit `5841c0afe4d6eb71ae5db0f8a6a376ee3e329afb` and `StandardHighHand`.

After adding a cache for repeated best-of-seven evaluations, the same gate was rerun unchanged:

- run `31949651215` on commit `872f99ebc82c023d54c20ef043c0653b83272cce`: **PASS**.

The cache therefore changed performance, not evaluator semantics.

### State-machine correction gate

- run `31948857753` on commit `45c4e03d42d068df5371f604f5b77edefaf3c1d4`: **PASS**;
- short all-in reopening is an explicit configurable rule instead of a hidden assumption;
- a prior actor can regain raise rights under the configured cumulative policy, but the engine independently forbids a raise into a dry side pot when no opponent with chips can respond;
- a full raise starts a new raise-right epoch for the other live players.

### Independent full-game PokerKit gate

The pinned PokerKit rules engine is now used beyond hand evaluation.

Fixed traces:

- run `31949047459`: **PASS**;
- three-way checkdown through river;
- raise followed by folds with exact uncalled-bet return;
- preflop multiway all-in with main/side-pot settlement.

Randomized trace battery:

- run `31949099966` on commit `0040556de2a426c71c24e7afdfd577ecdf62d4f5`: **PASS**;
- **100 deterministic randomized three-handed hands**;
- random unique cards and variable stacks;
- every action chosen from DeepCash's legal-action boundary and mirrored into PokerKit;
- board streets synchronized after betting transitions/all-in runout;
- exact final-stack equality required for every trace.

This is meaningful independent evidence for blind posting, action order, call/raise-to semantics, fold terminals, all-in runout, uncalled returns and side-pot accounting.

## Why R1 is still not PASS

The current external full-game battery is three-handed and deliberately bounded. It does not yet prove every 2–6 handed corner case. In addition, several facts are site/economy dependent and must not be invented:

1. broaden full-game independent parity across 2–6 handed and more adversarial multi-all-in/reopen traces;
2. target-site short-all-in/reopen behavior;
3. target-site odd-chip allocation order;
4. target-site rake eligibility, cap, rounding and timing;
5. incomplete blind/straddle/ante behavior if relevant to the selected games;
6. cross-language/native evaluator parity before a performance-critical production engine is frozen.

The Core will keep these as explicit configuration/debt rather than silently treat a conventional rule as a proven target-site fact.

## Next R1 work

R1 may progress in parallel with the representation/action laboratories. Before R1 PASS:

- expand external full-game traces to 2–6 handed and adversarial side-pot/reopen cases;
- parameterize any remaining site-dependent settlement rule that should not live as a hard-coded assumption;
- freeze the target cash-game economy from authoritative/client evidence once the target games are selected;
- add native evaluator parity when optimization becomes justified.
