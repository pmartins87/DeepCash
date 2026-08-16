from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import (
    ONE_BET_REFERENCE_FRACTIONS,
    parse_cards,
    parse_checkpoints,
    parse_names,
    quantile_range,
    restriction_loss_bounds,
)
from deepcash_core.river_lab import RiverGameSpec, materialize_bet_sizes
from deepcash_core.river_representation_fixtures import representation_board_registry
from deepcash_core.river_representation_lab import (
    RIVER_REPRESENTATION_CANDIDATES,
    candidate_bucket_maps,
    exact_bucket_maps,
    one_sided_bucket_maps,
)
from deepcash_core.river_representation_training import (
    advance_representation_cfr_plus,
    init_representation_cfr_plus,
    representation_result_from_state,
)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Measure river private-state representation restriction loss against "
            "an exact-combo common reference while keeping cards/payoffs/actions exact"
        )
    )
    ap.add_argument("--board-set", default="dev", choices=("dev", "heldout_v1"))
    ap.add_argument("--boards", default="all")
    ap.add_argument("--candidates", default="all")
    ap.add_argument("--range-combos", type=int, default=6)
    ap.add_argument("--p0-phase", type=float, default=0.00)
    ap.add_argument("--p1-phase", type=float, default=0.27)
    ap.add_argument("--pot", type=int, default=100)
    ap.add_argument("--stack", type=int, default=400)
    ap.add_argument("--min-bet", type=int, default=20)
    ap.add_argument("--checkpoints", default="100,400,1200")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("river_representation_reference.json"),
    )
    args = ap.parse_args()

    if args.range_combos <= 0:
        raise ValueError("range-combos must be positive")

    checkpoints = parse_checkpoints(args.checkpoints)
    board_registry = representation_board_registry(args.board_set)
    board_names = parse_names(args.boards, board_registry)
    available = {name: name for name in RIVER_REPRESENTATION_CANDIDATES}
    candidate_names = parse_names(args.candidates, available)
    bet_sizes = materialize_bet_sizes(
        pot=args.pot,
        stack=args.stack,
        min_bet=args.min_bet,
        fractions=ONE_BET_REFERENCE_FRACTIONS,
    )

    rows = []
    for board_name in board_names:
        board = parse_cards(board_registry[board_name])
        p0_range = quantile_range(board, args.range_combos, args.p0_phase)
        p1_range = quantile_range(board, args.range_combos, args.p1_phase)
        spec = RiverGameSpec(board, p0_range, p1_range, args.pot, bet_sizes)

        exact_maps = exact_bucket_maps(spec)
        reference_state = init_representation_cfr_plus(spec, exact_maps)
        reference_seconds = 0.0

        candidates = {}
        for candidate_name in candidate_names:
            candidate = candidate_bucket_maps(spec, candidate_name)
            p0_maps = one_sided_bucket_maps(spec, candidate, 0)
            p1_maps = one_sided_bucket_maps(spec, candidate, 1)
            candidates[candidate_name] = {
                "maps": candidate,
                "p0_maps": p0_maps,
                "p1_maps": p1_maps,
                "p0_state": init_representation_cfr_plus(spec, p0_maps),
                "p1_state": init_representation_cfr_plus(spec, p1_maps),
                "joint_state": init_representation_cfr_plus(spec, candidate),
                "p0_seconds": 0.0,
                "p1_seconds": 0.0,
                "joint_seconds": 0.0,
            }

        for checkpoint in checkpoints:
            started = time.perf_counter()
            advance_representation_cfr_plus(
                spec,
                exact_maps,
                reference_state,
                additional_iterations=checkpoint - reference_state.iterations,
            )
            reference_seconds += time.perf_counter() - started
            reference = representation_result_from_state(
                spec, exact_maps, reference_state
            )

            for candidate_name, item in candidates.items():
                candidate = item["maps"]

                started = time.perf_counter()
                advance_representation_cfr_plus(
                    spec,
                    item["p0_maps"],
                    item["p0_state"],
                    additional_iterations=checkpoint - item["p0_state"].iterations,
                )
                item["p0_seconds"] += time.perf_counter() - started
                p0_restricted = representation_result_from_state(
                    spec, item["p0_maps"], item["p0_state"]
                )

                started = time.perf_counter()
                advance_representation_cfr_plus(
                    spec,
                    item["p1_maps"],
                    item["p1_state"],
                    additional_iterations=checkpoint - item["p1_state"].iterations,
                )
                item["p1_seconds"] += time.perf_counter() - started
                p1_restricted = representation_result_from_state(
                    spec, item["p1_maps"], item["p1_state"]
                )

                started = time.perf_counter()
                advance_representation_cfr_plus(
                    spec,
                    candidate,
                    item["joint_state"],
                    additional_iterations=checkpoint - item["joint_state"].iterations,
                )
                item["joint_seconds"] += time.perf_counter() - started
                joint = representation_result_from_state(
                    spec, candidate, item["joint_state"]
                )

                bounds = restriction_loss_bounds(
                    reference, p0_restricted, p1_restricted, args.pot
                )
                interval_width = max(
                    reference.br0_value - reference.br1_value,
                    p0_restricted.br0_value - p0_restricted.br1_value,
                    p1_restricted.br0_value - p1_restricted.br1_value,
                ) / float(args.pot)
                exact_buckets = len(p0_range) + len(p1_range)
                materialized_buckets = (
                    candidate.p0_bucket_count + candidate.p1_bucket_count
                )
                row = {
                    "board_set": args.board_set,
                    "board": board_name,
                    "candidate": candidate_name,
                    "checkpoint": checkpoint,
                    "range_combos_per_player": args.range_combos,
                    "p0_phase": args.p0_phase,
                    "p1_phase": args.p1_phase,
                    "pot": args.pot,
                    "stack": args.stack,
                    "spr": args.stack / args.pot,
                    "bet_sizes": list(bet_sizes),
                    "p0_buckets": candidate.p0_bucket_count,
                    "p1_buckets": candidate.p1_bucket_count,
                    "bucket_compression_ratio": materialized_buckets / exact_buckets,
                    "reference_infosets": reference.infosets,
                    "joint_infosets": joint.infosets,
                    "reference_action_slots": reference.action_slots,
                    "joint_action_slots": joint.action_slots,
                    "reference_cumulative_train_seconds": reference_seconds,
                    "p0_restricted_cumulative_train_seconds": item["p0_seconds"],
                    "p1_restricted_cumulative_train_seconds": item["p1_seconds"],
                    "joint_cumulative_train_seconds": item["joint_seconds"],
                    "joint_exploitability_per_pot": joint.exploitability_per_pot,
                    "max_value_interval_width_per_pot": interval_width,
                    "method": "one_sided_private_infoset_aliasing_against_exact_combo_common_reference",
                    **bounds,
                }
                rows.append(row)
                print(
                    f"{args.board_set:10s} {board_name:24s} {candidate_name:20s} "
                    f"iter={checkpoint:5d} buckets={materialized_buckets:2d}/{exact_buckets:2d} "
                    f"upper/pot={bounds['worst_loss_upper_per_pot']:.6f} "
                    f"joint_exp/pot={joint.exploitability_per_pot:.6f} "
                    f"interval/pot={interval_width:.6f}"
                )

    payload = {
        "schema": "DEEPCASH_RIVER_REPRESENTATION_REFERENCE_V1",
        "method": (
            "exact card removal/payoffs/rich one-bet action tree; exact-combo reference; "
            "candidate private infosets aliased one player at a time; exact best responses "
            "computed after expanding candidate policy back to combo identity; staged CFR+ "
            "checkpoints use identical global linear-averaging iteration weights"
        ),
        "selection_warning": (
            "development benchmark only; do not freeze representation without independent "
            "held-out boards, tighter convergence where needed, invariance tests and physical "
            "Ryzen equal-wall-clock evidence"
        ),
        "board_set": args.board_set,
        "boards": list(board_names),
        "candidates": list(candidate_names),
        "range_combos_per_player": args.range_combos,
        "p0_phase": args.p0_phase,
        "p1_phase": args.p1_phase,
        "pot": args.pot,
        "stack": args.stack,
        "spr": args.stack / args.pot,
        "bet_sizes": list(bet_sizes),
        "checkpoints": list(checkpoints),
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
