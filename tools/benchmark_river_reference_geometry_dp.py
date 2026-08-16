from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

from deepcash_core.river_lab import materialize_bet_sizes
from deepcash_core.river_reference_dp import asymmetric_result_from_state_dp
from deepcash_core.river_reference_lab import AsymmetricRiverGameSpec
from deepcash_core.river_reference_training import (
    advance_asymmetric_river_cfr_plus,
    init_asymmetric_river_cfr_plus,
)
from tools.benchmark_river_reference_convergence import (
    BOARDS,
    CANDIDATES,
    REFERENCE_FRACTIONS,
    cards,
    loss_bounds,
    parse_names,
    quantile_range,
)


@dataclass(frozen=True)
class Geometry:
    name: str
    pot: int
    stack: int
    min_bet: int

    @property
    def spr(self) -> float:
        return self.stack / self.pot


GEOMETRIES = {
    "SPR0_5": Geometry("SPR0_5", pot=100, stack=50, min_bet=20),
    "SPR1": Geometry("SPR1", pot=100, stack=100, min_bet=20),
    "SPR2": Geometry("SPR2", pot=100, stack=200, min_bet=20),
    "SPR4": Geometry("SPR4", pot=100, stack=400, min_bet=20),
}


def parse_geometries(text: str) -> tuple[Geometry, ...]:
    if text == "all":
        return tuple(GEOMETRIES.values())
    names = tuple(x.strip() for x in text.split(",") if x.strip())
    unknown = set(names) - set(GEOMETRIES)
    if unknown:
        raise ValueError(f"unknown geometries: {sorted(unknown)}")
    return tuple(GEOMETRIES[name] for name in names)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="DeepCash multi-SPR common-reference restriction benchmark using dynamic exact BR"
    )
    ap.add_argument("--iterations", type=int, default=2000)
    ap.add_argument("--range-combos", type=int, default=5)
    ap.add_argument("--boards", default="all")
    ap.add_argument("--candidates", default="all")
    ap.add_argument("--geometries", default="all")
    ap.add_argument("--out", type=Path, default=Path("river_reference_geometry_dp.json"))
    args = ap.parse_args()

    if args.iterations <= 0 or args.range_combos <= 0:
        raise ValueError("iterations and range-combos must be positive")

    board_names = parse_names(args.boards, BOARDS)
    candidate_names = parse_names(args.candidates, CANDIDATES)
    geometries = parse_geometries(args.geometries)
    rows = []

    for geometry in geometries:
        reference_sizes = materialize_bet_sizes(
            pot=geometry.pot,
            stack=geometry.stack,
            min_bet=geometry.min_bet,
            fractions=REFERENCE_FRACTIONS,
        )
        for board_name in board_names:
            board = cards(BOARDS[board_name])
            p0 = quantile_range(board, args.range_combos, 0.00)
            p1 = quantile_range(board, args.range_combos, 0.27)

            ref_spec = AsymmetricRiverGameSpec(
                board, p0, p1, geometry.pot, reference_sizes, reference_sizes
            )
            ref_state = init_asymmetric_river_cfr_plus(ref_spec)
            started = time.perf_counter()
            advance_asymmetric_river_cfr_plus(
                ref_spec, ref_state, additional_iterations=args.iterations
            )
            reference_train_seconds = time.perf_counter() - started
            started = time.perf_counter()
            reference = asymmetric_result_from_state_dp(ref_spec, ref_state)
            reference_eval_seconds = time.perf_counter() - started

            for candidate_name in candidate_names:
                candidate_sizes = materialize_bet_sizes(
                    pot=geometry.pot,
                    stack=geometry.stack,
                    min_bet=geometry.min_bet,
                    fractions=CANDIDATES[candidate_name],
                )
                if not set(candidate_sizes).issubset(reference_sizes):
                    raise RuntimeError("candidate escaped common reference after materialization")

                p0_spec = AsymmetricRiverGameSpec(
                    board, p0, p1, geometry.pot, candidate_sizes, reference_sizes
                )
                p1_spec = AsymmetricRiverGameSpec(
                    board, p0, p1, geometry.pot, reference_sizes, candidate_sizes
                )
                p0_state = init_asymmetric_river_cfr_plus(p0_spec)
                p1_state = init_asymmetric_river_cfr_plus(p1_spec)

                started = time.perf_counter()
                advance_asymmetric_river_cfr_plus(
                    p0_spec, p0_state, additional_iterations=args.iterations
                )
                p0_train_seconds = time.perf_counter() - started
                started = time.perf_counter()
                advance_asymmetric_river_cfr_plus(
                    p1_spec, p1_state, additional_iterations=args.iterations
                )
                p1_train_seconds = time.perf_counter() - started

                started = time.perf_counter()
                p0_result = asymmetric_result_from_state_dp(p0_spec, p0_state)
                p0_eval_seconds = time.perf_counter() - started
                started = time.perf_counter()
                p1_result = asymmetric_result_from_state_dp(p1_spec, p1_state)
                p1_eval_seconds = time.perf_counter() - started

                bounds = loss_bounds(reference, p0_result, p1_result, geometry.pot)
                max_interval = max(
                    reference.br0_value - reference.br1_value,
                    p0_result.br0_value - p0_result.br1_value,
                    p1_result.br0_value - p1_result.br1_value,
                ) / float(geometry.pot)

                row = {
                    "geometry": geometry.name,
                    "pot": geometry.pot,
                    "stack": geometry.stack,
                    "spr": geometry.spr,
                    "min_bet": geometry.min_bet,
                    "board": board_name,
                    "candidate": candidate_name,
                    "reference_sizes": list(reference_sizes),
                    "candidate_sizes": list(candidate_sizes),
                    "iterations": args.iterations,
                    "range_combos": args.range_combos,
                    "max_value_interval_width_per_pot": max_interval,
                    "reference_exploitability_per_pot": reference.exploitability_per_pot,
                    "p0_restricted_exploitability_per_pot": p0_result.exploitability_per_pot,
                    "p1_restricted_exploitability_per_pot": p1_result.exploitability_per_pot,
                    "reference_train_seconds": reference_train_seconds,
                    "p0_train_seconds": p0_train_seconds,
                    "p1_train_seconds": p1_train_seconds,
                    "reference_eval_seconds": reference_eval_seconds,
                    "p0_eval_seconds": p0_eval_seconds,
                    "p1_eval_seconds": p1_eval_seconds,
                    "best_response_oracle": "dynamic_exact_dp_gated_against_enumerator",
                    **bounds,
                }
                rows.append(row)
                print(
                    f"{geometry.name:7s} {board_name:16s} {candidate_name:18s} "
                    f"ref={reference_sizes!s:24s} cand={candidate_sizes!s:18s} "
                    f"upper/pot={bounds['worst_loss_upper_per_pot']:.6f} "
                    f"interval/pot={max_interval:.6f}"
                )

    payload = {
        "schema": "DEEPCASH_RIVER_REFERENCE_GEOMETRY_DP_V1",
        "method": (
            "one-sided candidate action restriction versus a shared rich reference "
            "across multiple pot/stack SPR geometries; dynamic exact BR intervals propagated"
        ),
        "iterations": args.iterations,
        "range_combos": args.range_combos,
        "geometries": [g.__dict__ | {"spr": g.spr} for g in geometries],
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
