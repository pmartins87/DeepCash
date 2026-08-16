from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import (
    ONE_BET_CANDIDATES,
    ONE_BET_REFERENCE_FRACTIONS,
    RIVER_BOARDS,
    parse_cards,
    parse_checkpoints,
    parse_names,
    quantile_range,
    restriction_loss_bounds,
)
from deepcash_core.river_lab import materialize_bet_sizes
from deepcash_core.river_reference_dp import asymmetric_result_from_state_dp
from deepcash_core.river_reference_lab import AsymmetricRiverGameSpec
from deepcash_core.river_reference_training import (
    advance_asymmetric_river_cfr_plus,
    init_asymmetric_river_cfr_plus,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="DP-accelerated cumulative common-reference convergence v2")
    ap.add_argument("--checkpoints", default="250,1000,3000")
    ap.add_argument("--range-combos", type=int, default=4)
    ap.add_argument("--pot", type=int, default=100)
    ap.add_argument("--stack", type=int, default=300)
    ap.add_argument("--min-bet", type=int, default=20)
    ap.add_argument("--boards", default="all")
    ap.add_argument("--candidates", default="all")
    ap.add_argument("--out", type=Path, default=Path("river_reference_convergence_dp_v2.json"))
    args = ap.parse_args()

    checkpoints = parse_checkpoints(args.checkpoints)
    boards = parse_names(args.boards, RIVER_BOARDS)
    candidates = parse_names(args.candidates, ONE_BET_CANDIDATES)
    reference_sizes = materialize_bet_sizes(
        pot=args.pot, stack=args.stack, min_bet=args.min_bet,
        fractions=ONE_BET_REFERENCE_FRACTIONS,
    )
    rows = []

    for board_name in boards:
        board = parse_cards(RIVER_BOARDS[board_name])
        p0 = quantile_range(board, args.range_combos, 0.00)
        p1 = quantile_range(board, args.range_combos, 0.27)
        ref_spec = AsymmetricRiverGameSpec(board, p0, p1, args.pot, reference_sizes, reference_sizes)
        ref_state = init_asymmetric_river_cfr_plus(ref_spec)
        ref_seconds = 0.0

        candidate_states = {}
        for name in candidates:
            sizes = materialize_bet_sizes(
                pot=args.pot, stack=args.stack, min_bet=args.min_bet,
                fractions=ONE_BET_CANDIDATES[name],
            )
            if not set(sizes).issubset(reference_sizes):
                raise RuntimeError("candidate escaped common reference")
            p0_spec = AsymmetricRiverGameSpec(board, p0, p1, args.pot, sizes, reference_sizes)
            p1_spec = AsymmetricRiverGameSpec(board, p0, p1, args.pot, reference_sizes, sizes)
            candidate_states[name] = {
                "sizes": sizes,
                "p0_spec": p0_spec,
                "p1_spec": p1_spec,
                "p0_state": init_asymmetric_river_cfr_plus(p0_spec),
                "p1_state": init_asymmetric_river_cfr_plus(p1_spec),
                "p0_seconds": 0.0,
                "p1_seconds": 0.0,
            }

        for checkpoint in checkpoints:
            started = time.perf_counter()
            advance_asymmetric_river_cfr_plus(
                ref_spec, ref_state,
                additional_iterations=checkpoint - ref_state.iterations,
            )
            ref_seconds += time.perf_counter() - started
            started = time.perf_counter()
            ref_result = asymmetric_result_from_state_dp(ref_spec, ref_state)
            ref_eval = time.perf_counter() - started

            for name, item in candidate_states.items():
                started = time.perf_counter()
                advance_asymmetric_river_cfr_plus(
                    item["p0_spec"], item["p0_state"],
                    additional_iterations=checkpoint - item["p0_state"].iterations,
                )
                item["p0_seconds"] += time.perf_counter() - started
                started = time.perf_counter()
                advance_asymmetric_river_cfr_plus(
                    item["p1_spec"], item["p1_state"],
                    additional_iterations=checkpoint - item["p1_state"].iterations,
                )
                item["p1_seconds"] += time.perf_counter() - started

                started = time.perf_counter()
                p0r = asymmetric_result_from_state_dp(item["p0_spec"], item["p0_state"])
                p0_eval = time.perf_counter() - started
                started = time.perf_counter()
                p1r = asymmetric_result_from_state_dp(item["p1_spec"], item["p1_state"])
                p1_eval = time.perf_counter() - started

                bounds = restriction_loss_bounds(ref_result, p0r, p1r, args.pot)
                interval = max(
                    ref_result.br0_value - ref_result.br1_value,
                    p0r.br0_value - p0r.br1_value,
                    p1r.br0_value - p1r.br1_value,
                ) / float(args.pot)
                rows.append({
                    "board": board_name,
                    "candidate": name,
                    "candidate_sizes": list(item["sizes"]),
                    "reference_sizes": list(reference_sizes),
                    "checkpoint": checkpoint,
                    "range_combos": args.range_combos,
                    "pot": args.pot,
                    "stack": args.stack,
                    "spr": args.stack / args.pot,
                    "max_value_interval_width_per_pot": interval,
                    "reference_exploitability_per_pot": ref_result.exploitability_per_pot,
                    "p0_restricted_exploitability_per_pot": p0r.exploitability_per_pot,
                    "p1_restricted_exploitability_per_pot": p1r.exploitability_per_pot,
                    "reference_cumulative_train_seconds": ref_seconds,
                    "p0_cumulative_train_seconds": item["p0_seconds"],
                    "p1_cumulative_train_seconds": item["p1_seconds"],
                    "reference_eval_seconds": ref_eval,
                    "p0_eval_seconds": p0_eval,
                    "p1_eval_seconds": p1_eval,
                    "best_response_oracle": "dynamic_exact_dp_gated_against_enumerator",
                    **bounds,
                })
                print(
                    f"{board_name:16s} {name:18s} iter={checkpoint:5d} "
                    f"upper/pot={bounds['worst_loss_upper_per_pot']:.6f} "
                    f"interval/pot={interval:.6f}"
                )

    payload = {
        "schema": "DEEPCASH_RIVER_REFERENCE_CONVERGENCE_V1",
        "engine": "DEEPCASH_DYNAMIC_EXACT_BR_V1",
        "checkpoints": list(checkpoints),
        "range_combos": args.range_combos,
        "pot": args.pot,
        "stack": args.stack,
        "min_bet": args.min_bet,
        "reference_sizes": list(reference_sizes),
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
