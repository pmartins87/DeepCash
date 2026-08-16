from __future__ import annotations

import argparse
import json
import time
from fractions import Fraction
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import (
    ONE_RAISE_OPEN_REFERENCE_FRACTIONS,
    ONE_RAISE_SIZE_CANDIDATES,
    ONE_RAISE_SIZE_REFERENCE_FRACTIONS,
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


def _round_half_up(value: Fraction) -> int:
    q, r = divmod(value.numerator, value.denominator)
    return q + int(2 * r >= value.denominator)


def materialize_raise_map(
    *,
    pot: int,
    stack: int,
    opening_sizes: tuple[int, ...],
    fractions: tuple[Fraction, ...],
) -> tuple[tuple[int, tuple[int, ...]], ...]:
    """Materialize raise-to targets as fractions of pot after calling.

    Facing opening bet `b`, the pot after a call would be `P + 2b`. A raise
    fraction `f` creates target contribution `b + f * (P + 2b)`. Targets are
    rounded half-up to integer chips and capped by the effective stack.

    Clipping can collapse several requested fractions to one all-in target. If
    the opening itself is all-in, the target tuple is empty and the responder
    correctly has only fold/call.
    """
    if pot <= 0 or stack <= 0:
        raise ValueError("pot and stack must be positive")
    if tuple(sorted(set(fractions))) != fractions or any(f <= 0 for f in fractions):
        raise ValueError("raise fractions must be positive, sorted and unique")

    rows = []
    for bet in opening_sizes:
        if bet <= 0 or bet > stack:
            raise ValueError("opening bet must be within effective stack")
        targets: set[int] = set()
        if bet < stack:
            pot_after_call = pot + 2 * bet
            for fraction in fractions:
                exact = Fraction(bet) + Fraction(pot_after_call) * fraction
                target = min(stack, _round_half_up(exact))
                if target <= bet:
                    continue
                # Any target below a full min-raise-to of 2*b can only be legal
                # if it is the exact all-in. The chosen reference fractions are
                # normally above that boundary, but keep the generator honest
                # under future geometry changes.
                if target < 2 * bet and target != stack:
                    raise ValueError(
                        f"non-all-in sub-minimum raise target {target} after bet {bet}"
                    )
                targets.add(target)
        rows.append((bet, tuple(sorted(targets))))
    return tuple(rows)


def _assert_candidate_subset(reference_map, candidate_map) -> None:
    ref = dict(reference_map)
    cand = dict(candidate_map)
    if set(ref) != set(cand):
        raise RuntimeError("candidate/reference raise maps cover different opening sizes")
    for bet in ref:
        if not set(cand[bet]).issubset(ref[bet]):
            raise RuntimeError(
                f"candidate raise target escaped common reference at opening {bet}"
            )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Cumulative one-sided raise-size restriction against a shared "
            "one-raise river reference game"
        )
    )
    ap.add_argument("--checkpoints", default="100,400,1200")
    ap.add_argument("--range-combos", type=int, default=3)
    ap.add_argument("--pot", type=int, default=100)
    ap.add_argument("--stack", type=int, default=400)
    ap.add_argument("--min-bet", type=int, default=20)
    ap.add_argument("--boards", default="A_high_dry")
    ap.add_argument("--candidates", default="all")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("river_raise_size_reference_convergence.json"),
    )
    args = ap.parse_args()

    checkpoints = parse_checkpoints(args.checkpoints)
    board_names = parse_names(args.boards, RIVER_BOARDS)
    candidate_names = parse_names(args.candidates, ONE_RAISE_SIZE_CANDIDATES)
    opening_sizes = materialize_bet_sizes(
        pot=args.pot,
        stack=args.stack,
        min_bet=args.min_bet,
        fractions=ONE_RAISE_OPEN_REFERENCE_FRACTIONS,
    )
    reference_raise_map = materialize_raise_map(
        pot=args.pot,
        stack=args.stack,
        opening_sizes=opening_sizes,
        fractions=ONE_RAISE_SIZE_REFERENCE_FRACTIONS,
    )
    rows = []

    for board_name in board_names:
        board = parse_cards(RIVER_BOARDS[board_name])
        p0_range = quantile_range(board, args.range_combos, 0.00)
        p1_range = quantile_range(board, args.range_combos, 0.27)
        reference_spec = AsymmetricRiverRaiseGameSpec(
            board,
            p0_range,
            p1_range,
            args.pot,
            opening_sizes,
            opening_sizes,
            reference_raise_map,
            reference_raise_map,
        )
        reference_state = init_cfr_plus(reference_spec)
        reference_train_seconds = 0.0

        candidates = {}
        for name in candidate_names:
            candidate_raise_map = materialize_raise_map(
                pot=args.pot,
                stack=args.stack,
                opening_sizes=opening_sizes,
                fractions=ONE_RAISE_SIZE_CANDIDATES[name],
            )
            _assert_candidate_subset(reference_raise_map, candidate_raise_map)

            # Restrict only P0's raises versus P1 openings.
            p0_spec = AsymmetricRiverRaiseGameSpec(
                board,
                p0_range,
                p1_range,
                args.pot,
                opening_sizes,
                opening_sizes,
                reference_raise_map,
                candidate_raise_map,
            )
            # Restrict only P1's raises versus P0 openings.
            p1_spec = AsymmetricRiverRaiseGameSpec(
                board,
                p0_range,
                p1_range,
                args.pot,
                opening_sizes,
                opening_sizes,
                candidate_raise_map,
                reference_raise_map,
            )
            candidates[name] = {
                "raise_map": candidate_raise_map,
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
                reference_spec,
                reference_state,
                additional_iterations=checkpoint - reference_state.iterations,
            )
            reference_train_seconds += time.perf_counter() - started
            started = time.perf_counter()
            reference = result_from_state(reference_spec, reference_state)
            reference_eval_seconds = time.perf_counter() - started

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
                p0_restricted = result_from_state(item["p0_spec"], item["p0_state"])
                p0_eval_seconds = time.perf_counter() - started
                started = time.perf_counter()
                p1_restricted = result_from_state(item["p1_spec"], item["p1_state"])
                p1_eval_seconds = time.perf_counter() - started

                bounds = restriction_loss_bounds(
                    reference, p0_restricted, p1_restricted, args.pot
                )
                interval_width = max(
                    reference.br0_value - reference.br1_value,
                    p0_restricted.br0_value - p0_restricted.br1_value,
                    p1_restricted.br0_value - p1_restricted.br1_value,
                ) / float(args.pot)
                row = {
                    "board": board_name,
                    "candidate": name,
                    "restriction_dimension": "raise_size",
                    "opening_sizes": list(opening_sizes),
                    "reference_raise_targets": [
                        [bet, list(targets)] for bet, targets in reference_raise_map
                    ],
                    "candidate_raise_targets": [
                        [bet, list(targets)] for bet, targets in item["raise_map"]
                    ],
                    "checkpoint": checkpoint,
                    "range_combos": args.range_combos,
                    "pot": args.pot,
                    "stack": args.stack,
                    "spr": args.stack / args.pot,
                    "max_value_interval_width_per_pot": interval_width,
                    "reference_exploitability_per_pot": reference.exploitability_per_pot,
                    "p0_restricted_exploitability_per_pot": p0_restricted.exploitability_per_pot,
                    "p1_restricted_exploitability_per_pot": p1_restricted.exploitability_per_pot,
                    "reference_cumulative_train_seconds": reference_train_seconds,
                    "p0_cumulative_train_seconds": item["p0_seconds"],
                    "p1_cumulative_train_seconds": item["p1_seconds"],
                    "reference_eval_seconds": reference_eval_seconds,
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
            "one-sided raise-size restriction against a shared one-raise rich reference; "
            "opening sizes held fixed; dynamic exact BR intervals propagated"
        ),
        "restriction_dimension": "raise_size",
        "checkpoints": list(checkpoints),
        "range_combos": args.range_combos,
        "pot": args.pot,
        "stack": args.stack,
        "spr": args.stack / args.pot,
        "opening_sizes": list(opening_sizes),
        "reference_raise_targets": [
            [bet, list(targets)] for bet, targets in reference_raise_map
        ],
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
