from __future__ import annotations

import argparse
import json
import time
from fractions import Fraction
from itertools import combinations
from pathlib import Path

from deepcash_core.cards import card_from_str, full_deck
from deepcash_core.evaluator import evaluate_best
from deepcash_core.river_lab import RangeCombo, materialize_bet_sizes
from deepcash_core.river_reference_lab import AsymmetricRiverGameSpec
from deepcash_core.river_reference_training import (
    advance_asymmetric_river_cfr_plus,
    asymmetric_result_from_state,
    init_asymmetric_river_cfr_plus,
)

CANDIDATES = {
    "S1_50": (Fraction(1, 2),),
    "S2_33_100": (Fraction(1, 3), Fraction(1, 1)),
    "S3_25_75_150": (Fraction(1, 4), Fraction(3, 4), Fraction(3, 2)),
    "S4_25_50_100_200": (Fraction(1, 4), Fraction(1, 2), Fraction(1, 1), Fraction(2, 1)),
}
REFERENCE_FRACTIONS = (
    Fraction(1, 4), Fraction(1, 3), Fraction(1, 2), Fraction(3, 4),
    Fraction(1, 1), Fraction(3, 2), Fraction(2, 1),
)
BOARDS = {
    "A_high_dry": "Ah Kd 9c 7s 2h",
    "paired": "Qs Qd 9h 7c 2s",
    "four_straight": "9h 8d 7c 6s 2h",
    "four_flush": "Ah Jh 8h 4h 2c",
}


def cards(text: str) -> tuple[int, ...]:
    return tuple(card_from_str(x) for x in text.split())


def quantile_range(board: tuple[int, ...], count: int, phase: float) -> tuple[RangeCombo, ...]:
    remaining = [c for c in full_deck() if c not in set(board)]
    combos = list(combinations(remaining, 2))
    combos.sort(key=lambda h: (evaluate_best((*h, *board)), h))
    chosen = []
    used = set()
    for k in range(count):
        q = min(0.999999, max(0.000001, (k + 0.5 + phase) / count))
        idx = round(q * (len(combos) - 1))
        while combos[idx] in used:
            idx = min(len(combos) - 1, idx + 1)
        used.add(combos[idx])
        chosen.append(RangeCombo(tuple(combos[idx])))
    return tuple(chosen)


def parse_names(text: str, available: dict[str, object]) -> tuple[str, ...]:
    if text == "all":
        return tuple(available)
    names = tuple(x.strip() for x in text.split(",") if x.strip())
    unknown = set(names) - set(available)
    if unknown:
        raise ValueError(f"unknown names: {sorted(unknown)}")
    return names


def parse_checkpoints(text: str) -> tuple[int, ...]:
    values = tuple(sorted({int(x.strip()) for x in text.split(",") if x.strip()}))
    if not values or values[0] <= 0:
        raise ValueError("checkpoints must be positive")
    return values


