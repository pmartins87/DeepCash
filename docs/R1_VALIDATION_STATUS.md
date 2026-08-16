# R1 validation status — 2026-08-16

R1 is **IN PROGRESS**, not PASS.

The exact engine has independent evaluator parity and now has an **accepted 2-to-6 handed full-game PokerKit battery**, but only after that expanded oracle exposed and forced correction of a real betting-legality bug. This chronology is intentionally preserved: failed oracle runs are evidence, not noise to hide.

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
- ordinary dry-side-pot raises into already all-in opponents are forbidden.

A later independent full-game oracle found that this last rule was still **too narrow**: an opponent can have chips remaining yet be unable to contest any amount above the current price because its maximum total contribution is already at or below `current_bet`. In that situation a raise is also illegal because it creates only an immediately uncalled excess.

The diagnostic randomized trace was four-handed with current bet 1200: the only non-folded/non-all-in opponent could contribute at most 950 total. DeepCash incorrectly offered a raise; pinned PokerKit rejected it. The engine was changed so a raise requires at least one opponent whose `committed + stack > current_bet`.

Accepted correction evidence:

- commit `4b6738208e4daa0408c4b3a6af2ff1eb1a422939` — `Block raises when opponents cannot contest a higher price`;
- general CI run `31960365280`: **PASS**;
- independent full-game PokerKit run `31960365274`: **PASS**;
- explicit regression added in commit `8bfe751cede717fa2af6c901856dab5013407c78`;
- general CI run `31960383715`: **PASS**.

### Independent full-game PokerKit gate

Fixed three-handed traces first passed in run `31949047459`:

- checkdown through river;
- raise/folds with exact uncalled return;
- preflop multiway all-in with main/side-pot settlement.

A first randomized three-handed battery passed in run `31949099966` on commit `0040556de2a426c71c24e7afdfd577ecdf62d4f5`:

- 100 deterministic randomized hands;
- exact final-stack parity against PokerKit for every trace.

The battery was then generalized to all supported player counts. The generalized gate deliberately **did not receive PASS merely because the harness existed**:

1. the first 2-to-6 attempt exposed a heads-up positional mapping error in the cross-check harness;
2. after fixing that harness mapping, later generalized runs still failed on the effectively-all-in dry-side-pot legality case described above;
3. the cross-check was instrumented to print stacks, cards, action history and both engines' local state on any rejected action;
4. only after correcting the DeepCash legality rule did the full generalized battery pass.

Accepted generalized run:

- run `31960365274` on commit `4b6738208e4daa0408c4b3a6af2ff1eb1a422939`: **PASS**.

The accepted battery contains:

- 25 deterministic randomized hands for each player count from 2 through 6;
- **125 randomized full-game traces total** plus the fixed regression traces;
- random unique hole/board cards and variable stacks;
- every action selected from DeepCash's legal-action boundary and mirrored into pinned PokerKit;
- synchronized street transitions and all-in runouts;
- exact final-stack equality for every completed hand.

This is meaningful independent evidence for seating/blind/action order, fold/check/call/raise-to semantics, street progression, all-in runout, uncalled returns, side pots and settlement across the entire supported 2–6 handed range. It is not a proof that all target-site-specific rules are known.

### Focused adversarial gate

Dedicated run `31959996084`: **PASS**.

The focused fixtures cover:

- cumulative short raises immediately below the full-reopen threshold;
- cumulative short raises exactly at the full-reopen threshold;
- materially distinct `ANY_INCREASE` and `NEVER` policies;
- nested four-way side pots with separate eligibility layers;
- explicit odd-chip ordering.

Odd-chip settlement is now fail-closed: a tie requiring odd-chip allocation must provide an order covering every tied winner, and duplicate/incomplete orders are rejected rather than falling back silently to seat order. **The target site's actual order is still unconfirmed and therefore remains configuration debt.**

## Why R1 is still not PASS

The generic conventional NLHE engine is now much more strongly cross-checked, but production semantics still depend on facts that must be frozen from the target games rather than guessed:

1. target-site short-all-in/reopen behavior;
2. target-site odd-chip allocation order;
3. target-site rake eligibility, cap, rounding and timing;
4. incomplete forced-blind/straddle/ante behavior if relevant to the selected games, especially sub-BB stack edge cases;
5. additional adversarial/property coverage beyond the current deterministic samples;
6. cross-language/native evaluator parity before a performance-critical production engine is frozen.

The Core keeps these as explicit configuration/debt instead of silently promoting conventional assumptions to target-site facts.

## Next R1 work

R1 may continue in parallel with R3/R4 engineering. Before R1 PASS:

- expand adversarial forced-blind, short-stack and side-pot fixtures;
- preserve the self-diagnosing PokerKit full-game oracle as a required regression gate;
- parameterize any remaining site-dependent settlement rule;
- freeze the target cash-game economy from authoritative/client evidence once the target games are selected;
- add native evaluator parity when optimization becomes justified.

`R1 = IN PROGRESS`

`READY FOR TABLES = NO`
