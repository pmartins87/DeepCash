from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from deepcash_core.river_benchmark_fixtures import parse_cards, quantile_range
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


SCHEMA = "DEEPCASH_R5_HELDOUT_SAMPLED_FINALISTS_V1"
STATUS = "COMPLETE_HELDOUT_EVIDENCE_NOT_PHYSICAL_SELECTION"
COMPARATORS = ("ES_ZERO", "CCS_CFR_PLUS_LINEAR")
FROZEN_BOARDS = {
    "ace_low_mixed_r5ho": "As 7c 5d 3h 2s",
    "king_broadway_mixed_r5ho": "Kc Qs Td 6h 2c",
    "paired_jacks_r5ho": "Jh Jc 8s 5d 3c",
    "three_diamond_connected_r5ho": "9d 8d 6c 4s 2d",
}
FROZEN_RANGE_COMBOS = (8, 24, 48)
FROZEN_SEEDS = (401, 503, 607)
FROZEN_BUDGET_SECONDS = 15.0
P0_PHASE = 0.27
P1_PHASE = 0.73
POT = 100
BET_SIZES = (25, 50, 100)
INITIAL_CHUNK = 64
MIN_CHUNK = 1
MAX_CHUNK = 4096
MIN_WINS_PER_SUPPORT = 7
MIN_WINS_OVERALL = 27


def build_spec(board_name: str, range_combos: int) -> RiverGameSpec:
    if board_name not in FROZEN_BOARDS:
        raise ValueError(f"board outside frozen R5 held-out set: {board_name}")
    if range_combos not in FROZEN_RANGE_COMBOS:
        raise ValueError(f"range support outside frozen R5 held-out set: {range_combos}")
    board = parse_cards(FROZEN_BOARDS[board_name])
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


def _init(
    spec: RiverGameSpec,
    comparator: str,
    seed: int,
) -> RiverExternalSamplingState | CorrelatedChanceState:
    if comparator == "ES_ZERO":
        return init_external_sampling(
            spec,
            ExternalSamplingVariant.ES_CFR_PLUS_LINEAR,
            seed=seed,
        )
    if comparator == "CCS_CFR_PLUS_LINEAR":
        return init_correlated_chance(spec, seed=seed)
    raise ValueError(f"comparator outside frozen held-out set: {comparator}")


