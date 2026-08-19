from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from deepcash_core.cards import card_from_str, card_to_str
from deepcash_core.river_alternating_dcfr import (
    AlternatingVariant,
    advance_alternating_solver,
    alternating_solver_result,
    init_alternating_solver,
)
from deepcash_core.river_benchmark_fixtures import restriction_loss_bounds
from deepcash_core.river_lab import RiverGameSpec
from deepcash_core.river_representation_alternating_dcfr import (
    advance_alternating_representation_solver,
    alternating_representation_result,
    init_alternating_representation_solver,
)
from deepcash_core.river_representation_gen2 import (
    GEN2_REFERENCE_FRACTIONS,
    gen2_candidate_bucket_maps,
)
from deepcash_core.river_representation_lab import one_sided_bucket_maps
from deepcash_core.turn_river_exact_game import (
    advance_turn_river_solver,
    build_turn_river_game,
    conditioned_river_ranges,
    init_turn_river_solver,
    river_bet_sizes,
    river_geometry,
    turn_river_solver_result,
)
from deepcash_core.turn_river_public_state import build_turn_public_state


ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "deepcash_core" / "data" / "r4_production_representation_v1.json"
SCHEMA = "DEEPCASH_R6_POSTERIOR_RIVER_REPRESENTATION_BRIDGE_V1"
STATUS = "COMPLETE_POSTERIOR_BRIDGE_EVIDENCE_NOT_R6_PASS"
EXPECTED_PRODUCTION = "matchup_cluster8"
EXPECTED_ANCHOR = "equity8"
CANDIDATES = (EXPECTED_PRODUCTION, EXPECTED_ANCHOR)
VARIANT = AlternatingVariant.ALT_DCFR_150_0_2
SOURCE_RANGE_COMBOS = 12
SOURCE_P0_PHASE = 0.19
SOURCE_P1_PHASE = 0.67
SOURCE_POT = 100
SOURCE_STACK = 200
SOURCE_MIN_BET = 20
SOURCE_TURN_FRACTIONS = (0.5, 1.0)
SOURCE_ITERATIONS = 12
RIVER_ITERATIONS = 400
HISTORIES = ("CHECK_CHECK", "P0_BET_50_CALL", "P1_BET_50_CALL")
SOURCE_CASES = {
    "posterior_ahigh": {
        "turn_board": "Ah Kd 9c 4s",
        "river_cards": ("2h", "Tc"),
    },
    "posterior_connected": {
        "turn_board": "9h 8d 7c 3s",
        "river_cards": ("2d", "Qh"),
    },
}
EXPECTED_POSTERIOR_CELLS = len(SOURCE_CASES) * len(HISTORIES) * 2
EXPECTED_CANDIDATE_ROWS = EXPECTED_POSTERIOR_CELLS * len(CANDIDATES)


