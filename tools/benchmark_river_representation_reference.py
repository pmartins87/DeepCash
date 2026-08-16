from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import (
    ONE_BET_REFERENCE_FRACTIONS,
    parse_cards,
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
    solve_river_representation_cfr_plus,
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
    ap.add_argument("--iterations", type=int, default=600)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("river_representation_reference.json"),
    )
    args = ap.parse_args()

    if args.range_combos <= 0 or args.iterations <= 0:
        raise ValueError("range-combos and iterations must be positive")

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

        started = time.perf_counter()
        reference = solve_river_representation_cfr_plus(
            spec, exact_bucket_maps(spec), iterations=args.iterations
        )
        reference_seconds = time.perf_counter() - started

        for candidate_name in candidate_names:
            candidate = candidate_bucket_maps(spec, candidate_name)

            started = time.perf_counter()
            p0_restricted = solve_river_representation_cfr_plus(
                spec,
                one_sided_bucket_maps(spec, candidate, 0),
                iterations=args.iterations,
            )
            p0_seconds = time.perf_counter() - started

            started = time.perf_counter()
            p1_restricted = solve_river_representation_cfr_plus(
                spec,
                one_sided_bucket_maps(spec, candidate, 1),
                iterations=args.iterations,
            )
            p1_seconds = time.perf_counter() - started

            started = time.perf_counter()
            joint = solve_river_representation_cfr_plus(
                spec, candidate, iterations=args.iterations
            )
            joint_seconds = time.perf_counter() - started

            bounds = restriction_loss_bounds(
                reference, p0_restricted, p1_restricted, args.pot
            )
            interval_width = max(
                reference.br0_value - reference.br1_value,
                p0_restricted.br0_value - p0_restricted.br1_value,
                p1_restricted.br0_value - p1_restricted.br1_value,
            ) / float(args.pot)
            exact_buckets = len(p0_range) + len(p1_range)
            materialized_buckets = candidate.p0_bucket_count + candidate.p1_bucket_count
            row = {
                "board_set": args.board_set,
                "board": board_name,
                "candidate": candidate_name,
                "iterations": args.iterations,
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
                "reference_train_seconds": reference_seconds,
                "p0_restricted_train_seconds": p0_seconds,
                "p1_restricted_train_seconds": p1_seconds,
                "joint_train_seconds": joint_seconds,
                "joint_exploitability_per_pot": joint.exploitability_per_pot,
                "max_value_interval_width_per_pot": interval_width,
                "method": "one_sided_private_infoset_aliasing_against_exact_combo_common_reference",
                **bounds,
            }
            rows.append(row)
            print(
                f"{args.board_set:10s} {board_name:24s} {candidate_name:20s} "
                f"buckets={materialized_buckets:2d}/{exact_buckets:2d} "
                f"upper/pot={bounds['worst_loss_upper_per_pot']:.6f} "
                f"joint_exp/pot={joint.exploitability_per_pot:.6f} "
                f"interval/pot={interval_width:.6f}"
            )

    payload = {
        "schema": "DEEPCASH_RIVER_REPRESENTATION_REFERENCE_V1",
        "method": (
            "exact card removal/payoffs/rich one-bet action tree; exact-combo reference; "
            "candidate private infosets aliased one player at a time; exact best responses "
            "computed after expanding candidate policy back to combo identity"
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
        "iterations": args.iterations,
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
