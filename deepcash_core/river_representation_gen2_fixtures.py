from __future__ import annotations

from .river_benchmark_fixtures import RIVER_BOARDS
from .river_representation_fixtures import R4_REPRESENTATION_HELDOUT_V1_BOARDS


# Generation-2 development may use already-consumed Generation-1 evidence.
# Keep the set finite and explicit: four original controls plus four consumed
# held-out-v1 boards. No Generation-2 unseen board appears here.
R4_GEN2_DEV_BOARDS = {
    **RIVER_BOARDS,
    "king_wheel_dry_r4": R4_REPRESENTATION_HELDOUT_V1_BOARDS["king_wheel_dry_r4"],
    "ace_paired_r4": R4_REPRESENTATION_HELDOUT_V1_BOARDS["ace_paired_r4"],
    "three_club_connected_r4": R4_REPRESENTATION_HELDOUT_V1_BOARDS["three_club_connected_r4"],
    "four_spade_r4": R4_REPRESENTATION_HELDOUT_V1_BOARDS["four_spade_r4"],
}


# Frozen before the first Generation-2 numerical development run. These boards
# are disjoint by name and exact card tuple from all earlier R4 development and
# held-out-v1 boards. They remain unseen until a Generation-2 finalist freeze is
# recorded after development evidence is audited.
R4_GEN2_HELDOUT_V2_BOARDS = {
    "queen_high_dry_g2": "Qh 8c 5d 3s 2c",
    "king_paired_g2": "Kc Kh 9d 6s 3c",
    "three_diamond_connected_g2": "Td 8d 6d 4c 2s",
    "broadway_four_straight_g2": "Kd Qc Jh Ts 4d",
    "low_trips_g2": "5s 5d 5c Qh 2d",
    "full_house_board_g2": "9c 9d 9h 4s 4h",
    "five_club_board_g2": "Ac Jc 8c 5c 3c",
    "high_connected_rainbow_g2": "Qs Jd 9h 8c 4s",
}


def _normalized_board(text: str) -> frozenset[str]:
    return frozenset(text.split())


def validate_gen2_board_firewall() -> None:
    earlier = {
        **RIVER_BOARDS,
        **R4_REPRESENTATION_HELDOUT_V1_BOARDS,
    }
    if set(earlier).intersection(R4_GEN2_HELDOUT_V2_BOARDS):
        raise RuntimeError("Generation-2 held-out names overlap earlier R4 boards")

    earlier_cards = {_normalized_board(text) for text in earlier.values()}
    heldout_cards = [_normalized_board(text) for text in R4_GEN2_HELDOUT_V2_BOARDS.values()]
    if len(set(heldout_cards)) != len(heldout_cards):
        raise RuntimeError("Generation-2 held-out contains duplicate physical boards")
    if any(board in earlier_cards for board in heldout_cards):
        raise RuntimeError("Generation-2 held-out reuses an earlier physical board")


validate_gen2_board_firewall()


def gen2_board_registry(name: str) -> dict[str, str]:
    if name == "dev":
        return dict(R4_GEN2_DEV_BOARDS)
    if name == "heldout_v2":
        return dict(R4_GEN2_HELDOUT_V2_BOARDS)
    raise ValueError("R4 Generation-2 board set must be dev or heldout_v2")
