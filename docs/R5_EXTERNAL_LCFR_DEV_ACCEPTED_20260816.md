# R5 alternating external-sampling LCFR development v1 — accepted 2026-08-16

This document accepts the precommitted literature-aligned alternating external-sampling comparison, including its mixed/negative findings.

## Correctness gate

Implementation:

- alternating P0 then P1 sampled traversals with immediate strategy refresh;
- chance and non-traverser actions sampled;
- traverser's actions enumerated;
- exact own-reach average accumulation in this small-game control;
- deterministic PRNG checkpoint/resume.

Variants:

- `ALT_ES_CFR_UNIFORM`;
- `ALT_ES_CFR_LINEAR_AVG`;
- `ALT_ES_LCFR`, where instantaneous regret at global iteration `t` receives weight `t` and output average also receives weight `t`.

The correctness CI passed before numerical acceptance, including direct weighted-regret fixtures, same-seed identity, staged-vs-monolithic identity, JSON future-path identity, player-isolation and fail-closed state validation.

## Numerical gate

Workflow run `31966542606`: **PASS**.

Artifact:

- ID `9268697523`;
- SHA-256 `16bffe2dc7b2034096dda20642e38e61b3a7a4617c70970968ffdba4a8e0c5ec`.

Frozen battery:

- four exact river control boards;
- 6 exact combos/player;
- phases 0.00 / 0.27;
- pot 100, stack 400 / SPR 4;
- 25% / 50% / 100% action family;
- seeds `11,29,101,20260816`;
- checkpoints 1000 / 5000 / 20000;
- exact best-response evaluation.

## Aggregate result

| iterations | ALT ES CFR uniform mean / worst | ALT ES CFR linear-average mean / worst | ALT ES LCFR mean / worst |
|---:|---:|---:|---:|
| 1,000 | **0.032001 / 0.040397** | 0.038412 / 0.053295 | 0.032647 / 0.042640 |
| 5,000 | **0.012747 / 0.019012** | 0.018194 / 0.029336 | 0.013294 / **0.018150** |
| 20,000 | 0.005437 / 0.007945 | 0.008508 / 0.014226 | **0.005388 / 0.007816** |

Mean hosted training time at 20k is essentially identical across the three variants: about 5.85 s.

## Accepted interpretation

This experiment does **not** reproduce a dramatic LCFR advantage in the current DeepCash river microgame.

The result is still useful:

- linear output averaging by itself is clearly harmful under this alternating external-sampling setup;
- LCFR starts slightly worse than uniform CFR, becomes competitive by 5k, and is only marginally better in mean/worst at 20k;
- the late advantage is too small to promote LCFR as a decisive sampled solver from this generation;
- the result contrasts with the much stronger gains seen from correlated chance allocation in the separate chance-sampling control.

Therefore the current sampled research priority shifts toward **variance reduction / chance allocation and scaling**, rather than assuming regret reweighting alone will solve MCCFR variance.

This does not contradict the source literature; different games, update conventions, chance structure and small support can materially change practical ranking. DeepCash preserves its own negative/mixed evidence instead of tuning the experiment until the paper's preferred method wins.

`ALT_ES_LCFR = COMPETITIVE BUT NOT DECISIVE`

`R5 = IN PROGRESS`

`R5 production solver = NOT SELECTED`
