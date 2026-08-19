from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from deepcash_core.river_benchmark_fixtures import board_registry


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_r5_heldout_sampled_finalists_v1.py"
SPEC = importlib.util.spec_from_file_location("r5_heldout_sampled_finalists", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def synthetic_rows(*, ccs: float = 0.01, zero: float = 0.02):
    rows = []
    for board in runner.FROZEN_BOARDS:
        for support in runner.FROZEN_RANGE_COMBOS:
            for seed in runner.FROZEN_SEEDS:
                for comparator in runner.COMPARATORS:
                    rows.append(
                        {
                            "board": board,
                            "range_combos_per_player": support,
                            "seed": seed,
                            "comparator": comparator,
                            "exploitability_per_pot": (
                                ccs if comparator == "CCS_CFR_PLUS_LINEAR" else zero
                            ),
                            "cumulative_train_seconds": 15.0,
                            "iterations_per_second": 100.0,
                            "terminal_visits_per_second": 1000.0,
                            "timing_quality_flag": False,
                        }
                    )
    return rows


def test_frozen_heldout_coordinates_are_exact_and_do_not_overlap_existing_registry():
    assert runner.FROZEN_BOARDS == {
        "ace_low_mixed_r5ho": "As 7c 5d 3h 2s",
        "king_broadway_mixed_r5ho": "Kc Qs Td 6h 2c",
        "paired_jacks_r5ho": "Jh Jc 8s 5d 3c",
        "three_diamond_connected_r5ho": "9d 8d 6c 4s 2d",
    }
    assert runner.FROZEN_RANGE_COMBOS == (8, 24, 48)
    assert runner.FROZEN_SEEDS == (401, 503, 607)
    assert runner.COMPARATORS == ("ES_ZERO", "CCS_CFR_PLUS_LINEAR")
    assert runner.FROZEN_BUDGET_SECONDS == 15.0
    assert runner.P0_PHASE == 0.27
    assert runner.P1_PHASE == 0.73
    existing = set(board_registry("all").values())
    assert not existing.intersection(runner.FROZEN_BOARDS.values())


def test_chunk_contract_is_bounded_and_deterministic():
    assert runner.next_chunk_iterations(
        completed_iterations=0,
        cumulative_train_seconds=0.0,
        remaining_seconds=15.0,
    ) == 64
    assert runner.next_chunk_iterations(
        completed_iterations=100,
        cumulative_train_seconds=1.0,
        remaining_seconds=2.0,
    ) == 200
    assert runner.next_chunk_iterations(
        completed_iterations=100000,
        cumulative_train_seconds=1.0,
        remaining_seconds=15.0,
    ) == runner.MAX_CHUNK
    assert runner.next_chunk_iterations(
        completed_iterations=1,
        cumulative_train_seconds=100.0,
        remaining_seconds=0.001,
    ) == runner.MIN_CHUNK


def test_complete_artifact_and_frozen_decision_pass_on_clear_ccs_win():
    rows = synthetic_rows()
    runner.validate_full_artifact(rows)
    summary = runner.summarize(rows)
    paired = runner.paired_ccs_vs_zero(rows)
    decision = runner.frozen_decision(rows, summary, paired)

    assert paired["overall"]["wins"] == 36
    assert decision["provisional_decision"] == "PASS_TO_PHYSICAL_RYZEN_GATE"
    assert decision["overall_paired_wins_pass"] is True
    assert all(
        check["ccs_mean_no_greater_than_zero"]
        and check["paired_wins_pass"]
        for check in decision["support_checks"].values()
    )


def test_frozen_decision_fails_if_one_support_reverses():
    rows = synthetic_rows()
    for row in rows:
        if (
            row["range_combos_per_player"] == 48
            and row["comparator"] == "CCS_CFR_PLUS_LINEAR"
        ):
            row["exploitability_per_pot"] = 0.03
    summary = runner.summarize(rows)
    paired = runner.paired_ccs_vs_zero(rows)
    decision = runner.frozen_decision(rows, summary, paired)

    assert decision["support_checks"]["48"]["ccs_mean_no_greater_than_zero"] is False
    assert decision["support_checks"]["48"]["paired_wins_pass"] is False
    assert decision["provisional_decision"] == "FAIL_STRATEGIC_GENERALIZATION"


def test_timing_flags_require_review_even_when_strategy_passes():
    rows = synthetic_rows()
    rows[0]["timing_quality_flag"] = True
    summary = runner.summarize(rows)
    paired = runner.paired_ccs_vs_zero(rows)
    decision = runner.frozen_decision(rows, summary, paired)
    assert decision["timing_quality_flags"] == 1
    assert decision["provisional_decision"] == "TIMING_REVIEW_REQUIRED"


def test_incomplete_or_duplicate_artifact_fails_closed():
    rows = synthetic_rows()
    with pytest.raises(RuntimeError, match="incomplete"):
        runner.validate_full_artifact(rows[:-1])

    duplicated = list(rows)
    duplicated[-1] = dict(duplicated[0])
    with pytest.raises(RuntimeError, match="duplicate/missing"):
        runner.validate_full_artifact(duplicated)


def test_tiny_real_cell_emits_exact_metrics():
    row = runner.run_cell(
        board_name="ace_low_mixed_r5ho",
        range_combos=8,
        seed=401,
        comparator="ES_ZERO",
        budget_seconds=0.001,
    )
    assert row["board"] == "ace_low_mixed_r5ho"
    assert row["range_combos_per_player"] == 8
    assert row["seed"] == 401
    assert row["comparator"] == "ES_ZERO"
    assert row["iterations"] > 0
    assert row["terminal_visits"] > 0
    assert row["cumulative_train_seconds"] >= 0.001
    assert row["evaluation_seconds"] > 0.0
    assert row["exploitability_per_pot"] >= 0.0