def loss_bounds(reference, p0_restricted, p1_restricted, pot: int) -> dict:
    p0_lower = reference.br1_value - p0_restricted.br0_value
    p0_upper = reference.br0_value - p0_restricted.br1_value
    p1_lower = p1_restricted.br1_value - reference.br0_value
    p1_upper = p1_restricted.br0_value - reference.br1_value
    worst_upper = max(0.0, p0_upper, p1_upper)
    return {
        "p0_loss_lower": p0_lower,
        "p0_loss_upper": p0_upper,
        "p1_loss_lower": p1_lower,
        "p1_loss_upper": p1_upper,
        "worst_loss_upper": worst_upper,
        "worst_loss_upper_per_pot": worst_upper / float(pot),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Cumulative common-reference river restriction convergence")
    ap.add_argument("--checkpoints", default="20,80,250,800")
    ap.add_argument("--range-combos", type=int, default=6)
    ap.add_argument("--pot", type=int, default=100)
    ap.add_argument("--stack", type=int, default=300)
    ap.add_argument("--min-bet", type=int, default=20)
    ap.add_argument("--boards", default="all")
    ap.add_argument("--candidates", default="all")
    ap.add_argument("--out", type=Path, default=Path("river_reference_convergence.json"))
    args = ap.parse_args()

    checkpoints = parse_checkpoints(args.checkpoints)
    board_names = parse_names(args.boards, BOARDS)
    candidate_names = parse_names(args.candidates, CANDIDATES)
    reference_sizes = materialize_bet_sizes(
        pot=args.pot, stack=args.stack, min_bet=args.min_bet,
        fractions=REFERENCE_FRACTIONS,
    )
    rows = []

    for board_name in board_names:
        board = cards(BOARDS[board_name])
        p0 = quantile_range(board, args.range_combos, 0.00)
        p1 = quantile_range(board, args.range_combos, 0.27)
        ref_spec = AsymmetricRiverGameSpec(board, p0, p1, args.pot, reference_sizes, reference_sizes)
        ref_state = init_asymmetric_river_cfr_plus(ref_spec)
        ref_train_seconds = 0.0

        candidates = {}
        for name in candidate_names:
            sizes = materialize_bet_sizes(
                pot=args.pot, stack=args.stack, min_bet=args.min_bet,
                fractions=CANDIDATES[name],
            )
            if not set(sizes).issubset(reference_sizes):
                raise RuntimeError("candidate action escaped common reference")
            p0_spec = AsymmetricRiverGameSpec(board, p0, p1, args.pot, sizes, reference_sizes)
            p1_spec = AsymmetricRiverGameSpec(board, p0, p1, args.pot, reference_sizes, sizes)
            candidates[name] = {
                "sizes": sizes,
                "p0_spec": p0_spec,
                "p1_spec": p1_spec,
                "p0_state": init_asymmetric_river_cfr_plus(p0_spec),
                "p1_state": init_asymmetric_river_cfr_plus(p1_spec),
                "p0_seconds": 0.0,
                "p1_seconds": 0.0,
            }

        for checkpoint in checkpoints:
            add = checkpoint - ref_state.iterations
            started = time.perf_counter()
            advance_asymmetric_river_cfr_plus(ref_spec, ref_state, additional_iterations=add)
            ref_train_seconds += time.perf_counter() - started
            eval_started = time.perf_counter()
            reference = asymmetric_result_from_state(ref_spec, ref_state)
            ref_eval_seconds = time.perf_counter() - eval_started

            for name, item in candidates.items():
                p0_state = item["p0_state"]
                p1_state = item["p1_state"]
                started = time.perf_counter()
                advance_asymmetric_river_cfr_plus(item["p0_spec"], p0_state, additional_iterations=checkpoint - p0_state.iterations)
                item["p0_seconds"] += time.perf_counter() - started
                started = time.perf_counter()
                advance_asymmetric_river_cfr_plus(item["p1_spec"], p1_state, additional_iterations=checkpoint - p1_state.iterations)
                item["p1_seconds"] += time.perf_counter() - started

                eval_started = time.perf_counter()
                p0r = asymmetric_result_from_state(item["p0_spec"], p0_state)
                p0_eval = time.perf_counter() - eval_started
                eval_started = time.perf_counter()
                p1r = asymmetric_result_from_state(item["p1_spec"], p1_state)
                p1_eval = time.perf_counter() - eval_started
                bounds = loss_bounds(reference, p0r, p1r, args.pot)
                interval_width = max(
                    reference.br0_value - reference.br1_value,
                    p0r.br0_value - p0r.br1_value,
                    p1r.br0_value - p1r.br1_value,
                ) / float(args.pot)
                row = {
                    "board": board_name,
                    "candidate": name,
                    "candidate_sizes": list(item["sizes"]),
                    "reference_sizes": list(reference_sizes),
                    "checkpoint": checkpoint,
                    "reference_exploitability_per_pot": reference.exploitability_per_pot,
                    "p0_restricted_exploitability_per_pot": p0r.exploitability_per_pot,
                    "p1_restricted_exploitability_per_pot": p1r.exploitability_per_pot,
                    "max_value_interval_width_per_pot": interval_width,
                    "reference_cumulative_train_seconds": ref_train_seconds,
                    "p0_cumulative_train_seconds": item["p0_seconds"],
                    "p1_cumulative_train_seconds": item["p1_seconds"],
                    "reference_eval_seconds": ref_eval_seconds,
                    "p0_eval_seconds": p0_eval,
                    "p1_eval_seconds": p1_eval,
                    **bounds,
                }
                rows.append(row)
                print(
                    f"{board_name:16s} {name:18s} iter={checkpoint:5d} "
                    f"loss_upper/pot={bounds['worst_loss_upper_per_pot']:.6f} "
                    f"max_interval/pot={interval_width:.6f}"
                )

    payload = {
        "schema": "DEEPCASH_RIVER_REFERENCE_CONVERGENCE_V1",
        "method": "cumulative one-sided candidate restriction versus shared rich reference; exact-BR intervals propagated",
        "checkpoints": list(checkpoints),
        "reference_sizes": list(reference_sizes),
        "range_combos": args.range_combos,
        "pot": args.pot,
        "stack": args.stack,
        "min_bet": args.min_bet,
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
