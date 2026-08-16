from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

from deepcash_core.river_benchmark_fixtures import (
    board_registry,
    parse_cards,
    parse_checkpoints,
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
from deepcash_core.river_vr_tabular import (
    advance_tabular_vr,
    init_tabular_vr,
    tabular_vr_result,
)


MODES = ("ZERO", "TABULAR_RUNNING", "INFOSET_EXACT")


def parse_ints(text: str) -> tuple[int, ...]:
    values = tuple(int(x.strip()) for x in text.split(",") if x.strip())
    if not values or any(value <= 0 for value in values):
        raise ValueError("integer list must contain positive values")
    if len(set(values)) != len(values):
        raise ValueError("integer list must be unique")
    return values


def summarize(rows: list[dict]) -> dict:
    exps = [float(row["exploitability_per_pot"]) for row in rows]
    seconds = [float(row["cumulative_train_seconds"]) for row in rows]
    return {
        "runs": len(rows),
        "mean_exploitability_per_pot": statistics.mean(exps),
        "median_exploitability_per_pot": statistics.median(exps),
        "min_exploitability_per_pot": min(exps),
        "max_exploitability_per_pot": max(exps),
        "sample_stdev_exploitability_per_pot": (
            statistics.stdev(exps) if len(exps) >= 2 else 0.0
        ),
        "mean_cumulative_train_seconds": statistics.mean(seconds),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare ZERO, cheap tabular and exact-info VR")
    ap.add_argument("--boards", default="all")
    ap.add_argument("--range-combos", type=int, default=8)
    ap.add_argument("--p0-phase", type=float, default=0.13)
    ap.add_argument("--p1-phase", type=float, default=0.61)
    ap.add_argument("--pot", type=int, default=100)
    ap.add_argument("--bet-sizes", default="25,50,100")
    ap.add_argument("--checkpoints", default="500,2000,10000")
    ap.add_argument("--seeds", default="101,211,307,401,503")
    ap.add_argument("--out", type=Path, default=Path("r5_vr_tabular.json"))
    args = ap.parse_args()

    if args.range_combos <= 0 or args.pot <= 0:
        raise ValueError("range-combos and pot must be positive")
    boards = board_registry("control")
    board_names = parse_names(args.boards, boards)
    bet_sizes = parse_ints(args.bet_sizes)
    checkpoints = parse_checkpoints(args.checkpoints)
    seeds = parse_ints(args.seeds)

    rows: list[dict] = []
    for board_name in board_names:
        board = parse_cards(boards[board_name])
        spec = RiverGameSpec(
            board=board,
            p0_range=quantile_range(board, args.range_combos, args.p0_phase),
            p1_range=quantile_range(board, args.range_combos, args.p1_phase),
            pot=args.pot,
            bet_sizes=bet_sizes,
        )

        for seed in seeds:
            for mode in MODES:
                if mode == "TABULAR_RUNNING":
                    state = init_tabular_vr(
                        spec,
                        ExternalSamplingVariant.ES_CFR_PLUS_LINEAR,
                        seed=seed,
                    )
                else:
                    state = init_external_sampling(
                        spec,
                        ExternalSamplingVariant.ES_CFR_PLUS_LINEAR,
                        seed=seed,
                    )

                cumulative_seconds = 0.0
                previous = 0
                for checkpoint in checkpoints:
                    delta = checkpoint - previous
                    started = time.perf_counter()
                    if mode == "TABULAR_RUNNING":
                        advance_tabular_vr(spec, state, additional_iterations=delta)
                        result = tabular_vr_result(spec, state)
                        base = state.base
                        baseline_slots = sum(
                            len(values) for values in state.baseline_count.values()
                        )
                        visited_slots = sum(
                            1
                            for values in state.baseline_count.values()
                            for count in values
                            if count > 0
                        )
                        baseline_updates = sum(
                            count
                            for values in state.baseline_count.values()
                            for count in values
                        )
                    else:
                        vr_mode = (
                            VRBaselineMode.ZERO
                            if mode == "ZERO"
                            else VRBaselineMode.INFOSET_EXACT
                        )
                        advance_vr_external_sampling(
                            spec,
                            state,
                            additional_iterations=delta,
                            baseline_mode=vr_mode,
                        )
                        result = external_sampling_result(spec, state)
                        base = state
                        baseline_slots = None
                        visited_slots = None
                        baseline_updates = None
                    cumulative_seconds += time.perf_counter() - started

                    row = {
                        "board": board_name,
                        "seed": seed,
                        "mode": mode,
                        "checkpoint": checkpoint,
                        "iterations": base.iterations,
                        "terminal_visits": base.terminal_visits,
                        "cumulative_train_seconds": cumulative_seconds,
                        "policy_ev": result.policy_ev,
                        "br0_value": result.br0_value,
                        "br1_value": result.br1_value,
                        "exploitability_per_pot": result.exploitability_per_pot,
                        "baseline_slots": baseline_slots,
                        "baseline_visited_slots": visited_slots,
                        "baseline_updates": baseline_updates,
                        "baseline_coverage": (
                            None
                            if baseline_slots is None
                            else visited_slots / float(baseline_slots)
                        ),
                    }
                    rows.append(row)
                    print(
                        f"{board_name:18s} seed={seed:3d} {mode:15s} "
                        f"it={checkpoint:5d} exp/pot={result.exploitability_per_pot:.6f} "
                        f"seconds={cumulative_seconds:.3f}"
                    )
                    previous = checkpoint

    summary_by_checkpoint_mode: dict[str, dict] = {}
    summary_by_board_checkpoint_mode: dict[str, dict] = {}
    paired_vs_zero: dict[str, dict] = {}

    for checkpoint in checkpoints:
        cp_key = str(checkpoint)
        summary_by_checkpoint_mode[cp_key] = {}
        paired_vs_zero[cp_key] = {}
        for mode in MODES:
            subset = [
                row for row in rows
                if row["checkpoint"] == checkpoint and row["mode"] == mode
            ]
            summary_by_checkpoint_mode[cp_key][mode] = summarize(subset)

        lookup = {
            (row["board"], row["seed"], row["mode"]): row
            for row in rows if row["checkpoint"] == checkpoint
        }
        for mode in ("TABULAR_RUNNING", "INFOSET_EXACT"):
            diffs = []
            wins = 0
            for board_name in board_names:
                for seed in seeds:
                    candidate = lookup[(board_name, seed, mode)]["exploitability_per_pot"]
                    zero = lookup[(board_name, seed, "ZERO")]["exploitability_per_pot"]
                    diff = candidate - zero
                    diffs.append(diff)
                    wins += int(diff < 0.0)
            paired_vs_zero[cp_key][mode] = {
                "wins": wins,
                "cells": len(diffs),
                "mean_difference_candidate_minus_zero": statistics.mean(diffs),
                "median_difference_candidate_minus_zero": statistics.median(diffs),
            }

    for board_name in board_names:
        summary_by_board_checkpoint_mode[board_name] = {}
        for checkpoint in checkpoints:
            cp_key = str(checkpoint)
            summary_by_board_checkpoint_mode[board_name][cp_key] = {}
            for mode in MODES:
                subset = [
                    row for row in rows
                    if row["board"] == board_name
                    and row["checkpoint"] == checkpoint
                    and row["mode"] == mode
                ]
                summary_by_board_checkpoint_mode[board_name][cp_key][mode] = summarize(subset)

    final_cp = str(checkpoints[-1])
    final = summary_by_checkpoint_mode[final_cp]
    tabular_rows = [
        row for row in rows
        if row["checkpoint"] == checkpoints[-1]
        and row["mode"] == "TABULAR_RUNNING"
    ]
    final_comparison = {
        "checkpoint": checkpoints[-1],
        "tabular_time_multiplier_vs_zero": (
            final["TABULAR_RUNNING"]["mean_cumulative_train_seconds"]
            / final["ZERO"]["mean_cumulative_train_seconds"]
        ),
        "infoset_exact_time_multiplier_vs_zero": (
            final["INFOSET_EXACT"]["mean_cumulative_train_seconds"]
            / final["ZERO"]["mean_cumulative_train_seconds"]
        ),
        "tabular_mean_exploitability_reduction_vs_zero_fraction": (
            final["ZERO"]["mean_exploitability_per_pot"]
            - final["TABULAR_RUNNING"]["mean_exploitability_per_pot"]
        ) / final["ZERO"]["mean_exploitability_per_pot"],
        "tabular_minus_infoset_exact_mean_exploitability_per_pot": (
            final["TABULAR_RUNNING"]["mean_exploitability_per_pot"]
            - final["INFOSET_EXACT"]["mean_exploitability_per_pot"]
        ),
        "mean_tabular_baseline_coverage": statistics.mean(
            float(row["baseline_coverage"]) for row in tabular_rows
        ),
    }

    payload = {
        "schema": "DEEPCASH_R5_TABULAR_VR_BENCHMARK_V1",
        "warning": "Hosted-CI timing is engineering evidence only; physical Ryzen selection remains R8.",
        "configuration": {
            "boards": list(board_names),
            "range_combos_per_player": args.range_combos,
            "p0_phase": args.p0_phase,
            "p1_phase": args.p1_phase,
            "pot": args.pot,
            "bet_sizes": list(bet_sizes),
            "checkpoints": list(checkpoints),
            "seeds": list(seeds),
            "modes": list(MODES),
            "variant": ExternalSamplingVariant.ES_CFR_PLUS_LINEAR.value,
        },
        "rows": rows,
        "summary_by_checkpoint_mode": summary_by_checkpoint_mode,
        "summary_by_board_checkpoint_mode": summary_by_board_checkpoint_mode,
        "paired_vs_zero": paired_vs_zero,
        "final_comparison": final_comparison,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
