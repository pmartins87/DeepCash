# R6 exact turn+river best-response precommit — 2026-08-19

Status: **FROZEN BEFORE NUMERICAL CONSUMPTION**

This gate adds the correctness oracle required before the exact two-street R6 control can be used for convergence claims or compared with a lossy production representation.

## Frozen question

Can DeepCash compute an exact best response to an arbitrary fixed policy in the current heads-up turn+river control without allowing the responder to condition on the realized opponent private hand?

## Oracle contract

The best-response player may condition only on:

- its own exact private combo;
- the exact public turn board;
- the observed public turn action history;
- the exact public river card after chance;
- the observed public river action history.

The responder may **not** condition an action on the realized opponent private combo. Opponent private states are integrated inside each information set using normalized root private-deal mass, exact public-chance probability and the fixed opponent policy's realization reach.

## Frozen implementation method

Use a finite exact game tree for the existing one-bet-per-street control and solve best response by information-set dynamic programming:

1. enumerate every compatible exact private deal with its normalized chance mass;
2. enumerate exact public river chance for each deal;
3. multiply counterfactual reach only by chance and the fixed opponent's action probabilities;
4. do **not** multiply counterfactual reach by the best-response player's own earlier actions;
5. process best-response information sets from deepest to shallowest;
6. at each information set, aggregate each candidate action's P0 utility across every hidden-opponent occurrence in that information set;
7. choose max utility for a P0 best response and min utility for a P1 best response, with deterministic lowest-index tie breaking;
8. evaluate the resulting deterministic best-response plan against the fixed opponent policy over the full exact game.

This is the standard counterfactual best-response construction for a perfect-recall finite game and preserves one action per information set across all compatible opponent private hands.

## Acceptance conditions

The gate passes only if:

- every fixed policy is validated as finite, non-negative and normalized at every exact information set;
- BR actions are keyed only by `(player, public-node, own-hand-index)`;
- hidden opponent hands are aggregated rather than used as action keys;
- private-deal chance, public-river chance and opponent policy reach are included in information-set action values;
- BR0 value is never below the fixed policy self-play value beyond numerical tolerance;
- P0 value against BR1 is never above the fixed policy self-play value beyond numerical tolerance;
- exploitability is reported as `max(0, (BR0 - BR1) / 2)` and normalized by the initial turn pot only for the diagnostic ratio;
- deterministic repeated execution returns identical action selections and values;
- a separately written singleton-range perfect-information oracle agrees with the information-set BR result;
- the existing turn+river structural tests and full repository CI remain green.

## Scope boundary

Passing this gate will validate exact two-street exploitability measurement for the tractable R6 control. It will **not** mark R6 PASS, select a production solver, insert `matchup_cluster8` into the two-street path, prove bounded local-resolving latency, or authorize R9.

The next gate after this one is production-representation compatibility against this exact oracle on frozen tiny turn+river games.
