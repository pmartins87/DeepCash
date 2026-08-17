# R1 GGPoker reference and universal site-rule contract — 2026-08-17

Status: **ENGINEERING IMPLEMENTATION — AWAITING CI; R1 REMAINS IN PROGRESS**

## Scope

GGPoker is the first reference model for conventional 6-max NLHE cash. The exact
game engine and strategic policy remain site-agnostic. Site differences enter only
through explicit rules/economy/runtime adapters, and an absent fact never becomes
a silent engine default.

This checkpoint does **not** homologate GGPoker and does **not** authorize R1 PASS.

## Authoritative public facts frozen in the reference profile

Sources checked on 2026-08-17:

- [GGPoker 6-max No Limit Hold'em rake table](https://ggpoker.com/poker-games/texas-holdem/)
- [GGPoker Cash Games FAQ](https://help.ggpoker.com/article/Cash-Games---Frequently-Asked-Questions)
- [GGPoker no-limit betting structures](https://ggpoker.com/blog/the-beginners-guide-series-no-limit-vs-pot-limit-vs-fixed-limit/)
- [GGPoker straddle rules](https://ggpoker.com/poker-games/straddle/)
- [GGPoker House Rules](https://ggpoker.com/house-rules/)

Confirmed:

- classic 6-max NLHE uses a published 5% rake schedule with caps indexed by
  blind level and number of dealt players;
- the full published 6-max grid from $0.01/$0.02 through $10/$20 is stored as
  exact rational BB caps;
- GGPoker states that pre-flop rake applies only to pots involving a 3-bet or
  higher;
- an optional pre-deal straddle auction exists and must be activated only from
  explicit table metadata;
- the public Hold'em page defines a full raise as at least the previous bet/raise
  increment and permits a smaller raise only when all-in;
- GGPoker explicitly states that one sub-full all-in does not reopen betting
  action. The cumulative-short-all-in case remains undocumented.

## Facts deliberately left unresolved

| Fact | State | Why it blocks freeze |
|---|---|---|
| cumulative short-all-in reopen | UNRESOLVED | A single sub-full all-in is confirmed not to reopen action, but public rules do not say whether cumulative short all-ins reaching a full-raise increment reopen it. |
| odd-chip order | UNRESOLVED | No authoritative public GGPoker rule was found for tied cash pots. |
| rake rounding | UNRESOLVED | Public tables do not define chip rounding. |
| rake application timing | UNRESOLVED | Public material does not fully specify main/side-pot timing and per-pot cap behavior. |

The adapter raises `SiteRuleContractError` instead of materializing
`BettingConfig` or `RakePolicy` when a required fact is unresolved.

## Portability contract

Every supported site must provide the same typed facts:

1. betting reopen policy;
2. odd-chip order;
3. rake eligibility, rate, cap, rounding and timing;
4. optional forced-bet features;
5. currency/stake/chip-unit mapping;
6. runtime/table metadata outside the exact strategic core.

A new site normally changes only this adapter. A separate strategic core is
permitted only if measured rules materially change the game.

## Required evidence to close R1

1. Obtain authoritative GGPoker support answers or deterministic observed hand
   histories for short-all-in reopen and odd-chip order.
2. Collect small-pot, cap-boundary, split-pot and side-pot fixtures to identify
   exact rake rounding/timing.
3. Encode those facts as confirmed `RuleFact` values with immutable source
   records.
4. Replay fixtures against the exact engine and add parity tests.
5. Keep R1 `IN_PROGRESS` until all target facts and native/cross-language parity
   required by the roadmap pass.
