from __future__ import annotations

import argparse
import json
import statistics
import time
from fractions import Fraction
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import RIVER_BOARDS, parse_cards, quantile_range
from deepcash_core.river_external_lcfr import (
    AlternatingExternalVariant,
    advance_alternating_external,
    alternating_external_result,
    init_alternating_external,
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
    variants = tuple(AlternatingExternalVariant)
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
        for variant in variants:
            for seed in args.seeds:
                state = init_alternating_external(spec, variant, seed=seed)
                trained = 0
                elapsed = 0.0
                for checkpoint in checkpoints:
                    start = time.perf_counter()
                    advance_alternating_external(
                        spec, state, additional_iterations=checkpoint - trained
                    )
                    elapsed += time.perf_counter() - start
                    trained = checkpoint
                    eval_start = time.perf_counter()
                    result = alternating_external_result(spec, state)
                    eval_seconds = time.perf_counter() - eval_start
                    rows.append(
                        {
                            "board": board_name,
                            "variant": variant.value,
                            "seed": seed,
                            "checkpoint": checkpoint,
                            "exploitability_per_pot": result.exploitability_per_pot,
                            "policy_ev": result.policy_ev,
                            "br0_value": result.br0_value,
                            "br1_value": result.br1_value,
                            "value_interval_width": result.br0_value - result.br1_value,
                            "cumulative_training_seconds": elapsed,
                            "evaluation_seconds": eval_seconds,
                            "terminal_visits": state.terminal_visits,
                            "infosets": result.infosets,
                            "action_slots": result.action_slots,
                        }
                    )
                    print(
                        f"{board_name} {variant.value} seed={seed} iter={checkpoint} "
                        f"exploit/pot={result.exploitability_per_pot:.8f} "
                        f"visits={state.terminal_visits} train_s={elapsed:.3f}"
                    )

    aggregate = []
    for checkpoint in checkpoints:
        for variant in variants:
            selected = [
                row for row in rows
                if row["checkpoint"] == checkpoint and row["variant"] == variant.value
            ]
            values = [float(row["exploitability_per_pot"]) for row in selected]
            times = [float(row["cumulative_training_seconds"]) for row in selected]
            aggregate.append(
                {
                    "checkpoint": checkpoint,
                    "variant": variant.value,
                    "cells": len(selected),
                    "mean_exploitability_per_pot": statistics.mean(values),
                    "median_exploitability_per_pot": statistics.median(values),
                    "worst_exploitability_per_pot": max(values),
                    "stdev_exploitability_per_pot": statistics.stdev(values),
                    "mean_cumulative_training_seconds": statistics.mean(times),
                    "mean_terminal_visits": statistics.mean(
                        int(row["terminal_visits"]) for row in selected
                    ),
                }
            )

    payload = {
        "schema": "DEEPCASH_R5_ALTERNATING_EXTERNAL_LCFR_BENCHMARK_V1",
        "checkpoints": list(checkpoints),
        "seeds": list(args.seeds),
        "variants": [variant.value for variant in variants],
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
            "Precommitted alternating external-sampling development control. Each player "
            "contributes its exact own-reach average immediately before its own sampled "
            "traversal; P1 uses the profile refreshed after P0's update."
        ),
    }
    Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
