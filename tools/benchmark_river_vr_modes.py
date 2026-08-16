from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import (
    board_registry,
    parse_cards,
    parse_names,
    quantile_range,
)
from deepcash_core.river_external_sampling import (
    ExternalSamplingVariant,
    external_sampling_result,
    init_external_sampling,
)
from deepcash_core.river_lab import RiverGameSpec
from deepcash_core.river_vr_external_sampling import (
    VRBaselineMode,
    advance_vr_external_sampling,
)


def parse_ints(text: str) -> tuple[int, ...]:
    values = tuple(int(x.strip()) for x in text.split(",") if x.strip())
    if not values or any(x <= 0 for x in values):
        raise ValueError("integer list must contain positive values")
    if len(set(values)) != len(values):
        raise ValueError("integer list must be unique")
    return values


def parse_modes(text: str) -> tuple[VRBaselineMode, ...]:
    values = tuple(VRBaselineMode(x.strip()) for x in text.split(",") if x.strip())
    if not values or len(set(values)) != len(values):
        raise ValueError("mode list must be non-empty and unique")
    return values


def summarize(rows: list[dict]) -> dict:
    exploitabilities = [float(row["exploitability_per_pot"]) for row in rows]
    seconds = [float(row["train_seconds"]) for row in rows]
    terminals = [float(row["terminal_visits"]) for row in rows]
    return {
        "runs": len(rows),
        "mean_exploitability_per_pot": statistics.mean(exploitabilities),
        "median_exploitability_per_pot": statistics.median(exploitabilities),
        "min_exploitability_per_pot": min(exploitabilities),
        "max_exploitability_per_pot": max(exploitabilities),
        "sample_stdev_exploitability_per_pot": (
            statistics.stdev(exploitabilities) if len(exploitabilities) >= 2 else 0.0
        ),
        "mean_train_seconds": statistics.mean(seconds),
        "mean_terminal_visits": statistics.mean(terminals),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compare ZERO, legal INFOSET_EXACT and privileged PERFECT_HISTORY VR modes"
    )
    ap.add_argument("--boards", default="all")
    ap.add_argument("--range-combos", type=int, default=8)
    ap.add_argument("--p0-phase", type=float, default=0.13)
    ap.add_argument("--p1-phase", type=float, default=0.61)
    ap.add_argument("--pot", type=int, default=100)
    ap.add_argument("--bet-sizes", default="25,50,100")
    ap.add_argument("--iterations", type=int, default=2000)
    ap.add_argument("--seeds", default="101,211,307,401,503")
    ap.add_argument(
        "--modes",
        default="ZERO,INFOSET_EXACT,PERFECT_HISTORY",
    )
    ap.add_argument("--out", type=Path, default=Path("r5_vr_modes.json"))
    args = ap.parse_args()

    if args.range_combos <= 0 or args.pot <= 0 or args.iterations <= 0:
        raise ValueError("range-combos, pot and iterations must be positive")

    boards = board_registry("control")
    board_names = parse_names(args.boards, boards)
    bet_sizes = parse_ints(args.bet_sizes)
    seeds = parse_ints(args.seeds)
    modes = parse_modes(args.modes)

    rows: list[dict] = []
    for board_name in board_names:
        board = parse_cards(boards[board_name])
        p0_range = quantile_range(board, args.range_combos, args.p0_phase)
        p1_range = quantile_range(board, args.range_combos, args.p1_phase)
        spec = RiverGameSpec(
            board=board,
            p0_range=p0_range,
            p1_range=p1_range,
            pot=args.pot,
            bet_sizes=bet_sizes,
        )

        for mode in modes:
            for seed in seeds:
                state = init_external_sampling(
                    spec,
                    ExternalSamplingVariant.ES_CFR_PLUS_LINEAR,
                    seed=seed,
                )
                started = time.perf_counter()
                advance_vr_external_sampling(
                    spec,
                    state,
                    additional_iterations=args.iterations,
                    baseline_mode=mode,
                )
                train_seconds = time.perf_counter() - started
                result = external_sampling_result(spec, state)
                row = {
                    "board": board_name,
                    "mode": mode.value,
                    "seed": seed,
                    "iterations": state.iterations,
                    "terminal_visits": state.terminal_visits,
                    "train_seconds": train_seconds,
                    "policy_ev": result.policy_ev,
                    "br0_value": result.br0_value,
                    "br1_value": result.br1_value,
                    "exploitability_per_pot": result.exploitability_per_pot,
                }
                rows.append(row)
                print(
                    f"{board_name:20s} {mode.value:15s} seed={seed:4d} "
                    f"exp/pot={result.exploitability_per_pot:.6f} "
                    f"seconds={train_seconds:.3f} terminals={state.terminal_visits}"
                )

    per_board_mode = {}
    for board_name in board_names:
        per_board_mode[board_name] = {}
        for mode in modes:
            subset = [
                row
                for row in rows
                if row["board"] == board_name and row["mode"] == mode.value
            ]
            per_board_mode[board_name][mode.value] = summarize(subset)

    global_by_mode = {}
    for mode in modes:
        subset = [row for row in rows if row["mode"] == mode.value]
        global_by_mode[mode.value] = summarize(subset)

    payload = {
        "schema": "DEEPCASH_R5_VR_MODE_BENCHMARK_V1",
        "warning": (
            "Hosted-CI engineering evidence only. PERFECT_HISTORY uses privileged hidden "
            "information and is never production eligible. Physical Ryzen wall-clock remains R8."
        ),
        "configuration": {
            "board_set": "control",
            "boards": list(board_names),
            "range_combos_per_player": args.range_combos,
            "p0_phase": args.p0_phase,
            "p1_phase": args.p1_phase,
            "pot": args.pot,
            "bet_sizes": list(bet_sizes),
            "iterations": args.iterations,
            "seeds": list(seeds),
            "modes": [mode.value for mode in modes],
            "variant": ExternalSamplingVariant.ES_CFR_PLUS_LINEAR.value,
        },
        "rows": rows,
        "summary_by_board_mode": per_board_mode,
        "global_summary_by_mode": global_by_mode,
    }
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
