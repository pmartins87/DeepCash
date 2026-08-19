# R6 turn betting exact-control precommit — 2026-08-19

This precommit freezes the acceptance question for the first exact turn-betting control before any numerical convergence result is consumed.

## Frozen question

Can DeepCash compose a deterministic heads-up turn betting tree with exact public river chance and river betting while preserving exact card removal, pot/stack transitions, action-conditioned range reach and the audited `ALT_DCFR_150_0_2` update semantics?

## Acceptance conditions

The structural gate passes only if all of the following hold:

- turn and river action geometry is deterministic and derived from the correct street-local pot/stack;
- turn all-in calls remove river decision nodes and continue through exact public river chance to showdown;
- an independently computed all-check showdown path matches policy evaluation exactly within floating-point tolerance;
- action-conditioned ranges are generated from own realization reach only and exact public-card removal;
- no realized opponent private hand enters an infoset key or individual range-reach calculation;
- repeated deterministic execution is identical;
- continuing one iteration at a time yields the same state as the same total iteration count in one call;
- the full repository CI remains green.

## Non-acceptance claims

Passing this gate will not mark R6 PASS and will not select a production two-street abstraction. It will establish only the exact-control foundation required for the next precommitted gate: exact two-street best response/exploitability, followed by production-representation compatibility and bounded-latency resolving.
