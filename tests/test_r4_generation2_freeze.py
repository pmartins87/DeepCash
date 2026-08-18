import json
from pathlib import Path

from deepcash_core.river_lab import materialize_bet_sizes
from deepcash_core.river_representation_gen2 import (
    GEN2_REFERENCE_FRACTIONS,
    R4_GEN2_CANDIDATES,
)
from deepcash_core.river_representation_gen2_fixtures import (
    R4_GEN2_DEV_BOARDS,
    R4_GEN2_HELDOUT_V2_BOARDS,
)


FREEZE = Path("deepcash_core/data/r4_representation_generation2_v1.json")


def test_generation2_freeze_manifest_matches_code_exactly():
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert payload["schema"] == "DEEPCASH_R4_REPRESENTATION_GENERATION2_FREEZE_V1"
    assert payload["generation"] == 2
    assert tuple(payload["candidate_pool"]) == R4_GEN2_CANDIDATES
    assert payload["accuracy_anchor"] == "equity8"
    assert payload["development"]["board_count"] == len(R4_GEN2_DEV_BOARDS) == 8
    assert payload["heldout_v2"]["board_count"] == len(R4_GEN2_HELDOUT_V2_BOARDS) == 8
    assert payload["selection"]["max_heldout_finalists"] == 3
    assert payload["heldout_v2"]["status"].startswith("FROZEN_UNSEEN")


def test_generation2_manifest_physical_action_geometries_match_code():
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    expected = payload["development"]["expected_materialized_bet_sizes"]
    for stack in payload["development"]["stacks"]:
        spr = str(stack // payload["development"]["pot"])
        actual = materialize_bet_sizes(
            pot=payload["development"]["pot"],
            stack=stack,
            min_bet=payload["development"]["min_bet"],
            fractions=GEN2_REFERENCE_FRACTIONS,
        )
        assert list(actual) == expected[spr]
