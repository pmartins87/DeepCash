from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

from deepcash_core.river_alternating_dcfr import (
    AlternatingVariant,
    advance_alternating_solver,
    alternating_solver_result,
    init_alternating_solver,
)
from deepcash_core.river_benchmark_fixtures import parse_cards, quantile_range
from deepcash_core.river_correlated_chance_sampling import (
    advance_correlated_chance,
    correlated_chance_result,
    init_correlated_chance,
)
from deepcash_core.river_external_sampling import (
    ExternalSamplingVariant,
    WeightedDealSampler,
    external_sampling_result,
    init_external_sampling,
)
from deepcash_core.river_lab import RiverGameSpec
from deepcash_core.river_vr_external_sampling import VRBaselineMode, advance_vr_external_sampling


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "deepcash_core" / "data" / "r5_physical_ryzen_crossover_v1.json"
SCHEMA = "DEEPCASH_R5_PHYSICAL_RYZEN_CROSSOVER_RESULT_V1"
CONFIG_SCHEMA = "DEEPCASH_R5_PHYSICAL_RYZEN_CROSSOVER_CONFIG_V1"
EXPECTED_STATUS = "FROZEN_BEFORE_PHYSICAL_RESULT"
ALGORITHMS = ("ALT_DCFR_150_0_2", "CCS_CFR_PLUS_LINEAR", "ES_ZERO")
EXPECTED_BOARDS = {
    "physical_ace_mid": "Ac 9s 6d 4h 2c",
    "physical_king_dynamic": "Kh Jd 8c 5s 2d",
    "physical_paired_queens": "Qs Qd 7h 4c 3s",
    "physical_connected": "Td 9c 8h 5d 2s",
}
EXPECTED_PHASES = (
    ("P_A", 0.11, 0.59, 701),
    ("P_B", 0.37, 0.83, 809),
)
EXPECTED_SUPPORTS = (8, 24, 48)
EXPECTED_POT = 100
EXPECTED_BETS = (25, 50, 100)
EXPECTED_BUDGET = 30.0
REQUIRED_PAIRED_WINS = 5


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != CONFIG_SCHEMA:
        raise ValueError("unexpected R5 physical crossover config schema")
    if config.get("status") != EXPECTED_STATUS:
        raise ValueError("physical crossover config is not frozen before result")
    if config.get("boards") != EXPECTED_BOARDS:
        raise ValueError("physical board freeze drift")
    phases = tuple(
        (
            str(item["name"]),
            float(item["p0_phase"]),
            float(item["p1_phase"]),
            int(item["sampling_seed"]),
        )
        for item in config.get("phases", [])
    )
    if phases != EXPECTED_PHASES:
        raise ValueError("physical phase/seed freeze drift")
    if tuple(int(x) for x in config.get("range_combos_per_player", [])) != EXPECTED_SUPPORTS:
        raise ValueError("physical support freeze drift")
    if int(config.get("pot", 0)) != EXPECTED_POT:
        raise ValueError("physical pot freeze drift")
    if tuple(int(x) for x in config.get("bet_sizes", [])) != EXPECTED_BETS:
        raise ValueError("physical bet-size freeze drift")
    if not math.isclose(float(config.get("budget_seconds_per_cell", 0.0)), EXPECTED_BUDGET):
        raise ValueError("physical wall-clock budget freeze drift")
    if tuple(config.get("algorithms", [])) != ALGORITHMS:
        raise ValueError("physical algorithm freeze drift")
    execution = config.get("execution", {})
    if int(execution.get("parallel_workers", 0)) != 1:
        raise ValueError("physical crossover must run sequentially")
    if not bool(execution.get("cell_process_isolation", False)):
        raise ValueError("physical crossover requires per-cell process isolation")
    decision = config.get("decision_rule", {})
    if int(decision.get("cells_per_support_per_algorithm", 0)) != 8:
        raise ValueError("physical decision cell-count drift")
    if int(decision.get("strict_paired_wins_required_against_each_other_algorithm", 0)) != REQUIRED_PAIRED_WINS:
        raise ValueError("physical paired-win rule drift")


