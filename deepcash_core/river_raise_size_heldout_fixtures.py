from __future__ import annotations

# Raise-size validation receives its own unseen boards so it does not consume the
# opening-size held-out-v2 generation. These fixtures are frozen before the
# raise-size held-out workflow is launched.
RAISE_SIZE_HELDOUT_BOARDS = {
    "raise_A_paired_wet": "Ad Ac Js 8d 3c",
    "raise_K_high_four_straight": "Kc 9d 8h 7s 6c",
    "raise_three_flush": "Qd 9d 5d 3c 2s",
    "raise_double_pair_high": "Kh Kd 7s 7c 2d",
    "raise_low_connected": "Tc 6h 4d 3s 2c",
    "raise_quads_board": "5s 5h 5d 5c Ah",
}

RAISE_SIZE_HELDOUT_P0_PHASE = 0.22
RAISE_SIZE_HELDOUT_P1_PHASE = 0.68
RAISE_SIZE_HELDOUT_RANGE_COMBOS = 6
RAISE_SIZE_HELDOUT_STACKS = (100, 200, 400)
RAISE_SIZE_HELDOUT_CHECKPOINTS = (300, 1200, 3600)
