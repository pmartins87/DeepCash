# R3 held-out v2 precommit — 2026-08-16

This file freezes the **second unseen opening-size validation gate before the exhaustive opening-subset lattice result is inspected/accepted**.

Held-out v1 has already influenced engineering: its results showed that `O3_25_50_100` generalizes much better than the original O1/O2 controls but still leaves measurable residual upper-bound loss on several board families. Therefore held-out v1 is now development evidence and cannot be reused as final unseen validation for a revised candidate family.

## Candidate universe already frozen

The reference opening set remains exactly:

- 25% pot;
- 50% pot;
- 75% pot;
- 100% pot.

Before this v2 gate, `ONE_RAISE_OPEN_SUBSET_LATTICE` was frozen to **all 14 non-empty proper subsets** of those four sizes. No new arbitrary sizing value may be introduced in response to the lattice result without creating a new validation generation.

## Engineering evidence allowed for shortlist selection

The exhaustive lattice may use only already-seen evidence:

- four historical control boards at SPR 1 and 4, phases `0.00 / 0.27`, 4 combos/player;
- held-out-v1 boards, which are now explicitly treated as seen engineering evidence, at SPR 1 and 4, phases `0.13 / 0.61`, 6 combos/player;
- checkpoints 250 / 1000 / 3000.

## Precommitted shortlist rule

Candidates are grouped by cardinality: one-size, two-size and three-size subsets.

For each cardinality, forward **exactly one champion** to held-out v2 using this deterministic ordering at the final 3000-iteration engineering checkpoint:

1. minimize the **maximum conservative restriction-loss upper bound / pot** observed across every board in all four engineering cells (`control SPR1`, `control SPR4`, `heldout-v1 SPR1`, `heldout-v1 SPR4`);
2. if tied within `1e-12`, minimize the mean conservative upper bound across the same rows;
3. if still tied, minimize total cumulative training seconds across those rows;
4. if still tied, use lexical candidate name as the final deterministic tie-break.

The full four-size reference is not a candidate; it remains the common-reference baseline.

This rule is intentionally cardinality-aware. It produces one representative cost/accuracy point for 1, 2 and 3 opening sizes instead of simply picking whichever largest subset minimizes error.

## Frozen held-out v2 boards

Exactly six new boards, stored under `HELDOUT2_RIVER_BOARDS`:

1. `ace_wheel_connected_v2` — `Ac 7d 4c 3s 2h`;
2. `straight_on_board_v2` — `Tc 9d 8s 7h 6c`;
3. `five_flush_v2` — `Qc 9c 7c 4c 2c`;
4. `full_house_board_v2` — `Ts Th Td 4s 4d`;
5. `paired_connected_v2` — `8s 8c 7d 6h 5s`;
6. `ace_broadway_wet_v2` — `Ah Qh Tc 8d 3h`.

Fixture freeze commit: `f3323c50f9fc3ca6ec60a9e710c0814fa423a086`.

## Frozen held-out v2 private-range sampling

- exact range combos/player: **8**;
- P0 quantile phase: **0.31**;
- P1 quantile phase: **0.79**.

These phases differ from both control (`0.00 / 0.27`) and held-out v1 (`0.13 / 0.61`).

## Frozen geometry/checkpoints

- pot: 100;
- SPRs: **1, 2 and 4** — stacks 100, 200 and 400;
- checkpoints: **300, 1200, 3600**;
- common-reference raise-response geometry held rich/fixed while only opening sizes are restricted;
- all-in openings retain exact fold/call/no-raise semantics.

## Interpretation discipline

Held-out v2 is a generalization gate, not an automatic production freeze.

For each forwarded cardinality champion, report:

- mean and worst conservative restriction-loss upper bounds / pot;
- mean and worst exact-BR interval widths;
- per-board and per-SPR behavior;
- any materialized-action collapse caused by stack clipping;
- training/evaluation cost separately.

If held-out v2 reverses the engineering ordering or exposes a new high-impact failure mode, **do not retune on these six boards and call them held-out again**. Preserve the result, return to engineering, and create a new held-out generation before any final selection.

Even a clean held-out v2 result does not authorize production action freeze without physical Ryzen equal-compute evidence.

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