def run_git_required(*args: str) -> str:
    cp = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout.strip()


def process_affinity() -> list[int] | None:
    if hasattr(os, "sched_getaffinity"):
        try:
            return sorted(int(x) for x in os.sched_getaffinity(0))
        except Exception:
            pass
    if os.name == "nt":
        try:
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetCurrentProcess.argtypes = []
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.GetProcessAffinityMask.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ctypes.c_size_t),
                ctypes.POINTER(ctypes.c_size_t),
            ]
            kernel32.GetProcessAffinityMask.restype = wintypes.BOOL
            process_mask = ctypes.c_size_t()
            system_mask = ctypes.c_size_t()
            ok = kernel32.GetProcessAffinityMask(
                kernel32.GetCurrentProcess(),
                ctypes.byref(process_mask),
                ctypes.byref(system_mask),
            )
            if not ok:
                return None
            mask = int(process_mask.value)
            return [i for i in range(mask.bit_length()) if mask & (1 << i)]
        except Exception:
            return None
    return None


def process_memory() -> dict[str, int] | None:
    if os.name == "nt":
        try:
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32.GetCurrentProcess.argtypes = []
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                wintypes.DWORD,
            ]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            ok = psapi.GetProcessMemoryInfo(
                kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
            )
            if not ok:
                return None
            return {
                "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
                "working_set_bytes": int(counters.WorkingSetSize),
                "pagefile_bytes": int(counters.PagefileUsage),
                "peak_pagefile_bytes": int(counters.PeakPagefileUsage),
            }
        except Exception:
            return None
    try:
        import resource

        peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        peak_bytes = peak if sys.platform == "darwin" else peak * 1024
        return {
            "peak_working_set_bytes": peak_bytes,
            "working_set_bytes": peak_bytes,
            "pagefile_bytes": 0,
            "peak_pagefile_bytes": 0,
        }
    except Exception:
        return None


def validate_instrumentation() -> dict[str, Any]:
    memory = process_memory()
    affinity = process_affinity()
    if memory is None or int(memory.get("peak_working_set_bytes", 0)) <= 0:
        raise RuntimeError("peak working-set/RSS instrumentation unavailable")
    if os.name == "nt" and not affinity:
        raise RuntimeError("Windows process-affinity instrumentation unavailable")
    return {"memory": memory, "affinity": affinity}


def machine_metadata() -> dict[str, Any]:
    instrumentation = validate_instrumentation()
    head = run_git_required("rev-parse", "HEAD")
    tracked = run_git_required("status", "--porcelain", "--untracked-files=no")
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "processor_identifier": os.environ.get("PROCESSOR_IDENTIFIER", ""),
        "python": sys.version,
        "logical_cpu_count": os.cpu_count(),
        "affinity": instrumentation["affinity"],
        "preflight_memory": instrumentation["memory"],
        "git_head": head,
        "git_tracked_status_porcelain": tracked,
    }


def build_spec(config: dict[str, Any], board_name: str, support: int, phase_name: str) -> RiverGameSpec:
    validate_config(config)
    if board_name not in EXPECTED_BOARDS:
        raise ValueError("board outside frozen physical set")
    if support not in EXPECTED_SUPPORTS:
        raise ValueError("support outside frozen physical set")
    phase = next((item for item in config["phases"] if item["name"] == phase_name), None)
    if phase is None:
        raise ValueError("phase outside frozen physical set")
    board = parse_cards(EXPECTED_BOARDS[board_name])
    return RiverGameSpec(
        board=board,
        p0_range=quantile_range(board, support, float(phase["p0_phase"])),
        p1_range=quantile_range(board, support, float(phase["p1_phase"])),
        pot=EXPECTED_POT,
        bet_sizes=EXPECTED_BETS,
    )


