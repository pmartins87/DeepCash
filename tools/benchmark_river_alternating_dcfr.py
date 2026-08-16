from __future__ import annotations

import argparse
import json
import statistics
import time
from fractions import Fraction
from pathlib import Path

from deepcash_core.river_alternating_dcfr import (
    AlternatingVariant,
    advance_alternating_solver,
    alternating_solver_result,
    init_alternating_solver,
)
from deepcash_core.river_benchmark_fixtures import RIVER_BOARDS, parse_cards, quantile_range
from deepcash_core.river_lab import RiverGameSpec, materialize_bet_sizes
from deepcash_core.river_solver_variants import (
    SolverVariant,
    advance_river_solver,
    init_river_solver,
    river_solver_result,
)


def _ints(text: str) -> tuple[int, ...]:
    vals = tuple(int(v.strip()) for v in text.split(",") if v.strip())
    if not vals or any(v <= 0 for v in vals) or len(set(vals)) != len(vals):
        raise argparse.ArgumentTypeError("checkpoints must be unique positive integers")
    return vals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoints", type=_ints, default=(100, 400, 1200))
    parser.add_argument("--range-combos", type=int, default=6)
    parser.add_argument("--pot", type=int, default=100)
    parser.add_argument("--stack", type=int, default=400)
    parser.add_argument("--p0-phase", type=float, default=0.0)
    parser.add_argument("--p1-phase", type=float, default=0.27)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    checkpoints = tuple(sorted(args.checkpoints))
    if checkpoints != args.checkpoints:
        raise ValueError("checkpoints must already be strictly increasing")
    if args.range_combos <= 0 or args.pot <= 0 or args.stack <= 0:
        raise ValueError("range-combos/pot/stack must be positive")

    bet_sizes = materialize_bet_sizes(
        pot=args.pot,
        stack=args.stack,
        min_bet=1,
        fractions=(Fraction(1, 4), Fraction(1, 2), Fraction(1, 1)),
    )
    rows: list[dict] = []
    algorithms = ("SYNC_CFR_PLUS_LINEAR",) + tuple(v.value for v in AlternatingVariant)

    for board_name, board_text in RIVER_BOARDS.items():
        board = parse_cards(board_text)
        spec = RiverGameSpec(
            board=board,
            p0_range=quantile_range(board, args.range_combos, args.p0_phase),
            p1_range=quantile_range(board, args.range_combos, args.p1_phase),
            pot=args.pot,
            bet_sizes=bet_sizes,
        )

        for algorithm in algorithms:
            if algorithm == "SYNC_CFR_PLUS_LINEAR":
                state = init_river_solver(spec, SolverVariant.CFR_PLUS_LINEAR)
                advance = advance_river_solver
                get_result = river_solver_result
            else:
                state = init_alternating_solver(spec, AlternatingVariant(algorithm))
                advance = advance_alternating_solver
                get_result = alternating_solver_result

            trained = 0
            cumulative_seconds = 0.0
            for checkpoint in checkpoints:
                start = time.perf_counter()
                advance(spec, state, additional_iterations=checkpoint - trained)
                cumulative_seconds += time.perf_counter() - start
                trained = checkpoint
                eval_start = time.perf_counter()
                result = get_result(spec, state)
                eval_seconds = time.perf_counter() - eval_start
                rows.append(
                    {
                        "board": board_name,
                        "algorithm": algorithm,
                        "checkpoint": checkpoint,
                        "exploitability_per_pot": result.exploitability_per_pot,
                        "policy_ev": result.policy_ev,
                        "br0_value": result.br0_value,
                        "br1_value": result.br1_value,
                        "value_interval_width": result.br0_value - result.br1_value,
                        "infosets": result.infosets,
                        "action_slots": result.action_slots,
                        "cumulative_training_seconds": cumulative_seconds,
                        "evaluation_seconds": eval_seconds,
                    }
                )
                print(
                    f"{board_name} {algorithm} iter={checkpoint} "
                    f"exploit/pot={result.exploitability_per_pot:.8f} "
                    f"train_s={cumulative_seconds:.3f}"
                )

    aggregate = []
    for checkpoint in checkpoints:
        for algorithm in algorithms:
            selected = [
                row for row in rows
                if row["checkpoint"] == checkpoint and row["algorithm"] == algorithm
            ]
            values = [float(row["exploitability_per_pot"]) for row in selected]
            times = [float(row["cumulative_training_seconds"]) for row in selected]
            aggregate.append(
                {
                    "checkpoint": checkpoint,
                    "algorithm": algorithm,
                    "cells": len(selected),
                    "mean_exploitability_per_pot": statistics.mean(values),
                    "worst_exploitability_per_pot": max(values),
                    "stdev_exploitability_per_pot": statistics.stdev(values) if len(values) > 1 else 0.0,
                    "mean_cumulative_training_seconds": statistics.mean(times),
                }
            )

    payload = {
        "schema": "DEEPCASH_R5_ALTERNATING_DCFR_BENCHMARK_V1",
        "board_set": "R3_CONTROL_ONLY",
        "algorithms": list(algorithms),
        "checkpoints": list(checkpoints),
        "range_combos": args.range_combos,
        "pot": args.pot,
        "stack": args.stack,
        "spr": args.stack / args.pot,
        "p0_phase": args.p0_phase,
        "p1_phase": args.p1_phase,
        "bet_sizes": list(bet_sizes),
        "rows": rows,
        "aggregate": aggregate,
        "methodology_note": (
            "Precommitted exact full-tree development control. Alternating variants update "
            "P0 then P1 from the newly updated profile and average the post-alternation "
            "strategy. Hosted timing is not target-Ryzen production evidence."
        ),
    }
    Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
