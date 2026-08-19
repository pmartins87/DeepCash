from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from deepcash_core.river_benchmark_fixtures import RIVER_BOARDS, parse_cards, quantile_range
from deepcash_core.river_correlated_chance_sampling import (
    CCS_VARIANT,
    CorrelatedChanceState,
    advance_correlated_chance,
    correlated_chance_result,
    init_correlated_chance,
)
from deepcash_core.river_external_sampling import (
    ExternalSamplingVariant,
    RiverExternalSamplingState,
    WeightedDealSampler,
    external_sampling_result,
    init_external_sampling,
)
from deepcash_core.river_lab import RiverGameSpec, RiverSolveResult
from deepcash_core.river_vr_external_sampling import VRBaselineMode, advance_vr_external_sampling
from deepcash_core.river_vr_tabular import (
    RiverTabularVRState,
    advance_tabular_vr,
    init_tabular_vr,
    tabular_vr_result,
)

SCHEMA = "DEEPCASH_R5_EQUAL_WALLCLOCK_SCALING_V1"
COMPARATORS = (
    "ES_ZERO",
    "ES_TABULAR_RUNNING",
    "CCS_CFR_PLUS_LINEAR",
    "ES_INFOSET_EXACT",
)
FROZEN_BOARDS = ("A_high_dry", "four_straight")
FROZEN_RANGE_COMBOS = (8, 24, 48)
FROZEN_SEEDS = (101, 211, 307)
FROZEN_BUDGETS = (1.0, 5.0, 15.0)
P0_PHASE = 0.13
P1_PHASE = 0.61
POT = 100
BET_SIZES = (25, 50, 100)
INITIAL_CHUNK = 64
MIN_CHUNK = 1
MAX_CHUNK = 4096


def build_spec(board_name: str, range_combos: int) -> RiverGameSpec:
    if board_name not in FROZEN_BOARDS:
        raise ValueError(f"board outside frozen R5 scaling set: {board_name}")
    if range_combos not in FROZEN_RANGE_COMBOS:
        raise ValueError(f"range support outside frozen R5 scaling set: {range_combos}")
    board = parse_cards(RIVER_BOARDS[board_name])
    return RiverGameSpec(
        board=board,
        p0_range=quantile_range(board, range_combos, P0_PHASE),
        p1_range=quantile_range(board, range_combos, P1_PHASE),
        pot=POT,
        bet_sizes=BET_SIZES,
    )


def next_chunk_iterations(
    *,
    completed_iterations: int,
    cumulative_train_seconds: float,
    remaining_seconds: float,
) -> int:
    if remaining_seconds <= 0.0:
        return MIN_CHUNK
    if completed_iterations <= 0 or cumulative_train_seconds <= 0.0:
        return INITIAL_CHUNK
    ips = completed_iterations / cumulative_train_seconds
    estimate = int(math.ceil(ips * remaining_seconds))
    return max(MIN_CHUNK, min(MAX_CHUNK, estimate))


def _state_iterations(state: Any) -> int:
    if isinstance(state, RiverTabularVRState):
        return state.base.iterations
    return state.iterations


def _terminal_visits(state: Any) -> int:
    if isinstance(state, RiverTabularVRState):
        return state.base.terminal_visits
    return state.terminal_visits


def _advance(
    spec: RiverGameSpec,
    comparator: str,
    state: RiverExternalSamplingState | RiverTabularVRState | CorrelatedChanceState,
    additional_iterations: int,
) -> None:
    if comparator == "ES_ZERO":
        advance_vr_external_sampling(
            spec,
            state,
            additional_iterations=additional_iterations,
            baseline_mode=VRBaselineMode.ZERO,
        )
        return
    if comparator == "ES_TABULAR_RUNNING":
        advance_tabular_vr(spec, state, additional_iterations=additional_iterations)
        return
    if comparator == "CCS_CFR_PLUS_LINEAR":
        advance_correlated_chance(spec, state, additional_iterations=additional_iterations)
        return
    if comparator == "ES_INFOSET_EXACT":
        advance_vr_external_sampling(
            spec,
            state,
            additional_iterations=additional_iterations,
            baseline_mode=VRBaselineMode.INFOSET_EXACT,
        )
        return
    raise ValueError(f"unknown comparator: {comparator}")


