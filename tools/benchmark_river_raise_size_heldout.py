"""Run the existing raise-size common-reference benchmark on unseen fixtures.

The underlying benchmark remains unchanged. This wrapper replaces only the board
registry and deterministic range phases, then annotates the output with explicit
held-out provenance before the common convergence analyzer reads it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import benchmark_river_raise_size_reference_convergence as benchmark
from deepcash_core.river_raise_size_heldout_fixtures import (
    RAISE_SIZE_HELDOUT_BOARDS,
    RAISE_SIZE_HELDOUT_P0_PHASE,
    RAISE_SIZE_HELDOUT_P1_PHASE,
)

_original_quantile_range = benchmark.quantile_range


def _heldout_quantile_range(board, count, phase):
    if abs(float(phase) - 0.00) <= 1e-15:
        mapped = RAISE_SIZE_HELDOUT_P0_PHASE
    elif abs(float(phase) - 0.27) <= 1e-15:
        mapped = RAISE_SIZE_HELDOUT_P1_PHASE
    else:
        raise ValueError(f"unexpected base benchmark phase: {phase}")
    return _original_quantile_range(board, count, mapped)


def _out_path(argv: list[str]) -> Path:
    if "--out" not in argv:
        raise ValueError("held-out wrapper requires explicit --out path")
    idx = argv.index("--out")
    if idx + 1 >= len(argv):
        raise ValueError("--out missing value")
    return Path(argv[idx + 1])


def main() -> None:
    out = _out_path(sys.argv)
    benchmark.RIVER_BOARDS = dict(RAISE_SIZE_HELDOUT_BOARDS)
    benchmark.quantile_range = _heldout_quantile_range
    benchmark.main()

    payload = json.loads(out.read_text(encoding="utf-8"))
    payload["board_set"] = "raise_size_heldout"
    payload["p0_phase"] = RAISE_SIZE_HELDOUT_P0_PHASE
    payload["p1_phase"] = RAISE_SIZE_HELDOUT_P1_PHASE
    payload["method"] = (
        str(payload.get("method", ""))
        + "; unseen raise-size held-out boards and precommitted alternate range phases"
    )
    for row in payload["rows"]:
        row["board_set"] = "raise_size_heldout"
        row["p0_phase"] = RAISE_SIZE_HELDOUT_P0_PHASE
        row["p1_phase"] = RAISE_SIZE_HELDOUT_P1_PHASE
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"annotated held-out provenance in {out}")


if __name__ == "__main__":
    main()
