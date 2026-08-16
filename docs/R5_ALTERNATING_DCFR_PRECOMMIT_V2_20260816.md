# R5 alternating CFR+ / DCFR control v2 — corrected precommit 2026-08-16

**v1 is invalidated before numerical-result consumption.**

After launching the first alternating/DCFR workflow, a source-level literature implementation audit found that v1's average-strategy timing was not faithful to alternating CFR as implemented in the reference-style algorithm: v1 accumulated both players' averages only after both regret half-updates. No v1 numerical result was inspected or accepted.

The Brown & Sandholm paper states that its experiments use alternating CFR updates. A source audit of OpenSpiel's DCFR implementation confirms the operational order used here: each player's cumulative policy is accumulated during that player's own traversal under the current profile, then that player's regrets are discounted/updated and the current policy is refreshed before the next player's traversal.

This v2 precommit replaces v1 for numerical acceptance.

## Corrected frozen global iteration `t`

1. derive the current strategy profile;
2. accumulate **P0's** average-strategy contribution using P0 own realization reach and the current profile;
3. traverse the exact full chance/action tree for P0 counterfactual regrets;
4. apply P0 regret update/discount and refresh the strategy profile;
5. accumulate **P1's** average-strategy contribution using P1 own realization reach and this refreshed profile;
6. traverse the exact full chance/action tree for P1 regrets;
7. apply P1 regret update/discount and refresh policy for the next global iteration.

The output average is therefore player-local to the profile actually used for that player's alternating traversal, rather than a synthetic post-both-updates profile.

## Frozen variants

Unchanged from v1:

- `ALT_CFR_PLUS_LINEAR` — RM+ clipping, output contribution weight `t`;
- `ALT_CFR_PLUS_QUADRATIC` — RM+ clipping, output contribution weight `t^2`;
- `ALT_DCFR_150_0_2` — alpha=1.5, beta=0, gamma=2;
- `ALT_DCFR_150_050_2` — alpha=1.5, beta=0.5, gamma=2.

DCFR regret semantics remain:

- add instantaneous regret during the player's traversal;
- positive resulting cumulative regret × `t^alpha/(t^alpha+1)`;
- negative resulting cumulative regret × `t^beta/(t^beta+1)`.

DCFR cumulative-policy contribution is added directly with weight `t^gamma`, which is equivalent to the paper's relative output weighting and matches the audited implementation style.

## Same-run comparator

Existing synchronous `CFR_PLUS_LINEAR` remains included unchanged.

## Correctness gates added/retained

- staged == monolithic for all variants;
- JSON checkpoint future-path equality;
- wrong game/variant and non-finite state fail closed;
- direct alpha/beta/gamma factor fixtures;
- P0 half-step cannot mutate P1 regrets and vice versa;
- player-local average accumulator changes only the requested player's policy sums;
- P0 response-node average uses P0's own root-CHECK realization reach;
- linear vs quadratic output weighting is materially distinct;
- a two-half-step unit fixture verifies P1 average is taken **after P0 refresh but before P1 refresh**.

## Numerical battery

Unchanged:

- four R3 control boards;
- 6 exact combos/player;
- phases 0.00/0.27;
- pot 100;
- stack 400 / SPR 4;
- 25% / 50% / 100% river bet family;
- checkpoints 100 / 400 / 1200;
- exact BR evaluation.

Any v1 artifact is audit history only and cannot be accepted. Only a workflow launched after the v2 code correction may supply numerical evidence.

`R5 alternating/DCFR v2 = PRECOMMITTED`

`R5 production solver = NOT SELECTED`
