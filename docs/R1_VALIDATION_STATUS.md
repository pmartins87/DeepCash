# R1 validation status — 2026-08-16

R1 is **IN PROGRESS**, not PASS.

The exact engine now has independent evaluator parity and deterministic full-game parity against pinned PokerKit across **2-, 3-, 4-, 5- and 6-handed** randomized traces. The remaining R1 debt is concentrated in adversarial corner cases, target-site/economy facts and later native-performance parity.

## Accepted evidence

### General deterministic CI

- run `31948882362` on commit `acd390baa75cd4f94b7bf8894ef075c1cc691152`: **PASS**;
- exact-engine foundation tests, state-machine tests, deterministic replay, randomized chip conservation and explicit multiway side-pot regressions.

### Evaluator oracle gate

- run `31948656185` on commit `7022abd66bd57b9a7fea103b38596f18ab6d60cc`: **PASS**;
- all **2,598,960** five-card combinations matched the known standard Hold'em category distribution;
- deterministic independent cross-check against pinned PokerKit `StandardHighHand`.

After adding best-of-seven caching, run `31949651215` on commit `872f99ebc82c023d54c20ef043c0653b83272cce` repeated the evaluator gate: **PASS**. The optimization did not change semantics.

### Betting/state-machine gate

Run `31948857753` on commit `45c4e03d42d068df5371f604f5b77edefaf3c1d4`: **PASS**.

- short-all-in reopening is explicit/configurable instead of hidden;
- cumulative reopen rights are tracked per prior actor;
- full raises begin a new raise-right epoch;
- dry-side-pot raises are forbidden when no live opponent with chips can respond.

### Independent full-game PokerKit gate

Fixed three-handed traces first passed in run `31949047459`:

- checkdown through river;
- raise/folds with exact uncalled return;
- preflop multiway all-in with main/side-pot settlement.

A first randomized three-handed battery then passed in run `31949099966` on commit `0040556de2a426c71c24e7afdfd577ecdf62d4f5`:

- 100 deterministic randomized hands;
- exact final-stack parity against PokerKit for every trace.

The battery was subsequently generalized to all supported player counts. The first attempt correctly exposed a **heads-up positional mapping mistake in the cross-check harness**, not in the engine: PokerKit's HU convention has its final indexed player acting first preflop as Button/SB. The harness was corrected rather than masking the mismatch.

Run `31950636248` on commit `9a23e2fba9775771e3b2a5fe1eb5450989d52032`: **PASS**.

The accepted generalized battery contains:

- 25 deterministic randomized hands for each player count from 2 through 6;
- **125 randomized full-game traces total** plus the fixed regression traces;
- random unique hole/board cards and variable stacks;
- every action selected from DeepCash's legal-action boundary and mirrored into PokerKit;
- synchronized street transitions and all-in runouts;
- exact final-stack equality for every completed hand.

This is independent evidence for seating/blind/action order, fold/check/call/raise-to semantics, street progression, all-in runout, uncalled returns, side pots and settlement across the entire supported 2–6 handed range.

## Why R1 is still not PASS

The generic conventional NLHE engine is now strongly cross-checked, but production semantics still depend on facts that must be frozen from the target games rather than guessed:

1. adversarial multi-all-in/short-raise/reopen edge cases beyond the current randomized sample;
2. target-site short-all-in/reopen behavior;
3. target-site odd-chip allocation order;
4. target-site rake eligibility, cap, rounding and timing;
5. incomplete blind/straddle/ante behavior if relevant to the selected games;
6. cross-language/native evaluator parity before a performance-critical production engine is frozen.

The Core keeps these as explicit configuration/debt instead of silently promoting conventional assumptions to target-site facts.

## Next R1 work

R1 may continue in parallel with R3/R4 engineering. Before R1 PASS:

- add focused adversarial fixtures for cumulative short raises and complex multiway side pots;
- parameterize any remaining site-dependent settlement rule;
- freeze the target cash-game economy from authoritative/client evidence once the target games are selected;
- add native evaluator parity when optimization becomes justified.

`R1 = IN PROGRESS`

`READY FOR TABLES = NO`
