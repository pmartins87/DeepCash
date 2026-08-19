# R5 equal-wall-clock/scaling v1 — accepted hosted engineering evidence

Date: 2026-08-19

Status: **ACCEPTED HOSTED ENGINEERING EVIDENCE / CCS ADVANCES / PRODUCTION SELECTION NOT AUTHORIZED**

Source evidence:

- workflow: `DeepCash R5 equal-wallclock scaling v1`;
- workflow run: `32217495605`;
- source SHA: `95de0b2a220c0f4da08aa585ca456bbb9cf8122c`;
- published evidence commit: `e17df2533e146a79fc16bf06fa7eb09467fd1307`;
- JSON SHA-256: `fa0a98311c73097abdb6b04642f19828055c3c183f928c9ea09d51167ff5c5ea`;
- artifact schema: `DEEPCASH_R5_EQUAL_WALLCLOCK_SCALING_V1`;
- artifact status: `COMPLETE_HOSTED_ENGINEERING_EVIDENCE_NOT_PRODUCTION_SELECTION`.

The result is consumed under the frozen contract in `docs/R5_EQUAL_WALLCLOCK_SCALING_PRECOMMIT_20260817.md`.

## 1. Protocol audit

The published configuration matches the precommit exactly:

- boards: `A_high_dry`, `four_straight`;
- exact range support/player: `8, 24, 48`;
- P0/P1 phases: `0.13 / 0.61`;
- pot: `100`;
- bet sizes: `25,50,100`;
- seeds: `101,211,307`;
- cumulative training budgets: `1,5,15 s`;
- comparators: `ES_ZERO`, `ES_TABULAR_RUNNING`, `CCS_CFR_PLUS_LINEAR`, `ES_INFOSET_EXACT`;
- external variant: `ES_CFR_PLUS_LINEAR`;
- CCS variant: `CCS_CFR_PLUS_LINEAR`;
- chunk contract: initial 64, bounded to `[1,4096]`, with the frozen deterministic remaining-time estimate.

There are 6 cells in every range × budget × comparator aggregate: two boards × three seeds. Therefore the artifact contains the complete expected `3 × 3 × 4 × 6 = 216` numerical rows.

All summary timing-quality counts are zero, and no row carries `timing_quality_flag=true`. Evaluation time is reported separately from training time as required. The total hosted wall time was `1868.3041577339172 s`.

## 2. Fifteen-second equal-time result

Mean exploitability / initial pot after 15 seconds:

| range combos/player | CCS | ES_ZERO | TABULAR_RUNNING | INFOSET_EXACT |
|---:|---:|---:|---:|---:|
| 8 | **0.003230836** | 0.007089699 | 0.008097238 | 0.014423343 |
| 24 | **0.009922746** | 0.019260170 | 0.020212839 | 0.041091216 |
| 48 | **0.020807451** | 0.034555481 | 0.034713202 | 0.073078500 |

Relative to `ES_ZERO`, `CCS_CFR_PLUS_LINEAR` reduces mean exploitability at 15 seconds by approximately:

- **54.43%** at 8 combos/player;
- **48.48%** at 24 combos/player;
- **39.79%** at 48 combos/player.

Relative to `ES_TABULAR_RUNNING`, the corresponding reductions are approximately **60.10%**, **50.91%**, and **40.06%**.

The advantage remains material as support grows rather than disappearing at 48 combos/player.

## 3. Paired result across every frozen time/range coordinate

For `CCS_CFR_PLUS_LINEAR` versus `ES_ZERO`:

- 8 combos/player: 6/6 paired wins at 1 s, 6/6 at 5 s, 6/6 at 15 s;
- 24 combos/player: 6/6 at 1 s, 6/6 at 5 s, 6/6 at 15 s;
- 48 combos/player: 6/6 at 1 s, 6/6 at 5 s, 6/6 at 15 s.

That is **54/54 paired wins** across all frozen board × seed × support × budget cells. Every paired mean difference `CCS - ES_ZERO` is negative.

`ES_INFOSET_EXACT` records 0/6 paired wins versus ZERO at every frozen support/budget coordinate and is much slower. This is accepted negative production evidence; it remains useful only as a legal-information/reference construction.

`ES_TABULAR_RUNNING` is inconsistent. Across all 54 paired cells it wins only 20 against ZERO, and at the decisive 15-second checkpoint its mean exploitability is worse than ZERO at 8, 24 and 48 combos/player. The running baseline therefore does not justify continued production-finalist status from this gate.

## 4. Throughput interpretation

The algorithms perform different work per iteration, so iteration count is not used as the strategic normalization.

At 15 seconds:

- CCS executes fewer nominal iterations than ES_ZERO/TABULAR at the larger supports;
- CCS nevertheless produces substantially lower exact exploitability after the same training wall clock;
- CCS also has much higher terminal visits/second than ES_ZERO on these controls because it samples the private deal but traverses the full action tree;
- INFOSET_EXACT is both strategically worse at equal time and far slower in nominal iteration/terminal throughput.

This is exactly why the precommit required equal wall clock rather than equal iteration count.

## 5. Pareto audit

At 15 seconds the artifact's own Pareto summary reports:

- 8 combos/player: frontier = `CCS_CFR_PLUS_LINEAR` only;
- 24 combos/player: frontier = `ES_ZERO`, `ES_TABULAR_RUNNING`, `CCS_CFR_PLUS_LINEAR` under the artifact's multi-metric frontier definition;
- 48 combos/player: frontier = `CCS_CFR_PLUS_LINEAR` only.

The 24-combo multi-metric frontier does not reverse the equal-time strategic result: CCS has approximately half the mean exploitability of ZERO/TABULAR there. It only records that the comparators expose different raw-throughput tradeoffs.

## 6. Decision from this hosted gate

This result is strong enough to narrow the sampled traversal funnel, but not to select production.

**Advances as the leading sampled finalist:**

- `CCS_CFR_PLUS_LINEAR`.

**Retained as mandatory baseline/control for held-out and physical reproduction:**

- `ES_ZERO` / optimized `ES_CFR_PLUS_LINEAR`.

**Demoted from production-finalist status, retained for regression/research evidence:**

- `ES_TABULAR_RUNNING`.

**Reference-only; not a production finalist:**

- `ES_INFOSET_EXACT`.

The exact alternating `ALT_DCFR_150_0_2` control remains separately relevant to R5 correctness and to physical crossover measurement; this hosted sampled-traversal battery did not compare it and therefore makes no claim against it.

## 7. What this result does not authorize

This is development evidence on two frozen boards in GitHub-hosted CI. It does not satisfy:

- independent R5 held-out validation;
- physical Ryzen 9 equal-wall-clock reproduction;
- exact-vs-sampled physical crossover selection;
- multi-public-node sampled behavior required by later street architecture;
- final R5 production solver/traversal freeze;
- R8 PASS or R9 training authorization.

## 8. Next R5 gate

Freeze a fresh R5-specific held-out board battery before numerical consumption. The held-out run should compare the narrowed sampled pair `CCS_CFR_PLUS_LINEAR` vs `ES_ZERO` at equal time, with new seeds and no post-hoc candidate engineering. If that generalization gate passes, carry CCS, ES_ZERO and the exact `ALT_DCFR_150_0_2` control into the physical Ryzen crossover/selection protocol.
