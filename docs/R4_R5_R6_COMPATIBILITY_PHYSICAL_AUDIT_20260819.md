# R4 / R5 / R6 physical compatibility audit — 2026-08-19

Status: **PASS / R4 PRODUCTION REPRESENTATION FREEZE AUTHORIZED / R6 REMAINS IN PROGRESS**

Source artifact returned from the target Ryzen 9: `r4_r5_r6_compatibility_20260818_143025.zip`.

Artifact ZIP SHA-256: `58ef11362a0ca81b300f7120ddaaf35fe781562d81e8189fc4a664fee8e11cb5`.

This audit consumes the finite physical gate precommitted in `docs/R4_R5_R6_COMPATIBILITY_PRECOMMIT_20260818.md`. The frozen question was whether `matchup_cluster8` would preserve its fidelity advantage over the `equity8` anchor after combination with the leading exact R5 alternating discounted update semantics and the first R6 turn-to-river public chance boundary, without a material physical throughput or memory penalty.

## 1. Archive and provenance integrity

The archive contains 436 files. `SHA256SUMS.txt` lists 435 payload files; every listed file exists, every listed digest revalidated, and there are zero unlisted payload files.

Execution identity:

- git head: `143f36f8ff60ef9b1db6cfe9ae23ac0caa491839`;
- tracked git status: clean;
- Python: 3.11.9 x64;
- Windows: build 26200;
- CPU: `AMD64 Family 26 Model 68 Stepping 0, AuthenticAMD`;
- logical CPUs: 32;
- parent process affinity: all logical CPUs `[0..31]`.

Completeness:

- 48 exact-reference payloads;
- 48 physical river-child cells;
- 96 candidate result payloads = exactly 48 `matchup_cluster8` + 48 `equity8`;
- 96 candidate input payloads;
- 96 deterministic checkpoints;
- 96 candidate logs;
- one run manifest, one summary, one CSV result table and one digest manifest.

All 96 candidate payloads report solver variant `ALT_DCFR_150_0_2`, positive peak working-set measurements and affinity width 32. All 96 checkpoint files are present and their SHA-256 digests match the digest retained by their candidate payload. All 96 logs are non-empty and contain no `ERROR`, `TRACEBACK`, `EXCEPTION`, `FAILED`, `FATAL` or `ASSERT` token.

## 2. Frozen protocol verification

The artifact matches the precommit:

- exactly `matchup_cluster8` and `equity8`;
- exactly `ALT_DCFR_150_0_2` with historical/OpenSpiel-style post-update discount semantics;
- four turn boards × two range phases × SPR 1/2/4 × two river children = 48 physical child cells;
- each candidate receives 3.0 s target training wall clock per selected river child;
- round-robin chunk size = 5 iterations;
- exact-combo reference = 600 iterations and excluded from candidate budget;
- candidate workers are sequential and fresh-subprocess based;
- river children are selected from exact marginal chance mass after card removal, independent of candidate result;
- 8 exact range combos per player;
- pot 100 and minimum bet 20;
- physical action geometries remain SPR1 `[25,50,100]`, SPR2 `[25,50,100,200]`, SPR4 `[25,50,100,200,400]`.

No candidate was added after the freeze and no Generation-3 search occurred.

## 3. Exact-reference quality

Across the 48 exact-combo river references:

| metric | value |
|---|---:|
| mean exploitability / pot | `0.0000112927` |
| maximum exploitability / pot | `0.0000541911` |
| mean value-interval width / pot | `0.0000225854` |
| maximum value-interval width / pot | `0.0001083823` |
| mean reference wall time | `3.2161 s` |
| maximum reference wall time | `4.1808 s` |

The reference resolution is substantially below the aggregate candidate separation and is explicitly accounted for in pairwise reversal classification below.

## 4. Equal-wall-clock result

| candidate | mean conservative upper loss / pot | p90 | worst | mean joint it/s | mean peak working set | mean action-slot ratio | median iterations/state |
|---|---:|---:|---:|---:|---:|---:|---:|
| **`matchup_cluster8`** | **0.000130709** | **0.000273379** | **0.000531052** | 65.3957 | 26,662,827 B | 0.945313 | 195 |
| `equity8` | 0.001595765 | 0.006273244 | 0.007470421 | **65.5451** | **26,636,544 B** | 0.882813 | 195 |