def _advance(
    spec: RiverGameSpec,
    comparator: str,
    state: RiverExternalSamplingState | CorrelatedChanceState,
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
    if comparator == "CCS_CFR_PLUS_LINEAR":
        advance_correlated_chance(spec, state, additional_iterations=additional_iterations)
        return
    raise ValueError(f"comparator outside frozen held-out set: {comparator}")


def _result(
    spec: RiverGameSpec,
    comparator: str,
    state: RiverExternalSamplingState | CorrelatedChanceState,
) -> RiverSolveResult:
    if comparator == "ES_ZERO":
        return external_sampling_result(spec, state)
    if comparator == "CCS_CFR_PLUS_LINEAR":
        return correlated_chance_result(spec, state)
    raise ValueError(f"comparator outside frozen held-out set: {comparator}")


def run_cell(
    *,
    board_name: str,
    range_combos: int,
    seed: int,
    comparator: str,
    budget_seconds: float = FROZEN_BUDGET_SECONDS,
) -> dict[str, Any]:
    if comparator not in COMPARATORS:
        raise ValueError(f"comparator outside frozen held-out set: {comparator}")
    if budget_seconds <= 0.0 or not math.isfinite(budget_seconds):
        raise ValueError("budget_seconds must be finite and positive")

    spec = build_spec(board_name, range_combos)
    compatible_deal_count = len(WeightedDealSampler.from_spec(spec).deals)
    state = _init(spec, comparator, seed)
    cumulative_train_seconds = 0.0

    while cumulative_train_seconds < budget_seconds:
        remaining = budget_seconds - cumulative_train_seconds
        chunk = next_chunk_iterations(
            completed_iterations=state.iterations,
            cumulative_train_seconds=cumulative_train_seconds,
            remaining_seconds=remaining,
        )
        started = time.perf_counter()
        _advance(spec, comparator, state, chunk)
        cumulative_train_seconds += time.perf_counter() - started

    eval_started = time.perf_counter()
    result = _result(spec, comparator, state)
    evaluation_seconds = time.perf_counter() - eval_started
    overshoot = cumulative_train_seconds - budget_seconds
    timing_limit = max(0.10, 0.05 * budget_seconds)

    row = {
        "board": board_name,
        "board_text": FROZEN_BOARDS[board_name],
        "range_combos_per_player": range_combos,
        "compatible_deal_count": compatible_deal_count,
        "seed": seed,
        "comparator": comparator,
        "requested_budget_seconds": budget_seconds,
        "cumulative_train_seconds": cumulative_train_seconds,
        "timing_overshoot_seconds": overshoot,
        "timing_quality_flag": overshoot > timing_limit,
        "iterations": state.iterations,
        "iterations_per_second": state.iterations / cumulative_train_seconds,
        "terminal_visits": state.terminal_visits,
        "terminal_visits_per_second": state.terminal_visits / cumulative_train_seconds,
        "policy_ev": result.policy_ev,
        "br0_value": result.br0_value,
        "br1_value": result.br1_value,
        "exploitability_per_pot": result.exploitability_per_pot,
        "evaluation_seconds": evaluation_seconds,
    }
    print(
        f"{board_name:30s} range={range_combos:2d} seed={seed:3d} "
        f"{comparator:23s} actual={cumulative_train_seconds:7.3f}s "
        f"it={state.iterations:8d} exp/pot={result.exploitability_per_pot:.8f}"
    )
    return row


def validate_full_artifact(rows: list[dict[str, Any]]) -> None:
    expected = (
        len(FROZEN_BOARDS)
        * len(FROZEN_RANGE_COMBOS)
        * len(FROZEN_SEEDS)
        * len(COMPARATORS)
    )
    if len(rows) != expected:
        raise RuntimeError(f"incomplete R5 held-out artifact: rows={len(rows)} expected={expected}")
    identities = {
        (
            row["board"],
            row["range_combos_per_player"],
            row["seed"],
            row["comparator"],
        )
        for row in rows
    }
    if len(identities) != expected:
        raise RuntimeError("R5 held-out artifact contains duplicate/missing cell identities")


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(int(row["range_combos_per_player"]), str(row["comparator"]))].append(row)

    out: dict[str, Any] = {}
    for support in FROZEN_RANGE_COMBOS:
        out[str(support)] = {}
        for comparator in COMPARATORS:
            subset = groups[(support, comparator)]
            exps = [float(row["exploitability_per_pot"]) for row in subset]
            out[str(support)][comparator] = {
                "cells": len(subset),
                "mean_exploitability_per_pot": statistics.fmean(exps),
                "median_exploitability_per_pot": statistics.median(exps),
                "worst_exploitability_per_pot": max(exps),
                "sample_stdev_exploitability_per_pot": statistics.stdev(exps),
                "mean_actual_train_seconds": statistics.fmean(
                    float(row["cumulative_train_seconds"]) for row in subset
                ),
                "mean_iterations_per_second": statistics.fmean(
                    float(row["iterations_per_second"]) for row in subset
                ),
                "mean_terminal_visits_per_second": statistics.fmean(
                    float(row["terminal_visits_per_second"]) for row in subset
                ),
                "timing_quality_flags": sum(
                    bool(row["timing_quality_flag"]) for row in subset
                ),
            }
    return out


