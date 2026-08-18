from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from deepcash_core.river_alternating_dcfr import AlternatingVariant

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_r4_r5_r6_compatibility.py"
SPEC = importlib.util.spec_from_file_location("r4_r5_r6_compatibility_runner", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_frozen_compatibility_config_is_valid_and_finite() -> None:
    config = runner.load_json(runner.DEFAULT_CONFIG)
    runner.validate_config(config)
    assert config["solver_variant"] == AlternatingVariant.ALT_DCFR_150_0_2.value
    assert config["candidates"] == ["matchup_cluster8", "equity8"]
    assert len(config["turn_boards"]) == 4
    assert config["river_children_per_turn_state"] == 2
    assert config["reference_iterations_per_river_child"] == 600
    assert config["candidate_wall_budget_seconds_per_river_child"] == 3.0
    assert config["parallel_candidate_workers"] == 1


def test_river_child_selection_is_deterministic_and_candidate_independent() -> None:
    config = runner.load_json(runner.DEFAULT_CONFIG)
    phase = config["phases"][0]
    turn_name, turn_text = next(iter(config["turn_boards"].items()))
    state = runner.build_turn_state(config, turn_text, phase, 100)
    first = runner.selected_children(config, state)
    second = runner.selected_children(config, state)
    assert [(x.river_card, x.chance_mass) for x in first] == [
        (x.river_card, x.chance_mass) for x in second
    ]
    assert len(first) == 2
    all_children = sorted(
        runner.enumerate_river_children(state),
        key=lambda child: (-child.chance_mass, child.river_card),
    )
    assert [x.river_card for x in first] == [x.river_card for x in all_children[:2]]
    assert turn_name


def test_worker_emits_compatibility_cell_and_checkpoint(tmp_path: Path) -> None:
    config = runner.load_json(runner.DEFAULT_CONFIG)
    tiny = json.loads(json.dumps(config))
    tiny["candidate_wall_budget_seconds_per_river_child"] = 0.001
    tiny["candidate_chunk_iterations"] = 1
    phase = tiny["phases"][0]
    turn_name, turn_text = next(iter(tiny["turn_boards"].items()))
    state = runner.build_turn_state(tiny, turn_text, phase, 100)
    child = runner.selected_children(tiny, state)[0]
    reference = runner.train_exact_reference(child.spec, 2)
    payload = {
        "cell_index": 0,
        "turn_board": turn_name,
        "turn_board_text": turn_text,
        "phase": phase["name"],
        "phase_config": phase,
        "spr": 1.0,
        "stack": 100,
        "river_card": child.river_card,
        "candidate": "matchup_cluster8",
        "reference": reference,
        "config": tiny,
    }
    output = tmp_path / "cell.json"
    runner.worker_run(payload, output)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["schema"] == "DEEPCASH_R4_R5_R6_COMPATIBILITY_CELL_V1"
    assert result["candidate"] == "matchup_cluster8"
    assert result["solver_variant"] == AlternatingVariant.ALT_DCFR_150_0_2.value
    assert result["iterations_each_state"] >= 1
    assert result["train_wall_seconds"] > 0.0
    assert result["peak_working_set_bytes"] > 0
    assert result["checkpoint_bytes"] > 0
    assert output.with_suffix(".checkpoint.json").exists()
