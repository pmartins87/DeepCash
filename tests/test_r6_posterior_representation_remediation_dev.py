from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_r6_posterior_representation_remediation_dev_v1.py"
_spec = importlib.util.spec_from_file_location("r6_posterior_remediation_dev", SCRIPT)
assert _spec is not None and _spec.loader is not None
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)


def test_reserved_heldout_precedes_diagnostic_and_is_not_consumed_set():
    heldout = runner.validate_reserved_heldout_exists()
    assert heldout["status"] == "RESERVED_UNSEEN_BEFORE_REMEDIATION_DIAGNOSTIC"
    assert heldout["expected_posterior_cells"] == 24
    heldout_turns = {item["turn_board"] for item in heldout["source_cases"].values()}
    consumed_turns = {item["turn_board"] for item in runner.SOURCE_CASES.values()}
    assert heldout_turns.isdisjoint(consumed_turns)


def test_candidate_family_is_preexisting_generation2_only():
    assert runner.CANDIDATES == (
        "matchup_cluster8",
        "equity8",
        "matchup_cluster4",
        "equity4_matchup2",
    )
    assert set(runner.CANDIDATES).issubset(set(runner.R4_GEN2_CANDIDATES))


def test_consumed_source_geometry_is_stable():
    for case_name in runner.SOURCE_CASES:
        game = runner.build_source_game(case_name)
        assert game.turn_bet_sizes == (50, 100)
        assert game.turn_state.pot == 100
        assert game.turn_state.stack == 200


def test_pairwise_resolution_rule_distinguishes_resolved_from_unresolved():
    rows = []
    for case_name, case in runner.SOURCE_CASES.items():
        for history in runner.HISTORIES:
            for river_card in case["river_cards"]:
                for candidate in runner.CANDIDATES:
                    loss = 0.01
                    resolution = 0.001
                    if candidate == "matchup_cluster8":
                        loss = 0.012
                    elif candidate == "matchup_cluster4":
                        loss = 0.0105
                    elif candidate == "equity4_matchup2":
                        loss = 0.009
                    rows.append({
                        "case": case_name,
                        "history": history,
                        "river_card": river_card,
                        "candidate": candidate,
                        "worst_loss_upper_per_pot": loss,
                        "resolution_interval_per_pot": resolution,
                    })
    pairwise = runner.pairwise_vs_anchor(rows)
    assert pairwise["matchup_cluster8"]["resolved_losses"] == 12
    assert pairwise["matchup_cluster4"]["resolved_losses"] == 0
    assert pairwise["matchup_cluster4"]["unresolved_adverse"] == 12
    assert pairwise["equity4_matchup2"]["win_or_tie"] == 12
