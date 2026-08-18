from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from deepcash_core.river_representation_gen2_fixtures import gen2_board_registry

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_r4_ryzen_instrumentation_repair.py"
SPEC = importlib.util.spec_from_file_location("r4_ryzen_instrumentation_repair", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_repair_config_is_frozen_and_valid() -> None:
    config = runner.load_json(runner.DEFAULT_CONFIG)
    runner.validate_config(config)
    assert config["candidates"] == ["matchup_cluster8", "equity8", "matchup_cluster4"]
    assert config["board_set"] == "heldout_v2"
    assert config["spr_to_stack"] == {"1": 100, "2": 200, "4": 400}
    assert config["warmup_iterations_each_state"] == 100


def test_local_memory_instrumentation_returns_positive_peak() -> None:
    metrics = runner.validate_instrumentation(strict_windows=False)
    assert int(metrics["memory"]["peak_working_set_bytes"]) > 0


def test_repair_worker_emits_memory_and_affinity_fields(tmp_path: Path) -> None:
    board_name, board_text = next(iter(gen2_board_registry("dev").items()))
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
        "warmup_iterations_each_state": 1,
    }
    output = tmp_path / "repair.json"
    runner.worker_run(payload, output)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["schema"] == "DEEPCASH_R4_RYZEN_INSTRUMENTATION_REPAIR_CELL_V1"
    assert result["candidate"] == "matchup_cluster4"
    assert result["peak_working_set_bytes"] > 0
    assert result["working_set_bytes"] > 0
    assert result["joint_action_slots"] > 0
