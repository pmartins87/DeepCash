# R5 VR-MCCFR mode benchmark — frozen plan 2026-08-16

Purpose: quantify the strategic gain and CPU cost of a legal no-private-leak exact infoset baseline after its integration oracle passes.

This is an engineering benchmark, not a production solver selection.

## Compared modes

1. `ZERO` — exact identity control for ordinary external sampling;
2. `INFOSET_EXACT` — expensive legal-information oracle using traverser private combo + public history/current policy and integrating over compatible hidden opponent hands;
3. `PERFECT_HISTORY` — deliberately privileged hidden-state variance lower bound, never production eligible.

`PERFECT_HISTORY` is included only to show remaining reducible variance. It cannot win a production comparison.

## Frozen battery

- board set: existing four river development/control boards only;
- range combos: 8 per player;
- p0 phase: 0.13;
- p1 phase: 0.61;
- pot: 100;
- bet sizes: 25, 50, 100;
- regret variant: `ES_CFR_PLUS_LINEAR`;
- iterations per run: 2000;
- seeds: `101, 211, 307, 401, 503`;
- exact best response after every completed run;
- wall-clock measured only as hosted-CI engineering evidence, never as Ryzen calibration.

For each board × mode × seed record:

- exploitability per pot;
- policy EV;
- exact BR0 and BR1 values;
- training seconds;
- terminal visits;
- final iteration count.

Aggregate per board × mode and globally:

- mean/median/min/max exploitability per pot;
- sample standard deviation across seeds;
- mean training seconds;
- mean terminal visits.

## Interpretation

No post-hoc PASS threshold is permitted. The questions are:

1. Does `INFOSET_EXACT` reduce seed-to-seed strategic error relative to `ZERO` at the same iteration count?
2. Is the reduction large enough to justify approximating this baseline cheaply later?
3. How much of the gap between `ZERO` and the privileged `PERFECT_HISTORY` lower-bound oracle is closed?
4. What CPU multiplier does the exact legal baseline impose?

Even a strong `INFOSET_EXACT` result does not make the exact oracle production eligible if its hidden-support integration cost scales poorly. Its intended role is to establish a target for a later tabular/bootstrapped baseline that uses the same legal information set at much lower cost.

Physical Ryzen equal-wall-clock selection remains an R8 requirement.
