# DeepCash exact engine contract v1

This document freezes the current R1 implementation boundary. It is intentionally narrower than the final production engine.

## Exact, already represented

- conventional 52-card codec;
- standard Hold'em hand ordering including wheel A2345;
- best five out of 5/6/7 cards;
- 2–6 handed button/blind/action-order rules including the HU button/SB exception;
- side-pot tranches from exact integer contributions;
- unmatched/uncalled top contribution removed before contested-pot/rake accounting;
- deterministic split-pot and odd-chip allocation given an explicit odd-chip order;
- one-street no-limit state machine with fold/check/call/raise-to;
- minimum full raise tracking;
- short all-in raise support;
- explicit short-all-in reopen policy (`NEVER`, `ANY_INCREASE`, `CUMULATIVE_FULL_RAISE`);
- cumulative reopen measured per prior actor instead of inferred globally;
- dry-side-pot protection: a player cannot bet/raise when no live opponent with chips can respond;
- exact rake percentage/cap with rounding deliberately separated from poker legality;
- deterministic preflop/flop/turn/river hand state machine for fully supplied cards;
- blind posting, street transitions, fold terminals and automatic all-in runouts;
- gross side-pot settlement before rake;
- action records, replay and SHA-256 state fingerprints;
- deterministic randomized legal-hand tests for chip conservation and replay identity;
- exhaustive five-card category distribution gate plus independent PokerKit evaluator cross-check.

## Important chip-state convention

`BettingRoundState.create(stacks=..., committed=...)` receives **remaining stack** in `stacks` and chips already committed on the current street in `committed`. Therefore total chips currently owned by a player on that street are `stack + committed`.

## Reopen policy is not silently assumed

The default research configuration is `CUMULATIVE_FULL_RAISE`, matching the conventional cash-rule interpretation we intend to test. It is **not yet a target-site fact**. The rule is therefore a first-class `BettingConfig` field and must be frozen from authoritative/observed target-site evidence before production use.

## Deliberate v1 restriction

`HandSetup` currently requires every dealt stack to cover at least one full big blind. Incomplete forced-blind edge cases will not be guessed; they remain a later R1 contract item.

## Not yet claimed

R1 is not PASS. Still required before its exit gate:

- deeper independent full-game oracle parity, not only evaluator parity;
- deeper property/fuzz coverage for side pots, multi-all-in and reopen corner cases;
- incomplete blind/straddle/ante policy decisions if the target economy requires them;
- target-site short-all-in/reopen rule confirmation;
- target-site odd-chip ordering confirmation;
- target-site rake eligibility/cap/rounding evidence;
- cross-language/native evaluator parity before performance-critical production use.

No unknown economy or site-specific rule may be guessed by the Core. Unknown rounding remains an explicit error.
