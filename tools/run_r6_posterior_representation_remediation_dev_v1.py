from __future__ import annotations

import argparse
import json
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
    R4_GEN2_CANDIDATES,
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
HELDOUT_V2 = ROOT / "deepcash_core" / "data" / "r6_posterior_representation_heldout_v2.json"
SCHEMA = "DEEPCASH_R6_POSTERIOR_REPRESENTATION_REMEDIATION_DEV_V1"
STATUS = "COMPLETE_CONSUMED_DEVELOPMENT_DIAGNOSTIC_NOT_HELDOUT"
VARIANT = AlternatingVariant.ALT_DCFR_150_0_2
CANDIDATES = (
    "matchup_cluster8",
    "equity8",
    "matchup_cluster4",
    "equity4_matchup2",
)
ANCHOR = "equity8"
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
EXPECTED_POSTERIOR_CELLS = 12
EXPECTED_ROWS = EXPECTED_POSTERIOR_CELLS * len(CANDIDATES)


def validate_reserved_heldout_exists(path: Path = HELDOUT_V2) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "DEEPCASH_R6_POSTERIOR_REPRESENTATION_HELDOUT_V2_CONFIG":
        raise ValueError("unexpected reserved held-out schema")
    if payload.get("status") != "RESERVED_UNSEEN_BEFORE_REMEDIATION_DIAGNOSTIC":
        raise ValueError("fresh posterior held-out is not reserved before diagnostic")
    if int(payload.get("expected_posterior_cells", 0)) != 24:
        raise ValueError("reserved posterior held-out cell count drift")
    if tuple(payload.get("candidate_family_boundary", [])) != CANDIDATES:
        raise ValueError("reserved remediation candidate boundary drift")
    return payload


def build_source_game(case_name: str):
    if case_name not in SOURCE_CASES:
        raise ValueError(f"unknown consumed source case: {case_name}")
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
        raise RuntimeError(f"consumed source turn geometry drifted: {game.turn_bet_sizes}")
    return game


def solve_source_policy(case_name: str):
    game = build_source_game(case_name)
    state = init_turn_river_solver(game, VARIANT)
    started = time.perf_counter()
    advance_turn_river_solver(game, state, additional_iterations=SOURCE_ITERATIONS)
    train_seconds = time.perf_counter() - started
    result = turn_river_solver_result(game, state)
    return game, result.policy, {
        "iterations": result.iterations,
        "policy_ev": result.policy_ev,
        "infosets": result.infosets,
        "action_slots": result.action_slots,
        "train_seconds": train_seconds,
    }


def build_posterior_spec(game, policy, *, history: str, river_card_text: str) -> RiverGameSpec:
    if history not in HISTORIES:
        raise ValueError("history outside consumed diagnostic set")
    river_card = card_from_str(river_card_text)
    p0_range, p1_range = conditioned_river_ranges(
        game,
        policy,
        history=history,
        river_card=river_card,
    )
    pot, stack = river_geometry(game, history)
    bets = river_bet_sizes(game, history)
    if stack <= 0 or not bets:
        raise RuntimeError("consumed posterior cell unexpectedly has no river decision")
    return RiverGameSpec(
        board=(*game.turn_state.board, river_card),
        p0_range=p0_range,
        p1_range=p1_range,
        pot=pot,
        bet_sizes=bets,
    )


def solve_exact_reference(spec: RiverGameSpec):
    state = init_alternating_solver(spec, VARIANT)
    advance_alternating_solver(spec, state, additional_iterations=RIVER_ITERATIONS)
    return alternating_solver_result(spec, state)


def solve_one_sided(spec: RiverGameSpec, candidate: str, restricted_player: int):
    if candidate not in CANDIDATES or candidate not in R4_GEN2_CANDIDATES:
        raise ValueError("candidate outside pre-existing Generation-2 boundary")
    maps = gen2_candidate_bucket_maps(spec, candidate)
    one_sided = one_sided_bucket_maps(spec, maps, restricted_player)
    state = init_alternating_representation_solver(spec, one_sided, VARIANT)
    advance_alternating_representation_solver(
        spec,
        one_sided,
        state,
        additional_iterations=RIVER_ITERATIONS,
    )
    return alternating_representation_result(spec, one_sided, state)


def action_slot_ratio(spec: RiverGameSpec, *, p0_buckets: int, p1_buckets: int) -> float:
    n_bets = len(spec.bet_sizes)
    slots_per_bucket = 1 + 3 * n_bets
    exact_slots = (len(spec.p0_range) + len(spec.p1_range)) * slots_per_bucket
    abstract_slots = (p0_buckets + p1_buckets) * slots_per_bucket
    return abstract_slots / float(exact_slots)


def run_cell(*, case_name: str, game, policy, history: str, river_card_text: str):
    spec = build_posterior_spec(
        game,
        policy,
        history=history,
        river_card_text=river_card_text,
    )
    reference = solve_exact_reference(spec)
    reference_width = (reference.br0_value - reference.br1_value) / float(spec.pot)
    ref_row = {
        "case": case_name,
        "history": history,
        "river_card": river_card_text,
        "river_board": " ".join(card_to_str(card) for card in spec.board),
        "river_pot": spec.pot,
        "river_bet_sizes": list(spec.bet_sizes),
        "p0_posterior_combos": len(spec.p0_range),
        "p1_posterior_combos": len(spec.p1_range),
        "reference_exploitability_per_pot": reference.exploitability_per_pot,
        "reference_interval_width_per_pot": reference_width,
    }

    rows: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        maps = gen2_candidate_bucket_maps(spec, candidate)
        p0_result = solve_one_sided(spec, candidate, 0)
        p1_result = solve_one_sided(spec, candidate, 1)
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
        rows.append({
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
            "resolution_interval_per_pot": resolution,
            **bounds,
        })
    return ref_row, rows


