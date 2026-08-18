from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .river_representation_gen2 import R4_GEN2_CANDIDATES

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA = "DEEPCASH_R4_REPRESENTATION_GENERATION2_FINALIST_FREEZE_V1"
_EXPECTED_FINALISTS = ("equity8", "matchup_cluster8", "matchup_cluster4")


class Generation2FreezeError(ValueError):
    pass


def _exact_keys(data: Mapping[str, Any], expected: set[str], label: str) -> None:
    supplied = set(data)
    if supplied != expected:
        raise Generation2FreezeError(
            f"{label} keys mismatch; missing={sorted(expected - supplied)} extra={sorted(supplied - expected)}"
        )


def load_generation2_finalist_freeze(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Generation2FreezeError(f"cannot read Generation-2 freeze manifest {source}") from exc
    if not isinstance(data, dict):
        raise Generation2FreezeError("freeze manifest root must be an object")
    _exact_keys(data, {"schema", "generation", "status", "source", "selection", "heldout_v2", "production_boundary"}, "root")
    if data["schema"] != _SCHEMA or data["generation"] != 2 or data["status"] != "FROZEN_HELDOUT_V2_NOT_RUN":
        raise Generation2FreezeError("unexpected Generation-2 freeze identity")

    src = data["source"]
    _exact_keys(src, {"workflow_run", "head_sha", "artifact_id", "artifact_name", "artifact_zip_sha256", "shared_checkpoint", "development_payloads", "development_cells", "precommit", "audit"}, "source")
    expected_source = {
        "workflow_run": 32095713074,
        "head_sha": "e01886850109fc8047cf92224f24f850ab87e2ee",
        "artifact_id": 9310917903,
        "artifact_name": "r4-representation-gen2-dev-v1",
        "shared_checkpoint": 3600,
        "development_payloads": 6,
        "development_cells": 48,
        "precommit": "docs/R4_GENERATION2_CLUSTERING_PRECOMMIT_20260817.md",
        "audit": "docs/R4_GENERATION2_DEVELOPMENT_AUDIT_20260818.md",
    }
    for key, expected in expected_source.items():
        if src[key] != expected:
            raise Generation2FreezeError(f"source drift for {key}")
    if src["artifact_zip_sha256"] != "027cee5bb2d1074756f80f4e4e558646c1c92ed6565cdaeab9dcfb9d895681b5" or not _SHA256_RE.fullmatch(src["artifact_zip_sha256"]):
        raise Generation2FreezeError("unexpected development artifact digest")

    selection = data["selection"]
    _exact_keys(selection, {"candidate_pool", "finalists", "eliminated", "metrics", "rule"}, "selection")
    if tuple(selection["candidate_pool"]) != tuple(R4_GEN2_CANDIDATES):
        raise Generation2FreezeError("Generation-2 candidate pool drift")
    finalists = tuple(selection["finalists"])
    if finalists != _EXPECTED_FINALISTS:
        raise Generation2FreezeError("Generation-2 finalist freeze drift")
    if tuple(selection["eliminated"]) != ("equity4_matchup2",):
        raise Generation2FreezeError("unexpected eliminated candidate set")
    if set(selection["metrics"]) != set(finalists):
        raise Generation2FreezeError("metrics must cover exactly the frozen finalists")

    heldout = data["heldout_v2"]
    _exact_keys(heldout, {"status", "workflow", "trigger", "board_set", "board_count", "range_combos_per_player", "phases", "pot", "spr_to_stack", "min_bet", "reference_fractions", "expected_materialized_bet_sizes", "checkpoints"}, "heldout_v2")
    expected_heldout = {
        "status": "PREPARED_NOT_RUN",
        "workflow": ".github/workflows/river-representation-gen2-heldout-v2.yml",
        "trigger": "workflow_dispatch",
        "board_set": "heldout_v2",
        "board_count": 8,
        "range_combos_per_player": 8,
        "phases": [
            {"phase": "A", "p0_phase": 0.19, "p1_phase": 0.47},
            {"phase": "B", "p0_phase": 0.58, "p1_phase": 0.83},
        ],
        "pot": 100,
        "spr_to_stack": {"1": 100, "2": 200, "4": 400},
        "min_bet": 20,
        "reference_fractions": ["1/4", "1/2", "1", "2", "4"],
        "expected_materialized_bet_sizes": {
            "1": [25, 50, 100],
            "2": [25, 50, 100, 200],
            "4": [25, 50, 100, 200, 400],
        },
        "checkpoints": [300, 1200, 3600],
    }
    if heldout != expected_heldout:
        raise Generation2FreezeError("held-out-v2 coordinates drift from the frozen protocol")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the immutable R4 Generation-2 finalist freeze")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--emit-candidates", action="store_true")
    args = parser.parse_args()
    try:
        data = load_generation2_finalist_freeze(args.manifest)
    except Generation2FreezeError as exc:
        parser.error(str(exc))
    finalists = data["selection"]["finalists"]
    if args.emit_candidates:
        print(",".join(finalists))
    else:
        print(json.dumps({"schema": data["schema"], "status": data["status"], "finalists": finalists}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
