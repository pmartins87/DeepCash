from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from deepcash_core.river_representation_gen2_fixtures import gen2_board_registry


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_r4_ryzen_equal_wallclock.py"
SPEC = importlib.util.spec_from_file_location("r4_ryzen_runner", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_frozen_physical_config_is_valid() -> None:
    config = runner.load_json(runner.DEFAULT_CONFIG)
    runner.validate_config(config)
    assert config["candidates"] == ["matchup_cluster8", "equity8", "matchup_cluster4"]
    assert config["candidate_wall_budget_seconds_per_board_phase_spr"] == 20.0
    assert config["parallel_candidate_workers"] == 1


def test_worker_emits_physical_cell_and_checkpoint(tmp_path: Path) -> None:
    board_name, board_text = next(iter(gen2_board_registry("dev").items()))
    spec = runner.build_spec(
        board_text=board_text,
        p0_phase=0.19,
        p1_phase=0.47,
        range_combos=4,
        pot=100,
        stack=100,
        min_bet=20,
    )
    reference = runner.train_exact_reference(spec, 1)
    payload = {
        "cell_index": 0,
        "phase": "TEST",
        "board": board_name,
        "board_text": board_text,
        "candidate": "matchup_cluster4",
        "p0_phase": 0.19,
        "p1_phase": 0.47,
        "pot": 100,
        "stack": 100,
        "range_combos": 4,
        "min_bet": 20,
        "budget_seconds": 0.001,
        "chunk_iterations": 1,
        "reference": reference,
    }
    output = tmp_path / "cell.json"
    runner.worker_run(payload, output)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["schema"] == "DEEPCASH_R4_RYZEN_EQUAL_WALLCLOCK_CELL_V1"
    assert result["candidate"] == "matchup_cluster4"
    assert result["iterations_each_state"] >= 1
    assert result["train_wall_seconds"] > 0.0
    assert result["checkpoint_bytes"] > 0
    assert output.with_suffix(".checkpoint.json").exists()
