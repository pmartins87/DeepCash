from __future__ import annotations

import argparse
import json
import time
from fractions import Fraction
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import (
    RIVER_BOARDS,
    parse_cards,
    quantile_range,
)
from deepcash_core.river_lab import RiverGameSpec, materialize_bet_sizes
from deepcash_core.river_solver_variants import (
    SolverVariant,
    advance_river_solver,
    init_river_solver,
    river_solver_result,
)


def _parse_checkpoints(text: str) -> tuple[int, ...]:
    vals = tuple(sorted({int(v.strip()) for v in text.split(",") if v.strip()}))
    if not vals or vals[0] <= 0:
        raise argparse.ArgumentTypeError("checkpoints must be positive")
    return vals


def _parse_variants(text: str) -> tuple[SolverVariant, ...]:
    vals = tuple(SolverVariant(v.strip()) for v in text.split(",") if v.strip())
    if not vals:
        raise argparse.ArgumentTypeError("at least one variant is required")
    if len(set(vals)) != len(vals):
        raise argparse.ArgumentTypeError("duplicate variants")
    return vals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoints", type=_parse_checkpoints, default=(100, 400, 1200))
    parser.add_argument("--range-combos", type=int, default=6)
    parser.add_argument("--pot", type=int, default=100)
    parser.add_argument("--stack", type=int, default=400)
    parser.add_argument("--p0-phase", type=float, default=0.0)
    parser.add_argument("--p1-phase", type=float, default=0.27)
    parser.add_argument(
        "--variants",
        type=_parse_variants,
        default=tuple(SolverVariant),
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if args.range_combos <= 0 or args.pot <= 0 or args.stack <= 0:
        raise ValueError("range-combos/pot/stack must be positive")

    bet_sizes = materialize_bet_sizes(
        pot=args.pot,
        stack=args.stack,
        min_bet=1,
        fractions=(Fraction(1, 4), Fraction(1, 2), Fraction(1, 1)),
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
        for variant in args.variants:
            state = init_river_solver(spec, variant)
            trained = 0
            cumulative_training_seconds = 0.0
            for checkpoint in args.checkpoints:
                start = time.perf_counter()
                advance_river_solver(
                    spec,
                    state,
                    additional_iterations=checkpoint - trained,
                )
                cumulative_training_seconds += time.perf_counter() - start
                trained = checkpoint

                eval_start = time.perf_counter()
                result = river_solver_result(spec, state)
                evaluation_seconds = time.perf_counter() - eval_start
                rows.append(
                    {
                        "board": board_name,
                        "variant": variant.value,
                        "checkpoint": checkpoint,
                        "policy_ev": result.policy_ev,
                        "br0_value": result.br0_value,
                        "br1_value": result.br1_value,
                        "value_interval_width": result.br0_value - result.br1_value,
                        "exploitability_per_pot": result.exploitability_per_pot,
                        "infosets": result.infosets,
                        "action_slots": result.action_slots,
                        "cumulative_training_seconds": cumulative_training_seconds,
                        "evaluation_seconds": evaluation_seconds,
                    }
                )
                print(
                    f"{board_name} {variant.value} iter={checkpoint} "
                    f"exploit/pot={result.exploitability_per_pot:.8f} "
                    f"train_s={cumulative_training_seconds:.3f} eval_s={evaluation_seconds:.3f}"
                )

    payload = {
        "schema": "DEEPCASH_R5_TABULAR_SOLVER_BENCHMARK_V1",
        "board_set": "R3_CONTROL_ONLY",
        "checkpoints": list(args.checkpoints),
        "range_combos": args.range_combos,
        "pot": args.pot,
        "stack": args.stack,
        "spr": args.stack / args.pot,
        "p0_phase": args.p0_phase,
        "p1_phase": args.p1_phase,
        "bet_sizes": list(bet_sizes),
        "variants": [variant.value for variant in args.variants],
        "rows": rows,
        "methodology_note": (
            "Development control only. Exact full-chance tree and exact best responses; "
            "hosted-CI timing is not target-Ryzen production evidence."
        ),
    }
    Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
