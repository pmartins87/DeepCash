# R5 DCFR semantics audit — 2026-08-16

A second literature audit found that the label **DCFR** hides two operational update orders that should not be conflated in DeepCash.

## What the accepted v2 implemented

`deepcash_core/river_alternating_dcfr.py` follows the same regret-discount order used by OpenSpiel's public `DiscountedCFRSolver` implementation:

1. traverse and add the current instantaneous regret to cumulative regret;
2. inspect the resulting cumulative regret's sign;
3. multiply that updated cumulative regret by the positive/negative DCFR factor.

The accepted v2 numerical evidence remains valid for that concrete algorithm. It is not discarded.

## What the 2026 HS-DCFR paper writes explicitly

Zhang, McAleer & Sandholm, *Faster Game Solving via Hyperparameter Schedules* (AAAI 2026), Equation 2, writes the DCFR recurrence as:

`R_{t+1} = R_t * d_t(sign(R_t)) + r_{t+1}`

where the **old** cumulative regret is discounted according to its old sign and the new instantaneous regret is then added. Equation 3 likewise writes cumulative strategy as old cumulative strategy discounted first, plus the current reach-weighted policy contribution.

Those recurrences are not algebraically identical to the OpenSpiel-style add-then-discount order used in DeepCash v2.

## Consequence for DeepCash

The v2 result is reclassified as an accepted **OpenSpiel-style post-update discounted control**, not as definitive evidence for the exact recurrence used by the 2026 HS paper.

In particular, the previous statement that `ALT_DCFR_150_0_2` was the leading exact tabular control is now qualified:

- it remains the leading **tested** exact discounted control so far;
- a paper-equation DCFR baseline must be implemented before the exact-control hierarchy is considered stable;
- HS-DCFR(30/15) must be built on the paper-equation recurrence, not by silently modifying the v2 post-update implementation.

This audit was performed **before any HS-DCFR DeepCash numerical result existed**.

## New gate

`docs/R5_HS_DCFR_PRECOMMIT_20260816.md` freezes a new exact generation containing:

- paper-equation DCFR(1.5, 0, 2);
- HS-DCFR(30);
- HS-DCFR(15);
- same-run alternating CFR+ and the accepted OpenSpiel-style post-update discounted control as comparators.

Only after that gate completes may DeepCash update the label of its leading exact tabular solver.

`R5 DCFR semantics = AUDITED`

`R5 production solver = NOT SELECTED`
