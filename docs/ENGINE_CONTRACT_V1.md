# DeepCash exact engine contract v1

This document freezes the first R1 implementation boundary. It is intentionally narrower than the final engine.

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
- per-player cumulative reopen logic after multiple short all-ins;
- exact rake percentage/cap with rounding deliberately separated from the poker rules.

## Important chip-state convention

`BettingRoundState.create(stacks=..., committed=...)` receives **remaining stack** in `stacks` and chips already committed on the current street in `committed`. Therefore total chips currently owned by a player on that street are `stack + committed`.

## Not yet claimed

R1 is not PASS. Still required before its exit gate:

- full-hand state machine crossing preflop/flop/turn/river;
- forced-blind posting from total stacks;
- carry-forward total contribution accounting across streets;
- all terminal fold/runout cases;
- side-pot integration into full-hand settlement;
- site-specific odd-chip ordering confirmation;
- independent evaluator/game oracle parity;
- exhaustive five-card distribution audit;
- deterministic replay/fingerprints;
- property/fuzz testing of chip conservation and action legality;
- target-site rake eligibility/cap/rounding evidence.

No unknown economy rule may be guessed by the Core. Unknown rounding remains an explicit error.
