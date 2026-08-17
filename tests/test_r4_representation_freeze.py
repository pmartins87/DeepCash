import json

import pytest

from deepcash_core.r4_representation_freeze import (
    RepresentationFreezeError,
    load_representation_freeze,
)


MANIFEST = "configs/r4_representation_finalists_v1.json"


def test_canonical_r4_freeze_is_valid_and_exact():
    data = load_representation_freeze(MANIFEST)
    assert data["selection"]["finalists"] == [
        "equity8",
        "equity4_blocker2",
        "category_equity4",
    ]
    assert data["heldout"]["status"] == "PREPARED_NOT_RUN"
    assert data["heldout"]["trigger"] == "workflow_dispatch"


def test_freeze_rejects_more_than_three_finalists(tmp_path):
    data = load_representation_freeze(MANIFEST)
    data["selection"]["finalists"].append("category")
    data["selection"]["metrics"]["category"] = {}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RepresentationFreezeError, match="one to three"):
        load_representation_freeze(path)


def test_freeze_rejects_heldout_coordinate_drift(tmp_path):
    data = load_representation_freeze(MANIFEST)
    data["heldout"]["checkpoints"] = [300, 1200, 7200]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RepresentationFreezeError, match="coordinates drift"):
        load_representation_freeze(path)
