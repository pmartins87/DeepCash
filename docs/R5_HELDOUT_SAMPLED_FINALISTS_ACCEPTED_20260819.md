# R5 sampled-finalist held-out v1 — accepted 2026-08-19

Status: **PASS / ADVANCE TO PHYSICAL RYZEN CROSSOVER / PRODUCTION SOLVER NOT YET SELECTED**

## Frozen evidence identity

- workflow run: `32220043090`;
- published evidence commit: `e001fe3193ef662ad63d4c1d703b1be7798d391e`;
- schema: `DEEPCASH_R5_HELDOUT_SAMPLED_FINALISTS_V1`;
- artifact status: `COMPLETE_HELDOUT_EVIDENCE_NOT_PHYSICAL_SELECTION`;
- source contract: `docs/R5_HELDOUT_SAMPLED_FINALISTS_PRECOMMIT_20260819.md`.

The held-out coordinates were frozen before numerical execution: four fresh boards, exact supports 8/24/48 combos per player, phases 0.27/0.73, seeds 401/503/607, pot 100, bet sizes 25/50/100 and exactly 15 seconds of cumulative hosted training per cell. The only sampled finalists were `CCS_CFR_PLUS_LINEAR` and `ES_ZERO`.

## Completeness and timing audit

Expected rows: `4 boards × 3 supports × 3 seeds × 2 comparators = 72`.

The evidence is complete and its frozen decision reports zero timing-quality flags. Total hosted wall time was approximately `1341.2291 s`. Evaluation remained outside the 15-second training budget.

## Frozen acceptance result

The precommitted acceptance rule required, at every support, CCS mean exploitability/pot no greater than ES_ZERO and at least 7/12 strict paired wins, plus at least 27/36 wins overall.

Observed:

| support | CCS mean exploit/pot | ES_ZERO mean exploit/pot | paired wins CCS | required |
|---:|---:|---:|---:|---:|
| 8 | **0.003007570** | 0.007925855 | **12/12** | 7/12 |
| 24 | **0.010948240** | 0.020303948 | **12/12** | 7/12 |
| 48 | **0.022544374** | 0.035560960 | **12/12** | 7/12 |

Overall CCS won **36/36** paired board × seed cells; the frozen minimum was 27/36. Mean paired `CCS - ES_ZERO` exploitability/pot was `-0.0090968599`, median `-0.0091796356`.

Worst exploitability/pot also favored CCS at every support:

- support 8: CCS `0.003216095` vs ZERO `0.008688043`;
- support 24: CCS `0.011819351` vs ZERO `0.022331516`;
- support 48: CCS `0.024824607` vs ZERO `0.037808645`.

This is a decisive held-out generalization PASS for the sampled finalist comparison.

## Accepted interpretation

`CCS_CFR_PLUS_LINEAR` advances as the sampled challenger. `ES_ZERO` remains the mandatory physical baseline/control. The result does not erase the exact `ALT_DCFR_150_0_2` control: that algorithm remains the strongest accepted exact tabular control and must participate in the physical crossover because the hosted sampled-finalist battery did not compare sampled traversal against it.

The production R5 outcome may legitimately be a crossover architecture rather than one solver everywhere: use the least stochastic traversal that wins or remains competitive at the actual target-machine state/chance support. The crossover coordinate must be measured on the Ryzen and must not be inferred from hosted runners.

## Next gate

Freeze and execute a physical Ryzen equal-compute/crossover protocol containing:

1. `ALT_DCFR_150_0_2` exact alternating control;
2. `CCS_CFR_PLUS_LINEAR` sampled challenger;
3. `ES_ZERO` sampled control.

The physical protocol must record machine identity, affinity, peak memory, actual training wall clock, exact strategic evaluation, checkpoints and immutable hashes. No physical result may be consumed before its coordinates and decision rules are frozen.

`R5 sampled-finalist held-out v1 = PASS`

`R5 production solver/traversal = NOT YET FROZEN`

`NEXT = PHYSICAL RYZEN CROSSOVER`
