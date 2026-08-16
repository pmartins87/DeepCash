# R5 VR-MCCFR no-leak baseline oracle v1 — failed gate 2026-08-16

Workflow run `31969450992` completed with **failure**. No no-leak baseline result from v1 was accepted and no production conclusion was drawn from it.

The failure is preserved as part of the audit trail rather than overwritten.

Before retrying, the oracle implementation was rewritten as a self-contained v2 continuation evaluator (`deepcash_core/river_vr_infoset_baseline_v2.py`) instead of relying on an internal continuation helper from the existing river lab. The information contract did not change:

- traverser's own private combo is allowed;
- public board/history/node and current strategy/range model are allowed;
- realized opponent private combo is not an API input;
- hidden-opponent expectation is integrated explicitly from compatible range mass;
- P1's late posterior conditions hidden P0 mass on the publicly observed P0 CHECK probability.

The v2 tests independently reconstruct the hidden-hand weighted expectations rather than using the baseline implementation itself as its oracle.

A separate v2 workflow was launched. Until that workflow passes and is inspected:

`R5 VR-MCCFR no-leak baseline = UNACCEPTED`

`READY FOR TABLES = NO`
