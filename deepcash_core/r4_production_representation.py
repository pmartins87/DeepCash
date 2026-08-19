from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .river_representation_gen2 import R4_GEN2_CANDIDATES

_SCHEMA = "DEEPCASH_R4_PRODUCTION_REPRESENTATION_FREEZE_V1"
_EXPECTED_REPRESENTATION = "matchup_cluster8"
_EXPECTED_ANCHOR = "equity8"
_EXPECTED_CONTROL = "matchup_cluster4"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ProductionRepresentationFreezeError(ValueError):
    pass


def _exact_keys(data: Mapping[str, Any], expected: set[str], label: str) -> None:
    supplied = set(data)
    if supplied != expected:
        raise ProductionRepresentationFreezeError(
            f"{label} keys mismatch; missing={sorted(expected - supplied)} "
            f"extra={sorted(supplied - expected)}"
        )


def _require_sha(value: Any, label: str) -> str:
    text = str(value)
    if not _SHA256_RE.fullmatch(text):
        raise ProductionRepresentationFreezeError(f"invalid SHA-256 for {label}")
    return text


def load_r4_production_representation_freeze(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionRepresentationFreezeError(
            f"cannot read R4 production representation freeze {source}"
        ) from exc
    if not isinstance(data, dict):
        raise ProductionRepresentationFreezeError("freeze root must be an object")

    _exact_keys(
        data,
        {
            "schema",
            "status",
            "generation",
            "representation",
            "accuracy_anchor",
            "compression_control",
            "selection_rule",
            "evidence",
            "architecture_boundary",
        },
        "root",
    )
    if data["schema"] != _SCHEMA or data["status"] != "FROZEN" or data["generation"] != 2:
        raise ProductionRepresentationFreezeError("unexpected production freeze identity")
    if data["representation"] != _EXPECTED_REPRESENTATION:
        raise ProductionRepresentationFreezeError("production representation drift")
    if data["accuracy_anchor"] != _EXPECTED_ANCHOR:
        raise ProductionRepresentationFreezeError("accuracy anchor drift")
    if data["compression_control"] != _EXPECTED_CONTROL:
        raise ProductionRepresentationFreezeError("compression control drift")
    for name in (_EXPECTED_REPRESENTATION, _EXPECTED_ANCHOR, _EXPECTED_CONTROL):
        if name not in R4_GEN2_CANDIDATES:
            raise ProductionRepresentationFreezeError(
                f"frozen representation name is outside Generation-2 pool: {name}"
            )

    evidence = data["evidence"]
    _exact_keys(
        evidence,
        {
            "generation2_heldout_v2",
            "ryzen_equal_wallclock_run1",
            "ryzen_instrumentation_repair",
            "r4_r5_r6_physical_compatibility",
        },
        "evidence",
    )

    heldout = evidence["generation2_heldout_v2"]
    _exact_keys(heldout, {"workflow_run", "artifact_id", "artifact_sha256", "audit"}, "heldout")
    if heldout["workflow_run"] != 32101218388 or heldout["artifact_id"] != 9312441121:
        raise ProductionRepresentationFreezeError("held-out-v2 provenance drift")
    if _require_sha(heldout["artifact_sha256"], "heldout artifact") != "92cc1825cbb4155b3cb3239469969cefdf0b1261724fb97182ee2c4d7b3dd4b7":
        raise ProductionRepresentationFreezeError("held-out-v2 digest drift")
    if heldout["audit"] != "docs/R4_GENERATION2_HELDOUT_V2_AUDIT_20260818.md":
        raise ProductionRepresentationFreezeError("held-out audit path drift")

    wallclock = evidence["ryzen_equal_wallclock_run1"]
    _exact_keys(wallclock, {"artifact_filename", "artifact_sha256", "audit"}, "wallclock")
    if _require_sha(wallclock["artifact_sha256"], "wallclock artifact") != "136810b601a01449fdfcf1725b25dd357f9309f3f0c3d25e0496d170097e4909":
        raise ProductionRepresentationFreezeError("wallclock digest drift")

    repair = evidence["ryzen_instrumentation_repair"]
    _exact_keys(repair, {"artifact_filename", "artifact_sha256", "audit"}, "repair")
    if _require_sha(repair["artifact_sha256"], "repair artifact") != "5bbf592b2f53e76cb650d7a336cc016a23f227392a3fcc6008b114f4dffabaf7":
        raise ProductionRepresentationFreezeError("instrumentation-repair digest drift")

    compat = evidence["r4_r5_r6_physical_compatibility"]
    _exact_keys(
        compat,
        {
            "artifact_filename",
            "artifact_sha256",
            "source_git_head",
            "precommit",
            "audit",
            "solver_variant",
            "physical_child_cells",
            "candidate_runs",
            "affinity_width",
            "resolved_pairwise_losses",
            "metrics",
        },
        "compatibility",
    )
    if _require_sha(compat["artifact_sha256"], "compatibility artifact") != "58ef11362a0ca81b300f7120ddaaf35fe781562d81e8189fc4a664fee8e11cb5":
        raise ProductionRepresentationFreezeError("compatibility artifact digest drift")
    if compat["source_git_head"] != "143f36f8ff60ef9b1db6cfe9ae23ac0caa491839":
        raise ProductionRepresentationFreezeError("compatibility source head drift")
    if compat["solver_variant"] != "ALT_DCFR_150_0_2":
        raise ProductionRepresentationFreezeError("compatibility solver drift")
    if compat["physical_child_cells"] != 48 or compat["candidate_runs"] != 96:
        raise ProductionRepresentationFreezeError("compatibility cardinality drift")
    if compat["affinity_width"] != 32:
        raise ProductionRepresentationFreezeError("compatibility affinity drift")
    if compat["resolved_pairwise_losses"] != 0:
        raise ProductionRepresentationFreezeError("production freeze cannot retain resolved physical reversals")
    if compat["precommit"] != "docs/R4_R5_R6_COMPATIBILITY_PRECOMMIT_20260818.md":
        raise ProductionRepresentationFreezeError("compatibility precommit drift")
    if compat["audit"] != "docs/R4_R5_R6_COMPATIBILITY_PHYSICAL_AUDIT_20260819.md":
        raise ProductionRepresentationFreezeError("compatibility audit drift")

    metrics = compat["metrics"]
    _exact_keys(metrics, {_EXPECTED_REPRESENTATION, _EXPECTED_ANCHOR}, "compatibility metrics")
    rep = metrics[_EXPECTED_REPRESENTATION]
    anchor = metrics[_EXPECTED_ANCHOR]
    metric_keys = {
        "mean_loss_upper_per_pot",
        "p90_loss_upper_per_pot",
        "worst_loss_upper_per_pot",
        "mean_joint_iterations_per_second",
        "peak_working_set_bytes_mean",
        "mean_action_slot_ratio",
        "median_iterations_each_state",
    }
    _exact_keys(rep, metric_keys, "representation metrics")
    _exact_keys(anchor, metric_keys, "anchor metrics")

    # Fail closed on the substantive frozen decision rather than merely parsing
    # names.  These are broad invariants, not a second post-hoc selector.
    for key in ("mean_loss_upper_per_pot", "p90_loss_upper_per_pot", "worst_loss_upper_per_pot"):
        if not (0.0 <= float(rep[key]) < float(anchor[key])):
            raise ProductionRepresentationFreezeError(f"frozen fidelity ordering lost for {key}")
    throughput_ratio = float(rep["mean_joint_iterations_per_second"]) / float(anchor["mean_joint_iterations_per_second"])
    memory_ratio = float(rep["peak_working_set_bytes_mean"]) / float(anchor["peak_working_set_bytes_mean"])
    if not 0.95 <= throughput_ratio <= 1.05:
        raise ProductionRepresentationFreezeError("frozen throughput compatibility boundary violated")
    if not 0.95 <= memory_ratio <= 1.05:
        raise ProductionRepresentationFreezeError("frozen memory compatibility boundary violated")

    boundary = data["architecture_boundary"]
    _exact_keys(boundary, {"compressed", "remains_exact", "r6_scope", "r5_scope"}, "architecture boundary")
    required_exact = {
        "public cards",
        "private-card legality and card removal",
        "chance mass",
        "payoff",
        "stack and pot geometry",
        "legal action tree",
    }
    if set(boundary["remains_exact"]) != required_exact:
        raise ProductionRepresentationFreezeError("exact architecture boundary drift")
    return data


def production_representation_name(path: str | Path) -> str:
    return str(load_r4_production_representation_freeze(path)["representation"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the immutable R4 production representation freeze")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--emit-name", action="store_true")
    args = parser.parse_args()
    try:
        data = load_r4_production_representation_freeze(args.manifest)
    except ProductionRepresentationFreezeError as exc:
        parser.error(str(exc))
    if args.emit_name:
        print(data["representation"])
    else:
        print(
            json.dumps(
                {
                    "schema": data["schema"],
                    "status": data["status"],
                    "representation": data["representation"],
                    "accuracy_anchor": data["accuracy_anchor"],
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
