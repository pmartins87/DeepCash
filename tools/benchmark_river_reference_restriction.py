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
from deepcash_core.river_reference_lab import AsymmetricRiverGameSpec, solve_asymmetric_river_cfr_plus

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


def parse_cards(text: str) -> tuple[int, ...]:
    return tuple(card_from_str(x) for x in text.split())


def quantile_range(board: tuple[int, ...], count: int, phase: float) -> tuple[RangeCombo, ...]:
    remaining = [c for c in full_deck() if c not in set(board)]
    combos = list(combinations(remaining, 2))
    combos.sort(key=lambda h: (evaluate_best((*h, *board)), h))
    selected = []
    used = set()
    for k in range(count):
        q = min(0.999999, max(0.000001, (k + 0.5 + phase) / count))
        idx = round(q * (len(combos) - 1))
        while combos[idx] in used:
            idx = min(len(combos) - 1, idx + 1)
        used.add(combos[idx])
        selected.append(RangeCombo(tuple(combos[idx])))
    return tuple(selected)


def choose_names(text: str, available: dict[str, object]) -> tuple[str, ...]:
    if text == "all":
        return tuple(available)
    names = tuple(x.strip() for x in text.split(",") if x.strip())
    unknown = set(names) - set(available)
    if unknown:
        raise ValueError(f"unknown names: {sorted(unknown)}")
    return names


def restriction_bounds(reference, p0_restricted, p1_restricted, pot: int) -> dict:
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
    ap = argparse.ArgumentParser(description="DeepCash common-reference river sizing restriction benchmark")
    ap.add_argument("--iterations", type=int, default=1500)
    ap.add_argument("--range-combos", type=int, default=8)
    ap.add_argument("--pot", type=int, default=100)
    ap.add_argument("--stack", type=int, default=300)
    ap.add_argument("--min-bet", type=int, default=20)
    ap.add_argument("--boards", default="all")
    ap.add_argument("--candidates", default="all")
    ap.add_argument("--out", type=Path, default=Path("river_reference_restriction_results.json"))
    args = ap.parse_args()

    board_names = choose_names(args.boards, BOARDS)
    candidate_names = choose_names(args.candidates, CANDIDATES)
    reference_sizes = materialize_bet_sizes(
        pot=args.pot,
        stack=args.stack,
        min_bet=args.min_bet,
        fractions=REFERENCE_FRACTIONS,
    )
    rows = []

    for board_name in board_names:
        board = parse_cards(BOARDS[board_name])
        p0 = quantile_range(board, args.range_combos, phase=0.00)
        p1 = quantile_range(board, args.range_combos, phase=0.27)

        ref_spec = AsymmetricRiverGameSpec(
            board, p0, p1, args.pot, reference_sizes, reference_sizes
        )
        started = time.perf_counter()
        reference = solve_asymmetric_river_cfr_plus(ref_spec, iterations=args.iterations)
        ref_seconds = time.perf_counter() - started

        for candidate_name in candidate_names:
            candidate_sizes = materialize_bet_sizes(
                pot=args.pot,
                stack=args.stack,
                min_bet=args.min_bet,
                fractions=CANDIDATES[candidate_name],
            )
            if not set(candidate_sizes).issubset(reference_sizes):
                raise RuntimeError("materialized candidate escaped reference action set")

            started = time.perf_counter()
            p0_restricted = solve_asymmetric_river_cfr_plus(
                AsymmetricRiverGameSpec(
                    board, p0, p1, args.pot, candidate_sizes, reference_sizes
                ),
                iterations=args.iterations,
            )
            p0_seconds = time.perf_counter() - started

            started = time.perf_counter()
            p1_restricted = solve_asymmetric_river_cfr_plus(
                AsymmetricRiverGameSpec(
                    board, p0, p1, args.pot, reference_sizes, candidate_sizes
                ),
                iterations=args.iterations,
            )
            p1_seconds = time.perf_counter() - started

            bounds = restriction_bounds(reference, p0_restricted, p1_restricted, args.pot)
            row = {
                "board": board_name,
                "candidate": candidate_name,
                "reference_sizes": list(reference_sizes),
                "candidate_sizes": list(candidate_sizes),
                "iterations": args.iterations,
                "range_combos": args.range_combos,
                "reference_exploitability_per_pot": reference.exploitability_per_pot,
                "p0_restricted_exploitability_per_pot": p0_restricted.exploitability_per_pot,
                "p1_restricted_exploitability_per_pot": p1_restricted.exploitability_per_pot,
                "reference_seconds": ref_seconds,
                "p0_restricted_seconds": p0_seconds,
                "p1_restricted_seconds": p1_seconds,
                **bounds,
            }
            rows.append(row)
            print(
                f"{board_name:16s} {candidate_name:18s} candidate={candidate_sizes!s:20s} "
                f"loss_upper/pot={bounds['worst_loss_upper_per_pot']:.6f} "
                f"solver_xpl=[{reference.exploitability_per_pot:.5f},"
                f"{p0_restricted.exploitability_per_pot:.5f},"
                f"{p1_restricted.exploitability_per_pot:.5f}]"
            )

    payload = {
        "schema": "DEEPCASH_RIVER_REFERENCE_RESTRICTION_V1",
        "method": "one-sided action restriction against a common rich reference game; loss bounds use exact-BR value intervals",
        "reference_fractions": [str(x) for x in REFERENCE_FRACTIONS],
        "reference_sizes": list(reference_sizes),
        "iterations": args.iterations,
        "range_combos": args.range_combos,
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
