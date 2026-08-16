# R3 raise-size held-out precommit — 2026-08-16

This file freezes an unseen validation gate for the **raise-size** abstraction before that gate is launched.

Opening-size and raise-size validation remain separate. The opening-size held-out-v2 boards are not reused here, so running this gate does not consume the unseen opening validation generation.

## Fixed candidate/reference family

Rich one-raise reference targets are measured as fractions of the pot after calling the opening bet:

- 0.5x;
- 1.0x;
- 1.5x.

Candidates are already fixed:

- `Q1_100` — 1.0x only;
- `Q2_50_100` — 0.5x / 1.0x;
- `Q2_100_150` — 1.0x / 1.5x;
- `Q3_50_100_150` — full reference.

The development control battery showed no certified strategic gain from adding raise sizes beyond Q1 at its current exact-BR precision. This held-out gate tests whether that conclusion generalizes; candidate definitions may not change after the result is seen.

## Frozen unseen boards

Exactly six deterministic boards under `RAISE_SIZE_HELDOUT_BOARDS`:

1. `raise_A_paired_wet` — `Ad Ac Js 8d 3c`;
2. `raise_K_high_four_straight` — `Kc 9d 8h 7s 6c`;
3. `raise_three_flush` — `Qd 9d 5d 3c 2s`;
4. `raise_double_pair_high` — `Kh Kd 7s 7c 2d`;
5. `raise_low_connected` — `Tc 6h 4d 3s 2c`;
6. `raise_quads_board` — `5s 5h 5d 5c Ah`.

## Frozen private-range sampling

- exact combos/player: **6**;
- P0 phase: **0.22**;
- P1 phase: **0.68**.

## Frozen geometry/checkpoints

- pot: 100;
- SPRs: **1, 2 and 4** — stacks 100, 200 and 400;
- checkpoints: **300, 1200 and 3600**;
- rich opening set remains fixed at 25 / 50 / 75 / 100% pot, clipped by stack;
- only the raise-size dimension is restricted;
- all-in openings retain fold/call/no-raise semantics;
- raise targets are clipped to stack and duplicate clipped targets collapse exactly.

## Interpretation rule

The workflow reports conservative common-reference restriction-loss upper bounds and exact-BR interval widths. It does **not** automatically declare Q1 or any larger candidate production-ready.

A smaller candidate is considered *not distinguishable from the richer reference at current precision* on a row when its conservative upper bound is no larger than that row's exact-BR interval width. This is a diagnostic statement about measurement resolution, not a permanent production threshold.

If unseen held-out rows reveal a material Q1 loss beyond solver uncertainty, preserve that evidence and return to raise-size engineering. Do not retune on these six boards and reuse them as unseen validation.

Physical Ryzen equal-compute evidence remains mandatory before any final action-family freeze.

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
