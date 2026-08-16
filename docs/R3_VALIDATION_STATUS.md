# R3 action-abstraction validation status — 2026-08-16

R3 is **IN PROGRESS**.

The river action-abstraction program now has resumable exact-card CFR+, common-reference restriction games, a one-raise tree, dynamic exact best responses gated against enumeration, exact low-SPR all-in opening semantics, opening-size evidence across SPR 0.5/1/2/4, and a separate raise-size restriction laboratory. **No production action family has been frozen.**

## Accepted controls

The current R3 stack contains:

- `deepcash_core.river_lab` — exact-card HU river one-bet microgame;
- synchronous full-chance CFR+ with linear average strategy;
- exact compatible-card chance enumeration;
- exact best responses and exploitability/value intervals;
- exact infoset/action-slot accounting;
- resumable deterministic CFR+ checkpoints with exact staged-vs-monolithic equivalence;
- `deepcash_core.river_reference_lab` / `river_reference_training` — asymmetric common-reference games;
- `deepcash_core.river_raise_reference_lab` / `river_raise_reference_training` — asymmetric one-raise common-reference games;
- dynamic exact BR for the one-raise reference tree, independently gated against the older enumerative oracle on tractable fixtures;
- package-safe benchmark fixtures and convergence analysis under `deepcash_core`;
- control and separately precommitted held-out board registries;
- explicit experiment provenance: board set, range phases, range count, pot, stack, SPR and restriction dimension;
- CI regression and archived benchmark artifacts.

There is still no private-state abstraction in these controls. Exact combos remain separate.

## Methodological correction — own-tree exploitability is not abstraction loss

A smaller action family and a larger action family define **different games**. Therefore a candidate cannot be judged by comparing only its exploitability inside its own restricted tree.

A tiny tree can be easier to solve and can show lower own-tree exploitability precisely because strategically useful opponent actions have been removed. That number remains useful as a convergence diagnostic, but it is **not** the primary measure of action-abstraction quality.

R3 uses a richer common reference game. For reference action set `R` and candidate subset `C`, it solves:

1. `R vs R`;
2. `C vs R` — only P0 is restricted;
3. `R vs C` — only P1 is restricted.

Every finite CFR policy has an exact-BR value interval `BR1 <= V <= BR0`. Restriction-loss bounds are propagated from those intervals rather than treating finite-iteration policy EV as the exact game value.

No strategic PASS threshold is being invented after seeing the control numbers. The analyzers report interval tightening and conservative restriction-loss bounds; the final selection must be precommitted against future held-out/target-hardware evidence rather than tuned to the existing four-board controls.

## Initial one-bet controls

Workflow run `31949683719` on commit `2640371563cd40067eb5f370af30ee123aaddb21`: **PASS**.

At 120 CFR+ iterations and 6 exact combos/player, own-tree exploitability/pot was:

| Board | S1 50% | S2 33/100% | S3 25/75/150% | S4 25/50/100/200% |
|---|---:|---:|---:|---:|
| A-high dry | 0.002324 | 0.004596 | 0.006590 | 0.005061 |
| Paired | 0.002087 | 0.005830 | 0.006172 | 0.008407 |
| Four-straight | 0.002529 | 0.008423 | 0.010329 | 0.009817 |
| Four-flush | 0.002639 | 0.005544 | 0.005175 | 0.005755 |

These numbers were **not** used to select S1. They primarily demonstrated that richer trees converge more slowly under equal iteration count.

Resumable one-bet CFR+ run `31949968733`: **PASS**. Artifact `9264366421`, SHA-256 `47d83b15555c934bd9eee4ac739cebf2a0069664ec1dd287ce61279629c446fa`.

The checkpoint gate proves exact staged-vs-monolithic training equivalence, exact JSON resume continuity, spec mismatch rejection and refusal to evaluate untrained states.

## Common-reference one-bet infrastructure

The asymmetric/reference solver and common-reference restriction methodology are operational and resumable. Workflow `31950481366`: **PASS**.

The original tiny common-reference smoke intentionally produced wide exact-BR intervals; that result was treated as a warning that finite-iteration upper bounds cannot be interpreted before convergence, not as evidence for or against a candidate sizing family.

## One-raise exact-reference gate

