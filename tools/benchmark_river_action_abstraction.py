from __future__ import annotations

import argparse
import json
import time
from fractions import Fraction
from itertools import combinations
from pathlib import Path

from deepcash_core.cards import card_from_str, full_deck
from deepcash_core.evaluator import evaluate_best
from deepcash_core.river_lab import (
    RangeCombo,
    RiverGameSpec,
    materialize_bet_sizes,
    solve_river_cfr_plus,
)

CANDIDATES = {
    "S1_50": (Fraction(1, 2),),
    "S2_33_100": (Fraction(1, 3), Fraction(1, 1)),
    "S3_25_75_150": (Fraction(1, 4), Fraction(3, 4), Fraction(3, 2)),
    "S4_25_50_100_200": (Fraction(1, 4), Fraction(1, 2), Fraction(1, 1), Fraction(2, 1)),
}

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
        q = (k + 0.5 + phase) / count
        q = min(0.999999, max(0.000001, q))
        idx = round(q * (len(combos) - 1))
        step = 0
        while combos[idx] in used:
            step += 1
            idx = min(len(combos) - 1, idx + step)
        used.add(combos[idx])
        selected.append(RangeCombo(tuple(combos[idx])))
    return tuple(selected)


def main() -> None:
    ap = argparse.ArgumentParser(description="DeepCash river action-abstraction benchmark v1")
    ap.add_argument("--iterations", type=int, default=1500)
    ap.add_argument("--range-combos", type=int, default=12)
    ap.add_argument("--pot", type=int, default=100)
    ap.add_argument("--stack", type=int, default=300)
    ap.add_argument("--min-bet", type=int, default=20)
    ap.add_argument("--out", type=Path, default=Path("river_action_abstraction_results.json"))
    args = ap.parse_args()

    rows = []
    for board_name, board_text in BOARDS.items():
        board = parse_cards(board_text)
        p0 = quantile_range(board, args.range_combos, phase=0.00)
        p1 = quantile_range(board, args.range_combos, phase=0.27)
        for candidate, fractions in CANDIDATES.items():
            bet_sizes = materialize_bet_sizes(
                pot=args.pot,
                stack=args.stack,
                min_bet=args.min_bet,
                fractions=fractions,
            )
            spec = RiverGameSpec(
                board=board,
                p0_range=p0,
                p1_range=p1,
                pot=args.pot,
                bet_sizes=bet_sizes,
            )
            started = time.perf_counter()
            result = solve_river_cfr_plus(spec, iterations=args.iterations)
            elapsed = time.perf_counter() - started
            row = {
                "board": board_name,
                "candidate": candidate,
                "fractions": [str(x) for x in fractions],
                "bet_sizes": list(bet_sizes),
                "iterations": args.iterations,
                "range_combos": args.range_combos,
                "infosets": result.infosets,
                "action_slots": result.action_slots,
                "policy_ev": result.policy_ev,
                "br0_value": result.br0_value,
                "br1_value": result.br1_value,
                "exploitability": result.exploitability,
                "exploitability_per_pot": result.exploitability_per_pot,
                "wall_seconds": elapsed,
            }
            rows.append(row)
            print(
                f"{board_name:16s} {candidate:18s} sizes={bet_sizes!s:18s} "
                f"expl/pot={result.exploitability_per_pot:.6f} "
                f"infosets={result.infosets:4d} slots={result.action_slots:4d} "
                f"sec={elapsed:.3f}"
            )

    payload = {
        "schema": "DEEPCASH_RIVER_ACTION_ABSTRACTION_V1",
        "iterations": args.iterations,
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