def load_production_freeze(path: Path = FREEZE_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "DEEPCASH_R4_PRODUCTION_REPRESENTATION_FREEZE_V1":
        raise ValueError("unexpected R4 production representation freeze schema")
    if payload.get("status") != "FROZEN":
        raise ValueError("R4 production representation is not frozen")
    if payload.get("representation") != EXPECTED_PRODUCTION:
        raise ValueError("R4 production representation drift")
    if payload.get("accuracy_anchor") != EXPECTED_ANCHOR:
        raise ValueError("R4 accuracy anchor drift")
    return payload


def build_source_game(case_name: str):
    if case_name not in SOURCE_CASES:
        raise ValueError(f"unknown frozen source case: {case_name}")
    case = SOURCE_CASES[case_name]
    turn = build_turn_public_state(
        board_text=str(case["turn_board"]),
        p0_phase=SOURCE_P0_PHASE,
        p1_phase=SOURCE_P1_PHASE,
        range_combos=SOURCE_RANGE_COMBOS,
        pot=SOURCE_POT,
        stack=SOURCE_STACK,
        min_bet=SOURCE_MIN_BET,
    )
    game = build_turn_river_game(
        turn,
        turn_fractions=SOURCE_TURN_FRACTIONS,
        river_fractions=GEN2_REFERENCE_FRACTIONS,
    )
    if game.turn_bet_sizes != (50, 100):
        raise RuntimeError(f"frozen turn geometry drifted: {game.turn_bet_sizes}")
    return game


def solve_source_policy(case_name: str, *, iterations: int = SOURCE_ITERATIONS):
    if iterations <= 0:
        raise ValueError("source iterations must be positive")
    game = build_source_game(case_name)
    state = init_turn_river_solver(game, VARIANT)
    started = time.perf_counter()
    advance_turn_river_solver(game, state, additional_iterations=iterations)
    train_seconds = time.perf_counter() - started
    result = turn_river_solver_result(game, state)
    return game, result.policy, {
        "iterations": result.iterations,
        "policy_ev": result.policy_ev,
        "infosets": result.infosets,
        "action_slots": result.action_slots,
        "train_seconds": train_seconds,
    }


def build_posterior_river_spec(
    game,
    policy,
    *,
    history: str,
    river_card_text: str,
) -> RiverGameSpec:
    if history not in HISTORIES:
        raise ValueError(f"history outside frozen bridge set: {history}")
    river_card = card_from_str(river_card_text)
    if river_card in game.turn_state.board:
        raise ValueError("frozen river card already appears on turn board")
    p0_range, p1_range = conditioned_river_ranges(
        game,
        policy,
        history=history,
        river_card=river_card,
    )
    pot, stack = river_geometry(game, history)
    bets = river_bet_sizes(game, history)
    if stack <= 0 or not bets:
        raise RuntimeError("frozen posterior bridge unexpectedly has no river decisions")
    spec = RiverGameSpec(
        board=(*game.turn_state.board, river_card),
        p0_range=p0_range,
        p1_range=p1_range,
        pot=pot,
        bet_sizes=bets,
    )
    spec.validate()
    return spec


def solve_exact_reference(spec: RiverGameSpec, *, iterations: int = RIVER_ITERATIONS):
    if iterations <= 0:
        raise ValueError("river iterations must be positive")
    state = init_alternating_solver(spec, VARIANT)
    advance_alternating_solver(spec, state, additional_iterations=iterations)
    return alternating_solver_result(spec, state)


def solve_one_sided_candidate(
    spec: RiverGameSpec,
    *,
    candidate: str,
    restricted_player: int,
    iterations: int = RIVER_ITERATIONS,
):
    if candidate not in CANDIDATES:
        raise ValueError(f"candidate outside frozen bridge pair: {candidate}")
    maps = gen2_candidate_bucket_maps(spec, candidate)
    one_sided = one_sided_bucket_maps(spec, maps, restricted_player)
    state = init_alternating_representation_solver(spec, one_sided, VARIANT)
    advance_alternating_representation_solver(
        spec,
        one_sided,
        state,
        additional_iterations=iterations,
    )
    return alternating_representation_result(spec, one_sided, state)


def action_slot_ratio(spec: RiverGameSpec, *, p0_buckets: int, p1_buckets: int) -> float:
    n_bets = len(spec.bet_sizes)
    slots_per_bucket = 1 + 3 * n_bets
    exact_slots = (len(spec.p0_range) + len(spec.p1_range)) * slots_per_bucket
    abstract_slots = (p0_buckets + p1_buckets) * slots_per_bucket
    return abstract_slots / float(exact_slots)


def run_posterior_cell(
    *,
    case_name: str,
    game,
    policy,
    history: str,
    river_card_text: str,
    reference_iterations: int = RIVER_ITERATIONS,
    candidate_iterations: int = RIVER_ITERATIONS,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    spec = build_posterior_river_spec(
        game,
        policy,
        history=history,
        river_card_text=river_card_text,
    )
    reference = solve_exact_reference(spec, iterations=reference_iterations)
    reference_width = (reference.br0_value - reference.br1_value) / float(spec.pot)
    if reference_width < -1e-12:
        raise RuntimeError("reference BR interval is negative")

    ref_row = {
        "case": case_name,
        "turn_board": " ".join(card_to_str(card) for card in game.turn_state.board),
        "history": history,
        "river_card": river_card_text,
        "river_board": " ".join(card_to_str(card) for card in spec.board),
        "river_pot": spec.pot,
        "river_stack": river_geometry(game, history)[1],
        "river_bet_sizes": list(spec.bet_sizes),
        "p0_posterior_combos": len(spec.p0_range),
        "p1_posterior_combos": len(spec.p1_range),
        "p0_posterior_weight": sum(float(combo.weight) for combo in spec.p0_range),
        "p1_posterior_weight": sum(float(combo.weight) for combo in spec.p1_range),
        "compatible_deals": len(
            [
                (i, j)
                for i, p0 in enumerate(spec.p0_range)
                for j, p1 in enumerate(spec.p1_range)
                if not set(p0.hole).intersection(p1.hole)
            ]
        ),
        "reference_iterations": reference.iterations,
        "reference_policy_ev": reference.policy_ev,
        "reference_br0": reference.br0_value,
        "reference_br1": reference.br1_value,
        "reference_exploitability_per_pot": reference.exploitability_per_pot,
        "reference_interval_width_per_pot": reference_width,
    }
    if ref_row["compatible_deals"] <= 0:
        raise RuntimeError("posterior river spec has no compatible private deals")

    rows: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        maps = gen2_candidate_bucket_maps(spec, candidate)
        maps.validate(spec)
        if maps.p0_bucket_count > 8 or maps.p1_bucket_count > 8:
            raise RuntimeError("frozen R4 candidate materialized more than eight buckets")
        p0_result = solve_one_sided_candidate(
            spec,
            candidate=candidate,
            restricted_player=0,
            iterations=candidate_iterations,
        )
        p1_result = solve_one_sided_candidate(
            spec,
            candidate=candidate,
            restricted_player=1,
            iterations=candidate_iterations,
        )
        bounds = restriction_loss_bounds(
            SimpleNamespace(br0_value=reference.br0_value, br1_value=reference.br1_value),
            p0_result,
            p1_result,
            spec.pot,
        )
        resolution = max(
            reference.br0_value - reference.br1_value,
            p0_result.br0_value - p0_result.br1_value,
            p1_result.br0_value - p1_result.br1_value,
        ) / float(spec.pot)
        rows.append(
            {
                "case": case_name,
                "history": history,
                "river_card": river_card_text,
                "candidate": candidate,
                "p0_buckets": maps.p0_bucket_count,
                "p1_buckets": maps.p1_bucket_count,
                "action_slot_ratio": action_slot_ratio(
                    spec,
                    p0_buckets=maps.p0_bucket_count,
                    p1_buckets=maps.p1_bucket_count,
                ),
                "candidate_iterations": candidate_iterations,
                "resolution_interval_per_pot": resolution,
                **bounds,
            }
        )
    return ref_row, rows


def classify_pairs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {
        (row["case"], row["history"], row["river_card"], row["candidate"]): row
        for row in rows
    }
    pairs: list[dict[str, Any]] = []
    nominal_wins_or_ties = 0
    unresolved_adverse = 0
    resolved_losses = 0
    for case_name, case in SOURCE_CASES.items():
        for history in HISTORIES:
            for river_card in case["river_cards"]:
                key = (case_name, history, river_card)
                prod = lookup[(*key, EXPECTED_PRODUCTION)]
                anchor = lookup[(*key, EXPECTED_ANCHOR)]
                adverse = float(prod["worst_loss_upper_per_pot"]) - float(
                    anchor["worst_loss_upper_per_pot"]
                )
                envelope = max(
                    float(prod["resolution_interval_per_pot"]),
                    float(anchor["resolution_interval_per_pot"]),
                )
                if adverse <= 0.0:
                    classification = "WIN_OR_TIE"
                    nominal_wins_or_ties += 1
                elif adverse <= envelope:
                    classification = "UNRESOLVED_ADVERSE"
                    unresolved_adverse += 1
                else:
                    classification = "RESOLVED_LOSS"
                    resolved_losses += 1
                pairs.append(
                    {
                        "case": case_name,
                        "history": history,
                        "river_card": river_card,
                        "matchup_minus_equity_loss_upper_per_pot": adverse,
                        "resolution_envelope_per_pot": envelope,
                        "classification": classification,
                    }
                )
    return {
        "pairs": pairs,
        "nominal_wins_or_ties": nominal_wins_or_ties,
        "unresolved_adverse": unresolved_adverse,
        "resolved_losses": resolved_losses,
    }


def summarize(rows: list[dict[str, Any]], pair_audit: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for candidate in CANDIDATES:
        selected = [row for row in rows if row["candidate"] == candidate]
        losses = [float(row["worst_loss_upper_per_pot"]) for row in selected]
        out[candidate] = {
            "cells": len(selected),
            "mean_loss_upper_per_pot": statistics.fmean(losses),
            "median_loss_upper_per_pot": statistics.median(losses),
            "worst_loss_upper_per_pot": max(losses),
            "mean_resolution_interval_per_pot": statistics.fmean(
                float(row["resolution_interval_per_pot"]) for row in selected
            ),
            "mean_action_slot_ratio": statistics.fmean(
                float(row["action_slot_ratio"]) for row in selected
            ),
        }
    mean_pass = (
        out[EXPECTED_PRODUCTION]["mean_loss_upper_per_pot"]
        <= out[EXPECTED_ANCHOR]["mean_loss_upper_per_pot"]
    )
    decision = (
        "PASS_TO_BOUNDED_LOCAL_RESOLVING_GATE"
        if mean_pass and pair_audit["resolved_losses"] == 0
        else "FAIL_POSTERIOR_REPRESENTATION_BRIDGE"
    )
    return {
        "candidates": out,
        "production_mean_no_greater_than_anchor": mean_pass,
        "resolved_pairwise_losses": pair_audit["resolved_losses"],
        "decision": decision,
    }


def validate_complete(
    references: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> None:
    if len(references) != EXPECTED_POSTERIOR_CELLS:
        raise RuntimeError(
            f"posterior reference completeness failure: {len(references)} != {EXPECTED_POSTERIOR_CELLS}"
        )
    if len(rows) != EXPECTED_CANDIDATE_ROWS:
        raise RuntimeError(
            f"posterior candidate completeness failure: {len(rows)} != {EXPECTED_CANDIDATE_ROWS}"
        )
    ref_ids = {(x["case"], x["history"], x["river_card"]) for x in references}
    row_ids = {
        (x["case"], x["history"], x["river_card"], x["candidate"])
        for x in rows
    }
    if len(ref_ids) != EXPECTED_POSTERIOR_CELLS:
        raise RuntimeError("duplicate/missing posterior reference identity")
    if len(row_ids) != EXPECTED_CANDIDATE_ROWS:
        raise RuntimeError("duplicate/missing posterior candidate identity")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run frozen R6 action-conditioned posterior river representation bridge v1"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("r6_posterior_river_representation_bridge_v1.json"),
    )
    args = parser.parse_args()

    freeze = load_production_freeze()
    started = time.perf_counter()
    references: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    source_summaries: dict[str, Any] = {}

    for case_name, case in SOURCE_CASES.items():
        print(f"[source] {case_name}", flush=True)
        game, policy, source_summary = solve_source_policy(case_name)
        source_summaries[case_name] = source_summary
        for history in HISTORIES:
            for river_card in case["river_cards"]:
                print(
                    f"[posterior] {case_name} history={history} river={river_card}",
                    flush=True,
                )
                reference, candidate_rows = run_posterior_cell(
                    case_name=case_name,
                    game=game,
                    policy=policy,
                    history=history,
                    river_card_text=river_card,
                )
                references.append(reference)
                rows.extend(candidate_rows)

    validate_complete(references, rows)
    pairs = classify_pairs(rows)
    summary = summarize(rows, pairs)
    payload = {
        "schema": SCHEMA,
        "status": STATUS,
        "configuration": {
            "r4_freeze_schema": freeze["schema"],
            "production_representation": freeze["representation"],
            "accuracy_anchor": freeze["accuracy_anchor"],
            "source_cases": SOURCE_CASES,
            "source_range_combos": SOURCE_RANGE_COMBOS,
            "source_p0_phase": SOURCE_P0_PHASE,
            "source_p1_phase": SOURCE_P1_PHASE,
            "source_pot": SOURCE_POT,
            "source_stack": SOURCE_STACK,
            "source_min_bet": SOURCE_MIN_BET,
            "source_turn_fractions": list(SOURCE_TURN_FRACTIONS),
            "source_iterations": SOURCE_ITERATIONS,
            "river_iterations": RIVER_ITERATIONS,
            "histories": list(HISTORIES),
            "variant": VARIANT.value,
            "resolution_rule": (
                "resolved loss iff matchup loss_upper - equity loss_upper > "
                "max(matchup resolution interval, equity resolution interval)"
            ),
        },
        "source_summaries": source_summaries,
        "references": references,
        "rows": rows,
        "pair_audit": pairs,
        "summary": summary,
        "wall_seconds_total": time.perf_counter() - started,
        "scope_warning": (
            "Posterior representation bridge only; does not mark R6 PASS or "
            "authorize R9."
        ),
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
