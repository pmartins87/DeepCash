import json
from pathlib import Path

import pytest

from deepcash_core.r4_production_representation import (
    ProductionRepresentationFreezeError,
    load_r4_production_representation_freeze,
    production_representation_name,
)
from deepcash_core.river_representation_gen2 import R4_GEN2_CANDIDATES


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "deepcash_core" / "data" / "r4_production_representation_v1.json"


def test_r4_production_representation_freeze_loads_and_is_gen2_candidate():
    data = load_r4_production_representation_freeze(FREEZE)
    assert data["status"] == "FROZEN"
    assert data["generation"] == 2
    assert data["representation"] == "matchup_cluster8"
    assert data["representation"] in R4_GEN2_CANDIDATES
    assert data["accuracy_anchor"] == "equity8"
    assert data["compression_control"] == "matchup_cluster4"
    assert production_representation_name(FREEZE) == "matchup_cluster8"


def test_frozen_physical_compatibility_has_zero_resolved_losses():
    data = load_r4_production_representation_freeze(FREEZE)
    compat = data["evidence"]["r4_r5_r6_physical_compatibility"]
    assert compat["physical_child_cells"] == 48
    assert compat["candidate_runs"] == 96
    assert compat["affinity_width"] == 32
    assert compat["resolved_pairwise_losses"] == 0
    assert compat["solver_variant"] == "ALT_DCFR_150_0_2"


def test_frozen_candidate_strictly_leads_anchor_on_aggregate_fidelity():
    data = load_r4_production_representation_freeze(FREEZE)
    metrics = data["evidence"]["r4_r5_r6_physical_compatibility"]["metrics"]
    rep = metrics["matchup_cluster8"]
    anchor = metrics["equity8"]
    for key in (
        "mean_loss_upper_per_pot",
        "p90_loss_upper_per_pot",
        "worst_loss_upper_per_pot",
    ):
        assert rep[key] < anchor[key]
    assert rep["mean_joint_iterations_per_second"] / anchor["mean_joint_iterations_per_second"] == pytest.approx(0.9977202509688141)
    assert rep["peak_working_set_bytes_mean"] / anchor["peak_working_set_bytes_mean"] == pytest.approx(1.000986714592804)


def test_freeze_fails_closed_if_representation_is_changed(tmp_path: Path):
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    payload["representation"] = "equity8"
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ProductionRepresentationFreezeError, match="production representation drift"):
        load_r4_production_representation_freeze(altered)


def test_freeze_fails_closed_if_resolved_loss_is_added(tmp_path: Path):
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    payload["evidence"]["r4_r5_r6_physical_compatibility"]["resolved_pairwise_losses"] = 1
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ProductionRepresentationFreezeError, match="resolved physical reversals"):
        load_r4_production_representation_freeze(altered)
