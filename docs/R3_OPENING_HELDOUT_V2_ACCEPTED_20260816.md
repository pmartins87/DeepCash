# R3 opening-size held-out v2 — accepted 2026-08-16

This document accepts the complete **unseen-v2 generalization gate** that was chained only after the seen engineering lattice had already selected exactly one candidate at each cardinality. It does not retroactively change the selector and does not yet freeze the production action family.

## Firewall chronology

Source workflow:

- `.github/workflows/river-opening-subset-lattice-v1.yml`;
- run `31962334355` on source commit `723096d01cea3a2bd39869734329f81ecd480aad`: **PASS**.

Before unseen-v2 results existed, the frozen seen-data selector had already forwarded exactly:

- one size: `L1_100`;
- two sizes: `L2_50_100`;
- three sizes: `L3_25_50_100`.

The unseen-v2 generation was independently precommitted in `docs/R3_HELDOUT_V2_PRECOMMIT_20260816.md`:

- six new river board families;
- 8 exact combos/player;
- range phases 0.31 / 0.79;
- SPR 1 / 2 / 4;
- checkpoints 300 / 1200 / 3600;
- no candidate outside the three frozen cardinality champions could enter.

All three unseen-v2 cells and the final summary job completed successfully.

Artifacts:

- SPR 1: `9268520895`, SHA-256 `e3afdc9ea099e2e66ec49b27069949bb710c0c27e4b534e8334271a90dd10aa4`;
- SPR 2: `9268564885`, SHA-256 `200fad22af45445f702f5fb879b0b3da3dcdc17c5756adf9d5ffcbae64d374cb`;
- SPR 4: `9268489450`, SHA-256 `95da3ed46901545d02c62e29010a9a23bcfcd18a293f467ee52c9c967e706b35`;
- final summary: `9268566954`, SHA-256 `158eef1f2d9d9adfff1254af14d694464a0e8ff85a6716cd3ea27c75291de641`.

## Final checkpoint 3600 — unseen-v2 summary

Values are conservative opening-restriction loss upper bounds per pot. Exact-BR interval width is reported alongside loss because differences at or below that numerical resolution must not be overinterpreted.

### Cross-SPR aggregate

| candidate | cardinality | mean upper | worst upper | mean interval | worst interval | cumulative hosted train s |
|---|---:|---:|---:|---:|---:|---:|
| `L1_100` | 1 | 0.00589680 | 0.01368868 | 0.00090256 | 0.00159098 | 1399.28 |
| `L2_50_100` | 2 | 0.00114458 | 0.00267837 | 0.00089021 | 0.00150819 | 1553.76 |
| `L3_25_50_100` | 3 | **0.00097338** | **0.00168981** | 0.00089245 | **0.00146348** | 1705.82 |

The one-size candidate fails the generalization gate strategically: its loss is far above remaining exact-BR resolution across the deeper geometries.

### By SPR

#### SPR 1

| candidate | mean upper | worst upper | mean interval | worst interval |
|---|---:|---:|---:|---:|
| L1_100 | 0.00345685 | 0.00554055 | 0.00067914 | 0.00129570 |
| **L2_50_100** | **0.00086169** | **0.00167303** | 0.00067914 | 0.00129570 |
| L3_25_50_100 | 0.00087825 | 0.00168981 | 0.00069252 | 0.00129570 |

At SPR 1, L2 and L3 are strategically indistinguishable at the current exact-BR resolution; the cheaper L2 has the slight raw numerical edge.

#### SPR 2

| candidate | mean upper | worst upper | mean interval | worst interval |
|---|---:|---:|---:|---:|
| L1_100 | 0.00737925 | 0.01289496 | 0.00096260 | 0.00134389 |
| L2_50_100 | 0.00131097 | 0.00267837 | 0.00098563 | 0.00130652 |
| **L3_25_50_100** | **0.00098010** | **0.00127046** | 0.00098295 | 0.00130652 |

This is the strongest unseen-v2 distinction between the two serious candidates. L2's worst conservative loss exceeds its worst exact-BR interval by about `0.001372 pot`, while L3's worst loss is fully contained inside the remaining interval. Therefore the extra 25% opening branch has a resolved strategic benefit in at least the difficult SPR-2 region of this unseen generation.

#### SPR 4

| candidate | mean upper | worst upper | mean interval | worst interval |
|---|---:|---:|---:|---:|
| L1_100 | 0.00685429 | 0.01368868 | 0.00106593 | 0.00159098 |
| L2_50_100 | 0.00126107 | 0.00156155 | 0.00100585 | 0.00150819 |
| **L3_25_50_100** | **0.00106180** | **0.00148712** | 0.00100189 | 0.00146348 |

At SPR 4 the two- and three-size families are again close to resolution, with L3 retaining a small raw strategic edge.

## Generalization verdict

The unseen-v2 gate materially strengthens the action-abstraction conclusion rather than reversing it:

- `L1_100` is rejected as too coarse for a general river opening abstraction;
- `L2_50_100` remains a strong compute-efficient candidate, especially at SPR 1;
- `L3_25_50_100` generalizes successfully and is now the **leading strategic opening-size candidate**, driven primarily by a resolved SPR-2 advantage;
- the 75% opening branch remains unnecessary in every selected richer family;
- the independent raise-size held-out gate separately identified 50%+100% as the leading raise family, producing a coherent but not forced convergence around 25/50/100 openings and 50/100 raises.

The result is particularly useful because `L3_25_50_100` was not privileged in unseen-v2: it first had to survive the complete 14-candidate seen lattice, and unseen-v2 then evaluated only the already-frozen cardinality champions.

## Why R3 still does not PASS

A production action family is not frozen from hosted CI alone. Remaining R3 debt:

1. tighten exact-BR intervals on any cells where the final L2/L3 cost-quality decision remains resolution-limited;
2. compare the serious finalists under **equal real wall-clock on the physical Ryzen 9**;
3. convert the river evidence into a street/SPR-dependent action-family contract rather than extrapolating one river grid blindly to flop/turn/preflop;
4. preserve geometric clipping so nominal actions that materialize identically do not consume solver/model capacity.

Current engineering leaders:

- river opening sizes: **25% / 50% / 100%** strategically leading;
- river raise sizes: **50% / 100%** compute-efficient leading family.

These are **R3 finalists, not production constants**.

`R3 unseen-v2 = PASS`

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
