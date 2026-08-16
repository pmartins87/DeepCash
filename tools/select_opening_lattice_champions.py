"""Select one precommitted opening-size champion per candidate cardinality.

Inputs are the four already-seen engineering analysis artifacts produced by
`river-opening-subset-lattice-v1.yml`: control/heldout-v1 at SPR 1 and 4.
The selection order is frozen in `docs/R3_HELDOUT_V2_PRECOMMIT_20260816.md`.
This script does not look at held-out-v2 evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from functools import cmp_to_key
from pathlib import Path

TOL = 1e-12
EXPECTED_CELLS = {
    ("control", 100, 4, 0.00, 0.27),
    ("control", 400, 4, 0.00, 0.27),
    ("heldout", 100, 6, 0.13, 0.61),
    ("heldout", 400, 6, 0.13, 0.61),
}
EXPECTED_CANDIDATE_COUNT = 14
FINAL_CHECKPOINT = 3000


def _cardinality(name: str) -> int:
    match = re.fullmatch(r"L([123])_.+", name)
    if not match:
        raise ValueError(f"unexpected lattice candidate name: {name}")
    return int(match.group(1))


def _cell(payload: dict) -> tuple[str, int, int, float, float]:
    geometry = payload.get("source_geometry", {})
    try:
        return (
            str(geometry["board_set"]),
            int(geometry["stack"]),
            int(geometry["range_combos"]),
            float(geometry["p0_phase"]),
            float(geometry["p1_phase"]),
        )
    except KeyError as exc:
        raise ValueError(f"analysis missing engineering geometry: {exc}") from exc


def _compare(a: dict, b: dict) -> int:
    # Precommitted ordering: worst upper, mean upper, total training seconds,
    # lexical name. The first two metrics use an explicit 1e-12 tie tolerance.
    for key in ("worst_loss_upper_per_pot", "mean_loss_upper_per_pot"):
        av = float(a[key])
        bv = float(b[key])
        if abs(av - bv) > TOL:
            return -1 if av < bv else 1
    at = float(a["total_cumulative_training_seconds"])
    bt = float(b["total_cumulative_training_seconds"])
    if at != bt:
        return -1 if at < bt else 1
    return (a["candidate"] > b["candidate"]) - (a["candidate"] < b["candidate"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Select opening subset champions from seen engineering evidence")
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("opening_subset_champions.json"))
    args = ap.parse_args()

    paths = sorted(args.input_dir.rglob("*_analysis.json"))
    if len(paths) != 4:
        raise ValueError(f"expected exactly four engineering analysis files, found {len(paths)}: {paths}")

    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    cells = {_cell(payload) for payload in payloads}
    if cells != EXPECTED_CELLS:
        raise ValueError(f"unexpected engineering cells: got={sorted(cells)} expected={sorted(EXPECTED_CELLS)}")
    if any(int(payload["latest_checkpoint"]) != FINAL_CHECKPOINT for payload in payloads):
        raise ValueError("all lattice analyses must reach checkpoint 3000")

    per_candidate: dict[str, dict] = {}
    for payload in payloads:
        cell = _cell(payload)
        aggregates = {
            row["candidate"]: row for row in payload["latest_checkpoint_aggregate"]
        }
        cell_candidates = {curve["candidate"] for curve in payload["curves"]}
        if len(cell_candidates) != EXPECTED_CANDIDATE_COUNT:
            raise ValueError(
                f"cell {cell} has {len(cell_candidates)} candidates; expected {EXPECTED_CANDIDATE_COUNT}"
            )
        for curve in payload["curves"]:
            candidate = str(curve["candidate"])
            item = per_candidate.setdefault(
                candidate,
                {
                    "candidate": candidate,
                    "cardinality": _cardinality(candidate),
                    "loss_uppers": [],
                    "interval_widths": [],
                    "training_seconds": 0.0,
                    "rows": 0,
                    "cells": set(),
                },
            )
            item["loss_uppers"].append(float(curve["last_loss_upper_per_pot"]))
            item["interval_widths"].append(float(curve["last_interval_width_per_pot"]))
            item["rows"] += 1
            item["cells"].add(cell)
        for candidate, row in aggregates.items():
            per_candidate[candidate]["training_seconds"] += float(
                row["total_cumulative_training_seconds"]
            )

    if len(per_candidate) != EXPECTED_CANDIDATE_COUNT:
        raise ValueError(f"expected {EXPECTED_CANDIDATE_COUNT} unique candidates, found {len(per_candidate)}")

    rankings: dict[str, list[dict]] = {}
    champions: dict[str, dict] = {}
    for cardinality in (1, 2, 3):
        rows: list[dict] = []
        for candidate, item in sorted(per_candidate.items()):
            if item["cardinality"] != cardinality:
                continue
            if item["cells"] != EXPECTED_CELLS:
                raise ValueError(f"candidate {candidate} missing engineering cells")
            loss_uppers = item["loss_uppers"]
            interval_widths = item["interval_widths"]
            row = {
                "candidate": candidate,
                "cardinality": cardinality,
                "engineering_board_rows": item["rows"],
                "worst_loss_upper_per_pot": max(loss_uppers),
                "mean_loss_upper_per_pot": sum(loss_uppers) / len(loss_uppers),
                "worst_exact_br_interval_width_per_pot": max(interval_widths),
                "mean_exact_br_interval_width_per_pot": sum(interval_widths) / len(interval_widths),
                "total_cumulative_training_seconds": item["training_seconds"],
            }
            rows.append(row)
        rows.sort(key=cmp_to_key(_compare))
        rankings[str(cardinality)] = rows
        champions[str(cardinality)] = rows[0]

    output = {
        "schema": "DEEPCASH_R3_OPENING_SUBSET_CHAMPIONS_V1",
        "selection_precommit": "docs/R3_HELDOUT_V2_PRECOMMIT_20260816.md",
        "input_cells": [
            {
                "board_set": cell[0],
                "stack": cell[1],
                "spr": cell[1] / 100.0,
                "range_combos": cell[2],
                "p0_phase": cell[3],
                "p1_phase": cell[4],
            }
            for cell in sorted(cells)
        ],
        "final_checkpoint": FINAL_CHECKPOINT,
        "tie_tolerance": TOL,
        "champions": champions,
        "rankings": rankings,
        "methodology_note": (
            "Champions use only control plus heldout-v1 evidence, both already seen. "
            "Held-out-v2 remains unseen and is not read by this selector."
        ),
    }
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Opening subset cardinality champions:")
    for cardinality in (1, 2, 3):
        row = champions[str(cardinality)]
        print(
            f"- {cardinality} size(s): {row['candidate']} "
            f"worst_upper={row['worst_loss_upper_per_pot']:.8f} "
            f"mean_upper={row['mean_loss_upper_per_pot']:.8f} "
            f"worst_interval={row['worst_exact_br_interval_width_per_pot']:.8f}"
        )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
