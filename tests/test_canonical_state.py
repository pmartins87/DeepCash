from dataclasses import replace
from itertools import permutations

from deepcash_core.betting import StreetAction, StreetActionKind
from deepcash_core.canonical_state import (
    ActionSnapshot,
    DecisionSnapshot,
    PlayerSnapshot,
    canonical_decision_key,
    decision_snapshot_from_hand_state,
    rotate_physical_seats,
)
from deepcash_core.cards import card_from_str
from deepcash_core.hand import HandSetup, HandState, Street


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
            ActionSnapshot("FLOP", 2, "RAISE_TO", 50, paid=50, pot_before=225),
            ActionSnapshot("FLOP", 3, "RAISE_TO", 150, paid=150, pot_before=275),
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


def test_action_actor_order_amount_and_geometry_remain_semantic():
    s = base_snapshot()
    key = canonical_decision_key(s)
    modified = list(s.action_history)
    modified[-1] = replace(modified[-1], raise_to=151)
    assert canonical_decision_key(replace(s, action_history=tuple(modified))) != key
    modified = list(s.action_history)
    modified[-1] = replace(modified[-1], paid=151)
    assert canonical_decision_key(replace(s, action_history=tuple(modified))) != key
    assert canonical_decision_key(replace(s, action_history=tuple(reversed(s.action_history)))) != key


def c(text: str) -> int:
    return card_from_str(text)


def A(kind: str, raise_to: int | None = None) -> StreetAction:
    return StreetAction(StreetActionKind(kind), raise_to)


def test_real_hand_state_projects_to_lossless_decision_snapshot_without_leaking_opponent_cards():
    setup = HandSetup(
        occupied_clockwise=(0, 1, 2),
        button=0,
        stacks={0: 1000, 1: 1000, 2: 1000},
        small_blind=50,
        big_blind=100,
        hole_cards={0: (c("As"), c("Kd")), 1: (c("Qh"), c("Qd")), 2: (c("Jh"), c("Jd"))},
        board=(c("2c"), c("7s"), c("9h"), c("Tc"), c("3d")),
    )
    state = HandState.new(setup)
    state = state.apply(A("RAISE_TO", 300))  # BTN
    state = state.apply(A("FOLD"))           # SB
    state = state.apply(A("CALL"))           # BB
    assert state.street == Street.FLOP
    state = state.apply(A("CHECK"))           # BB; BTN acts next

    snap = decision_snapshot_from_hand_state(state)
    assert snap.actor == 0
    assert set(snap.hero_hole) == {"As", "Kd"}
    assert snap.flop == ("2c", "7s", "9h")
    assert snap.turn is None and snap.river is None
    assert snap.pot == 650
    assert snap.to_call == 0
    assert snap.action_history[0].kind == "RAISE_TO"
    assert snap.action_history[0].paid == 300
    assert snap.action_history[2].kind == "CALL"
    assert snap.action_history[2].paid == 200
    flattened = repr(canonical_decision_key(snap))
    assert "Qh" not in flattened and "Qd" not in flattened and "Jh" not in flattened and "Jd" not in flattened


def test_projection_is_stable_under_consistent_physical_seat_relabeling():
    # The adapter creates a real engine-derived snapshot; the canonical boundary
    # must then erase physical-chair labels without erasing strategic geometry.
    setup = HandSetup(
        occupied_clockwise=(0, 2, 5),
        button=2,
        stacks={0: 1200, 2: 1000, 5: 800},
        small_blind=50,
        big_blind=100,
        hole_cards={0: (c("As"), c("Kd")), 2: (c("Qh"), c("Qd")), 5: (c("Jh"), c("Jd"))},
        board=(c("2c"), c("7s"), c("9h"), c("Tc"), c("3d")),
    )
    state = HandState.new(setup)
    snap = decision_snapshot_from_hand_state(state)
    mapping = {0: 1, 2: 4, 5: 0}
    assert canonical_decision_key(rotate_physical_seats(snap, mapping)) == canonical_decision_key(snap)
