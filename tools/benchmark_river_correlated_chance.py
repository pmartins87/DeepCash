from __future__ import annotations

import argparse
import json
import statistics
import time
from fractions import Fraction
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import RIVER_BOARDS, parse_cards, quantile_range
from deepcash_core.river_chance_sampling import (
    ChanceSamplingVariant,
    advance_chance_sampling,
    chance_sampling_result,
    init_chance_sampling,
)
from deepcash_core.river_correlated_chance_sampling import (
    advance_correlated_chance,
    correlated_chance_result,
    init_correlated_chance,
)
from deepcash_core.river_lab import RiverGameSpec, materialize_bet_sizes


def _ints(text: str) -> tuple[int, ...]:
    values = tuple(int(v.strip()) for v in text.split(",") if v.strip())
    if not values or any(v <= 0 for v in values) or len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("values must be unique positive integers")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoints", type=_ints, default=(1000, 5000, 20000))
    parser.add_argument("--seeds", type=_ints, default=(11, 29, 101, 20260816))
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
    algorithms = ("IID_CS_CFR_PLUS_LINEAR", "CCS_CFR_PLUS_LINEAR")

    for board_name, board_text in RIVER_BOARDS.items():
        board = parse_cards(board_text)
        spec = RiverGameSpec(
            board=board,
            p0_range=quantile_range(board, args.range_combos, args.p0_phase),
            p1_range=quantile_range(board, args.range_combos, args.p1_phase),
            pot=args.pot,
            bet_sizes=bet_sizes,
        )
        for seed in args.seeds:
            for algorithm in algorithms:
                if algorithm == "IID_CS_CFR_PLUS_LINEAR":
                    state = init_chance_sampling(
                        spec, ChanceSamplingVariant.CS_CFR_PLUS_LINEAR, seed=seed
                    )
                    advance = advance_chance_sampling
                    result_fn = chance_sampling_result
                else:
                    state = init_correlated_chance(spec, seed=seed)
                    advance = advance_correlated_chance
                    result_fn = correlated_chance_result

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
                            "seed": seed,
                            "algorithm": algorithm,
                            "checkpoint": checkpoint,
                            "exploitability_per_pot": result.exploitability_per_pot,
                            "policy_ev": result.policy_ev,
                            "br0_value": result.br0_value,
                            "br1_value": result.br1_value,
                            "value_interval_width": result.br0_value - result.br1_value,
                            "cumulative_training_seconds": elapsed,
                            "evaluation_seconds": eval_seconds,
                            "terminal_visits": state.terminal_visits,
                        }
                    )
                    print(
                        f"{board_name} seed={seed} {algorithm} iter={checkpoint} "
                        f"exploit/pot={result.exploitability_per_pot:.8f} train_s={elapsed:.3f}"
                    )

    aggregate: list[dict] = []
    paired: list[dict] = []
    for checkpoint in checkpoints:
        for algorithm in algorithms:
            selected = [
                row for row in rows
                if row["checkpoint"] == checkpoint and row["algorithm"] == algorithm
            ]
            values = [float(row["exploitability_per_pot"]) for row in selected]
            aggregate.append(
                {
                    "checkpoint": checkpoint,
                    "algorithm": algorithm,
                    "cells": len(selected),
                    "mean_exploitability_per_pot": statistics.mean(values),
                    "median_exploitability_per_pot": statistics.median(values),
                    "worst_exploitability_per_pot": max(values),
                    "stdev_exploitability_per_pot": statistics.stdev(values),
                    "mean_cumulative_training_seconds": statistics.mean(
                        float(row["cumulative_training_seconds"]) for row in selected
                    ),
                }
            )

        for board_name in RIVER_BOARDS:
            for seed in args.seeds:
                iid = next(
                    row for row in rows
                    if row["checkpoint"] == checkpoint
                    and row["board"] == board_name
                    and row["seed"] == seed
                    and row["algorithm"] == "IID_CS_CFR_PLUS_LINEAR"
                )
                ccs = next(
                    row for row in rows
                    if row["checkpoint"] == checkpoint
                    and row["board"] == board_name
                    and row["seed"] == seed
                    and row["algorithm"] == "CCS_CFR_PLUS_LINEAR"
                )
                iid_x = float(iid["exploitability_per_pot"])
                ccs_x = float(ccs["exploitability_per_pot"])
                paired.append(
                    {
                        "checkpoint": checkpoint,
                        "board": board_name,
                        "seed": seed,
                        "iid_exploitability_per_pot": iid_x,
                        "ccs_exploitability_per_pot": ccs_x,
                        "ccs_minus_iid": ccs_x - iid_x,
                        "relative_improvement": (iid_x - ccs_x) / iid_x if iid_x > 0 else 0.0,
                    }
                )

    paired_summary = []
    for checkpoint in checkpoints:
        selected = [row for row in paired if row["checkpoint"] == checkpoint]
        deltas = [float(row["ccs_minus_iid"]) for row in selected]
        improvements = [float(row["relative_improvement"]) for row in selected]
        paired_summary.append(
            {
                "checkpoint": checkpoint,
                "cells": len(selected),
                "ccs_better_cells": sum(delta < 0.0 for delta in deltas),
                "iid_better_cells": sum(delta > 0.0 for delta in deltas),
                "ties": sum(delta == 0.0 for delta in deltas),
                "mean_ccs_minus_iid": statistics.mean(deltas),
                "median_ccs_minus_iid": statistics.median(deltas),
                "mean_relative_improvement": statistics.mean(improvements),
                "median_relative_improvement": statistics.median(improvements),
            }
        )

    payload = {
        "schema": "DEEPCASH_R5_CORRELATED_CHANCE_BENCHMARK_V1",
        "source_method": "persistent randomized golden-ratio Weyl root chance stream",
        "checkpoints": list(checkpoints),
        "seeds": list(args.seeds),
        "range_combos": args.range_combos,
        "pot": args.pot,
        "stack": args.stack,
        "spr": args.stack / args.pot,
        "p0_phase": args.p0_phase,
        "p1_phase": args.p1_phase,
        "bet_sizes": list(bet_sizes),
        "rows": rows,
        "aggregate": aggregate,
        "paired": paired,
        "paired_summary": paired_summary,
        "methodology_note": (
            "Paired precommitted development control. IID and CCS share identical CFR+ "
            "regret algebra, exact own-reach average strategy, action traversal and exact BR; "
            "only temporal allocation of private-deal chance outcomes differs."
        ),
    }
    Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
