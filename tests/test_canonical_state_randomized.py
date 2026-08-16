import random

from deepcash_core.canonical_state import (
    ActionSnapshot,
    DecisionSnapshot,
    PlayerSnapshot,
    canonical_decision_key,
    rotate_physical_seats,
)
from deepcash_core.cards import card_to_str, full_deck

SEED = 0xD33C4512
CASES_PER_PLAYER_COUNT = 20


def rename_suits(snapshot: DecisionSnapshot, mapping: dict[str, str]) -> DecisionSnapshot:
    def r(card):
        return None if card is None else card[0] + mapping[card[1]]

    return DecisionSnapshot(
        occupied_clockwise=snapshot.occupied_clockwise,
        button=snapshot.button,
        actor=snapshot.actor,
        hero_hole=tuple(r(c) for c in reversed(snapshot.hero_hole)),
        flop=tuple(r(c) for c in reversed(snapshot.flop)),
        turn=r(snapshot.turn),
        river=r(snapshot.river),
        players=snapshot.players,
        pot=snapshot.pot,
        to_call=snapshot.to_call,
        min_raise_to=snapshot.min_raise_to,
        action_history=snapshot.action_history,
    )


def random_snapshot(rng: random.Random, n: int) -> DecisionSnapshot:
    seats = tuple(range(n))
    button = rng.randrange(n)
    actor = rng.randrange(n)
    sample = rng.sample(list(full_deck()), 7)
    hero = (card_to_str(sample[0]), card_to_str(sample[1]))
    flop = tuple(card_to_str(c) for c in sample[2:5])
    turn = card_to_str(sample[5])
    river = card_to_str(sample[6])

    players = []
    for seat in seats:
        total = rng.randrange(0, 1201)
        street = rng.randrange(0, total + 1) if total else 0
        stack = rng.randrange(1, 2001)
        players.append(PlayerSnapshot(seat, stack, total, street))

    history = (
        ActionSnapshot("PREFLOP", seats[(button + 1) % n], "RAISE_TO", 250, paid=250, pot_before=150, to_call_before=100, current_bet_before=100, actor_committed_before=0, min_full_raise_to_before=200),
        ActionSnapshot("FLOP", seats[(button + 2) % n], "CALL", paid=75, pot_before=575, to_call_before=75, current_bet_before=75, actor_committed_before=0, min_full_raise_to_before=150),
    )
    return DecisionSnapshot(
        occupied_clockwise=seats,
        button=button,
        actor=actor,
        hero_hole=hero,
        flop=flop,
        turn=turn,
        river=river,
        players=tuple(players),
        pot=sum(p.committed_total for p in players),
        to_call=rng.randrange(0, 301),
        min_raise_to=rng.randrange(301, 1001),
        action_history=history,
    )


def test_randomized_2_to_6_player_metamorphic_invariance_battery():
    rng = random.Random(SEED)
    suits = "cdhs"
    for n in range(2, 7):
        for _ in range(CASES_PER_PLAYER_COUNT):
            snapshot = random_snapshot(rng, n)
            expected = canonical_decision_key(snapshot)

            perm = list(suits)
            rng.shuffle(perm)
            renamed = rename_suits(snapshot, dict(zip(suits, perm)))
            assert canonical_decision_key(renamed) == expected

            new_labels = rng.sample(range(20, 80), n)
            physical = {old: new for old, new in zip(snapshot.occupied_clockwise, new_labels)}
            rotated = rotate_physical_seats(renamed, physical)
            assert canonical_decision_key(rotated) == expected


def test_randomized_exact_geometry_mutations_never_alias():
    rng = random.Random(SEED ^ 0x55AA)
    for n in range(2, 7):
        for _ in range(CASES_PER_PLAYER_COUNT):
            snapshot = random_snapshot(rng, n)
            key = canonical_decision_key(snapshot)
            changed = DecisionSnapshot(
                occupied_clockwise=snapshot.occupied_clockwise,
                button=snapshot.button,
                actor=snapshot.actor,
                hero_hole=snapshot.hero_hole,
                flop=snapshot.flop,
                turn=snapshot.turn,
                river=snapshot.river,
                players=snapshot.players,
                pot=snapshot.pot + 1,
                to_call=snapshot.to_call,
                min_raise_to=snapshot.min_raise_to,
                action_history=snapshot.action_history,
            )
            assert canonical_decision_key(changed) != key
