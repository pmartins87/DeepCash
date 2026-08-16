# DeepCash active gates — 2026-08-16

This is a transient audit ledger for gates that have been launched but **must not be promoted to PASS merely because the implementation/workflow exists**. Canonical `STATUS.json`, `docs/R1_VALIDATION_STATUS.md`, `docs/R3_VALIDATION_STATUS.md` and `docs/ROADMAP.md` remain authoritative for accepted evidence.

## R1 — bidirectional legal-action oracle v2

Workflow:

- `.github/workflows/r1-legal-actions-oracle-v2.yml`

Tool:

- `tools/crosscheck_pokerkit_legal_actions_v2.py`

Purpose:

- close the directional blind spot in the existing full-game mirror;
- existing oracle proves every **chosen DeepCash-legal** action is accepted by pinned PokerKit;
- new gate additionally checks whether PokerKit exposes a real action that DeepCash omitted;
- compares actor, exact to-call/call amount, check/call availability, fold while facing a positive price, raise availability and actual lower/upper raise-to boundary probes;
- includes deterministic 2-to-6 handed randomized traces with the same shallow/sub-BB stack fixtures used by the accepted full-game oracle;
- uses the existing fail-closed zero-chip PokerKit bookkeeping synchronizer only when no chip-moving action is pending.

Acceptance rule:

- every checked strategic state must agree;
- every completed hand must retain exact final-stack parity;
- any disagreement is investigated as a potential engine bug before the gate can pass;
- do not weaken the comparison to obtain PASS.

Current canonical status until inspected: **UNACCEPTED**.

## R3 — exhaustive opening-size subset lattice -> unseen held-out v2

Workflow:

- `.github/workflows/river-opening-subset-lattice-v1.yml`

Engineering candidate universe:

- every one-, two- and three-size proper subset of the fixed 25/50/75/100% opening reference;
- 14 candidates total;
- no new arbitrary opening size may be introduced from the lattice result without starting a new validation generation.

Seen engineering cells:

1. control boards, SPR 1, 4 combos/player, phases 0.00/0.27;
2. control boards, SPR 4, 4 combos/player, phases 0.00/0.27;
3. held-out-v1 boards, now explicitly seen, SPR 1, 6 combos/player, phases 0.13/0.61;
4. held-out-v1 boards, now explicitly seen, SPR 4, 6 combos/player, phases 0.13/0.61.

Precommitted selector:

- `tools/select_opening_lattice_champions.py`;
- exactly one champion forwarded per cardinality 1/2/3;
- minimize worst conservative restriction-loss upper bound across all seen engineering boards/cells;
- tie within 1e-12 -> mean upper bound -> cumulative training seconds -> lexical name.

Unseen v2 validation:

- frozen in `docs/R3_HELDOUT_V2_PRECOMMIT_20260816.md` before lattice-result acceptance;
- six new boards;
- 8 combos/player;
- phases 0.31/0.79;
- SPR 1/2/4;
- checkpoints 300/1200/3600;
- only the three preselected cardinality champions may enter;
- selector has no access to held-out-v2 artifacts.

Acceptance discipline:

- held-out-v2 is a generalization gate, not an automatic production selector;
- if v2 exposes a material reversal/failure, preserve it as seen evidence, return to engineering and create a new unseen validation generation after any retuning;
- no action-family freeze without physical Ryzen equal-compute evidence.

Current canonical status until inspected: **UNACCEPTED**.

## R3 — independent raise-size unseen validation

Workflow:

- `.github/workflows/river-raise-size-heldout-v1.yml`

Precommit:

- `docs/R3_RAISE_SIZE_HELDOUT_PRECOMMIT_20260816.md`

Purpose:

- validate the raise-size conclusion on boards not used by opening held-out-v2;
- fixed candidates `Q1_100`, `Q2_50_100`, `Q2_100_150`, `Q3_50_100_150`;
- six separate unseen boards;
- 6 combos/player;
- phases 0.22/0.68;
- SPR 1/2/4;
- checkpoints 300/1200/3600.

Acceptance discipline:

- `upper <= exact-BR interval width` is reported only as a measurement-resolution diagnostic, never as a permanent production threshold;
- any held-out evidence for material Q1 loss returns the project to raise-size engineering;
- physical Ryzen cost remains mandatory before freeze.

Current canonical status until inspected: **UNACCEPTED**.

`R1 = IN PROGRESS`

`R3 = IN PROGRESS`

`READY FOR TABLES = NO`
