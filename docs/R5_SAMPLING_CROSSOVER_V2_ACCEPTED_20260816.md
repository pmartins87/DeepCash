# R5 sampling crossover v2 — accepted 2026-08-16

This document accepts the corrected scaling experiment after removing the accidental full compatible-deal enumeration from every sampled chance draw.

## Correction / semantic replay

Invalidated v1 run: `31965398733`.

Accepted v2 run: `31967392548` — **PASS**.

Artifact:

- ID `9268920317`;
- SHA-256 `963d606c9e9b7eee9b547e8a2b3de27de1afe06c18579382314988bb088a87f2`.

The v2 sampler builds the exact weighted compatible-deal CDF once per training batch and uses binary search for repeated draws.

Before accepting any timing conclusion, v1 and v2 artifacts were compared row by row across every algorithm / board / range size / seed / checkpoint. They are **strategically bit-identical** for all recorded fields:

- exploitability per pot;
- policy EV;
- BR0/BR1 values;
- BR interval width;
- terminal-visit counts.

Maximum numerical difference across those fields: exactly `0.0`.

Therefore the code change removed only hot-loop overhead; it did not alter the sampled game path or strategy result.

## Frozen scaling coordinates

Boards:

- A-high dry;
- four-straight.

Exact range support per player:

`6, 12, 24, 48` combos.

Shared geometry:

- pot 100;
- stack 400 / SPR 4;
- fixed 25% / 50% / 100% river action family;
- phases 0.00 / 0.27.

Full-tree comparator:

- synchronous `CFR_PLUS_LINEAR` at 100 / 400 iterations.

External-sampling comparator:

- `ES_CFR_PLUS_LINEAR` at 20k / 80k iterations;
- seeds 29 / 101.

Iteration counts are intentionally not treated as equal work. The gate measures exploitability against observed hosted wall-clock.

## Optimizer effect

External-sampling 80k mean training time before -> after sampler correction:

| combos/player | v1 seconds | v2 seconds | speedup |
|---:|---:|---:|---:|
| 6 | 24.69 | 17.81 | 1.39x |
| 12 | 35.05 | 24.97 | 1.40x |
| 24 | 69.48 | 39.61 | 1.75x |
| 48 | 306.47 | 47.48 | **6.45x** |

This confirms the v1 timing defect was increasingly dominant as exact chance support grew.

## Corrected scaling result

### 6 combos/player

- full-tree CFR+ 400: mean exploitability/pot `0.001814`, ~1.85 s;
- ES CFR+ 80k: `0.003367`, ~17.81 s.

Exact traversal dominates decisively.

### 12 combos/player

- full-tree 400: `0.001570`, ~9.81 s;
- ES 80k: `0.006896`, ~24.97 s.

Exact traversal still dominates.

### 24 combos/player

- full-tree 100: `0.008588`, ~12.41 s;
- full-tree 400: `0.001849`, ~49.30 s;
- ES 20k: `0.009226`, ~9.96 s;
- ES 80k: `0.005469`, ~39.61 s.

This is a transition region: at the nearest lower wall-clock pair, full-tree 100 remains slightly more accurate than ES 20k; at the longer pair, full-tree 400 is still substantially more accurate than ES 80k.

### 48 combos/player

- full-tree 100: mean/worst exploitability `0.008484 / 0.015717`, ~52.06 s;
- full-tree 400: `0.002282 / 0.004492`, ~205.54 s;
- ES 20k: `0.007112 / 0.008946`, ~11.87 s;
- ES 80k: **`0.004539 / 0.006400`**, ~47.48 s.

At roughly equal observed wall-clock, **ES 80k beats full-tree 100 at 48 combos/player**:

- mean exploitability improves from ~`0.008484` to ~`0.004539`;
- worst improves from ~`0.015717` to ~`0.006400`;
- ES uses slightly less hosted training time (~47.5 s vs ~52.1 s).

This is the first clean DeepCash evidence of a traversal-scaling crossover: external sampling is not worthwhile on tiny exact range supports, but by 48 exact combos/player it can deliver lower strategic error at the same approximate wall-clock than the synchronous full-tree comparator.

## Important limitation

This gate compares traversal scaling against **synchronous CFR+**, not against the much stronger alternating discounted exact control. It therefore establishes a computational crossover for tree traversal, not the production solver winner.

The result also uses only two river boards and hosted runners. The exact crossover coordinate is not a universal constant and must not be hardcoded into the architecture.

## Accepted architecture implication

DeepCash should use the **least stochastic traversal that still fits the state/chance support**:

- small subgames: exact/full-tree traversal remains superior;
- intermediate subgames: chance sampling / correlated chance may be preferable before opponent-action sampling;
- sufficiently large supports: sampled traversal becomes necessary and can already win error-per-wall-clock;
- variance reduction now matters because sampling is no longer merely hypothetical — a real crossover has been observed.

This materially strengthens the case for the next VR-MCCFR no-leak baseline work and for carrying correlated chance sampling into larger-support experiments.

`R5 sampling crossover v2 = PASS`

`R5 traversal crossover = OBSERVED BETWEEN THE 24- AND 48-COMBO CONTROL REGIMES`

`R5 production solver = NOT SELECTED`

`READY FOR TABLES = NO`
