from __future__ import annotations

import argparse
import json
from pathlib import Path

from deepcash_core.reference_convergence_analysis import analyze


def _format_float(x: float) -> str:
    return f"{float(x):.8f}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Analyze common-reference restriction convergence without post-hoc thresholds"
    )
    ap.add_argument("input", type=Path)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("river_reference_convergence_analysis.json"),
    )
    args = ap.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(payload)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Common-reference interval tightening:")
    for curve in result["curves"]:
        print(
            f"- {curve['board']} {curve['candidate']}: "
            f"iter {curve['first_checkpoint']}->{curve['last_checkpoint']} "
            f"interval {_format_float(curve['first_interval_width_per_pot'])}"
            f"->{_format_float(curve['last_interval_width_per_pot'])} "
            f"loss_upper {_format_float(curve['first_loss_upper_per_pot'])}"
            f"->{_format_float(curve['last_loss_upper_per_pot'])}"
        )
    print("Latest checkpoint aggregate:")
    for row in result["latest_checkpoint_aggregate"]:
        print(
            f"- {row['candidate']}: mean_upper={_format_float(row['mean_loss_upper_per_pot'])} "
            f"worst_upper={_format_float(row['worst_board_loss_upper_per_pot'])} "
            f"worst_interval={_format_float(row['worst_value_interval_width_per_pot'])}"
        )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
