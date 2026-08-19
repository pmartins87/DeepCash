# R6 posterior river representation bridge v1 — failed 2026-08-19

Status: **FAIL / BOUNDED LOCAL RESOLVING REMAINS BLOCKED / R4 STATIC FREEZE NOT SILENTLY REWRITTEN**

## Frozen evidence identity

- workflow run: `32220724503`;
- published evidence commit: `9a9c99576e45266d35a7b23d8a350489a6afaeae`;
- schema: `DEEPCASH_R6_POSTERIOR_RIVER_REPRESENTATION_BRIDGE_V1`;
- artifact status: `COMPLETE_POSTERIOR_BRIDGE_EVIDENCE_NOT_R6_PASS`;
- source contract: `docs/R6_POSTERIOR_RIVER_REPRESENTATION_BRIDGE_PRECOMMIT_20260819.md`.

The gate deliberately tested the immutable R4 production representation `matchup_cluster8` against its frozen `equity8` accuracy anchor after exact turn actions had changed the private posterior ranges. The comparison therefore exercised a boundary that the earlier static river/R4 compatibility gates had not resolved.

## Result

The frozen decision is `FAIL_POSTERIOR_REPRESENTATION_BRIDGE`.

Across 12 action-conditioned posterior river cells:

- `matchup_cluster8` nominally won or tied 7 cells;
- it suffered **5 resolved pairwise losses** versus `equity8`;
- there were zero merely unresolved adverse cells.

The five resolved losses were:

| case | turn history | river | matchup - equity loss upper/pot | resolution envelope/pot |
|---|---|---|---:|---:|
| posterior_ahigh | CHECK_CHECK | Tc | +0.014466429 | 0.000244040 |
| posterior_ahigh | P0_BET_50_CALL | 2h | +0.001017254 | 0.000074835 |
| posterior_ahigh | P0_BET_50_CALL | Tc | +0.002899448 | 0.000045543 |
| posterior_ahigh | P1_BET_50_CALL | Tc | +0.005991863 | 0.000067964 |
| posterior_connected | CHECK_CHECK | 2d | +0.003468894 | 0.000154999 |

Every adverse difference is larger than its frozen resolution envelope; these failures cannot be dismissed as solver-resolution noise.

## Aggregate context

Aggregate mean conservative loss upper/pot was slightly lower for `matchup_cluster8` (`0.005712630`) than for `equity8` (`0.006345487`), but that does not satisfy the precommitted gate because the pairwise resolved-loss requirement was zero. Worst loss upper/pot was `0.020120178` for `matchup_cluster8` versus `0.018013843` for `equity8`.

The failure is therefore local and informative rather than a claim that `matchup_cluster8` is globally worse. Its previous R4 static/physical evidence remains valid for the scope in which it was measured. What is rejected is the assumption that the same bucket identity can be carried unchanged into every action-conditioned posterior river range.

## Architecture consequence

R6 must reopen the **posterior/street-specific representation boundary**, not silently rewrite the existing R4 production freeze and not advance to bounded local resolving yet.

The consumed 12-cell set is now development evidence. It must never be reused as a fresh held-out acceptance set after candidate selection.

The remediation sequence is frozen conceptually as follows:

1. reserve a new unseen posterior held-out set before consuming any remediation comparison;
2. on the already-consumed development cells, compare only pre-existing deterministic Generation-2 families (`matchup_cluster8`, `equity8`, `matchup_cluster4`, `equity4_matchup2`) to diagnose the failure without inventing a post-hoc learned candidate;
3. select at most two posterior finalists under an explicit fidelity/compression rule;
4. evaluate those finalists once on the already-reserved unseen posterior held-out set;
5. only a held-out PASS may authorize bounded local resolving.

A posterior-specific choice is allowed to differ from the static R4 representation if evidence supports it. Exact cards, public chance, card removal, payoff, pot/stack geometry and legal action tree remain exact in all cases.

`R6 posterior representation bridge v1 = FAIL`

`R6 bounded local resolving = BLOCKED`

`NEXT = FRESH POSTERIOR HELD-OUT FREEZE + DEVELOPMENT DIAGNOSTIC`
