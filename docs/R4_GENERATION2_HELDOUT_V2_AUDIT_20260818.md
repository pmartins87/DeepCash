# R4 Generation-2 held-out-v2 audit — 2026-08-18

Status: **HELD-OUT-V2 CONSUMED / VALID / HOSTED-CI EVIDENCE ACCEPTED / PRODUCTION FREEZE STILL BLOCKED ON PHYSICAL RYZEN**

Source workflow: `DeepCash R4 representation Generation-2 held-out v2`, run `32101218388`, branch `main`, head `50fe1baa9c86a3587339d2bb9b49ca1304631c9d`.

## Execution integrity

- `structural-gate`: PASS;
- finalist-freeze/invariance test bundle: 46 tests PASS;
- frozen finalists printed by the gate: `equity8`, `matchup_cluster8`, `matchup_cluster4` and no others;
- all six frozen phase × SPR cells completed successfully;
- summarize job completed successfully;
- completeness gate found exactly six cell JSON files;
- all six cell artifacts were downloaded by the summarize job and their expected SHA-256 digests were verified;
- combined artifact: `r4-representation-gen2-heldout-v2`, artifact id `9312441121`, digest `sha256:92cc1825cbb4155b3cb3239469969cefdf0b1261724fb97182ee2c4d7b3dd4b7`;
- combined artifact contains six cell payloads plus one summary and 432 raw rows total.

No candidate outside the precommitted finalist freeze was evaluated.

## Geometry verification

All six payloads use the intended Generation-2 reference geometry:

- SPR1 / stack 100: `[25, 50, 100]`;
- SPR2 / stack 200: `[25, 50, 100, 200]`;
- SPR4 / stack 400: `[25, 50, 100, 200, 400]`.

Both phase pairs were present at every SPR:

- phase A: p0 phase 0.19 / p1 phase 0.47;
- phase B: p0 phase 0.58 / p1 phase 0.83.

Each payload used all eight frozen `heldout_v2` boards and checkpoints 300, 1200 and 3600. This removes the Generation-1 duplicated SPR2/SPR4 action-geometry limitation.

## Shared checkpoint 3600

| candidate | worst upper/pot | mean upper/pot | p90 upper/pot | worst interval/pot | compression | action-slot ratio | mean train sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| `equity8` | 0.011327 | 0.002185 | 0.009002 | 0.000696 | 0.855 | 0.855 | 17.801 |
| `matchup_cluster4` | 0.074263 | 0.015753 | 0.029209 | 0.001154 | 0.500 | 0.500 | 17.448 |
| `matchup_cluster8` | **0.000696** | **0.000323** | **0.000562** | **0.000696** | 0.887 | 0.887 | 17.835 |

The mechanical Pareto frontier contains all three finalists because `matchup_cluster4` offers much stronger compression while sacrificing fidelity.

## Convergence

Mean conservative upper loss per pot by checkpoint:

| candidate | 300 | 1200 | 3600 |
|---|---:|---:|---:|
| `equity8` | 0.006625 | 0.002767 | 0.002185 |
| `matchup_cluster4` | 0.019578 | 0.016309 | 0.015753 |
| `matchup_cluster8` | 0.004595 | 0.000884 | 0.000323 |

Worst conservative upper loss per pot by checkpoint:

| candidate | 300 | 1200 | 3600 |
|---|---:|---:|---:|
| `equity8` | 0.016840 | 0.012044 | 0.011327 |
| `matchup_cluster4` | 0.077889 | 0.074665 | 0.074263 |
| `matchup_cluster8` | 0.014415 | 0.002582 | 0.000696 |

All candidates' solver intervals shrink materially with more iterations. `matchup_cluster8` shows the strongest convergence and reaches the reference-resolution floor at the shared checkpoint. `matchup_cluster4` remains dominated on fidelity by a large margin; its only retained advantage is state/action-slot compression.

## Pairwise held-out behavior

Across the 48 board × phase × SPR checkpoint-3600 cells, `matchup_cluster8` is never meaningfully worse than `equity8` within numerical tolerance: it has 21 strict fidelity wins and 27 ties (the largest nominal adverse difference is approximately 5e-11). Its mean compression ratio is 0.887 versus 0.855 for `equity8`, a small increase in retained state compared with the large fidelity improvement.

`matchup_cluster4` is worse than `equity8` in 42/48 cells, tied in 2 and better in only 4; it remains a deliberately aggressive compression endpoint rather than a fidelity contender.

## Audit judgment

Hosted-CI held-out evidence strongly favors `matchup_cluster8` as the R4 strategic representation candidate. This is a robust generalization result across unseen boards, both phase pairs and genuinely distinct SPR1/2/4 action geometries.

This evidence **does not authorize a production representation freeze by itself**. The precommitted R4 production rule still requires equal-wall-clock validation on the physical Ryzen 9 under representative stack/street architecture. Hosted runner timing is not accepted as production-compute evidence.

Therefore:

- `matchup_cluster8`: **leading physical-Ryzen candidate**;
- `equity8`: **required deterministic accuracy/compute anchor**;
- `matchup_cluster4`: **aggressive compression control**;
- R4: **IN_PROGRESS — HOSTED EVIDENCE COMPLETE, PHYSICAL RYZEN GATE NEXT**.

No Generation-3 is justified by this evidence. A new candidate generation should be opened only if the physical comparison reveals a concrete scalability or street-transfer failure that invalidates all frozen finalists.
