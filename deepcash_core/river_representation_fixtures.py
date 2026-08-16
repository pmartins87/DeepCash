from __future__ import annotations

from .river_benchmark_fixtures import RIVER_BOARDS


# R4 development deliberately reuses only already-seen R3 control boards.
# It must not touch any R3 held-out registry while those action-abstraction gates
# are active.
R4_REPRESENTATION_DEV_BOARDS = dict(RIVER_BOARDS)


# Frozen before accepting any R4 numerical result. These boards are independent
# of R3 control, heldout-v1 and heldout-v2 registries so state-abstraction work
# cannot consume action-abstraction validation evidence.
R4_REPRESENTATION_HELDOUT_V1_BOARDS = {
    "king_wheel_dry_r4": "Kd 7c 4h 3s 2d",
    "ace_paired_r4": "Ac Ad 9h 6s 2c",
    "three_club_connected_r4": "Jc 9c 7c 5d 2h",
    "broadway_four_straight_r4": "Ad Kc Qs Jd 3h",
    "low_double_paired_r4": "6s 6d 3c 3h Kh",
    "quads_board_r4": "8c 8d 8h 8s Ac",
    "mid_connected_rainbow_r4": "Td 9c 7h 6s 4d",
    "four_spade_r4": "Ks Js 8s 5s 2d",
}


def representation_board_registry(name: str) -> dict[str, str]:
    if name == "dev":
        return dict(R4_REPRESENTATION_DEV_BOARDS)
    if name == "heldout_v1":
        return dict(R4_REPRESENTATION_HELDOUT_V1_BOARDS)
    if name == "all":
        overlap = set(R4_REPRESENTATION_DEV_BOARDS) & set(
            R4_REPRESENTATION_HELDOUT_V1_BOARDS
        )
        if overlap:
            raise RuntimeError(f"R4 development/held-out names overlap: {sorted(overlap)}")
        return {
            **R4_REPRESENTATION_DEV_BOARDS,
            **R4_REPRESENTATION_HELDOUT_V1_BOARDS,
        }
    raise ValueError("R4 board set must be dev, heldout_v1, or all")
