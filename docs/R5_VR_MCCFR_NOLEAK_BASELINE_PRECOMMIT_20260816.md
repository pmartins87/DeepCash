# R5 VR-MCCFR no-private-leak baseline oracle — precommit 2026-08-16

The estimator algebra and zero/perfect-history integration oracles have passed. The next gate removes the hidden-information privilege from the baseline itself.

## Frozen information contract

A production-eligible baseline for traverser `i` may depend on:

- traverser's own exact private combo;
- public board;
- public action node/history;
- known action/pot/stack geometry;
- current public strategy/range model used by the solver.

It may **not** depend on the realized opponent private combo.

This first no-leak oracle is intentionally expensive: it computes an exact conditional expectation across every compatible opponent private combo. Its purpose is to prove the information boundary and variance-reduction potential before replacing the exact expectation with a cheap online tabular/learned approximation.

## Frozen conditional weighting on the current river tree

For a P0 traverser at P1 response nodes, opponent-hand posterior mass is the compatible P1 range mass because no prior P1 action exists before those nodes.

For a P1 traverser:

- at the P0 root, posterior P0 mass is the compatible P0 range mass;
- at a later `P0_VS_BET_x` node, public history already contains P0 CHECK, so compatible P0 range mass is multiplied by P0's current root-CHECK probability before normalization.

Any action probability contributed solely by the traverser's own already-known combo is common across hidden-opponent candidates and cancels from the posterior.

## Frozen baseline target

For each non-traverser action at the current public node:

1. enumerate every compatible hidden opponent combo allowed by the information boundary;
2. weight it by the frozen conditional posterior above;
3. evaluate the exact continuation under the current strategy profile with that public action forced;
4. average to one baseline value for the traverser's augmented infoset/action.

The resulting baseline vector must be identical for two realized histories that differ only in opponent hidden cards but are indistinguishable to the traverser.

## Mandatory correctness gates

- exact no-leak baseline equals an independent brute-force conditional hidden-hand average on frozen fixtures;
- changing only the realized opponent hidden hand cannot change the baseline vector;
- P1 `P0_VS_BET_x` posterior explicitly incorporates observed P0 CHECK reach;
- zero-posterior-mass requests fail closed rather than inventing a baseline;
- no opponent-card identity appears in the baseline key/API;
- plugging this baseline into the accepted VR action estimator preserves conditional action-sampling unbiasedness;
- all current private-card/suit invariances remain intact.

## Integration rule

Only after the standalone baseline oracle passes may it be added as `INFOSET_EXACT` to the VR external traversal. That integration must then compare:

- zero baseline;
- no-leak exact conditional baseline;
- perfect-history privileged lower bound.

The expensive exact no-leak baseline is itself **not production eligible on cost grounds**. It is the target/oracle for the later online baseline approximator.

`R5 VR-MCCFR no-leak baseline oracle = PRECOMMITTED`

`R5 production baseline = NOT SELECTED`
