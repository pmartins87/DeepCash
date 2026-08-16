from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import (
    ONE_RAISE_OPEN_CANDIDATES,
    ONE_RAISE_OPEN_REFERENCE_FRACTIONS,
    RIVER_BOARDS,
    parse_cards,
    parse_checkpoints,
    parse_names,
    quantile_range,
    restriction_loss_bounds,
)
from deepcash_core.river_lab import materialize_bet_sizes
from deepcash_core.river_raise_reference_lab import AsymmetricRiverRaiseGameSpec
from deepcash_core.river_raise_reference_training import (
    advance_cfr_plus,
    init_cfr_plus,
    result_from_state,
)


def pot_raise_targets(
    *,
    pot: int,
    stack: int,
    opening_sizes: tuple[int, ...],
) -> tuple[tuple[int, tuple[int, ...]], ...]:
    """One exact reference raise target per opening bet: pot-sized raise-to.

    Facing a bet `b` into starting pot `P`, pot after calling is `P+2b`.
    A pot-sized raise adds that amount over the call, so total contribution is
    `b + (P+2b) = P+3b`. We cap at stack. This v1 gate deliberately requires
    the resulting target to exceed the opening bet; all-in/no-raise openings are
    a separate low-SPR extension rather than being silently misrepresented.
    """
    out = []
    for bet in opening_sizes:
        target = min(stack, pot + 3 * bet)
        if target <= bet:
            raise ValueError(
                f"no raise is possible after opening bet {bet} with stack={stack}; "
                "all-in/no-raise geometries are not part of one-raise v1"
            )
        out.append((bet, (target,)))
    return tuple(out)