def next_chunk_iterations(
    *,
    completed_iterations: int,
    cumulative_train_seconds: float,
    remaining_seconds: float,
    initial: int,
    minimum: int,
    maximum: int,
) -> int:
    if minimum <= 0 or initial < minimum or maximum < initial:
        raise ValueError("invalid chunk bounds")
    if remaining_seconds <= 0.0:
        return minimum
    if completed_iterations <= 0 or cumulative_train_seconds <= 0.0:
        return initial
    estimate = int(
        math.ceil(
            completed_iterations
            / cumulative_train_seconds
            * remaining_seconds
        )
    )
    return max(minimum, min(maximum, estimate))


def init_algorithm(spec: RiverGameSpec, algorithm: str, seed: int):
    if algorithm == "ALT_DCFR_150_0_2":
        return init_alternating_solver(spec, AlternatingVariant.ALT_DCFR_150_0_2)
    if algorithm == "CCS_CFR_PLUS_LINEAR":
        return init_correlated_chance(spec, seed=seed)
    if algorithm == "ES_ZERO":
        return init_external_sampling(
            spec,
            ExternalSamplingVariant.ES_CFR_PLUS_LINEAR,
            seed=seed,
        )
    raise ValueError(f"algorithm outside frozen physical set: {algorithm}")


def advance_algorithm(spec: RiverGameSpec, algorithm: str, state, iterations: int) -> None:
    if algorithm == "ALT_DCFR_150_0_2":
        advance_alternating_solver(spec, state, additional_iterations=iterations)
        return
    if algorithm == "CCS_CFR_PLUS_LINEAR":
        advance_correlated_chance(spec, state, additional_iterations=iterations)
        return
    if algorithm == "ES_ZERO":
        advance_vr_external_sampling(
            spec,
            state,
            additional_iterations=iterations,
            baseline_mode=VRBaselineMode.ZERO,
        )
        return
    raise ValueError(f"algorithm outside frozen physical set: {algorithm}")


def algorithm_result(spec: RiverGameSpec, algorithm: str, state):
    if algorithm == "ALT_DCFR_150_0_2":
        return alternating_solver_result(spec, state)
    if algorithm == "CCS_CFR_PLUS_LINEAR":
        return correlated_chance_result(spec, state)
    if algorithm == "ES_ZERO":
        return external_sampling_result(spec, state)
    raise ValueError(f"algorithm outside frozen physical set: {algorithm}")


def validate_finite_result(result) -> None:
    values = (
        result.policy_ev,
        result.br0_value,
        result.br1_value,
        result.exploitability_per_pot,
    )
    if not all(math.isfinite(float(value)) for value in values):
        raise RuntimeError("non-finite strategic result")
    if result.exploitability_per_pot < -1e-12:
        raise RuntimeError("negative exploitability result")


