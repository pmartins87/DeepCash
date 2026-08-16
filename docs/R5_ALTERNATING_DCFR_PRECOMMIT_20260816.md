# R5 alternating CFR+ / DCFR control — precommit 2026-08-16

A literature audit exposed an important gap in the first DeepCash exact solver battery: our initial exact controls use **simultaneous** regret updates, while Brown & Sandholm's Discounted CFR experiments explicitly use the **alternating-updates** form of CFR and note that alternating updates perform substantially better in practice.

This generation is frozen before its numerical results are accepted.

Primary specification source: Brown & Sandholm, *Solving Imperfect-Information Games via Discounted Regret Minimization*, arXiv:1809.04040.

## Frozen update contract

One global iteration `t`:

1. derive the current strategy profile from regrets;
2. traverse the exact full chance/action tree and update only P0 regrets;
3. derive the new strategy profile;
4. traverse the exact full chance/action tree and update only P1 regrets;
5. derive the post-alternation strategy profile;
6. accumulate the output average from that post-alternation profile using exact own realization reach.

Both player traversals use exact compatible-card chance weights. No sampling is introduced.

## Frozen candidates

### `ALT_CFR_PLUS_LINEAR`

- alternating player updates;
- RM+ clipping after each player's update;
- output-average iteration weight `t`.

### `ALT_CFR_PLUS_QUADRATIC`

- same alternating RM+ update;
- output-average iteration weight `t^2`.

The DCFR paper reports using quadratic rather than linear CFR+ output weighting in its experiments, so both are retained instead of silently changing our earlier control.

### `ALT_DCFR_150_0_2`

Literature-default DCFR parameters:

- alpha = 3/2;
- beta = 0;
- gamma = 2.

After adding the current instantaneous regret at iteration `t`:

- positive accumulated regret is multiplied by `t^alpha / (t^alpha + 1)`;
- negative accumulated regret is multiplied by `t^beta / (t^beta + 1)`;
- the accumulated average-strategy contribution, including the current profile, is multiplied by `(t/(t+1))^gamma`.

This preserves the paper's relative discounting semantics; global common scale factors cancel when strategies are normalized.

### `ALT_DCFR_150_050_2`

Same as above except beta = 1/2. Brown & Sandholm discuss this as more pruning-compatible because negative regrets can continue moving toward negative infinity rather than being halved every iteration.

## Frozen same-run comparator

Also benchmark existing synchronous `CFR_PLUS_LINEAR` in the same hosted runner to reduce cross-run timing noise. This comparator is not redefined.

## Correctness gates

Before numerical interpretation:

- staged training must equal monolithic training for every alternating variant;
- JSON checkpoint roundtrip must preserve the exact future path;
- wrong game/variant checkpoint must fail closed;
- non-finite state must fail closed;
- DCFR positive/negative one-step discount factors must have direct unit fixtures;
- alternating update must prove that P0's half-step cannot mutate P1 regret state and vice versa;
- average-weight controls must distinguish linear from quadratic weighting on a nonstationary strategy fixture.

## Frozen numerical battery

Same exact river control family:

- four existing R3 control boards;
- 6 exact combos/player;
- phases 0.00 / 0.27;
- pot 100;
- stack 400 / SPR 4;
- fixed 25% / 50% / 100% bet family;
- checkpoints 100 / 400 / 1200;
- exact BR evaluation.

## Acceptance discipline

This is a development control, not a production solver selection. If alternating/DCFR materially changes the ranking, preserve the earlier synchronous result as a valid but narrower control rather than rewriting history.

Hosted timing is not target-Ryzen evidence.

`R5 alternating/DCFR = PRECOMMITTED`

`R5 production solver = NOT SELECTED`
