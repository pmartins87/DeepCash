# R1 validation status — 2026-08-16

R1 is **IN PROGRESS**, not PASS.

The generic exact NLHE engine now has independent evaluator parity, accepted 2-to-6 handed full-game PokerKit parity, focused adversarial side-pot/reopen tests, and a second expanded PokerKit battery that includes **sub-BB forced-blind stacks**. The remaining R1 debt is now concentrated much more heavily in target-site/economy facts, optional straddle/ante variants and later native-performance parity.

Failed oracle runs remain part of the audit trail. Two of them found real problems, and one later failure identified a harness synchronization difference rather than an engine semantic error.

## Accepted evidence

### General deterministic CI

- run `31948882362` on commit `acd390baa75cd4f94b7bf8894ef075c1cc691152`: **PASS**;
- exact-engine foundation tests, state-machine tests, deterministic replay, randomized chip conservation and explicit multiway side-pot regressions.

### Evaluator oracle gate

- run `31948656185` on commit `7022abd66bd57b9a7fea103b38596f18ab6d60cc`: **PASS**;
- all **2,598,960** five-card combinations matched the known standard Hold'em category distribution;
- deterministic independent cross-check against pinned PokerKit `StandardHighHand`.

After adding best-of-seven caching, run `31949651215` on commit `872f99ebc82c023d54c20ef043c0653b83272cce` repeated the evaluator gate: **PASS**. The optimization did not change semantics.

### Betting/state-machine correction gate

Run `31948857753` on commit `45c4e03d42d068df5371f604f5b77edefaf3c1d4`: **PASS**.

- short-all-in reopening is explicit/configurable instead of hidden;
- cumulative reopen rights are tracked per prior actor;
- full raises begin a new raise-right epoch;
- ordinary dry-side-pot raises into already all-in opponents are forbidden.

A later independent full-game oracle found that the dry-side-pot rule was still **too narrow**: an opponent can have chips remaining yet be unable to contest any amount above the current price because its maximum total contribution is already at or below `current_bet`. In that situation a raise also creates only an immediately uncalled excess and is therefore not a legal strategic branch.

The diagnostic trace was four-handed with current bet 1200: the only non-folded/non-all-in opponent could contribute at most 950 total. DeepCash incorrectly offered a raise; pinned PokerKit rejected it. The engine was changed so a raise requires at least one opponent whose `committed + stack > current_bet`.

Accepted correction evidence:

- commit `4b6738208e4daa0408c4b3a6af2ff1eb1a422939` — `Block raises when opponents cannot contest a higher price`;
- general CI run `31960365280`: **PASS**;
- independent full-game PokerKit run `31960365274`: **PASS**;
- explicit regression commit `8bfe751cede717fa2af6c901856dab5013407c78`;
- general CI run `31960383715`: **PASS**.

### Independent full-game PokerKit gate — ordinary stacks

Fixed three-handed traces first passed in run `31949047459`:

- checkdown through river;
- raise/folds with exact uncalled return;
- preflop multiway all-in with main/side-pot settlement.

A first randomized three-handed battery passed in run `31949099966` on commit `0040556de2a426c71c24e7afdfd577ecdf62d4f5`:

- 100 deterministic randomized hands;
- exact final-stack parity against PokerKit for every trace.

The battery was then generalized to all supported player counts. It deliberately **did not receive PASS merely because the harness existed**:

1. the first 2-to-6 attempt exposed a heads-up positional mapping error in the cross-check harness;
2. after fixing that harness mapping, later generalized runs still failed on the effectively-all-in dry-side-pot legality case described above;
3. only after correcting the DeepCash legality rule did the full generalized battery pass.

Accepted generalized run:

- run `31960365274` on commit `4b6738208e4daa0408c4b3a6af2ff1eb1a422939`: **PASS**;
- 25 deterministic randomized hands for each player count from 2 through 6;
- **125 randomized full-game traces total** plus the fixed regressions;
- exact final-stack parity for every completed hand.

### Short-stack forced-blind semantics

R1 no longer assumes that every dealt stack covers a nominal big blind.

Before modifying the engine, a pinned PokerKit probe established conventional short-blind behavior for 50/100 NLHE:

- a BB with only 60 posts exactly 60 and the first caller owes 60;
- the nominal BB of 100 still defines the full-raise increment, so the first full raise-to is **160**, not 120 or 200;
- a short SB posts only its available chips and does not reduce a normal BB price;
- a player may call all-in for less than the current price;
- if both forced blinds are short, later players face the actual highest posted blind;
- in HU, a short SB or BB can create a hand with no further strategically meaningful betting decision.

The engine was then changed so forced blind posting is capped by the player's available stack while the nominal BB remains `min_bet` / full-raise increment. Zero-stack seats cannot be dealt into a new hand.

Dedicated DeepCash regressions cover:

- short BB actual posting + nominal-BB raise increment;
- short SB;
- both blinds short;
- short BTN calling all-in for less;
- HU short BB;
- HU short SB with uncalled BB excess returned at terminal settlement;
- rejection of zero-stack dealt seats.

General CI after those changes: run `31961651714`: **PASS**.

### Expanded independent full-game PokerKit gate — including sub-BB stacks

The randomized external oracle was expanded from 25 to **40 hands per player count** and now intentionally injects short-SB, short-BB, both-blinds-short, shallow and random 20-chip-granularity stacks. This gives **200 deterministic randomized 2-to-6 handed traces** plus the fixed regressions.

The first expanded run correctly failed on a synchronization difference. The concrete case was three-handed with stacks `(1000, 1000, 80)`: the 80-chip BTN called all-in, the SB folded, and DeepCash immediately ran the board because the BB was the only live player with chips. PokerKit exposed one additional mechanical **zero-chip CHECK** by that BB before enabling card burning. There was no alternative chip-moving action and no strategic branch missing from DeepCash.

The external harness was therefore normalized in a fail-closed way: it may consume such a PokerKit bookkeeping CHECK **only when DeepCash has already advanced and PokerKit's pending actor faces exactly zero chips**. If PokerKit requires any chip-moving action, the oracle fails instead of hiding the divergence.

Accepted expanded run:

- workflow `DeepCash full-game rules oracle sub-BB`;
- run `31961946231` on commit `8d03674495e64b563751bfa07d08e287ba066397`: **PASS**;
- **200 randomized traces, 40 per player count from 2 through 6**;
- deterministic forced short-blind fixtures plus broad shallow/random stacks;
- every real DeepCash action mirrored into pinned PokerKit;
- exact final-stack parity for every hand;
- fixed checkdown, uncalled-return and multiway-side-pot traces still pass.

The final log ends with:

`PASS randomized 2-to-6 handed trace battery with sub-BB stacks: cases=200 (40/player-count)`

This materially closes the previous generic sub-BB forced-blind debt.

### Focused adversarial gate

Dedicated run `31959996084`: **PASS**.

The focused fixtures cover:

- cumulative short raises immediately below the full-reopen threshold;
- cumulative short raises exactly at the full-reopen threshold;
- materially distinct `ANY_INCREASE` and `NEVER` policies;
- nested four-way side pots with separate eligibility layers;
- explicit odd-chip ordering.

Odd-chip settlement is fail-closed: a tie requiring odd-chip allocation must provide an order covering every tied winner, and duplicate/incomplete orders are rejected rather than falling back silently to seat order. **The target site's actual order remains unconfirmed configuration debt.**

## Why R1 is still not PASS

The conventional generic engine is now strongly cross-checked, including shallow/sub-BB stacks. Production semantics still depend on target-game facts that must not be guessed:

1. target-site short-all-in/reopen behavior;
2. target-site odd-chip allocation order;
3. target-site rake eligibility, cap, rounding and timing;
4. straddle/ante/other forced-bet variants if present in the selected target games;
5. additional adversarial/property coverage as new engine features are added;
6. cross-language/native evaluator parity before a performance-critical production engine is frozen.

The Core keeps these as explicit configuration/debt instead of silently promoting conventional assumptions to target-site facts.

## Next R1 work

R1 may continue in parallel with R3/R4 engineering. Before R1 PASS:

- preserve the expanded self-diagnosing PokerKit full-game oracle as a required regression gate;
- parameterize any remaining target-dependent settlement/forced-bet rule;
- freeze the target cash-game economy from authoritative/client evidence once the target games are selected;
- add native evaluator parity when optimization becomes justified.

`R1 = IN PROGRESS`

`READY FOR TABLES = NO`