def worker_run(payload: dict[str, Any], output_path: Path) -> None:
    config_path = Path(payload["config_path"]).resolve()
    config = load_json(config_path)
    validate_config(config)
    instrumentation = validate_instrumentation()

    board_name = str(payload["board"])
    support = int(payload["support"])
    phase_name = str(payload["phase"])
    algorithm = str(payload["algorithm"])
    seed = int(payload["sampling_seed"])
    spec = build_spec(config, board_name, support, phase_name)
    compatible_deals = len(WeightedDealSampler.from_spec(spec).deals)
    state = init_algorithm(spec, algorithm, seed)

    chunk_cfg = config["chunk_contract"][algorithm]
    budget = float(config["budget_seconds_per_cell"])
    cumulative = 0.0
    while cumulative < budget:
        chunk = next_chunk_iterations(
            completed_iterations=int(state.iterations),
            cumulative_train_seconds=cumulative,
            remaining_seconds=budget - cumulative,
            initial=int(chunk_cfg["initial"]),
            minimum=int(chunk_cfg["minimum"]),
            maximum=int(chunk_cfg["maximum"]),
        )
        started = time.perf_counter()
        advance_algorithm(spec, algorithm, state, chunk)
        cumulative += time.perf_counter() - started

    eval_started = time.perf_counter()
    result = algorithm_result(spec, algorithm, state)
    evaluation_seconds = time.perf_counter() - eval_started
    validate_finite_result(result)

    overshoot = cumulative - budget
    timing_limit = max(0.50, 0.05 * budget)
    terminal_visits = getattr(state, "terminal_visits", None)
    memory = process_memory()
    affinity = process_affinity()
    if memory is None or int(memory.get("peak_working_set_bytes", 0)) <= 0:
        raise RuntimeError("cell memory instrumentation unavailable")
    if os.name == "nt" and not affinity:
        raise RuntimeError("cell Windows affinity instrumentation unavailable")

    row = {
        "cell_index": int(payload["cell_index"]),
        "board": board_name,
        "board_text": EXPECTED_BOARDS[board_name],
        "support": support,
        "phase": phase_name,
        "p0_phase": float(payload["p0_phase"]),
        "p1_phase": float(payload["p1_phase"]),
        "sampling_seed": seed,
        "seed_used_by_algorithm": algorithm != "ALT_DCFR_150_0_2",
        "algorithm": algorithm,
        "compatible_deal_count": compatible_deals,
        "requested_budget_seconds": budget,
        "cumulative_train_seconds": cumulative,
        "timing_overshoot_seconds": overshoot,
        "timing_quality_limit_seconds": timing_limit,
        "timing_quality_flag": overshoot > timing_limit,
        "iterations": int(state.iterations),
        "iterations_per_second": int(state.iterations) / cumulative,
        "terminal_visits": terminal_visits,
        "terminal_visits_per_second": (
            float(terminal_visits) / cumulative if terminal_visits is not None else None
        ),
        "policy_ev": float(result.policy_ev),
        "br0_value": float(result.br0_value),
        "br1_value": float(result.br1_value),
        "exploitability_per_pot": float(result.exploitability_per_pot),
        "evaluation_seconds": evaluation_seconds,
        "affinity": affinity,
        **memory,
    }
    output_path.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "algorithm": algorithm,
        "board": board_name,
        "support": support,
        "phase": phase_name,
        "iterations": row["iterations"],
        "train_seconds": row["cumulative_train_seconds"],
        "exploitability_per_pot": row["exploitability_per_pot"],
    }, sort_keys=True))


def expected_public_coordinates(config: dict[str, Any]) -> list[dict[str, Any]]:
    validate_config(config)
    cells: list[dict[str, Any]] = []
    for board_name in config["boards"]:
        for support in config["range_combos_per_player"]:
            for phase in config["phases"]:
                cells.append({
                    "board": board_name,
                    "support": int(support),
                    "phase": str(phase["name"]),
                    "p0_phase": float(phase["p0_phase"]),
                    "p1_phase": float(phase["p1_phase"]),
                    "sampling_seed": int(phase["sampling_seed"]),
                })
    if len(cells) != 24:
        raise RuntimeError(f"expected 24 frozen public cells, got {len(cells)}")
    return cells


def validate_complete(rows: list[dict[str, Any]]) -> None:
    expected = 24 * len(ALGORITHMS)
    if len(rows) != expected:
        raise RuntimeError(f"incomplete physical crossover: {len(rows)} != {expected}")
    identities = {
        (row["board"], row["support"], row["phase"], row["algorithm"])
        for row in rows
    }
    if len(identities) != expected:
        raise RuntimeError("duplicate/missing physical cell identities")


