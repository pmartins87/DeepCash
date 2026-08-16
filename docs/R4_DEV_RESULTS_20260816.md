# R4 deterministic representation development results — 2026-08-16

Status: **development evidence accepted; no finalist and no production representation selected**.

Canonical source: GitHub Actions run `31964142661`, artifact `r4-representation-dev-v1`, artifact id `9270794930`, SHA-256 `2fcf9bac459126f6d2638421c5b06da5441ae14682ef0d999e80dba15473eb70`.

The run completed all six precommitted development cells: phase A and phase B at nominal SPR 1, 2 and 4. The held-out-v1 registry was not consumed.

## Frozen 1200-iteration aggregate

The precommit requires the largest shared development checkpoint, 1200 iterations, to be used for this inspection. Across all 24 board × phase × SPR cells:

| candidate | worst loss upper/pot | mean loss upper/pot | p90 loss upper/pot | worst BR interval/pot | mean bucket ratio |
|---|---:|---:|---:|---:|---:|
| `category` | 0.0493067 | 0.0281426 | 0.0475640 | 0.1236208 | 0.5625000 |
| `category_equity4` | 0.0455225 | 0.0170323 | 0.0419088 | 0.0792048 | 0.8020833 |
| `equity4` | 0.0455225 | 0.0244262 | 0.0419088 | 0.0792048 | 0.6666667 |
| `equity4_blocker2` | 0.0455225 | 0.0123195 | 0.0412422 | 0.0760457 | 0.8333333 |
| `equity8` | 0.00547082 | 0.00211593 | 0.00404692 | 0.0268303 | 0.9791667 |
| `equity8_blocker2` | 0.00547082 | 0.00211545 | 0.00404692 | 0.0268303 | 0.9895833 |
| `strength4` | 0.0455225 | 0.0244262 | 0.0419088 | 0.0792048 | 0.6666667 |

`p90` is the nearest-rank 90th percentile over the 24 frozen cells.

## Interpretation under the precommitted procedure

The development result does **not** justify selecting the final representation yet.

- `equity8` and `equity8_blocker2` are dramatically tighter strategically than the four-bucket/category controls, but achieve little compression on these six-combo microgames.
- lower-complexity candidates still occupy a genuine compression-vs-error trade-off, so the mechanical Pareto screen does not eliminate them simply because `equity8` has lower strategic loss;
- several low-complexity cells are not sufficiently converged for a trustworthy finalist decision because their exact-BR intervals are still wide;
- blocker splitting has almost no aggregate strategic gain at eight equity buckets in this small development battery, while it increases bucket count; this is development evidence only, not a held-out conclusion.

The all-24 global suit-permutation representation metamorphic test is already in the test suite for every deterministic candidate. It becomes accepted only with a green general CI containing that test.

## Cells requiring targeted convergence tightening

The largest uncertainty at 1200 iterations is concentrated rather than uniform:

- `category`, `A_high_dry`, phase A, SPR 2/4: BR interval/pot `0.1236208`;
- `category`, `paired`, phase B, SPR 2/4: `0.0958034`;
- `category_equity4` / `equity4`, `four_flush`, phase B, SPR 2/4: up to `0.0792048`;
- `equity4_blocker2`, `paired`, phase B, SPR 2/4: `0.0760457`;
- `category_equity4` / `equity4`, `four_straight`, phase A, SPR 2/4: up to `0.0705802`;
- `equity8` / `equity8_blocker2`, `four_straight`, phase A, SPR 2/4: `0.0268303`.

By contrast, the eight-equity-bucket candidates show substantial convergence on other difficult cells. Example: `equity8`, four-flush phase B SPR2, interval/loss upper falls from about `0.030909` at 100 to `0.011391` at 400 and `0.005471` at 1200. The paired phase-B SPR2 control falls from about `0.032415` to `0.008599` to `0.004047`.

## Geometry caveat

The current river one-bet representation laboratory carries pot and materialized bet sizes in `RiverGameSpec`, not an independent stack variable in the game state. `--stack` only clips the candidate bet sizes before the spec is built. Consequently nominal SPR2 and SPR4 frequently materialize the same action set and produce identical strategic rows. Those duplicate rows are not independent evidence.

The next convergence pass therefore uses one representative un-clipped geometry (`pot=100`, `stack=200`) for cells whose SPR2/SPR4 action trees are identical, instead of paying twice for the same game.

## Decision

**No R4 finalist is frozen from this artifact.** The next legal step is a precommitted targeted convergence extension on the difficult development cells. R4 held-out v1 remains unopened until that extension is inspected and at most three deterministic finalists are explicitly frozen from development evidence.