def validate_complete(references: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    if len(references) != EXPECTED_POSTERIOR_CELLS:
        raise RuntimeError("consumed diagnostic reference completeness failure")
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError("consumed diagnostic candidate completeness failure")
    if len({(x["case"], x["history"], x["river_card"]) for x in references}) != EXPECTED_POSTERIOR_CELLS:
        raise RuntimeError("duplicate/missing consumed diagnostic reference identity")
    if len({(x["case"], x["history"], x["river_card"], x["candidate"]) for x in rows}) != EXPECTED_ROWS:
        raise RuntimeError("duplicate/missing consumed diagnostic candidate identity")


def pairwise_vs_anchor(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {
        (row["case"], row["history"], row["river_card"], row["candidate"]): row
        for row in rows
    }
    out: dict[str, Any] = {}
    for candidate in CANDIDATES:
        if candidate == ANCHOR:
            continue
        win_or_tie = 0
        unresolved_adverse = 0
        resolved_losses = 0
        diffs: list[float] = []
        cells: list[dict[str, Any]] = []
        for case_name, case in SOURCE_CASES.items():
            for history in HISTORIES:
                for river_card in case["river_cards"]:
                    cand = lookup[(case_name, history, river_card, candidate)]
                    anchor = lookup[(case_name, history, river_card, ANCHOR)]
                    diff = float(cand["worst_loss_upper_per_pot"]) - float(
                        anchor["worst_loss_upper_per_pot"]
                    )
                    envelope = max(
                        float(cand["resolution_interval_per_pot"]),
                        float(anchor["resolution_interval_per_pot"]),
                    )
                    if diff <= 0.0:
                        classification = "WIN_OR_TIE"
                        win_or_tie += 1
                    elif diff <= envelope:
                        classification = "UNRESOLVED_ADVERSE"
                        unresolved_adverse += 1
                    else:
                        classification = "RESOLVED_LOSS"
                        resolved_losses += 1
                    diffs.append(diff)
                    cells.append({
                        "case": case_name,
                        "history": history,
                        "river_card": river_card,
                        "candidate_minus_equity8_loss_upper_per_pot": diff,
                        "resolution_envelope_per_pot": envelope,
                        "classification": classification,
                    })
        out[candidate] = {
            "cells": cells,
            "win_or_tie": win_or_tie,
            "unresolved_adverse": unresolved_adverse,
            "resolved_losses": resolved_losses,
            "mean_difference_vs_equity8": statistics.fmean(diffs),
            "median_difference_vs_equity8": statistics.median(diffs),
        }
    return out


def summarize(rows: list[dict[str, Any]], pairwise: dict[str, Any]) -> dict[str, Any]:
    candidates: dict[str, Any] = {}
    for candidate in CANDIDATES:
        selected = [row for row in rows if row["candidate"] == candidate]
        losses = [float(row["worst_loss_upper_per_pot"]) for row in selected]
        candidates[candidate] = {
            "cells": len(selected),
            "mean_loss_upper_per_pot": statistics.fmean(losses),
            "median_loss_upper_per_pot": statistics.median(losses),
            "worst_loss_upper_per_pot": max(losses),
            "mean_action_slot_ratio": statistics.fmean(
                float(row["action_slot_ratio"]) for row in selected
            ),
            "resolved_losses_vs_equity8": (
                0 if candidate == ANCHOR else int(pairwise[candidate]["resolved_losses"])
            ),
        }
    ranking = sorted(
        CANDIDATES,
        key=lambda name: (
            candidates[name]["resolved_losses_vs_equity8"],
            candidates[name]["mean_loss_upper_per_pot"],
            candidates[name]["mean_action_slot_ratio"],
            name,
        ),
    )
    return {
        "candidates": candidates,
        "development_ranking_only": ranking,
        "next_gate": "AUDIT_AND_FREEZE_AT_MOST_TWO_FINALISTS_BEFORE_RESERVED_HELDOUT_V2",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run consumed-cell R6 posterior remediation diagnostic v1")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("r6_posterior_representation_remediation_dev_v1.json"),
    )
    args = parser.parse_args()

    reserved = validate_reserved_heldout_exists()
    started = time.perf_counter()
    references: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    source_summaries: dict[str, Any] = {}

    for case_name, case in SOURCE_CASES.items():
        print(f"[consumed source] {case_name}", flush=True)
        game, policy, source_summary = solve_source_policy(case_name)
        source_summaries[case_name] = source_summary
        for history in HISTORIES:
            for river_card in case["river_cards"]:
                print(
                    f"[diagnostic] {case_name} history={history} river={river_card}",
                    flush=True,
                )
                ref, candidate_rows = run_cell(
                    case_name=case_name,
                    game=game,
                    policy=policy,
                    history=history,
                    river_card_text=river_card,
                )
                references.append(ref)
                rows.extend(candidate_rows)

    validate_complete(references, rows)
    pairwise = pairwise_vs_anchor(rows)
    summary = summarize(rows, pairwise)
    payload = {
        "schema": SCHEMA,
        "status": STATUS,
        "consumed_source_scope": SOURCE_CASES,
        "candidate_family": list(CANDIDATES),
        "accuracy_anchor": ANCHOR,
        "reserved_heldout_v2_schema": reserved["schema"],
        "reserved_heldout_v2_status": reserved["status"],
        "source_summaries": source_summaries,
        "references": references,
        "rows": rows,
        "pairwise_vs_equity8": pairwise,
        "summary": summary,
        "wall_seconds_total": time.perf_counter() - started,
        "scope_warning": (
            "Consumed-cell development diagnostic only. These numerical cells cannot "
            "serve as the reserved held-out v2 acceptance set."
        ),
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
