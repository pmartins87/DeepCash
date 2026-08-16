# R3 opening-size subset lattice — engineering selection accepted 2026-08-16

This document accepts only the **seen engineering lattice and precommitted cardinality selection**. The downstream held-out-v2 jobs are still unseen validation and are not covered by this acceptance.

## Complete seen lattice

Workflow run `31962334355`, source commit `723096d01cea3a2bd39869734329f81ecd480aad`.

All four precommitted engineering cells completed successfully:

- control boards, SPR 1, 4 combos/player, phases 0.00 / 0.27;
- control boards, SPR 4, 4 combos/player, phases 0.00 / 0.27;
- heldout-v1 boards (now explicitly seen), SPR 1, 6 combos/player, phases 0.13 / 0.61;
- heldout-v1 boards (now explicitly seen), SPR 4, 6 combos/player, phases 0.13 / 0.61.

The candidate universe contained every non-empty proper subset of the fixed `{25,50,75,100}%` opening reference: 4 singletons, 6 pairs and 4 triples, 14 candidates total.

Latest artifact identities consumed by the selector:

- control SPR 1: artifact `9267868478`, SHA-256 `8a8abd61759a4975b6e08ffe2f0f866f6df02fecb1a3a17787b58d2d6e7ab893`;
- control SPR 4: artifact `9267884394`, SHA-256 `1e225d6efdf07761363e3a0390b686be55a4c40bb666a79aa6e3aeabd17dd8f6`;
- seen heldout-v1 SPR 1: artifact `9268171467`, SHA-256 `10163f6b5514f8844579715d838fb423e99507d0318abd2b3451f11ded754846`;
- seen heldout-v1 SPR 4: artifact `9268275623`, SHA-256 `9deb39e8930b305a08ea01de52f1fa55c58845d5faa895fbbb674685d93a8fe6`.

## Frozen selector

The selector was committed before the final lattice results and had no access to held-out-v2 data.

At each candidate cardinality 1/2/3 it minimizes, in order:

1. worst conservative restriction-loss upper bound across all seen engineering boards/cells;
2. mean conservative upper bound;
3. cumulative training seconds;
4. lexical candidate name for ties within 1e-12.

It is required to forward exactly one candidate at each cardinality.

Selector job `select-cardinality-champions`: **PASS**.

Selector artifact:

- `opening-subset-cardinality-champions`;
- artifact ID `9268277521`;
- SHA-256 `f17838f1196564e4e30a9b622d85bd0157ce1d17b92af1cff349bb2f1427897a`.

## Preselected cardinality champions

| complexity | champion | worst upper/pot | mean upper/pot | worst interval/pot |
|---:|---|---:|---:|---:|
| 1 size | `L1_100` | 0.00881885 | 0.00269107 | 0.00273509 |
| 2 sizes | `L2_50_100` | 0.00342888 | 0.00153998 | 0.00285407 |
| 3 sizes | `L3_25_50_100` | 0.00316745 | 0.00132747 | 0.00273929 |

The workflow forwarded exactly:

`L1_100,L2_50_100,L3_25_50_100`

## Engineering interpretation before unseen-v2

Two structural patterns are already notable but are not final validation conclusions:

- among one-size candidates, pot-sized opening won the frozen seen-data selector;
- the two- and three-size champions both retain 50% and 100%; the three-size champion additionally retains 25%, while 75% is absent from both selected richer subsets.

The prior `O3_25_50_100` hypothesis therefore survived a much less privileged search: it is exactly the winning three-size subset of the complete four-size lattice on seen engineering evidence.

However, the loss difference between the 2-size and 3-size champions remains close enough to exact-BR interval widths that **no complexity choice is frozen from this lattice**.

## Held-out-v2 firewall

The second unseen generation was frozen before these champions were produced:

- six new board families;
- 8 exact combos/player;
- range phases 0.31 / 0.79;
- SPR 1 / 2 / 4;
- checkpoints 300 / 1200 / 3600;
- only the three preselected champions above may enter.

After the selector completed, the workflow automatically launched all three held-out-v2 SPR jobs. Their results must be inspected only as generalization evidence; they cannot retroactively change which candidates were selected.

`R3 opening lattice engineering selection = ACCEPTED`

`R3 unseen-v2 = RUNNING / UNACCEPTED`

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