def pairwise_for_support(rows: list[dict[str, Any]], support: int) -> dict[str, Any]:
    selected = [row for row in rows if int(row["support"]) == support]
    lookup = {
        (row["board"], row["phase"], row["algorithm"]): row
        for row in selected
    }
    out: dict[str, Any] = {}
    for left in ALGORITHMS:
        out[left] = {}
        for right in ALGORITHMS:
            if left == right:
                continue
            diffs: list[float] = []
            wins = 0
            for board_name in EXPECTED_BOARDS:
                for phase_name, _, _, _ in EXPECTED_PHASES:
                    lrow = lookup[(board_name, phase_name, left)]
                    rrow = lookup[(board_name, phase_name, right)]
                    diff = float(lrow["exploitability_per_pot"]) - float(
                        rrow["exploitability_per_pot"]
                    )
                    diffs.append(diff)
                    wins += int(diff < 0.0)
            out[left][right] = {
                "cells": len(diffs),
                "strict_wins": wins,
                "mean_difference_left_minus_right": statistics.fmean(diffs),
                "median_difference_left_minus_right": statistics.median(diffs),
            }
    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for support in EXPECTED_SUPPORTS:
        support_rows = [row for row in rows if int(row["support"]) == support]
        algorithms: dict[str, Any] = {}
        for algorithm in ALGORITHMS:
            subset = [row for row in support_rows if row["algorithm"] == algorithm]
            exps = [float(row["exploitability_per_pot"]) for row in subset]
            algorithms[algorithm] = {
                "cells": len(subset),
                "mean_exploitability_per_pot": statistics.fmean(exps),
                "median_exploitability_per_pot": statistics.median(exps),
                "worst_exploitability_per_pot": max(exps),
                "mean_train_seconds": statistics.fmean(
                    float(row["cumulative_train_seconds"]) for row in subset
                ),
                "mean_iterations_per_second": statistics.fmean(
                    float(row["iterations_per_second"]) for row in subset
                ),
                "peak_working_set_bytes_max": max(
                    int(row["peak_working_set_bytes"]) for row in subset
                ),
                "timing_quality_flags": sum(
                    bool(row["timing_quality_flag"]) for row in subset
                ),
            }
        summary[str(support)] = {
            "algorithms": algorithms,
            "pairwise": pairwise_for_support(rows, support),
        }
    return summary


def classify_support(support_summary: dict[str, Any]) -> dict[str, Any]:
    algorithms = support_summary["algorithms"]
    pairwise = support_summary["pairwise"]
    means = {
        name: float(algorithms[name]["mean_exploitability_per_pot"])
        for name in ALGORITHMS
    }
    minimum = min(means.values())
    leaders: list[str] = []
    for name in ALGORITHMS:
        lowest_mean = math.isclose(means[name], minimum, rel_tol=0.0, abs_tol=1e-15)
        paired_ok = all(
            int(pairwise[name][other]["strict_wins"]) >= REQUIRED_PAIRED_WINS
            for other in ALGORITHMS
            if other != name
        )
        if lowest_mean and paired_ok:
            leaders.append(name)
    if len(leaders) == 1:
        return {
            "status": "RESOLVED",
            "leader": leaders[0],
            "required_paired_wins": REQUIRED_PAIRED_WINS,
        }
    return {
        "status": "UNRESOLVED",
        "leader": None,
        "required_paired_wins": REQUIRED_PAIRED_WINS,
    }


