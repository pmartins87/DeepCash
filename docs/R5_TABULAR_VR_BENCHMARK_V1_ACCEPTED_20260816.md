# R5 cheap tabular VR benchmark v1 — ACCEPTED — 2026-08-16

## Evidence

Workflow run `31976572985`: **PASS**.

Artifact `9271293501`, SHA-256 `83e04bf241f59d645d7be68c9f781042f4dfe85a970b4f5d17ab5c6b7c6d67d6`.

Schema: `DEEPCASH_R5_TABULAR_VR_BENCHMARK_V1`.

Frozen configuration before execution:

- solver: `ES_CFR_PLUS_LINEAR`;
- modes: `ZERO`, `TABULAR_RUNNING`, `INFOSET_EXACT`;
- boards: `A_high_dry`, `paired`, `four_straight`, `four_flush`;
- seeds: `101, 211, 307, 401, 503`;
- 8 combos/player;
- pot 100;
- bet sizes 25/50/100;
- range phases P0=.13, P1=.61;
- cumulative checkpoints 500 / 2000 / 10000.

The dedicated structural gate had already passed in run `31976450221`: first-iteration identity with ZERO, same-seed determinism, staged=monolithic training, exact checkpoint/resume future path, and baseline identity restricted to traverser private combo + public node + action. The realized opponent private hand is not part of the baseline key/API.

## Aggregate results

### Checkpoint 500

| mode | mean exploitability/pot | sample stdev | mean cumulative train s |
|---|---:|---:|---:|
| ZERO | 0.06160095 | 0.00794880 | 0.37505 |
| TABULAR_RUNNING | 0.05995135 | 0.00634759 | 0.39818 |
| INFOSET_EXACT | 0.05850546 | 0.00737753 | 0.92248 |

### Checkpoint 2000

| mode | mean exploitability/pot | sample stdev | mean cumulative train s |
|---|---:|---:|---:|
| ZERO | 0.03427096 | 0.00477694 | 1.02024 |
| TABULAR_RUNNING | 0.03343693 | 0.00404820 | 1.11165 |
| INFOSET_EXACT | 0.03311817 | 0.00359434 | 3.21221 |

### Checkpoint 10000

| mode | mean exploitability/pot | sample stdev | mean cumulative train s |
|---|---:|---:|---:|
| ZERO | 0.01619797 | 0.00188020 | 3.41965 |
| TABULAR_RUNNING | **0.01577459** | **0.00098999** | 3.84933 |
| INFOSET_EXACT | 0.01500396 | 0.00101858 | 14.25467 |

At 10k:

- `TABULAR_RUNNING` reduces mean exploitability versus ZERO by about **2.61%**;
- hosted-CI training time is only **1.126x ZERO**;
- `INFOSET_EXACT` is stronger strategically, but costs **4.168x ZERO**;
- mean tabular baseline coverage is 1.0;
- `TABULAR_RUNNING` beats ZERO in 11/20 paired board-seed cells at 10k;
- `INFOSET_EXACT` beats ZERO in 16/20 cells at 10k;
- `TABULAR_RUNNING` remains about `0.00077063` exploitability/pot worse than `INFOSET_EXACT` on the global 10k mean.

The most interesting signal is not only the small mean improvement: the sample stdev at 10k falls from `0.00188020` for ZERO to `0.00098999` for TABULAR_RUNNING, about a **47% reduction** in cross-seed dispersion, at low overhead.

## Interpretation

`TABULAR_RUNNING` is **accepted as the leading cheap legal variance-reduction primitive currently tested for external sampling**, not as the production R5 winner.

The result supports keeping a learned/bootstrap baseline in the sampled-solver funnel: it captures a non-trivial part of the benefit of exact conditional baselines while preserving near-ZERO cost. However, the fixed-iteration mean gain is modest and paired wins are not universal. Therefore it must still be evaluated under equal wall-clock, larger game scaling, compatibility with the best regret/chance-sampling primitives, and physical Ryzen timing.

`INFOSET_EXACT` remains an oracle-quality legal target for variance reduction but is not currently compute-efficient enough to lead production.

Hosted-CI timing is engineering evidence only. Physical Ryzen evidence remains mandatory before R5 production freeze.

## Next R5 step

Do not tune this same four-board/five-seed battery until TABULAR_RUNNING wins. The next justified experiment is a precommitted **equal-wall-clock/scaling comparison** of:

1. ordinary optimized external CFR+ (`ZERO` baseline);
2. external CFR+ + `TABULAR_RUNNING`;
3. the strongest compatible chance-allocation / regret-update combination already gated;
4. `INFOSET_EXACT` only as an expensive legal reference, not a production favorite.

The comparison must keep the no-private-leak boundary and checkpoint determinism intact and must eventually be repeated on the physical Ryzen 9.
