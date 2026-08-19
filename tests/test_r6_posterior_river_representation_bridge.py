from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from deepcash_core.river_representation_gen2 import gen2_candidate_bucket_maps


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_r6_posterior_river_representation_bridge_v1.py"
SPEC = importlib.util.spec_from_file_location("r6_posterior_bridge", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_bridge_is_bound_to_immutable_r4_production_identity():
    freeze = runner.load_production_freeze()
    assert freeze["status"] == "FROZEN"
    assert freeze["representation"] == "matchup_cluster8"
    assert freeze["accuracy_anchor"] == "equity8"
    assert runner.CANDIDATES == ("matchup_cluster8", "equity8")


def test_frozen_source_geometry_and_coordinates_are_exact():
    assert runner.SOURCE_RANGE_COMBOS == 12
    assert runner.SOURCE_ITERATIONS == 12
    assert runner.RIVER_ITERATIONS == 400
    assert runner.HISTORIES == (
        "CHECK_CHECK",
        "P0_BET_50_CALL",
        "P1_BET_50_CALL",
    )
    assert runner.EXPECTED_POSTERIOR_CELLS == 12
    assert runner.EXPECTED_CANDIDATE_ROWS == 24

    game = runner.build_source_game("posterior_ahigh")
    assert game.turn_state.pot == 100
    assert game.turn_state.stack == 200
    assert game.turn_bet_sizes == (50, 100)
    assert len(game.turn_state.p0_range) == 12
    assert len(game.turn_state.p1_range) == 12


def test_exact_source_policy_deterministically_generates_action_conditioned_river_specs():
    game1, policy1, summary1 = runner.solve_source_policy("posterior_ahigh", iterations=1)
    game2, policy2, summary2 = runner.solve_source_policy("posterior_ahigh", iterations=1)
    assert policy1 == policy2
    assert summary1["iterations"] == summary2["iterations"] == 1

    checked = runner.build_posterior_river_spec(
        game1,
        policy1,
        history="CHECK_CHECK",
        river_card_text="2h",
    )
    called = runner.build_posterior_river_spec(
        game1,
        policy1,
        history="P0_BET_50_CALL",
        river_card_text="2h",
    )
    assert checked.pot == 100
    assert checked.bet_sizes == (25, 50, 100, 200)
    assert called.pot == 200
    assert called.bet_sizes == (50, 100, 150)
    assert 0 < len(checked.p0_range) <= 12
    assert 0 < len(checked.p1_range) <= 12
    assert 0 < len(called.p0_range) <= 12
    assert 0 < len(called.p1_range) <= 12
    assert max(len(checked.p0_range), len(checked.p1_range)) > 8

    maps = gen2_candidate_bucket_maps(checked, "matchup_cluster8")
    assert maps.p0_bucket_count <= 8
    assert maps.p1_bucket_count <= 8
    assert runner.action_slot_ratio(
        checked,
        p0_buckets=maps.p0_bucket_count,
        p1_buckets=maps.p1_bucket_count,
    ) < 1.0


def synthetic_rows(*, production_loss: float, anchor_loss: float, resolution: float):
    rows = []
    for case_name, case in runner.SOURCE_CASES.items():
        for history in runner.HISTORIES:
            for river_card in case["river_cards"]:
                for candidate in runner.CANDIDATES:
                    rows.append(
                        {
                            "case": case_name,
                            "history": history,
                            "river_card": river_card,
                            "candidate": candidate,
                            "worst_loss_upper_per_pot": (
                                production_loss
                                if candidate == runner.EXPECTED_PRODUCTION
                                else anchor_loss
                            ),
                            "resolution_interval_per_pot": resolution,
                            "action_slot_ratio": 0.8,
                        }
                    )
    return rows


def test_resolution_rule_distinguishes_unresolved_adverse_from_resolved_loss():
    unresolved = synthetic_rows(
        production_loss=0.0011,
        anchor_loss=0.0010,
        resolution=0.0002,
    )
    audit = runner.classify_pairs(unresolved)
    assert audit["resolved_losses"] == 0
    assert audit["unresolved_adverse"] == 12

    resolved = synthetic_rows(
        production_loss=0.0014,
        anchor_loss=0.0010,
        resolution=0.0002,
    )
    audit = runner.classify_pairs(resolved)
    assert audit["resolved_losses"] == 12
    assert audit["unresolved_adverse"] == 0


def test_frozen_summary_requires_mean_advantage_and_zero_resolved_losses():
    winning = synthetic_rows(
        production_loss=0.0005,
        anchor_loss=0.0010,
        resolution=0.0001,
    )
    audit = runner.classify_pairs(winning)
    summary = runner.summarize(winning, audit)
    assert summary["production_mean_no_greater_than_anchor"] is True
    assert summary["resolved_pairwise_losses"] == 0
    assert summary["decision"] == "PASS_TO_BOUNDED_LOCAL_RESOLVING_GATE"

    losing = synthetic_rows(
        production_loss=0.0015,
        anchor_loss=0.0010,
        resolution=0.0001,
    )
    audit = runner.classify_pairs(losing)
    summary = runner.summarize(losing, audit)
    assert summary["decision"] == "FAIL_POSTERIOR_REPRESENTATION_BRIDGE"


def test_complete_artifact_validation_fails_closed():
    references = []
    rows = synthetic_rows(
        production_loss=0.0005,
        anchor_loss=0.0010,
        resolution=0.0001,
    )
    for case_name, case in runner.SOURCE_CASES.items():
        for history in runner.HISTORIES:
            for river_card in case["river_cards"]:
                references.append(
                    {"case": case_name, "history": history, "river_card": river_card}
                )
    runner.validate_complete(references, rows)

    with pytest.raises(RuntimeError, match="reference completeness failure"):
        runner.validate_complete(references[:-1], rows)
    with pytest.raises(RuntimeError, match="candidate completeness failure"):
        runner.validate_complete(references, rows[:-1])


def test_tiny_real_posterior_cell_emits_one_row_per_frozen_candidate():
    game, policy, _ = runner.solve_source_policy("posterior_connected", iterations=1)
    reference, rows = runner.run_posterior_cell(
        case_name="posterior_connected",
        game=game,
        policy=policy,
        history="CHECK_CHECK",
        river_card_text="2d",
        reference_iterations=2,
        candidate_iterations=2,
    )
    assert reference["compatible_deals"] > 0
    assert reference["reference_iterations"] == 2
    assert {row["candidate"] for row in rows} == set(runner.CANDIDATES)
    for row in rows:
        assert row["p0_buckets"] <= 8
        assert row["p1_buckets"] <= 8
        assert row["worst_loss_upper_per_pot"] >= 0.0
        assert row["resolution_interval_per_pot"] >= 0.0
