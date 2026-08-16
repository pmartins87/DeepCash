from __future__ import annotations

import argparse
import json
import statistics
import time
from fractions import Fraction
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import RIVER_BOARDS, parse_cards, quantile_range
from deepcash_core.river_external_sampling import (
    ExternalSamplingVariant,
    advance_external_sampling,
    external_sampling_result,
    init_external_sampling,
)
from deepcash_core.river_lab import RiverGameSpec, _valid_deals, materialize_bet_sizes
from deepcash_core.river_solver_variants import (
    SolverVariant,
    advance_river_solver,
    init_river_solver,
    river_solver_result,
)


def _ints(text: str) -> tuple[int, ...]:
    vals = tuple(int(v.strip()) for v in text.split(",") if v.strip())
    if not vals or any(v <= 0 for v in vals) or len(set(vals)) != len(vals):
        raise argparse.ArgumentTypeError("values must be unique positive integers")
    return vals


def _names(text: str) -> tuple[str, ...]:
    vals = tuple(v.strip() for v in text.split(",") if v.strip())
    if not vals or len(set(vals)) != len(vals):
        raise argparse.ArgumentTypeError("board names must be non-empty and unique")
    unknown = set(vals) - set(RIVER_BOARDS)
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown boards: {sorted(unknown)}")
    return vals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boards", type=_names, default=("A_high_dry", "four_straight"))
    parser.add_argument("--range-combos", type=_ints, default=(6, 12, 24, 48))
    parser.add_argument("--full-checkpoints", type=_ints, default=(100, 400))
    parser.add_argument("--es-checkpoints", type=_ints, default=(20000, 80000))
    parser.add_argument("--es-seeds", type=_ints, default=(29, 101))
    parser.add_argument("--pot", type=int, default=100)
    parser.add_argument("--stack", type=int, default=400)
    parser.add_argument("--p0-phase", type=float, default=0.0)
    parser.add_argument("--p1-phase", type=float, default=0.27)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    full_checkpoints = tuple(sorted(args.full_checkpoints))
    es_checkpoints = tuple(sorted(args.es_checkpoints))
    if full_checkpoints != args.full_checkpoints or es_checkpoints != args.es_checkpoints:
        raise ValueError("checkpoint lists must already be strictly increasing")
    if args.pot <= 0 or args.stack <= 0:
        raise ValueError("pot/stack must be positive")

    bet_sizes = materialize_bet_sizes(
        pot=args.pot,
        stack=args.stack,
        min_bet=1,
        fractions=(Fraction(1, 4), Fraction(1, 2), Fraction(1, 1)),
    )
    rows: list[dict] = []

    for combo_count in args.range_combos:
        for board_name in args.boards:
            board = parse_cards(RIVER_BOARDS[board_name])
            spec = RiverGameSpec(
                board=board,
                p0_range=quantile_range(board, combo_count, args.p0_phase),
                p1_range=quantile_range(board, combo_count, args.p1_phase),
                pot=args.pot,
                bet_sizes=bet_sizes,
            )
            deal_count = len(_valid_deals(spec))

            full = init_river_solver(spec, SolverVariant.CFR_PLUS_LINEAR)
            trained = 0
            elapsed = 0.0
            for checkpoint in full_checkpoints:
                start = time.perf_counter()
                advance_river_solver(spec, full, additional_iterations=checkpoint - trained)
                elapsed += time.perf_counter() - start
                trained = checkpoint
                eval_start = time.perf_counter()
                result = river_solver_result(spec, full)
                eval_seconds = time.perf_counter() - eval_start
                rows.append(
                    {
                        "algorithm": "CFR_PLUS_LINEAR",
                        "board": board_name,
                        "range_combos": combo_count,
                        "deal_count": deal_count,
                        "seed": None,
                        "checkpoint": checkpoint,
                        "exploitability_per_pot": result.exploitability_per_pot,
                        "policy_ev": result.policy_ev,
                        "br0_value": result.br0_value,
                        "br1_value": result.br1_value,
                        "value_interval_width": result.br0_value - result.br1_value,
                        "cumulative_training_seconds": elapsed,
                        "evaluation_seconds": eval_seconds,
                        "terminal_visits": None,
                    }
                )
                print(
                    f"FULL board={board_name} combos={combo_count} deals={deal_count} "
                    f"iter={checkpoint} exploit/pot={result.exploitability_per_pot:.8f} "
                    f"train_s={elapsed:.3f}"
                )

            for seed in args.es_seeds:
                es = init_external_sampling(
                    spec, ExternalSamplingVariant.ES_CFR_PLUS_LINEAR, seed=seed
                )
                trained = 0
                elapsed = 0.0
                for checkpoint in es_checkpoints:
                    start = time.perf_counter()
                    advance_external_sampling(
                        spec, es, additional_iterations=checkpoint - trained
                    )
                    elapsed += time.perf_counter() - start
                    trained = checkpoint
                    eval_start = time.perf_counter()
                    result = external_sampling_result(spec, es)
                    eval_seconds = time.perf_counter() - eval_start
                    rows.append(
                        {
                            "algorithm": "ES_CFR_PLUS_LINEAR",
                            "board": board_name,
                            "range_combos": combo_count,
                            "deal_count": deal_count,
                            "seed": seed,
                            "checkpoint": checkpoint,
                            "exploitability_per_pot": result.exploitability_per_pot,
                            "policy_ev": result.policy_ev,
                            "br0_value": result.br0_value,
                            "br1_value": result.br1_value,
                            "value_interval_width": result.br0_value - result.br1_value,
                            "cumulative_training_seconds": elapsed,
                            "evaluation_seconds": eval_seconds,
                            "terminal_visits": es.terminal_visits,
                        }
                    )
                    print(
                        f"ES board={board_name} combos={combo_count} deals={deal_count} seed={seed} "
                        f"iter={checkpoint} exploit/pot={result.exploitability_per_pot:.8f} "
                        f"visits={es.terminal_visits} train_s={elapsed:.3f}"
                    )

    aggregate: list[dict] = []
    for combo_count in args.range_combos:
        for algorithm, checkpoints in (
            ("CFR_PLUS_LINEAR", full_checkpoints),
            ("ES_CFR_PLUS_LINEAR", es_checkpoints),
        ):
            for checkpoint in checkpoints:
                selected = [
                    row for row in rows
                    if row["range_combos"] == combo_count
                    and row["algorithm"] == algorithm
                    and row["checkpoint"] == checkpoint
                ]
                values = [float(row["exploitability_per_pot"]) for row in selected]
                times = [float(row["cumulative_training_seconds"]) for row in selected]
                aggregate.append(
                    {
                        "range_combos": combo_count,
                        "algorithm": algorithm,
                        "checkpoint": checkpoint,
                        "cells": len(selected),
                        "mean_exploitability_per_pot": statistics.mean(values),
                        "worst_exploitability_per_pot": max(values),
                        "stdev_exploitability_per_pot": statistics.stdev(values) if len(values) > 1 else 0.0,
                        "mean_cumulative_training_seconds": statistics.mean(times),
                        "worst_cumulative_training_seconds": max(times),
                    }
                )

    payload = {
        "schema": "DEEPCASH_R5_SAMPLING_CROSSOVER_V1",
        "boards": list(args.boards),
        "range_combos": list(args.range_combos),
        "full_checkpoints": list(full_checkpoints),
        "es_checkpoints": list(es_checkpoints),
        "es_seeds": list(args.es_seeds),
        "pot": args.pot,
        "stack": args.stack,
        "spr": args.stack / args.pot,
        "p0_phase": args.p0_phase,
        "p1_phase": args.p1_phase,
        "bet_sizes": list(bet_sizes),
        "rows": rows,
        "aggregate": aggregate,
        "methodology_note": (
            "Precommitted development scaling battery. Iteration counts are intentionally "
            "not treated as equal work; interpretation uses recorded wall clock, exact deal "
            "support and exploitability. Hosted timing is not target-Ryzen evidence."
        ),
    }
    Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