def subset_map(full_map, sizes):
    mapping = dict(full_map)
    return tuple((b, mapping[b]) for b in sizes)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Cumulative common-reference opening-size restriction in a one-raise river tree"
    )
    ap.add_argument("--checkpoints", default="100,400,1200")
    ap.add_argument("--range-combos", type=int, default=3)
    ap.add_argument("--pot", type=int, default=100)
    ap.add_argument("--stack", type=int, default=400)
    ap.add_argument("--min-bet", type=int, default=20)
    ap.add_argument("--boards", default="A_high_dry")
    ap.add_argument("--candidates", default="all")
    ap.add_argument("--out", type=Path, default=Path("river_raise_reference_convergence.json"))
    args = ap.parse_args()

    checkpoints = parse_checkpoints(args.checkpoints)
    board_names = parse_names(args.boards, RIVER_BOARDS)
    candidate_names = parse_names(args.candidates, ONE_RAISE_OPEN_CANDIDATES)
    reference_sizes = materialize_bet_sizes(
        pot=args.pot,
        stack=args.stack,
        min_bet=args.min_bet,
        fractions=ONE_RAISE_OPEN_REFERENCE_FRACTIONS,
    )
    reference_raise_map = pot_raise_targets(
        pot=args.pot, stack=args.stack, opening_sizes=reference_sizes
    )
    rows = []

    for board_name in board_names:
        board = parse_cards(RIVER_BOARDS[board_name])
        p0_range = quantile_range(board, args.range_combos, 0.00)
        p1_range = quantile_range(board, args.range_combos, 0.27)
        ref_spec = AsymmetricRiverRaiseGameSpec(
            board,
            p0_range,
            p1_range,
            args.pot,
            reference_sizes,
            reference_sizes,
            reference_raise_map,
            reference_raise_map,
        )
        ref_state = init_cfr_plus(ref_spec)
        ref_train_seconds = 0.0

        candidates = {}
        for name in candidate_names:
            sizes = materialize_bet_sizes(
                pot=args.pot,
                stack=args.stack,
                min_bet=args.min_bet,
                fractions=ONE_RAISE_OPEN_CANDIDATES[name],
            )
            if not set(sizes).issubset(reference_sizes):
                raise RuntimeError("candidate opening sizes escaped reference action set")
            candidate_raise_map = subset_map(reference_raise_map, sizes)
            p0_spec = AsymmetricRiverRaiseGameSpec(
                board,
                p0_range,
                p1_range,
                args.pot,
                sizes,
                reference_sizes,
                candidate_raise_map,
                reference_raise_map,
            )
            p1_spec = AsymmetricRiverRaiseGameSpec(
                board,
                p0_range,
                p1_range,
                args.pot,
                reference_sizes,
                sizes,
                reference_raise_map,
                candidate_raise_map,
            )
            candidates[name] = {
                "sizes": sizes,
                "p0_spec": p0_spec,
                "p1_spec": p1_spec,
                "p0_state": init_cfr_plus(p0_spec),
                "p1_state": init_cfr_plus(p1_spec),
                "p0_seconds": 0.0,
                "p1_seconds": 0.0,
            }

        for checkpoint in checkpoints:
            started = time.perf_counter()
            advance_cfr_plus(
                ref_spec,
                ref_state,
                additional_iterations=checkpoint - ref_state.iterations,
            )
            ref_train_seconds += time.perf_counter() - started
            started = time.perf_counter()
            reference = result_from_state(ref_spec, ref_state)
            ref_eval_seconds = time.perf_counter() - started

            for name, item in candidates.items():
                started = time.perf_counter()
                advance_cfr_plus(
                    item["p0_spec"],
                    item["p0_state"],
                    additional_iterations=checkpoint - item["p0_state"].iterations,
                )
                item["p0_seconds"] += time.perf_counter() - started
                started = time.perf_counter()
                advance_cfr_plus(
                    item["p1_spec"],
                    item["p1_state"],
                    additional_iterations=checkpoint - item["p1_state"].iterations,
                )
                item["p1_seconds"] += time.perf_counter() - started

                started = time.perf_counter()
                p0r = result_from_state(item["p0_spec"], item["p0_state"])
                p0_eval_seconds = time.perf_counter() - started
                started = time.perf_counter()
                p1r = result_from_state(item["p1_spec"], item["p1_state"])
                p1_eval_seconds = time.perf_counter() - started

                bounds = restriction_loss_bounds(reference, p0r, p1r, args.pot)
                interval_width = max(
                    reference.br0_value - reference.br1_value,
                    p0r.br0_value - p0r.br1_value,
                    p1r.br0_value - p1r.br1_value,
                ) / float(args.pot)
                row = {
                    "board": board_name,
                    "candidate": name,
                    "reference_open_sizes": list(reference_sizes),
                    "candidate_open_sizes": list(item["sizes"]),
                    "reference_raise_targets": [
                        [bet, list(targets)] for bet, targets in reference_raise_map
                    ],
                    "checkpoint": checkpoint,
                    "range_combos": args.range_combos,
                    "pot": args.pot,
                    "stack": args.stack,
                    "spr": args.stack / args.pot,
                    "max_value_interval_width_per_pot": interval_width,
                    "reference_exploitability_per_pot": reference.exploitability_per_pot,
                    "p0_restricted_exploitability_per_pot": p0r.exploitability_per_pot,
                    "p1_restricted_exploitability_per_pot": p1r.exploitability_per_pot,
                    "reference_cumulative_train_seconds": ref_train_seconds,
                    "p0_cumulative_train_seconds": item["p0_seconds"],
                    "p1_cumulative_train_seconds": item["p1_seconds"],
                    "reference_eval_seconds": ref_eval_seconds,
                    "p0_eval_seconds": p0_eval_seconds,
                    "p1_eval_seconds": p1_eval_seconds,
                    "best_response_oracle": "dynamic_exact_one_raise_dp_gated_against_enumerator",
                    **bounds,
                }
                rows.append(row)
                print(
                    f"{board_name:16s} {name:16s} iter={checkpoint:5d} "
                    f"upper/pot={bounds['worst_loss_upper_per_pot']:.6f} "
                    f"interval/pot={interval_width:.6f}"
                )

    payload = {
        "schema": "DEEPCASH_RIVER_RAISE_REFERENCE_CONVERGENCE_V1",
        "method": (
            "one-sided opening-size restriction against a shared one-raise rich reference; "
            "raise-response geometry held fixed to isolate opening-size loss; "
            "dynamic exact BR intervals propagated"
        ),
        "checkpoints": list(checkpoints),
        "range_combos": args.range_combos,
        "pot": args.pot,
        "stack": args.stack,
        "spr": args.stack / args.pot,
        "reference_open_sizes": list(reference_sizes),
        "reference_raise_targets": [[b, list(t)] for b, t in reference_raise_map],
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