def _result(
    spec: RiverGameSpec,
    comparator: str,
    state: RiverExternalSamplingState | RiverTabularVRState | CorrelatedChanceState,
) -> RiverSolveResult:
    if comparator in {"ES_ZERO", "ES_INFOSET_EXACT"}:
        return external_sampling_result(spec, state)
    if comparator == "ES_TABULAR_RUNNING":
        return tabular_vr_result(spec, state)
    if comparator == "CCS_CFR_PLUS_LINEAR":
        return correlated_chance_result(spec, state)
    raise ValueError(f"unknown comparator: {comparator}")


def _init(
    spec: RiverGameSpec,
    comparator: str,
    seed: int,
) -> RiverExternalSamplingState | RiverTabularVRState | CorrelatedChanceState:
    if comparator in {"ES_ZERO", "ES_INFOSET_EXACT"}:
        return init_external_sampling(
            spec,
            ExternalSamplingVariant.ES_CFR_PLUS_LINEAR,
            seed=seed,
        )
    if comparator == "ES_TABULAR_RUNNING":
        return init_tabular_vr(
            spec,
            ExternalSamplingVariant.ES_CFR_PLUS_LINEAR,
            seed=seed,
        )
    if comparator == "CCS_CFR_PLUS_LINEAR":
        return init_correlated_chance(spec, seed=seed)
    raise ValueError(f"unknown comparator: {comparator}")


def _baseline_metrics(state: Any) -> tuple[int | None, int | None, int | None, float | None]:
    if not isinstance(state, RiverTabularVRState):
        return None, None, None, None
    slots = sum(len(values) for values in state.baseline_count.values())
    visited = sum(
        1
        for values in state.baseline_count.values()
        for count in values
        if count > 0
    )
    updates = sum(
        count
        for values in state.baseline_count.values()
        for count in values
    )
    return slots, visited, updates, visited / float(slots)


