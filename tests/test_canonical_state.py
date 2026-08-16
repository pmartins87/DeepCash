from dataclasses import replace
from itertools import permutations

from deepcash_core.canonical_state import (
    ActionSnapshot,
    DecisionSnapshot,
    PlayerSnapshot,
    canonical_decision_key,
    rotate_physical_seats,
)


def base_snapshot() -> DecisionSnapshot:
    return DecisionSnapshot(
        occupied_clockwise=(0, 2, 3, 5),
        button=3,
        actor=0,
        hero_hole=("As", "Kd"),
        flop=("Qh", "7c", "2s"),
        turn="Tc",
        river=None,
        players=(
            PlayerSnapshot(0, 875, 125, 75),
            PlayerSnapshot(2, 900, 100, 50),
            PlayerSnapshot(3, 800, 200, 150),
            PlayerSnapshot(5, 1000, 0, 0, folded=True),
        ),
        pot=425,
        to_call=75,
        min_raise_to=300,
        action_history=(
            ActionSnapshot("PREFLOP", 5, "FOLD"),
            ActionSnapshot("FLOP", 2, "RAISE_TO", 50),
            ActionSnapshot("FLOP", 3, "RAISE_TO", 150),
        ),
    )


def rename_suits(snapshot: DecisionSnapshot, mapping: dict[str, str]) -> DecisionSnapshot:
    def r(card):
        return None if card is None else card[0] + mapping[card[1]]

    return replace(
        snapshot,
        hero_hole=tuple(r(c) for c in snapshot.hero_hole),
        flop=tuple(r(c) for c in snapshot.flop),
        turn=r(snapshot.turn),
        river=r(snapshot.river),
    )


def test_combined_hole_flop_and_global_suit_invariance():
    s = base_snapshot()
    expected = canonical_decision_key(s)
    suits = "cdhs"
    for perm in permutations(suits):
        mapping = dict(zip(suits, perm))
        renamed = rename_suits(s, mapping)
        for hole in (renamed.hero_hole, renamed.hero_hole[::-1]):
            for flop in permutations(renamed.flop):
                candidate = replace(renamed, hero_hole=hole, flop=tuple(flop))
                assert canonical_decision_key(candidate) == expected


def test_physical_chair_rotation_and_renaming_is_invariant():
    s = base_snapshot()
    expected = canonical_decision_key(s)
    # A consistent physical chair relabeling preserves clockwise order but wraps
    # around the six physical table slots.
    mapping = {0: 1, 2: 3, 3: 4, 5: 0}
    rotated = rotate_physical_seats(s, mapping)
    assert rotated.occupied_clockwise == (1, 3, 4, 0)
    assert canonical_decision_key(rotated) == expected


def test_exact_chip_geometry_is_not_bucketed_away():
    s = base_snapshot()
    key = canonical_decision_key(s)
    assert canonical_decision_key(replace(s, pot=s.pot + 1)) != key
    assert canonical_decision_key(replace(s, to_call=s.to_call + 1)) != key
    assert canonical_decision_key(replace(s, min_raise_to=s.min_raise_to + 1)) != key

    players = list(s.players)
    players[0] = replace(players[0], stack=players[0].stack + 1)
    assert canonical_decision_key(replace(s, players=tuple(players))) != key


def test_action_actor_is_button_relative_but_action_order_and_amount_remain_semantic():
    s = base_snapshot()
    key = canonical_decision_key(s)
    modified_amount = list(s.action_history)
    modified_amount[-1] = replace(modified_amount[-1], amount=151)
    assert canonical_decision_key(replace(s, action_history=tuple(modified_amount))) != key

    reversed_history = tuple(reversed(s.action_history))
    assert canonical_decision_key(replace(s, action_history=reversed_history)) != key