def paired_ccs_vs_zero(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {
        (
            row["board"],
            int(row["range_combos_per_player"]),
            int(row["seed"]),
            row["comparator"],
        ): row
        for row in rows
    }
    per_support: dict[str, Any] = {}
    total_wins = 0
    all_diffs: list[float] = []
    for support in FROZEN_RANGE_COMBOS:
        diffs: list[float] = []
        wins = 0
        for board_name in FROZEN_BOARDS:
            for seed in FROZEN_SEEDS:
                ccs = lookup[(board_name, support, seed, "CCS_CFR_PLUS_LINEAR")]
                zero = lookup[(board_name, support, seed, "ES_ZERO")]
                diff = float(ccs["exploitability_per_pot"]) - float(
                    zero["exploitability_per_pot"]
                )
                diffs.append(diff)
                wins += int(diff < 0.0)
        total_wins += wins
        all_diffs.extend(diffs)
        per_support[str(support)] = {
            "wins": wins,
            "cells": len(diffs),
            "mean_difference_ccs_minus_zero": statistics.fmean(diffs),
            "median_difference_ccs_minus_zero": statistics.median(diffs),
        }
    return {
        "per_support": per_support,
        "overall": {
            "wins": total_wins,
            "cells": len(all_diffs),
            "mean_difference_ccs_minus_zero": statistics.fmean(all_diffs),
            "median_difference_ccs_minus_zero": statistics.median(all_diffs),
        },
    }


def frozen_decision(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    paired: dict[str, Any],
) -> dict[str, Any]:
    support_checks: dict[str, Any] = {}
    strategic_pass = True
    for support in FROZEN_RANGE_COMBOS:
        key = str(support)
        ccs_mean = float(summary[key]["CCS_CFR_PLUS_LINEAR"]["mean_exploitability_per_pot"])
        zero_mean = float(summary[key]["ES_ZERO"]["mean_exploitability_per_pot"])
        wins = int(paired["per_support"][key]["wins"])
        mean_ok = ccs_mean <= zero_mean
        wins_ok = wins >= MIN_WINS_PER_SUPPORT
        support_checks[key] = {
            "ccs_mean_no_greater_than_zero": mean_ok,
            "ccs_paired_wins": wins,
            "required_paired_wins": MIN_WINS_PER_SUPPORT,
            "paired_wins_pass": wins_ok,
        }
        strategic_pass = strategic_pass and mean_ok and wins_ok

    overall_wins = int(paired["overall"]["wins"])
    overall_pass = overall_wins >= MIN_WINS_OVERALL
    strategic_pass = strategic_pass and overall_pass
    timing_flags = sum(bool(row["timing_quality_flag"]) for row in rows)

    if not strategic_pass:
        provisional = "FAIL_STRATEGIC_GENERALIZATION"
    elif timing_flags:
        provisional = "TIMING_REVIEW_REQUIRED"
    else:
        provisional = "PASS_TO_PHYSICAL_RYZEN_GATE"

    return {
        "support_checks": support_checks,
        "overall_paired_wins": overall_wins,
        "required_overall_paired_wins": MIN_WINS_OVERALL,
        "overall_paired_wins_pass": overall_pass,
        "timing_quality_flags": timing_flags,
        "provisional_decision": provisional,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen R5 sampled-finalist held-out v1")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("r5_heldout_sampled_finalists_v1.json"),
    )
    args = parser.parse_args()

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    for board_name in FROZEN_BOARDS:
        for support in FROZEN_RANGE_COMBOS:
            for seed in FROZEN_SEEDS:
                for comparator in COMPARATORS:
                    rows.append(
                        run_cell(
                            board_name=board_name,
                            range_combos=support,
                            seed=seed,
                            comparator=comparator,
                        )
                    )

    validate_full_artifact(rows)
    summary = summarize(rows)
    paired = paired_ccs_vs_zero(rows)
    decision = frozen_decision(rows, summary, paired)
    payload = {
        "schema": SCHEMA,
        "status": STATUS,
        "warning": (
            "Hosted held-out timing is engineering evidence only; physical Ryzen "
            "reproduction/crossover remains mandatory before R5/R8 exit."
        ),
        "configuration": {
            "boards": dict(FROZEN_BOARDS),
            "range_combos_per_player": list(FROZEN_RANGE_COMBOS),
            "p0_phase": P0_PHASE,
            "p1_phase": P1_PHASE,
            "pot": POT,
            "bet_sizes": list(BET_SIZES),
            "seeds": list(FROZEN_SEEDS),
            "budget_seconds": FROZEN_BUDGET_SECONDS,
            "comparators": list(COMPARATORS),
            "external_variant": ExternalSamplingVariant.ES_CFR_PLUS_LINEAR.value,
            "ccs_variant": CCS_VARIANT,
            "chunk_contract": {
                "initial": INITIAL_CHUNK,
                "minimum": MIN_CHUNK,
                "maximum": MAX_CHUNK,
                "next_chunk": (
                    "ceil(cumulative_iterations / cumulative_train_seconds * "
                    "remaining_seconds), clipped to [1,4096]"
                ),
            },
            "acceptance": {
                "min_wins_per_support": MIN_WINS_PER_SUPPORT,
                "min_wins_overall": MIN_WINS_OVERALL,
                "ccs_mean_must_not_exceed_zero_each_support": True,
            },
        },
        "rows": rows,
        "summary_by_support_comparator": summary,
        "paired_ccs_vs_zero": paired,
        "frozen_decision": decision,
        "wall_seconds_total": time.perf_counter() - started,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
