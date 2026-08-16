from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import (
    ONE_BET_CANDIDATES,
    ONE_BET_REFERENCE_FRACTIONS,
    RIVER_BOARDS,
    parse_cards,
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
    "SPR0_5": Geometry("SPR0_5", 100, 50, 20),
    "SPR1": Geometry("SPR1", 100, 100, 20),
    "SPR2": Geometry("SPR2", 100, 200, 20),
    "SPR4": Geometry("SPR4", 100, 400, 20),
}


def parse_geometries(text: str) -> tuple[Geometry, ...]:
    if text == "all":
        return tuple(GEOMETRIES.values())
    names = tuple(x.strip() for x in text.split(",") if x.strip())
    unknown = set(names) - set(GEOMETRIES)
    if unknown:
        raise ValueError(f"unknown geometries: {sorted(unknown)}")
    return tuple(GEOMETRIES[x] for x in names)


def main() -> None:
    ap = argparse.ArgumentParser(description="Package-safe multi-SPR common-reference benchmark")
    ap.add_argument("--iterations", type=int, default=1200)
    ap.add_argument("--range-combos", type=int, default=4)
    ap.add_argument("--boards", default="all")
    ap.add_argument("--candidates", default="all")
    ap.add_argument("--geometries", default="all")
    ap.add_argument("--out", type=Path, default=Path("river_reference_geometry_dp_v2.json"))
    args = ap.parse_args()

    if args.iterations <= 0 or args.range_combos <= 0:
        raise ValueError("iterations and range-combos must be positive")
    board_names = parse_names(args.boards, RIVER_BOARDS)
    candidate_names = parse_names(args.candidates, ONE_BET_CANDIDATES)
    geometries = parse_geometries(args.geometries)
    rows = []

    for geo in geometries:
        reference_sizes = materialize_bet_sizes(
            pot=geo.pot, stack=geo.stack, min_bet=geo.min_bet,
            fractions=ONE_BET_REFERENCE_FRACTIONS,
        )
        for board_name in board_names:
            board = parse_cards(RIVER_BOARDS[board_name])
            p0 = quantile_range(board, args.range_combos, 0.00)
            p1 = quantile_range(board, args.range_combos, 0.27)
            ref_spec = AsymmetricRiverGameSpec(board, p0, p1, geo.pot, reference_sizes, reference_sizes)
            ref_state = init_asymmetric_river_cfr_plus(ref_spec)
            started = time.perf_counter()
            advance_asymmetric_river_cfr_plus(ref_spec, ref_state, additional_iterations=args.iterations)
            ref_train = time.perf_counter() - started
            started = time.perf_counter()
            reference = asymmetric_result_from_state_dp(ref_spec, ref_state)
            ref_eval = time.perf_counter() - started

            for name in candidate_names:
                candidate_sizes = materialize_bet_sizes(
                    pot=geo.pot, stack=geo.stack, min_bet=geo.min_bet,
                    fractions=ONE_BET_CANDIDATES[name],
                )
                if not set(candidate_sizes).issubset(reference_sizes):
                    raise RuntimeError("candidate escaped common reference")
                p0_spec = AsymmetricRiverGameSpec(board, p0, p1, geo.pot, candidate_sizes, reference_sizes)
                p1_spec = AsymmetricRiverGameSpec(board, p0, p1, geo.pot, reference_sizes, candidate_sizes)
                p0_state = init_asymmetric_river_cfr_plus(p0_spec)
                p1_state = init_asymmetric_river_cfr_plus(p1_spec)
                started = time.perf_counter()
                advance_asymmetric_river_cfr_plus(p0_spec, p0_state, additional_iterations=args.iterations)
                p0_train = time.perf_counter() - started
                started = time.perf_counter()
                advance_asymmetric_river_cfr_plus(p1_spec, p1_state, additional_iterations=args.iterations)
                p1_train = time.perf_counter() - started
                started = time.perf_counter()
                p0r = asymmetric_result_from_state_dp(p0_spec, p0_state)
                p0_eval = time.perf_counter() - started
                started = time.perf_counter()
                p1r = asymmetric_result_from_state_dp(p1_spec, p1_state)
                p1_eval = time.perf_counter() - started

                bounds = restriction_loss_bounds(reference, p0r, p1r, geo.pot)
                interval = max(
                    reference.br0_value - reference.br1_value,
                    p0r.br0_value - p0r.br1_value,
                    p1r.br0_value - p1r.br1_value,
                ) / float(geo.pot)
                rows.append({
                    "geometry": geo.name,
                    "pot": geo.pot,
                    "stack": geo.stack,
                    "spr": geo.spr,
                    "min_bet": geo.min_bet,
                    "board": board_name,
                    "candidate": name,
                    "reference_sizes": list(reference_sizes),
                    "candidate_sizes": list(candidate_sizes),
                    "iterations": args.iterations,
                    "range_combos": args.range_combos,
                    "max_value_interval_width_per_pot": interval,
                    "reference_exploitability_per_pot": reference.exploitability_per_pot,
                    "p0_restricted_exploitability_per_pot": p0r.exploitability_per_pot,
                    "p1_restricted_exploitability_per_pot": p1r.exploitability_per_pot,
                    "reference_train_seconds": ref_train,
                    "p0_train_seconds": p0_train,
                    "p1_train_seconds": p1_train,
                    "reference_eval_seconds": ref_eval,
                    "p0_eval_seconds": p0_eval,
                    "p1_eval_seconds": p1_eval,
                    "best_response_oracle": "dynamic_exact_dp_gated_against_enumerator",
                    **bounds,
                })
                print(
                    f"{geo.name:7s} {board_name:16s} {name:18s} "
                    f"ref={reference_sizes!s:22s} cand={candidate_sizes!s:16s} "
                    f"upper/pot={bounds['worst_loss_upper_per_pot']:.6f} "
                    f"interval/pot={interval:.6f}"
                )

    payload = {
        "schema": "DEEPCASH_RIVER_REFERENCE_GEOMETRY_DP_V1",
        "iterations": args.iterations,
        "range_combos": args.range_combos,
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
