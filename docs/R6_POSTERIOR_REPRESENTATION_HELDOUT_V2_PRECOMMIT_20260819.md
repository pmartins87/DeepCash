# R6 posterior representation held-out v2 — precommit 2026-08-19

Status: **RESERVED UNSEEN BEFORE REMEDIATION DIAGNOSTIC**

The first action-conditioned posterior bridge failed: `matchup_cluster8` recorded five resolved losses against `equity8`. Its 12 posterior cells are therefore consumed development evidence and may not be recycled as a fresh acceptance set.

This document reserves the next unseen posterior battery **before** any four-candidate remediation diagnostic is numerically consumed.

## Immutable unseen coordinates

Four turn source cases were repository-searched before this freeze and returned no matches:

- `heldout_low_ace`: `As 8c 5h 3d`, rivers `2c`, `Jh`;
- `heldout_broadway`: `Kc Qh 8s 4d`, rivers `2s`, `Td`;
- `heldout_paired`: `Qd Qc 7s 3h`, rivers `2d`, `9c`;
- `heldout_connected`: `Th 9d 6c 4s`, rivers `2h`, `8c`.

For every source case the frozen turn histories are:

- `CHECK_CHECK`;
- `P0_BET_50_CALL`;
- `P1_BET_50_CALL`.

This gives `4 × 2 rivers × 3 histories = 24` posterior river cells.

Shared source geometry:

- exact source range support/player: `12` combos;
- P0/P1 quantile phases: `0.31 / 0.79`;
- source pot/stack/min-bet: `100 / 200 / 20`;
- turn fractions: `0.5,1.0`;
- exact source turn solver: `ALT_DCFR_150_0_2`, 12 iterations;
- river reference/candidate solver: `ALT_DCFR_150_0_2`, 400 iterations.

## Candidate firewall

Remediation engineering is restricted to the already-existing deterministic Generation-2 family:

- `matchup_cluster8`;
- `equity8`;
- `matchup_cluster4`;
- `equity4_matchup2`.

No learned embedding or newly engineered feature candidate may be introduced in this remediation generation after the first bridge failure.

The consumed v1 posterior cells may be used to rank/diagnose those four existing families. At most two finalists may then be frozen. The names and evidence hashes of those finalists must be committed **before this unseen v2 battery is executed**.

## Held-out acceptance rule

For the two frozen finalists, conservative one-sided restriction-loss bounds are measured against the exact reference on all 24 posterior cells.

A finalist can be promoted from this held-out generation only if:

1. its mean conservative loss upper/pot is the lowest among the two frozen finalists; and
2. it has **zero resolved pairwise losses** against the other finalist.

A pairwise adverse result is resolved only when:

`candidate loss_upper - comparator loss_upper > max(candidate resolution interval, comparator resolution interval)`.

An adverse difference inside that envelope remains unresolved and is not treated as proof of reversal. If neither finalist satisfies the rule, R6 remains blocked and a new architectural remediation must be frozen; this held-out set must not be tuned against.

## Execution prohibition

The coordinates are deliberately present in the repository now so their existence predates the remediation diagnostic. No workflow in this PR is allowed to execute this held-out battery. A later finalist-freeze PR must add/enable the runner only after the development evidence has been audited.

`R6 posterior held-out v2 = RESERVED / NOT YET RUN`