def frozen_decision(rows: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    timing_flags = sum(bool(row["timing_quality_flag"]) for row in rows)
    support_decisions = {
        str(support): classify_support(summary[str(support)])
        for support in EXPECTED_SUPPORTS
    }
    if timing_flags:
        decision = "TIMING_REVIEW_REQUIRED"
    elif any(item["status"] != "RESOLVED" for item in support_decisions.values()):
        decision = "UNRESOLVED_REPEAT_SEPARATELY_FROZEN_LONGER_GATE"
    else:
        leaders = [item["leader"] for item in support_decisions.values()]
        decision = (
            f"RESOLVED_UNIFORM_{leaders[0]}"
            if len(set(leaders)) == 1
            else "RESOLVED_SUPPORT_DEPENDENT_CROSSOVER"
        )
    return {
        "decision": decision,
        "timing_quality_flags": timing_flags,
        "support_decisions": support_decisions,
        "scope": "physical river-control crossover; not standalone R5/R8/READY_FOR_TABLES PASS",
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "cell_index", "board", "support", "phase", "algorithm", "sampling_seed",
        "compatible_deal_count", "requested_budget_seconds", "cumulative_train_seconds",
        "timing_overshoot_seconds", "timing_quality_flag", "iterations",
        "iterations_per_second", "terminal_visits", "terminal_visits_per_second",
        "policy_ev", "br0_value", "br1_value", "exploitability_per_pot",
        "evaluation_seconds", "peak_working_set_bytes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fields})


def parent_run(config_path: Path, out_root: Path) -> Path:
    config = load_json(config_path)
    validate_config(config)
    metadata = machine_metadata()
    if metadata["git_tracked_status_porcelain"]:
        raise RuntimeError("tracked repository files are dirty; commit/revert before physical run")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"r5_physical_ryzen_crossover_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "cells").mkdir()
    (run_dir / "logs").mkdir()

    manifest = {
        "schema": "DEEPCASH_R5_PHYSICAL_RYZEN_CROSSOVER_RUN_MANIFEST_V1",
        "started_unix": time.time(),
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "machine": metadata,
        "config": config,
    }
    (run_dir / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rows: list[dict[str, Any]] = []
    public_cells = expected_public_coordinates(config)
    total = len(public_cells) * len(ALGORITHMS)
    completed = 0
    for cell_index, cell in enumerate(public_cells):
        offset = cell_index % len(ALGORITHMS)
        order = list(ALGORITHMS[offset:] + ALGORITHMS[:offset])
        for algorithm in order:
            completed += 1
            stem = f"cell_{cell_index:03d}_{cell['board']}_s{cell['support']}_{cell['phase']}_{algorithm}"
            input_path = run_dir / "cells" / f"{stem}.input.json"
            output_path = run_dir / "cells" / f"{stem}.json"
            log_path = run_dir / "logs" / f"{stem}.log"
            payload = {
                **cell,
                "cell_index": cell_index,
                "algorithm": algorithm,
                "config_path": str(config_path),
            }
            input_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(
                f"[physical {completed}/{total}] board={cell['board']} support={cell['support']} "
                f"phase={cell['phase']} algorithm={algorithm}",
                flush=True,
            )
            cp = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--config",
                    str(config_path),
                    "--worker-input",
                    str(input_path),
                    "--worker-output",
                    str(output_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            log_path.write_text(
                "STDOUT\n======\n" + cp.stdout + "\nSTDERR\n======\n" + cp.stderr,
                encoding="utf-8",
            )
            if cp.returncode != 0:
                raise RuntimeError(f"physical crossover worker failed: {stem}; inspect {log_path}")
            rows.append(load_json(output_path))

    validate_complete(rows)
    summary = summarize(rows)
    decision = frozen_decision(rows, summary)
    result_payload = {
        "schema": SCHEMA,
        "status": "COMPLETE_PHYSICAL_EVIDENCE_NOT_STANDALONE_R5_PASS",
        "config_sha256": sha256_file(config_path),
        "machine": metadata,
        "rows": rows,
        "summary_by_support": summary,
        "frozen_decision": decision,
        "scope_warning": config["scope_warning"],
    }
    (run_dir / "RESULT.json").write_text(
        json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_csv(run_dir / "RESULTS.csv", rows)

    hashes: list[str] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            hashes.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    (run_dir / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")

    zip_path = run_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(run_dir.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=f"{run_dir.name}/{path.relative_to(run_dir).as_posix()}")

    print("\nR5 physical Ryzen crossover complete")
    print(f"DECISION={decision['decision']}")
    print(f"RUN_DIR={run_dir}")
    print(f"UPLOAD_ME={zip_path}")
    print(f"ZIP_SHA256={sha256_file(zip_path)}")
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepCash frozen R5 physical Ryzen crossover v1")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-root", type=Path, default=ROOT / "r5_ryzen_runs")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--worker-input", type=Path)
    parser.add_argument("--worker-output", type=Path)
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = load_json(config_path)
    validate_config(config)

    if args.preflight:
        metadata = machine_metadata()
        if metadata["git_tracked_status_porcelain"]:
            raise RuntimeError("tracked repository files are dirty")
        print(json.dumps({
            "config_sha256": sha256_file(config_path),
            "git_head": metadata["git_head"],
            "instrumentation": validate_instrumentation(),
        }, sort_keys=True))
        return 0

    if args.worker_input or args.worker_output:
        if not args.worker_input or not args.worker_output:
            parser.error("worker mode requires both --worker-input and --worker-output")
        worker_run(load_json(args.worker_input), args.worker_output)
        return 0

    parent_run(config_path, args.out_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