The river reference tree supports one opening bet followed by fold/call/raise, then fold/call after the raise. Opening action sets may differ by player so only one side can be restricted while the opponent keeps the rich reference tree.

The exact best response used for larger one-raise batteries is dynamic rather than pure-plan enumeration. The dynamic oracle is gated against the independent enumerative control on small fixtures before it is trusted for larger trees.

A first resumable one-raise common-reference convergence smoke passed in workflow `31951341083`. At 1000 iterations on A-high dry, 3 combos/player, pot 100, stack 400 (SPR 4), conservative restriction-loss upper bounds/pot were approximately:

- `O1_50`: 0.037924;
- `O2_25_75`: 0.017274;
- `O3_25_50_100`: 0.001947.

That single-board smoke was not used to freeze an action set.

## Exact all-in/no-raise semantics

Low-SPR opening bets can exhaust the effective stack. The one-raise reference game now represents this exactly: an all-in opening remains in the opening action set but carries an **empty raise-target tuple**, so the responder has fold/call and no fabricated raise branch.

This behavior is gated against the one-bet exact control: when every opening has an empty raise set, the one-raise game must produce exactly the same policy EV, BR0, BR1, exploitability, infoset count and action-slot count as the corresponding one-bet game at the same iteration count.

Accepted implementation/tests:

- `deepcash_core.river_raise_reference_lab` commit `7c263c0b17da9cdcc9ab1b50a50b67fa7670c8cb`;
- benchmark low-SPR support commit `d3ad4652fd25a7bc8a6069eff011dda850de60fa`;
- exact semantic regression commit `d05a02ee98eb970e03710be53b3e08287d881095`;
- general CI run `31960722077`: **PASS**.

This closes the prior R3 debt that excluded low-SPR one-raise states.

## Opening-size common-reference battery across SPR 0.5 / 1 / 2 / 4

Workflow run `31960758207` on commit `6d96926df770ee3a46721d20c24f7e17432ddcbf`: **PASS** in all four matrix jobs.

Shared configuration:

- pot 100;
- stacks 50, 100, 200, 400 => SPR 0.5, 1, 2, 4;
- four stable control boards: A-high dry, paired, four-straight, four-flush;
- 4 exact range combos/player;
- checkpoints 250, 1000, 3000;
- opening candidates `O1_50`, `O2_25_75`, `O3_25_50_100`;
- reference opening sizes 25%, 50%, 75%, 100% pot, clipped exactly by stack;
- pot-sized raise-response geometry held fixed while only opening sizes are restricted;
- all-in openings retain fold/call and no raise branch.

Artifacts:

| SPR | stack | artifact | SHA-256 |
|---:|---:|---:|---|
| 0.5 | 50 | `9267189103` | `953e23ddd6a3e3ede41de1c746030a47929c7797bae9fcd524f4164cef62b206` |
| 1 | 100 | `9267209423` | `6b33a6117f83d75ea1b4480ee6c518dc3c1892982b51fe3c9e75a60e87d67863` |
| 2 | 200 | `9267212233` | `dbe4a829aef43729561f3ae10344b89ca626927d4e8f8f573884ec5236b5678c` |
| 4 | 400 | `9267213394` | `3f36e74bcdd0cc060cc33d83b83f8fe66d3b11b206d2cd29db2f8c89ef151fad` |

At the final 3000-iteration checkpoint, aggregate conservative upper bounds were:

| SPR | O1 mean / worst | O2 mean / worst | O3 mean / worst | worst exact-BR interval |
|---:|---:|---:|---:|---:|
| 0.5 | 0.001768 / 0.004225 | 0.000839 / 0.000900 | 0.000839 / 0.000900 | 0.001154 |
| 1 | 0.018995 / 0.023405 | 0.008197 / 0.010410 | 0.001510 / 0.001630 | 0.001860 |
| 2 | 0.026965 / 0.033987 | 0.011181 / 0.013935 | 0.001587 / 0.003729 | 0.002940 |
| 4 | 0.026688 / 0.033807 | 0.011250 / 0.013843 | 0.001295 / 0.003167 | 0.001966 |

### Interpretation of the multi-SPR control

The result is structurally useful:

- at **SPR 0.5**, clipping collapses `O2` and `O3` to the same materialized action set, and their results are exactly identical. This is desirable: the abstraction does not pay for nominal branches that cannot exist geometrically;
- at **SPR 1**, `O3`'s worst upper bound (0.001630/pot) is below the remaining worst interval width (0.001860/pot), so no loss larger than current solver uncertainty is certified on this control battery;
- at **SPR 2**, the four-straight board remains difficult: O3 worst upper 0.003729 versus interval 0.002940;
- at **SPR 4**, O3 worst upper 0.003167 versus interval 0.001966;
- `O1` and `O2` show clearly larger restriction upper bounds once the stack is deep enough that the omitted sizes remain distinct.

This strengthens `O3_25_50_100` as the leading opening-size **engineering candidate** across the control SPR range, but still does not freeze it for production.

## Raise-size restriction is now a separate dimension

Opening-size and raise-size abstraction are no longer conflated. The raise-size laboratory holds the rich opening set fixed and restricts only one player's raise targets at a time.

Reference raise fractions are measured against the pot after calling the opening bet: 0.5x, 1.0x and 1.5x pot-after-call. Candidate controls are:

- `Q1_100`;
- `Q2_50_100`;
- `Q2_100_150`;
- `Q3_50_100_150` = full reference.

The generator rounds deterministic integer-chip targets, clips to stack, verifies literal candidate-subset membership after clipping, rejects non-all-in sub-minimum raises, and uses an empty target set when the opening itself is all-in.

Raise-size smoke run `31960872365`: **PASS**. Artifact `9267206071`, SHA-256 `36dc43cd28ca7063e8c9bd7dfcf3be58b30338a1db6f601018b0718412f89216`.

At A-high dry, SPR 4, 3 combos/player, checkpoint 1200:

- Q1 upper 0.002269, interval 0.002100;
- Q2 50/100 upper 0.001967, interval 0.002100;
- Q2 100/150 upper 0.002163, interval 0.002108;
- full Q3 upper 0.002100, interval 0.002100.

Those differences are dominated by the remaining exact-BR uncertainty, so **the smoke selects nothing**. A four-board/4-combo/3000-iteration raise-size battery has been launched separately; it is not accepted until its workflow completes successfully.

## Held-out evidence was precommitted before seeing results

The four control boards above have already informed engineering, so they must not become the sole basis of a final action-family choice.

A separate held-out registry was committed before its benchmark results were available, containing six new board families:

- K-high dry;
- double-paired;
- three-flush;
- Broadway-connected;
- low-connected;
- trips board.

The held-out battery also changes deterministic range sampling phases from control `0.00 / 0.27` to `0.13 / 0.61`, uses 6 exact combos/player, and tests SPR 1 and SPR 4. The historical control `--boards all` behavior is intentionally unchanged; held-out boards require explicit `--board-set heldout` so later additions cannot silently alter old regression artifacts.

Workflow `.github/workflows/river-raise-opening-heldout-v1.yml` was launched from commit `df2145abdda4ad2e841a01b8bc58907b533adc16`. **No result from that held-out workflow is recorded as accepted evidence until it completes.**

## Equal-compute discipline

R3 separately tracks:

- cumulative training time;
- exact-BR evaluation time;
- own-tree convergence error;
- common-reference one-sided restriction-loss bounds;
- exact-BR interval width;
- infosets/action slots;
- board/range/SPR geometry;
- restriction dimension (opening vs raise size);
- eventually memory and target-Ryzen throughput.

Hosted-CI wall time is engineering evidence only. The decisive equal-wall-clock comparison must be run on the physical Ryzen 9 before action-family freeze.

## Remaining R3 gates

1. accept/reject the running four-board raise-size battery from actual workflow evidence;
2. accept/reject the precommitted held-out opening-size battery from actual workflow evidence;
3. expand held-out/alternate-range evidence further only if the current held-out results reveal unresolved geometry-specific behavior;
4. tighten difficult-board exact-BR intervals where they remain comparable to candidate restriction loss;
5. run equal-wall-clock evidence on the physical Ryzen 9;
6. define the final selection procedure against future/held-out evidence rather than retrofitting a threshold to the control results;
7. only then freeze the smallest action family on the strategic-error/compute Pareto frontier;
8. later add richer raise depths only if measured gain justifies cost.

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