def run_comparator_cell(
    *,
    board_name: str,
    range_combos: int,
    seed: int,
    comparator: str,
    budgets: tuple[float, ...] = FROZEN_BUDGETS,
) -> list[dict[str, Any]]:
    if comparator not in COMPARATORS:
        raise ValueError(f"comparator outside frozen set: {comparator}")
    if tuple(budgets) != tuple(sorted(budgets)) or not budgets or budgets[0] <= 0:
        raise ValueError("budgets must be positive and sorted")

    spec = build_spec(board_name, range_combos)
    compatible_deal_count = len(WeightedDealSampler.from_spec(spec).deals)
    state = _init(spec, comparator, seed)
    cumulative_train_seconds = 0.0
    rows: list[dict[str, Any]] = []

    for requested_budget in budgets:
        while cumulative_train_seconds < requested_budget:
            remaining = requested_budget - cumulative_train_seconds
            chunk = next_chunk_iterations(
                completed_iterations=_state_iterations(state),
                cumulative_train_seconds=cumulative_train_seconds,
                remaining_seconds=remaining,
            )
            started = time.perf_counter()
            _advance(spec, comparator, state, chunk)
            cumulative_train_seconds += time.perf_counter() - started

        eval_started = time.perf_counter()
        result = _result(spec, comparator, state)
        evaluation_seconds = time.perf_counter() - eval_started
        iterations = _state_iterations(state)
        terminal_visits = _terminal_visits(state)
        slots, visited, updates, coverage = _baseline_metrics(state)
        overshoot = cumulative_train_seconds - requested_budget
        timing_limit = max(0.10, 0.05 * requested_budget)
        row = {
            "board": board_name,
            "range_combos_per_player": range_combos,
            "compatible_deal_count": compatible_deal_count,
            "seed": seed,
            "comparator": comparator,
            "requested_budget_seconds": requested_budget,
            "cumulative_train_seconds": cumulative_train_seconds,
            "timing_overshoot_seconds": overshoot,
            "timing_quality_flag": overshoot > timing_limit,
            "iterations": iterations,
            "iterations_per_second": iterations / cumulative_train_seconds,
            "terminal_visits": terminal_visits,
            "terminal_visits_per_second": terminal_visits / cumulative_train_seconds,
            "policy_ev": result.policy_ev,
            "br0_value": result.br0_value,
            "br1_value": result.br1_value,
            "exploitability_per_pot": result.exploitability_per_pot,
            "evaluation_seconds": evaluation_seconds,
            "baseline_slots": slots,
            "baseline_visited_slots": visited,
            "baseline_updates": updates,
            "baseline_coverage": coverage,
        }
        rows.append(row)
        print(
            f"{board_name:14s} range={range_combos:2d} seed={seed:3d} "
            f"{comparator:23s} budget={requested_budget:4.1f}s "
            f"actual={cumulative_train_seconds:7.3f}s it={iterations:8d} "
            f"exp/pot={result.exploitability_per_pot:.8f}"
        )
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[int, float, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[
            (
                int(row["range_combos_per_player"]),
                float(row["requested_budget_seconds"]),
                str(row["comparator"]),
            )
        ].append(row)

    summary: dict[str, Any] = {}
    for range_combos in FROZEN_RANGE_COMBOS:
        range_key = str(range_combos)
        summary[range_key] = {}
        for budget in FROZEN_BUDGETS:
            budget_key = f"{budget:g}"
            summary[range_key][budget_key] = {}
            for comparator in COMPARATORS:
                subset = groups[(range_combos, budget, comparator)]
                if not subset:
                    continue
                exps = [float(row["exploitability_per_pot"]) for row in subset]
                seconds = [float(row["cumulative_train_seconds"]) for row in subset]
                throughput = [float(row["iterations_per_second"]) for row in subset]
                summary[range_key][budget_key][comparator] = {
                    "cells": len(subset),
                    "mean_exploitability_per_pot": statistics.fmean(exps),
                    "median_exploitability_per_pot": statistics.median(exps),
                    "worst_exploitability_per_pot": max(exps),
                    "sample_stdev_exploitability_per_pot": statistics.stdev(exps) if len(exps) >= 2 else 0.0,
                    "mean_actual_train_seconds": statistics.fmean(seconds),
                    "mean_timing_overshoot_seconds": statistics.fmean(
                        float(row["timing_overshoot_seconds"]) for row in subset
                    ),
                    "timing_quality_flags": sum(bool(row["timing_quality_flag"]) for row in subset),
                    "mean_iterations_per_second": statistics.fmean(throughput),
                    "mean_terminal_visits_per_second": statistics.fmean(
                        float(row["terminal_visits_per_second"]) for row in subset
                    ),
                    "mean_baseline_coverage": (
                        statistics.fmean(
                            float(row["baseline_coverage"])
                            for row in subset
                            if row["baseline_coverage"] is not None
                        )
                        if comparator == "ES_TABULAR_RUNNING"
                        else None
                    ),
                }
    return summary


def paired_vs_zero(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {
        (
            row["board"],
            row["range_combos_per_player"],
            row["seed"],
            row["requested_budget_seconds"],
            row["comparator"],
        ): row
        for row in rows
    }
    out: dict[str, Any] = {}
    for range_combos in FROZEN_RANGE_COMBOS:
        range_key = str(range_combos)
        out[range_key] = {}
        for budget in FROZEN_BUDGETS:
            budget_key = f"{budget:g}"
            out[range_key][budget_key] = {}
            for comparator in COMPARATORS:
                if comparator == "ES_ZERO":
                    continue
                diffs: list[float] = []
                wins = 0
                for board_name in FROZEN_BOARDS:
                    for seed in FROZEN_SEEDS:
                        candidate = lookup[(board_name, range_combos, seed, budget, comparator)]
                        zero = lookup[(board_name, range_combos, seed, budget, "ES_ZERO")]
                        diff = float(candidate["exploitability_per_pot"]) - float(zero["exploitability_per_pot"])
                        diffs.append(diff)
                        wins += int(diff < 0.0)
                out[range_key][budget_key][comparator] = {
                    "wins_vs_zero": wins,
                    "cells": len(diffs),
                    "mean_difference_candidate_minus_zero": statistics.fmean(diffs),
                    "median_difference_candidate_minus_zero": statistics.median(diffs),
                }
    return out


def final_pareto(summary: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    budget_key = f"{FROZEN_BUDGETS[-1]:g}"
    for range_combos in FROZEN_RANGE_COMBOS:
        data = summary[str(range_combos)][budget_key]
        frontier: list[str] = []
        dominance: dict[str, list[str]] = {name: [] for name in COMPARATORS}
        for left in COMPARATORS:
            dominated = False
            for right in COMPARATORS:
                if left == right:
                    continue
                r = data[right]
                l = data[left]
                right_dominates = (
                    r["mean_exploitability_per_pot"] <= l["mean_exploitability_per_pot"]
                    and r["mean_actual_train_seconds"] <= l["mean_actual_train_seconds"]
                    and (
                        r["mean_exploitability_per_pot"] < l["mean_exploitability_per_pot"]
                        or r["mean_actual_train_seconds"] < l["mean_actual_train_seconds"]
                    )
                )
                if right_dominates:
                    dominated = True
                    dominance[right].append(left)
            if not dominated:
                frontier.append(left)
        out[str(range_combos)] = {
            "budget_seconds": FROZEN_BUDGETS[-1],
            "frontier": frontier,
            "dominates": dominance,
            "tabular_minus_infoset_exact_mean_exploitability_per_pot": (
                data["ES_TABULAR_RUNNING"]["mean_exploitability_per_pot"]
                - data["ES_INFOSET_EXACT"]["mean_exploitability_per_pot"]
            ),
        }
    return out


def validate_full_artifact(rows: list[dict[str, Any]]) -> None:
    expected = len(FROZEN_BOARDS) * len(FROZEN_RANGE_COMBOS) * len(FROZEN_SEEDS) * len(COMPARATORS) * len(FROZEN_BUDGETS)
    if len(rows) != expected:
        raise RuntimeError(f"incomplete R5 scaling artifact: rows={len(rows)} expected={expected}")
    identities = {
        (
            row["board"],
            row["range_combos_per_player"],
            row["seed"],
            row["comparator"],
            row["requested_budget_seconds"],
        )
        for row in rows
    }
    if len(identities) != expected:
        raise RuntimeError("R5 scaling artifact contains duplicate/missing cell identities")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen R5 equal-wall-clock scaling v1 battery")
    parser.add_argument("--out", type=Path, default=Path("r5_equal_wallclock_scaling_v1.json"))
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="structural smoke only: one board/range/seed, budgets 0.01/0.02 seconds; never promotable",
    )
    args = parser.parse_args()

    if args.smoke:
        boards = (FROZEN_BOARDS[0],)
        ranges = (FROZEN_RANGE_COMBOS[0],)
        seeds = (FROZEN_SEEDS[0],)
        budgets = (0.01, 0.02)
    else:
        boards = FROZEN_BOARDS
        ranges = FROZEN_RANGE_COMBOS
        seeds = FROZEN_SEEDS
        budgets = FROZEN_BUDGETS

    rows: list[dict[str, Any]] = []
    started = time.time()
    for board_name in boards:
        for range_combos in ranges:
            for seed in seeds:
                for comparator in COMPARATORS:
                    rows.extend(
                        run_comparator_cell(
                            board_name=board_name,
                            range_combos=range_combos,
                            seed=seed,
                            comparator=comparator,
                            budgets=budgets,
                        )
                    )

    if args.smoke:
        payload = {
            "schema": SCHEMA,
            "status": "SMOKE_NOT_PROMOTABLE",
            "configuration": {
                "boards": list(boards),
                "range_combos_per_player": list(ranges),
                "seeds": list(seeds),
                "budgets_seconds": list(budgets),
                "comparators": list(COMPARATORS),
            },
            "rows": rows,
        }
    else:
        validate_full_artifact(rows)
        summary = summarize_rows(rows)
        payload = {
            "schema": SCHEMA,
            "status": "COMPLETE_HOSTED_ENGINEERING_EVIDENCE_NOT_PRODUCTION_SELECTION",
            "warning": "Hosted timing is engineering evidence only; physical Ryzen equal-wall-clock reproduction remains mandatory before R5/R8 exit.",
            "configuration": {
                "boards": list(FROZEN_BOARDS),
                "board_text": {name: RIVER_BOARDS[name] for name in FROZEN_BOARDS},
                "range_combos_per_player": list(FROZEN_RANGE_COMBOS),
                "p0_phase": P0_PHASE,
                "p1_phase": P1_PHASE,
                "pot": POT,
                "bet_sizes": list(BET_SIZES),
                "seeds": list(FROZEN_SEEDS),
                "budgets_seconds": list(FROZEN_BUDGETS),
                "comparators": list(COMPARATORS),
                "external_variant": ExternalSamplingVariant.ES_CFR_PLUS_LINEAR.value,
                "ccs_variant": CCS_VARIANT,
                "chunk_contract": {
                    "initial": INITIAL_CHUNK,
                    "minimum": MIN_CHUNK,
                    "maximum": MAX_CHUNK,
                    "next_chunk": "ceil(cumulative_iterations / cumulative_train_seconds * remaining_seconds), clipped to [1,4096]",
                },
            },
            "rows": rows,
            "summary_by_range_budget_comparator": summary,
            "paired_vs_zero": paired_vs_zero(rows),
            "pareto_at_15_seconds": final_pareto(summary),
            "wall_seconds_total": time.time() - started,
        }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
