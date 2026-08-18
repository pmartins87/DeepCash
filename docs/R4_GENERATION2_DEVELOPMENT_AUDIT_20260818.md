# R4 Generation-2 development audit — 2026-08-18

Status: **DEVELOPMENT CONSUMED / AUDITED / HELD-OUT-V2 STILL UNSEEN**

Source workflow: `DeepCash R4 representation Generation-2 dev v1`, run `32095713074`, commit `e01886850109fc8047cf92224f24f850ab87e2ee`.

## Execution integrity

- workflow conclusion: `success`;
- `structural-gate`: PASS;
- all six frozen development cells completed successfully;
- summarize job completed successfully;
- all six cell artifacts were present and digest-verified by the summarize job;
- combined artifact: `r4-representation-gen2-dev-v1`, artifact id `9310917903`, digest `sha256:027cee5bb2d1074756f80f4e4e558646c1c92ed6565cdaeab9dcfb9d895681b5`.

The development run used only `--board-set dev`; held-out-v2 was not run or consumed.

## Frozen geometry verification

The six matrix cells used the frozen stacks exactly as precommitted:

- SPR1: stack 100;
- SPR2: stack 200;
- SPR4: stack 400.

The benchmark was therefore executed under distinct SPR geometries rather than the Generation-1 accidental duplicated one-bet geometry. The Generation-2 structural gate also passed before development began.

## Shared-checkpoint summary

Final shared checkpoint: `3600` iterations.

| Candidate | Worst upper/pot | Mean upper/pot | P90 upper/pot | Interval/pot | Compression | Slot ratio | Seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| `equity8` | 0.009489 | 0.001976 | 0.008867 | 0.000986 | 0.922 | 0.922 | 16.946 |
| `matchup_cluster4` | 0.088868 | 0.019331 | 0.043494 | 0.000986 | 0.500 | 0.500 | 16.582 |
| `matchup_cluster8` | 0.000986 | 0.000328 | 0.000591 | 0.000986 | 0.984 | 0.984 | 16.972 |
| `equity4_matchup2` | 0.031807 | 0.012615 | 0.022058 | 0.001716 | 0.574 | 0.574 | 16.651 |

The summarizer reports all four candidates on the raw Pareto frontier because each preserves a different fidelity/compression tradeoff. The frozen selection rule, however, requires conservative development judgment and allows at most three finalists.

## Audit judgment

### Advance: `matchup_cluster8`

This is the clear fidelity leader in development. Its worst, mean, and P90 conservative restriction-loss upper bounds are all lower than `equity8`, with essentially identical wall-clock cost. Its compression is slightly worse than `equity8` in this small laboratory (0.984 versus 0.922), but the fidelity gain is large and consistent enough to justify held-out validation.

### Advance: `equity8`

Retain the fixed Generation-1 accuracy anchor exactly as precommitted. It remains the required reference against which Generation-2 must prove a real advantage.

### Advance: `matchup_cluster4`

Retain one deliberately aggressive compression point. It halves the nominal action-state slots and is the only candidate offering a qualitatively large compression reduction. Development fidelity is materially worse than the anchor, so it is not a current winner; it advances only to test whether that compression/fidelity tradeoff generalizes on unseen boards.

### Do not advance: `equity4_matchup2`

This hybrid is dominated for the purpose of finalist allocation. It compresses substantially, but its conservative fidelity is much worse than `equity8` and much worse than `matchup_cluster8`, while offering less compression than `matchup_cluster4`. It therefore does not earn one of the maximum three frozen finalist slots.

## Finalist freeze

Frozen Generation-2 held-out-v2 finalists, in no winner order:

1. `equity8`;
2. `matchup_cluster8`;
3. `matchup_cluster4`.

`equity4_matchup2` is eliminated after development.

No scalar score was invented. The selection follows the precommitted conservative fidelity/compression/compute rule.

## Firewall state

Held-out-v2 remains **FROZEN_UNSEEN_DO_NOT_RUN** at this commit. This audit records the finalist freeze required before any held-out-v2 consumption.

The next admissible R4 action is a held-out-v2 run restricted to the three frozen finalists above. Even a successful held-out-v2 will remain engineering evidence; R4 still requires physical Ryzen equal-wall-clock comparison on a representative street/stack architecture before R4 can PASS.
