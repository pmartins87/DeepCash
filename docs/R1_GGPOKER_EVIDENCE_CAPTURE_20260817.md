# R1 GGPoker evidence capture contract — 2026-08-17

Status: **IMPLEMENTED_AWAITING_CI**  
Scope: the three unresolved GGPoker facts that keep R1 fail-closed.

This checkpoint adds a strict, deterministic and anonymization-enforcing fixture
format. It does **not** turn an illustrative hand into authoritative evidence and
does **not** change R1 from IN_PROGRESS.

## Admission rules

Every fixture must include the client build, UTC capture time, source kind,
source locator and SHA-256 of the untouched source. Player names, account IDs,
table IDs and other personal identifiers must be removed before the fixture is
accepted. The canonical JSON receives its own deterministic SHA-256 fingerprint.

Accepted source kinds are:

- an official published rule;
- an official support reply;
- an observed hand history.

A hand-history fixture resolves a rule only when its geometry distinguishes the
competing rule interpretations.

## Required discriminating captures

### Cumulative short-all-in reopen

Record a prior actor who already acted facing price **P**, the last full-raise
increment **F**, then at least two all-in increases. Each individual increase must
be less than **F**, while their cumulative increase from **P** must be at least
**F**. Record whether the client actually made a raise legal when action returned
to that prior actor.

A single short all-in, or several short all-ins whose total is still below **F**,
cannot answer the cumulative-reopen question and is rejected by the schema.

### Odd-chip split order

Record an indivisible pot with at least two tied winners, the button, all live
positions in clockwise order, the pot amount and the exact seat or seats receiving
the remainder chips. The remainder count must equal
`pot_amount_chips % tied_winner_count`.

### Rake rounding and settlement timing

Capture exact chip-unit contributions, every contested main/side pot before rake,
any uncalled return, total rake and total net payouts. The validator enforces both
conservation identities:

`contributions = contested pots + uncalled return`

`contested pots = rake + net payouts`

The useful minimum set is:

1. a small pot exposing chip-unit rounding;
2. a pot immediately around a published cap boundary;
3. a multiway main/side-pot settlement;
4. a hand containing an uncalled return;
5. an indivisible split pot if available.

Preflop raise count and street reached are mandatory so eligibility can be checked
without inference.

## Validation command

```bash
python tools/validate_site_rule_evidence.py path/to/anonymized_fixture.json
```

Success prints the schema version, scenario, source kind and canonical fixture
SHA-256. Any unknown field, missing field, geometry ambiguity, conservation
failure, non-UTC timestamp, invalid source hash or retained personal data fails
closed.

## Acceptance boundary

Tooling CI proves only that the fixture contract is deterministic and strict.
R1 remains IN_PROGRESS until admitted evidence resolves all three facts and the
resolved values are wired into the GGPoker adapter with regression tests.
