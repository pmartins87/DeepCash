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
from deepcash_core.river_hs_dcfr import (
    PaperDCFRVariant,
    advance_paper_dcfr,
    init_paper_dcfr,
    paper_dcfr_result,
)
from deepcash_core.river_lab import RiverGameSpec, materialize_bet_sizes


def _ints(text: str) -> tuple[int, ...]:
    values = tuple(int(v.strip()) for v in text.split(",") if v.strip())
    if not values or any(v <= 0 for v in values) or len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("values must be unique positive integers")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoints", type=_ints, default=(100, 400, 1200))
    parser.add_argument("--horizon", type=int, default=1200)
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
    if checkpoints[-1] > args.horizon or args.horizon <= 0:
        raise ValueError("checkpoints must fit inside positive frozen horizon")
    if args.range_combos <= 0 or args.pot <= 0 or args.stack <= 0:
        raise ValueError("range-combos/pot/stack must be positive")

    bet_sizes = materialize_bet_sizes(
        pot=args.pot,
        stack=args.stack,
        min_bet=1,
        fractions=(Fraction(1, 4), Fraction(1, 2), Fraction(1, 1)),
    )
    algorithms = (
        "ALT_CFR_PLUS_LINEAR",
        "OPEN_SPIEL_STYLE_POST_DCFR_150_0_2",
        PaperDCFRVariant.PAPER_DCFR_150_0_2.value,
        PaperDCFRVariant.HS_DCFR_30.value,
        PaperDCFRVariant.HS_DCFR_15.value,
    )
    rows: list[dict] = []

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
            if algorithm == "ALT_CFR_PLUS_LINEAR":
                state = init_alternating_solver(spec, AlternatingVariant.ALT_CFR_PLUS_LINEAR)
                advance = advance_alternating_solver
                result_fn = alternating_solver_result
            elif algorithm == "OPEN_SPIEL_STYLE_POST_DCFR_150_0_2":
                state = init_alternating_solver(spec, AlternatingVariant.ALT_DCFR_150_0_2)
                advance = advance_alternating_solver
                result_fn = alternating_solver_result
            else:
                state = init_paper_dcfr(
                    spec,
                    PaperDCFRVariant(algorithm),
                    horizon=args.horizon,
                )
                advance = advance_paper_dcfr
                result_fn = paper_dcfr_result

            trained = 0
            elapsed = 0.0
            for checkpoint in checkpoints:
                start = time.perf_counter()
                advance(spec, state, additional_iterations=checkpoint - trained)
                elapsed += time.perf_counter() - start
                trained = checkpoint
                eval_start = time.perf_counter()
                result = result_fn(spec, state)
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
                        "cumulative_training_seconds": elapsed,
                        "evaluation_seconds": eval_seconds,
                    }
                )
                print(
                    f"{board_name} {algorithm} iter={checkpoint}/{args.horizon} "
                    f"exploit/pot={result.exploitability_per_pot:.10f} "
                    f"train_s={elapsed:.3f}"
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
        "schema": "DEEPCASH_R5_PAPER_HS_DCFR_BENCHMARK_V1",
        "horizon": args.horizon,
        "checkpoints": list(checkpoints),
        "algorithms": list(algorithms),
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
            "Precommitted exact full-tree development control. PAPER/HS variants implement "
            "the 2026 paper recurrence old-discount-then-add; the historical DeepCash/OpenSpiel-"
            "style post-update discounted control is retained explicitly as a comparator."
        ),
    }
    Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
