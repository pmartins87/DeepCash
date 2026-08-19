from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_r5_equal_wallclock_scaling_v1.py"
SPEC = importlib.util.spec_from_file_location("r5_equal_wallclock_scaling_runner", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_frozen_scaling_contract_matches_precommit() -> None:
    assert runner.SCHEMA == "DEEPCASH_R5_EQUAL_WALLCLOCK_SCALING_V1"
    assert runner.COMPARATORS == (
        "ES_ZERO",
        "ES_TABULAR_RUNNING",
        "CCS_CFR_PLUS_LINEAR",
        "ES_INFOSET_EXACT",
    )
    assert runner.FROZEN_BOARDS == ("A_high_dry", "four_straight")
    assert runner.FROZEN_RANGE_COMBOS == (8, 24, 48)
    assert runner.FROZEN_SEEDS == (101, 211, 307)
    assert runner.FROZEN_BUDGETS == (1.0, 5.0, 15.0)
    assert runner.P0_PHASE == pytest.approx(0.13)
    assert runner.P1_PHASE == pytest.approx(0.61)
    assert runner.POT == 100
    assert runner.BET_SIZES == (25, 50, 100)
    assert runner.INITIAL_CHUNK == 64
    assert runner.MIN_CHUNK == 1
    assert runner.MAX_CHUNK == 4096


def test_dynamic_chunk_contract_is_bounded_and_deterministic() -> None:
    assert runner.next_chunk_iterations(
        completed_iterations=0,
        cumulative_train_seconds=0.0,
        remaining_seconds=1.0,
    ) == 64
    assert runner.next_chunk_iterations(
        completed_iterations=100,
        cumulative_train_seconds=2.0,
        remaining_seconds=3.0,
    ) == 150
    assert runner.next_chunk_iterations(
        completed_iterations=100000,
        cumulative_train_seconds=0.01,
        remaining_seconds=20.0,
    ) == 4096
    assert runner.next_chunk_iterations(
        completed_iterations=1,
        cumulative_train_seconds=100.0,
        remaining_seconds=0.001,
    ) == 1


def test_frozen_spec_has_exact_requested_geometry() -> None:
    spec = runner.build_spec("A_high_dry", 8)
    assert len(spec.board) == 5
    assert len(spec.p0_range) == 8
    assert len(spec.p1_range) == 8
    assert spec.pot == 100
    assert spec.bet_sizes == (25, 50, 100)
    with pytest.raises(ValueError, match="board outside frozen"):
        runner.build_spec("paired", 8)
    with pytest.raises(ValueError, match="range support outside frozen"):
        runner.build_spec("A_high_dry", 16)


def test_zero_smoke_cell_crosses_each_budget_and_records_exact_evaluation() -> None:
    rows = runner.run_comparator_cell(
        board_name="A_high_dry",
        range_combos=8,
        seed=101,
        comparator="ES_ZERO",
        budgets=(0.001, 0.002),
    )
    assert len(rows) == 2
    assert [row["requested_budget_seconds"] for row in rows] == [0.001, 0.002]
    assert rows[0]["cumulative_train_seconds"] >= 0.001
    assert rows[1]["cumulative_train_seconds"] >= rows[0]["cumulative_train_seconds"]
    assert rows[0]["iterations"] > 0
    assert rows[1]["iterations"] >= rows[0]["iterations"]
    assert rows[0]["terminal_visits"] > 0
    assert rows[0]["evaluation_seconds"] >= 0.0
    assert rows[0]["exploitability_per_pot"] >= 0.0
    assert rows[0]["baseline_coverage"] is None


def test_tabular_smoke_records_legal_baseline_coverage() -> None:
    rows = runner.run_comparator_cell(
        board_name="A_high_dry",
        range_combos=8,
        seed=101,
        comparator="ES_TABULAR_RUNNING",
        budgets=(0.001,),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["baseline_slots"] > 0
    assert 0 < row["baseline_visited_slots"] <= row["baseline_slots"]
    assert row["baseline_updates"] > 0
    assert 0.0 < row["baseline_coverage"] <= 1.0
