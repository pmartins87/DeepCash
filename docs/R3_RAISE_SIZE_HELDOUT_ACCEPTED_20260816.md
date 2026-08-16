# R3 raise-size held-out evidence — accepted 2026-08-16

This document records the inspected independent raise-size held-out generation from workflow run `31962687271` plus its repaired cross-SPR postprocessor run `31964700344`.

R3 remains **IN PROGRESS**. This evidence narrows the engineering candidate family but does **not** freeze production actions. Physical Ryzen equal-compute evidence is still mandatory.

## Precommitted experiment

The held-out generation was frozen before its results were consumed:

- board set: `raise_size_heldout`;
- six unseen river boards;
- 6 exact combos/player;
- range phases 0.22 / 0.68;
- pot 100;
- stacks 100 / 200 / 400 => SPR 1 / 2 / 4;
- checkpoints 300 / 1200 / 3600;
- reference raise family: 50%, 100%, 150% of pot-after-call, geometrically clipped;
- candidates: `Q1_100`, `Q2_50_100`, `Q2_100_150`, `Q3_50_100_150`;
- exact cards/chance/payoff tree retained; only one player's raise targets are restricted in each common-reference comparison.

All three expensive matrix cells completed successfully and uploaded artifacts:

- SPR 1 artifact `9267994573`, SHA-256 `d0c715178bf8f905018f8d59f316ddc5f98540d6d30292fa8700b0bd78d2b68d`;
- SPR 2 artifact `9268089087`, SHA-256 `24f25a68a5a8e63f0d51bfc5ecfea2b381b163871b92d5a517028d1917cccee0`;
- SPR 4 artifact `9268068340`, SHA-256 `bdda835b97924ea393295df38bdaf1bb0d16e31273adee13feebd2de760d76fb`.

## Postprocessor failure and repair

The original workflow's final `summarize` job failed for an operational reason only: the workflow referenced `tools/summarize_raise_size_heldout.py`, but that file did not yet exist at the source commit. The three numerical matrix jobs themselves had already completed successfully.

The failure was not ignored and the expensive cells were not rerun merely to obtain a green badge. A fail-closed summarizer was added:

- `deepcash_core/raise_size_summary.py`;
- `tools/summarize_raise_size_heldout.py`;
- `tests/test_raise_size_heldout_summary.py`.

It validates schema, complete candidate set, unique/required SPR cells, common latest checkpoints and non-negative finite metrics. It applies no post-hoc strategic threshold.

A dedicated postprocessor workflow downloaded the already-completed immutable artifacts from run `31962687271` and summarized them without retraining:

- workflow run `31964700344`: **PASS**;
- source commit `96efc3a243e3b45cd91d56d139b1d91ca87e5474`;
- summary artifact `9268162754`;
- summary artifact SHA-256 `a77790aefe7e255f0d4ec7a76cbdb2c8d7331432ab664583036888695734f9b5`.

General CI for the same commit also passed in run `31964700348`.

## Final checkpoint evidence

All values below are conservative restriction-loss upper bounds per pot at checkpoint 3600. The interval column is the remaining exact-BR value-interval resolution.

### SPR 1

All four nominal candidates geometrically collapse to the same materialized raise tree. Consequently their strategic numbers are identical.

| Candidate | mean upper | worst upper | mean interval | worst interval |
|---|---:|---:|---:|---:|
| Q1_100 | 0.00096270 | 0.00184060 | 0.00096270 | 0.00184060 |
| Q2_50_100 | 0.00096270 | 0.00184060 | 0.00096270 | 0.00184060 |
| Q2_100_150 | 0.00096270 | 0.00184060 | 0.00096270 | 0.00184060 |
| Q3_50_100_150 | 0.00096270 | 0.00184060 | 0.00096270 | 0.00184060 |

This is a useful geometric invariant: DeepCash must not pay representation/training cost for nominal branches that clip to the same physical action.

### SPR 2

| Candidate | mean upper | worst upper | mean interval | worst interval | resolved worst excess |
|---|---:|---:|---:|---:|---:|
| Q1_100 | 0.00125188 | 0.00542334 | 0.00078196 | 0.00254006 | 0.00288328 |
| Q2_50_100 | 0.00073065 | 0.00240061 | 0.00074157 | 0.00254006 | 0.00000000 |
| Q2_100_150 | 0.00125565 | 0.00561036 | 0.00078007 | 0.00262026 | 0.00299011 |
| Q3_50_100_150 | 0.00073903 | 0.00254006 | 0.00073903 | 0.00254006 | 0.00000000 |

The two families that omit the 50% raise (`Q1_100` and `Q2_100_150`) show resolved loss beyond the remaining exact-BR interval. `Q2_50_100` remains resolution-limited and is slightly cheaper than the full Q3 family.

### SPR 4

| Candidate | mean upper | worst upper | mean interval | worst interval | resolved worst excess |
|---|---:|---:|---:|---:|---:|
| Q1_100 | 0.00342306 | 0.01109559 | 0.00103177 | 0.00309862 | 0.00799696 |
| Q2_50_100 | 0.00075892 | 0.00235825 | 0.00077817 | 0.00234411 | 0.00001414 |
| Q2_100_150 | 0.00345546 | 0.01123168 | 0.00125750 | 0.00360103 | 0.00763065 |
| Q3_50_100_150 | 0.00076439 | 0.00234411 | 0.00076439 | 0.00234411 | 0.00000000 |

Again the 50% raise is the important retained branch in this held-out generation. Removing 150% while keeping 50%+100% produces only a tiny worst-cell excess (`1.4139e-05 pot`) at the current resolution, while the mean upper bound is actually slightly lower than Q3's finite-iteration bound and the training cost is lower.

## Cross-SPR descriptive aggregation

The repaired summarizer intentionally computes a **descriptive**, not production-authorizing, Pareto frontier over:

1. mean conservative upper loss across SPR cells;
2. worst board upper loss across SPR cells;
3. cumulative hosted-CI training seconds.

| Candidate | mean upper | worst upper | max resolved worst excess | cumulative seconds | Pareto |
|---|---:|---:|---:|---:|---|
| Q1_100 | 0.00187922 | 0.01109559 | 0.00799696 | 1505.48 | yes |
| Q2_50_100 | 0.00081742 | 0.00240061 | 0.00001414 | 1599.41 | yes |
| Q2_100_150 | 0.00189127 | 0.01123168 | 0.00763065 | 1568.38 | no |
| Q3_50_100_150 | 0.00082204 | 0.00254006 | 0.00000000 | 1662.45 | no |

`Q2_100_150` is descriptively dominated. `Q3_50_100_150` is also descriptively dominated by `Q2_50_100` on the three aggregate objectives in this hosted-CI evidence. `Q1_100` remains on the Pareto frontier only because it is cheaper; its strategic loss at SPR 2/4 is materially resolved.

## Accepted interpretation

The independent unseen generation provides strong evidence for the following engineering conclusion:

- a 50% raise branch carries material strategic value at deeper river geometries;
- 100% alone is too coarse at SPR 2/4;
- adding 150% on top of 50%+100% has not shown a resolved strategic gain large enough to justify its extra cost in this held-out generation;
- therefore `Q2_50_100` is the **leading raise-size engineering candidate** from the current evidence.

This is **not** a production freeze. Before R3 can PASS, the project still requires:

- completion/inspection of the opening-size subset-lattice -> unseen-v2 gate;
- tightening any exact-BR cells where final candidate differences remain close to numerical resolution;
- physical equal-wall-clock measurement on the target Ryzen 9;
- a final action-family decision across street/SPR geometry, not river-only extrapolation.

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
