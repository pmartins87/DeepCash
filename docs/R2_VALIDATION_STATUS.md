# R2 canonical-state validation status — 2026-08-16

R2 is **PASS** for the exact canonical decision-state boundary.

This does not freeze the future neural/private-state encoder. R4 will still decide what lossy representation, if any, is worth using. R2 only proves that the lossless state handed to those later abstractions does not waste capacity on trivial physical equivalences and does not silently erase strategic geometry.

## Accepted boundary

`deepcash_core.canonical_state.DecisionSnapshot` preserves:

- exact current actor;
- exact private hole cards for the actor only;
- exact public board by street;
- exact stack and total/street commitment for every player;
- exact pot and amount to call;
- exact minimum legal full-raise target when raising is available;
- ordered actor-aware action history;
- exact action monetary context (`paid`, `pot_before`, `to_call_before`, `current_bet_before`, actor commitment and minimum full raise before the action).

`decision_snapshot_from_hand_state` projects a real non-terminal `HandState` into that boundary. Although the simulator knows every hole card for showdown, the decision projection deliberately exposes **only the current actor's private cards**.

## Invariances guaranteed by construction

`canonical_decision_key` canonicalizes:

1. hero hole-card order;
2. simultaneous flop-card order;
3. all global suit renamings;
4. physical chair labels/rotations while preserving clockwise order and Button-relative geometry.

It does **not** bucket pot, call, stack, commitments, raise targets or historical action amounts.

## Metamorphic evidence

Run `31949413618` on commit `76988a4ebadf3cb5f8df51a73d082d1d7d3dcdd1`: **PASS**.

The accepted tests include:

- exhaustive all-24 global suit permutations on a frozen nontrivial state;
- both hole-card orders;
- all six permutations of the three simultaneous flop cards;
- Button-relative physical chair relabeling;
- exact-geometry anti-alias checks: changing pot/call/min-raise/stack by one chip changes the key;
- actor/action order and action monetary geometry remain semantic;
- real `HandState -> DecisionSnapshot` projection;
- explicit opponent-private-card leakage regression;
- deterministic randomized **2-, 3-, 4-, 5- and 6-handed** metamorphic states across preflop, flop, turn and river.

## Action-history rule

R2 intentionally does not invent broad action-history equivalences. The only history transformations canonicalized are those proven to be physically irrelevant, such as consistent chair relabeling. Different ordered actions or different exact sizing geometry remain different states.

This is conservative by design. Later R4 encoders may compress history only after an ablation proves that the compression buys enough compute without unacceptable strategic loss.

## Exit decision

The R2 exit criterion is satisfied:

> equivalent physical states map to the same exact canonical key, strategically different chip/action geometry remains distinguishable, and the engine-to-boundary adapter does not leak hidden opponent cards.

Therefore:

`R2 = PASS`

`READY FOR TABLES = NO`
