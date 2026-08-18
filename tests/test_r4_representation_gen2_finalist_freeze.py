from __future__ import annotations

import json
from pathlib import Path

import pytest

from deepcash_core.r4_representation_gen2_freeze import (
    Generation2FreezeError,
    load_generation2_finalist_freeze,
)

MANIFEST = Path("deepcash_core/data/r4_representation_generation2_finalists_v1.json")


def test_generation2_finalist_freeze_loads() -> None:
    data = load_generation2_finalist_freeze(MANIFEST)
    assert data["selection"]["finalists"] == [
        "equity8",
        "matchup_cluster8",
        "matchup_cluster4",
    ]
    assert data["heldout_v2"]["status"] == "PREPARED_NOT_RUN"
    assert data["heldout_v2"]["expected_materialized_bet_sizes"] == {
        "1": [25, 50, 100],
        "2": [25, 50, 100, 200],
        "4": [25, 50, 100, 200, 400],
    }


def test_generation2_finalist_freeze_rejects_candidate_drift(tmp_path: Path) -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["selection"]["finalists"] = ["equity8", "equity4_matchup2"]
    path = tmp_path / "drift.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Generation2FreezeError, match="finalist freeze drift"):
        load_generation2_finalist_freeze(path)


def test_generation2_finalist_freeze_rejects_heldout_coordinate_drift(tmp_path: Path) -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["heldout_v2"]["spr_to_stack"]["4"] = 200
    path = tmp_path / "drift.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Generation2FreezeError, match="held-out-v2 coordinates drift"):
        load_generation2_finalist_freeze(path)
