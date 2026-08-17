from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .river_representation_lab import RIVER_REPRESENTATION_CANDIDATES


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA = "DEEPCASH_R4_REPRESENTATION_FINALIST_FREEZE_V1"


class RepresentationFreezeError(ValueError):
    pass


def _exact_keys(data: Mapping[str, Any], expected: set[str], label: str) -> None:
    supplied = set(data)
    if supplied != expected:
        raise RepresentationFreezeError(
            f"{label} keys mismatch; missing={sorted(expected - supplied)} "
            f"extra={sorted(supplied - expected)}"
        )


def load_representation_freeze(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepresentationFreezeError(f"cannot read freeze manifest {source}") from exc
    if not isinstance(data, dict):
        raise RepresentationFreezeError("freeze manifest root must be an object")
    _exact_keys(data, {"schema", "status", "source", "selection", "heldout"}, "root")
    if data["schema"] != _SCHEMA or data["status"] != "FROZEN_HELDOUT_NOT_RUN":
        raise RepresentationFreezeError("unexpected freeze schema or status")

    source_data = data["source"]
    _exact_keys(
        source_data,
        {
            "workflow_run", "artifact_id", "artifact_name",
            "artifact_zip_sha256", "artifact_files", "artifact_rows",
            "checkpoint_rows", "selection_precommit", "methodology_correction",
        },
        "source",
    )
    if source_data["workflow_run"] != 31976302604:
        raise RepresentationFreezeError("unexpected development workflow run")
    if source_data["artifact_id"] != 9274193444:
        raise RepresentationFreezeError("unexpected development artifact")
    if not _SHA256_RE.fullmatch(source_data["artifact_zip_sha256"]):
        raise RepresentationFreezeError("artifact digest must be lowercase SHA-256")
    if (source_data["artifact_files"], source_data["artifact_rows"], source_data["checkpoint_rows"]) != (6, 504, 168):
        raise RepresentationFreezeError("development artifact cardinality drift")

    selection = data["selection"]
    _exact_keys(
        selection,
        {"shared_checkpoint", "development_cells", "candidate_count", "pareto_frontier", "finalists", "metrics"},
        "selection",
    )
    finalists = tuple(selection["finalists"])
    if not 1 <= len(finalists) <= 3 or len(set(finalists)) != len(finalists):
        raise RepresentationFreezeError("freeze must contain one to three unique finalists")
    if any(name not in RIVER_REPRESENTATION_CANDIDATES for name in finalists):
        raise RepresentationFreezeError("freeze contains an unknown candidate")
    if set(selection["metrics"]) != set(finalists):
        raise RepresentationFreezeError("metrics must cover exactly the frozen finalists")
    if (selection["shared_checkpoint"], selection["development_cells"], selection["candidate_count"]) != (1200, 24, 7):
        raise RepresentationFreezeError("development selection coordinates drift")

    heldout = data["heldout"]
    _exact_keys(
        heldout,
        {"status", "workflow", "trigger", "board_set", "board_count", "range_combos_per_player", "phase_pairs", "pot", "spr_to_stack", "min_bet", "checkpoints"},
        "heldout",
    )
    expected_coordinates = {
        "status": "PREPARED_NOT_RUN",
        "workflow": ".github/workflows/river-representation-heldout-v1.yml",
        "trigger": "workflow_dispatch",
        "board_set": "heldout_v1",
        "board_count": 8,
        "range_combos_per_player": 8,
        "phase_pairs": [
            {"name": "A", "p0_phase": 0.19, "p1_phase": 0.47},
            {"name": "B", "p0_phase": 0.58, "p1_phase": 0.83},
        ],
        "pot": 100,
        "spr_to_stack": {"1": 100, "2": 200, "4": 400},
        "min_bet": 20,
        "checkpoints": [300, 1200, 3600],
    }
    if heldout != expected_coordinates:
        raise RepresentationFreezeError("held-out coordinates drift from the v1 precommit")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the immutable R4 finalist freeze")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--emit-candidates", action="store_true")
    args = parser.parse_args()
    try:
        data = load_representation_freeze(args.manifest)
    except RepresentationFreezeError as exc:
        parser.error(str(exc))
    finalists = data["selection"]["finalists"]
    if args.emit_candidates:
        print(",".join(finalists))
    else:
        print(json.dumps({"schema": data["schema"], "status": data["status"], "finalists": finalists}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