Relative to `equity8`, `matchup_cluster8` reduces:

- mean conservative upper loss by approximately **91.81%**;
- p90 conservative upper loss by approximately **95.64%**;
- worst conservative upper loss by approximately **92.89%**.

The physical cost difference is immaterial at this scale:

- throughput difference: approximately **-0.23%** for `matchup_cluster8`;
- mean peak-working-set difference: approximately **+0.10%**;
- `matchup_cluster8` retains about 7.1% more action-slot mass than `equity8`, but this does not translate into a meaningful wall-clock or process-memory penalty in the measured bridge.

## 5. Pairwise resolution audit

Across the 48 paired physical child cells:

- `matchup_cluster8` has 28 nominal wins;
- 15 exact/tiny ties;
- 5 nominal adverse differences;
- of the 28 nominal wins, 18 exceed the conservative per-cell resolution interval and are resolved wins;
- the remaining 10 wins are inside the resolution interval;
- **all 5 nominal adverse differences remain inside the exact-reference/solver resolution interval**;
- therefore there are **zero resolved losses** for `matchup_cluster8`.

The five nominal adverse differences in conservative upper loss/pot are approximately `4.69e-06`, `4.07e-07`, `3.75e-06`, `3.24e-05` and `1.44e-04`; each is smaller than the corresponding conservative resolution envelope.

This satisfies the precommitted rule that tiny adverse differences inside resolution must not be treated as resolved reversals.

## 6. Turn/SPR strata

Mean conservative upper loss/pot remains lower for `matchup_cluster8` in every aggregate phase × SPR stratum:

| phase | SPR | matchup_cluster8 | equity8 | relative reduction |
|---|---:|---:|---:|---:|
| A | 1 | 0.000039008 | 0.002983550 | 98.69% |
| A | 2 | 0.000103253 | 0.003035973 | 96.60% |
| A | 4 | 0.000261937 | 0.003082970 | 91.50% |
| B | 1 | 0.000062981 | 0.000094120 | 33.08% |
| B | 2 | 0.000098874 | 0.000131072 | 24.57% |
| B | 4 | 0.000218199 | 0.000246902 | 11.63% |

The advantage narrows in phase B as the anchor itself becomes very accurate, but it does not reverse at the aggregate level.

## 7. Decision

The physical artifact passes the frozen compatibility question.

`matchup_cluster8`:

1. preserves the large held-out fidelity advantage already seen in Generation-2;
2. remains compatible with `ALT_DCFR_150_0_2` without changing its update semantics;
3. remains deterministic/checkpointable through the combined representation + solver path;
4. survives the first exact public turn-to-river chance/card-removal boundary;
5. has no material equal-wall-clock throughput penalty versus `equity8`;
6. has no material process-memory penalty versus `equity8`;
7. has zero resolved pairwise physical losses under the precommitted resolution rule.

Therefore **`matchup_cluster8` is frozen as the R4 production private-state representation primitive**.

`equity8` remains the deterministic accuracy/regression anchor. `matchup_cluster4` remains an aggressive compression control only.

No Generation-3 representation search is justified.

## 8. Scope boundary

This freeze is deliberately precise. Exact public cards, chance, payoff, stack/pot geometry and legal action tree remain exact; only solver information-state identity is compressed by the production representation primitive.

The compatibility PASS does not claim that turn/flop/preflop resolving is finished. The first R6 boundary currently proves exact turn-public-state -> public-river chance -> river-subgame transfer. R6 must still implement and validate turn betting/local resolving, then flop+turn+river, then preflop-to-river integration.

The result also does not select the final sampled production traversal for R5, prove multi-public-node CCS/VR-MCCFR behavior, mark R6 PASS, or authorize R9 production training.

## 9. Roadmap consequence

- **R4: PASS** — production representation primitive frozen to `matchup_cluster8` under the evidence chain above.
- **R5: IN PROGRESS** — exact update compatibility is proven; production traversal/solver architecture still requires held-out/scaling/physical selection.
- **R6: IN PROGRESS** — the first public turn-to-river transfer boundary exists and passed the physical compatibility bridge; turn betting/local resolving remains the next street-solver milestone.
- **R9: BLOCKED** until R1-R8 satisfy their production gates.
