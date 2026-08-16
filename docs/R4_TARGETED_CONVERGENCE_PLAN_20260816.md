# R4 targeted convergence extension — frozen plan 2026-08-16

Purpose: reduce solver uncertainty on the development cells that remained ambiguous after accepted run `31964142661`. This plan is frozen before the extension is run. It does not use the R4 held-out-v1 board set and does not add new representation candidates.

## Stage 1

Common settings:
- board set: `dev`;
- 6 range combos per player;
- pot 100;
- stack 200;
- min bet 20;
- checkpoints 1200 and 3600;
- same solver and exact-BR machinery as the accepted development battery.

`stack=200` is the representative geometry because the difficult nominal SPR2 and SPR4 cases in the accepted artifact materialized the same river action tree. Re-running the identical SPR4 tree would not add independent evidence.

Targeted cells:

| board | p0 phase | p1 phase | candidates |
|---|---:|---:|---|
| `A_high_dry` | 0.00 | 0.27 | `category,equity8,equity8_blocker2` |
| `paired` | 0.11 | 0.54 | `category,equity4,equity4_blocker2,equity8` |
| `four_flush` | 0.11 | 0.54 | `category_equity4,equity4,equity4_blocker2,equity8` |
| `four_straight` | 0.00 | 0.27 | `category_equity4,equity4,equity8,equity8_blocker2` |

The eight-bucket candidates remain in selected cells as convergence/reference controls, not as preselected winners.

## Interpretation

At 3600 iterations report for each targeted candidate/cell:
1. worst one-sided restriction-loss upper bound per pot;
2. exact-BR interval width per pot;
3. change from the same cell at 1200;
4. bucket compression ratio;
5. cumulative training time.

No absolute acceptance threshold will be invented after results are known. The goal is to distinguish representation loss from solver uncertainty and decide whether development evidence is stable enough to record at most three finalists.

If a cell remains unresolved at 3600, any further extension must receive a separate frozen plan before it is executed.

## Held-out separation

R4 held-out v1 remains untouched during this stage. Its boards, phases, ranges and checkpoints remain exactly as already frozen. The held-out evaluation begins only after this stage is inspected, representation invariance gates are green, and the development finalists are explicitly recorded.
