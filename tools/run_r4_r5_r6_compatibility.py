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
from types import SimpleNamespace
from typing import Any

from deepcash_core.cards import card_to_str
from deepcash_core.r4_representation_gen2_freeze import load_generation2_finalist_freeze
from deepcash_core.river_alternating_dcfr import (
    AlternatingVariant,
    advance_alternating_solver,
    alternating_solver_result,
    init_alternating_solver,
)
from deepcash_core.river_benchmark_fixtures import restriction_loss_bounds
from deepcash_core.river_representation_alternating_dcfr import (
    advance_alternating_representation_solver,
    alternating_representation_result,
    alternating_representation_state_to_dict,
    init_alternating_representation_solver,
)
from deepcash_core.river_representation_gen2 import gen2_candidate_bucket_maps
from deepcash_core.river_representation_lab import one_sided_bucket_maps
from deepcash_core.turn_river_public_state import build_turn_public_state, enumerate_river_children

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "deepcash_core" / "data" / "r4_r5_r6_compatibility_v1.json"
FINALIST_FREEZE = ROOT / "deepcash_core" / "data" / "r4_representation_generation2_finalists_v1.json"
EXPECTED_CANDIDATES = ["matchup_cluster8", "equity8"]
EXPECTED_VARIANT = AlternatingVariant.ALT_DCFR_150_0_2


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_git(*args: str) -> str:
    try:
        cp = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True)
        return cp.stdout.strip()
    except Exception:
        return ""


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
                kernel32.GetCurrentProcess(), ctypes.byref(process_mask), ctypes.byref(system_mask)
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
        "git_head": run_git("rev-parse", "HEAD"),
        "git_tracked_status_porcelain": run_git("status", "--porcelain", "--untracked-files=no"),
    }


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != "DEEPCASH_R4_R5_R6_COMPATIBILITY_V1":
        raise ValueError("unexpected compatibility config schema")
    if config.get("status") != "FROZEN_BEFORE_PHYSICAL_RESULT":
        raise ValueError("compatibility config is not frozen")
    if config.get("candidates") != EXPECTED_CANDIDATES:
        raise ValueError("R4 compatibility candidate freeze drift")
    if config.get("solver_variant") != EXPECTED_VARIANT.value:
        raise ValueError("R5 solver variant drift")
    if config.get("spr_to_stack") != {"1": 100, "2": 200, "4": 400}:
        raise ValueError("SPR geometry drift")
    if len(config.get("turn_boards", {})) != 4:
        raise ValueError("expected exactly four frozen turn boards")
    if int(config.get("river_children_per_turn_state", 0)) != 2:
        raise ValueError("expected exactly two selected river children per turn state")
    if int(config.get("parallel_candidate_workers", 0)) != 1:
        raise ValueError("compatibility candidate workers must be sequential")
    if int(config.get("reference_iterations_per_river_child", 0)) <= 0:
        raise ValueError("reference iterations must be positive")
    if float(config.get("candidate_wall_budget_seconds_per_river_child", 0.0)) <= 0.0:
        raise ValueError("candidate wall budget must be positive")
    if int(config.get("candidate_chunk_iterations", 0)) <= 0:
        raise ValueError("candidate chunk must be positive")


def build_turn_state(config: dict[str, Any], board_text: str, phase: dict[str, Any], stack: int):
    return build_turn_public_state(
        board_text=board_text,
        p0_phase=float(phase["p0_phase"]),
        p1_phase=float(phase["p1_phase"]),
        range_combos=int(config["range_combos_per_player"]),
        pot=int(config["pot"]),
        stack=int(stack),
        min_bet=int(config["min_bet"]),
    )


def selected_children(config: dict[str, Any], state):
    children = list(enumerate_river_children(state))
    children.sort(key=lambda child: (-child.chance_mass, child.river_card))
    count = int(config["river_children_per_turn_state"])
    if len(children) < count:
        raise RuntimeError("insufficient legal river children")
    return tuple(children[:count])


def train_exact_reference(spec, iterations: int) -> dict[str, Any]:
    state = init_alternating_solver(spec, EXPECTED_VARIANT)
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    advance_alternating_solver(spec, state, additional_iterations=iterations)
    train_wall = time.perf_counter() - started_wall
    train_cpu = time.process_time() - started_cpu
    result = alternating_solver_result(spec, state)
    return {
        "variant": EXPECTED_VARIANT.value,
        "iterations": result.iterations,
        "br0_value": result.br0_value,
        "br1_value": result.br1_value,
        "policy_ev": result.policy_ev,
        "exploitability": result.exploitability,
        "exploitability_per_pot": result.exploitability_per_pot,
        "value_interval_width_per_pot": (result.br0_value - result.br1_value) / float(spec.pot),
        "infosets": result.infosets,
        "action_slots": result.action_slots,
        "train_wall_seconds": train_wall,
        "train_cpu_seconds": train_cpu,
    }


def write_checkpoint(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    started = time.perf_counter()
    path.write_bytes(encoded)
    write_seconds = time.perf_counter() - started
    started = time.perf_counter()
    reread = path.read_bytes()
    read_seconds = time.perf_counter() - started
    if reread != encoded:
        raise RuntimeError("checkpoint readback mismatch")
    size = len(encoded)
    return {
        "checkpoint_file": path.name,
        "checkpoint_bytes": size,
        "checkpoint_sha256": sha256_bytes(encoded),
        "checkpoint_write_seconds": write_seconds,
        "checkpoint_read_seconds": read_seconds,
        "checkpoint_write_mib_s": (size / 1048576.0) / max(write_seconds, 1e-12),
        "checkpoint_read_mib_s": (size / 1048576.0) / max(read_seconds, 1e-12),
    }


def worker_run(payload: dict[str, Any], output_path: Path) -> None:
    validate_instrumentation()
    config = payload["config"]
    state = build_turn_state(config, str(payload["turn_board_text"]), payload["phase_config"], int(payload["stack"]))
    children = selected_children(config, state)
    child = next((item for item in children if item.river_card == int(payload["river_card"])), None)
    if child is None:
        raise RuntimeError("worker river child is not in deterministic selected set")
    spec = child.spec

    candidate_name = str(payload["candidate"])
    maps = gen2_candidate_bucket_maps(spec, candidate_name)
    p0_maps = one_sided_bucket_maps(spec, maps, 0)
    p1_maps = one_sided_bucket_maps(spec, maps, 1)
    p0_state = init_alternating_representation_solver(spec, p0_maps, EXPECTED_VARIANT)
    p1_state = init_alternating_representation_solver(spec, p1_maps, EXPECTED_VARIANT)
    joint_state = init_alternating_representation_solver(spec, maps, EXPECTED_VARIANT)

    budget = float(config["candidate_wall_budget_seconds_per_river_child"])
    chunk = int(config["candidate_chunk_iterations"])
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    cycles = 0
    while True:
        advance_alternating_representation_solver(spec, p0_maps, p0_state, additional_iterations=chunk)
        advance_alternating_representation_solver(spec, p1_maps, p1_state, additional_iterations=chunk)
        advance_alternating_representation_solver(spec, maps, joint_state, additional_iterations=chunk)
        cycles += 1
        if time.perf_counter() - started_wall >= budget:
            break
    train_wall = time.perf_counter() - started_wall
    train_cpu = time.process_time() - started_cpu

    eval_started = time.perf_counter()
    p0_result = alternating_representation_result(spec, p0_maps, p0_state)
    p1_result = alternating_representation_result(spec, p1_maps, p1_state)
    joint_result = alternating_representation_result(spec, maps, joint_state)
    eval_wall = time.perf_counter() - eval_started

    reference = payload["reference"]
    ref = SimpleNamespace(br0_value=float(reference["br0_value"]), br1_value=float(reference["br1_value"]))
    bounds = restriction_loss_bounds(ref, p0_result, p1_result, int(config["pot"]))
    interval_width = max(
        float(reference["br0_value"]) - float(reference["br1_value"]),
        p0_result.br0_value - p0_result.br1_value,
        p1_result.br0_value - p1_result.br1_value,
    ) / float(config["pot"])

    checkpoint_path = output_path.with_suffix(".checkpoint.json")
    checkpoint = write_checkpoint(
        checkpoint_path,
        alternating_representation_state_to_dict(joint_state),
    )
    memory = process_memory()
    affinity = process_affinity()
    if memory is None or int(memory.get("peak_working_set_bytes", 0)) <= 0:
        raise RuntimeError("candidate memory instrumentation failed")
    if os.name == "nt" and not affinity:
        raise RuntimeError("candidate affinity instrumentation failed")

    result = {
        "schema": "DEEPCASH_R4_R5_R6_COMPATIBILITY_CELL_V1",
        "cell_index": int(payload["cell_index"]),
        "turn_board": payload["turn_board"],
        "turn_board_text": payload["turn_board_text"],
        "phase": payload["phase"],
        "candidate": candidate_name,
        "solver_variant": EXPECTED_VARIANT.value,
        "river_card": int(payload["river_card"]),
        "river_card_text": card_to_str(int(payload["river_card"])),
        "river_chance_mass": child.chance_mass,
        "river_chance_probability": child.chance_probability,
        "pot": int(config["pot"]),
        "stack": int(payload["stack"]),
        "spr": float(payload["spr"]),
        "bet_sizes": list(spec.bet_sizes),
        "budget_seconds": budget,
        "chunk_iterations": chunk,
        "cycles": cycles,
        "iterations_each_state": joint_state.iterations,
        "train_wall_seconds": train_wall,
        "train_cpu_seconds": train_cpu,
        "budget_overshoot_seconds": train_wall - budget,
        "joint_iterations_per_second": joint_state.iterations / max(train_wall, 1e-12),
        "p0_buckets": maps.p0_bucket_count,
        "p1_buckets": maps.p1_bucket_count,
        "joint_infosets": joint_result.infosets,
        "joint_action_slots": joint_result.action_slots,
        "joint_action_slot_ratio": joint_result.action_slots / float(reference["action_slots"]),
        "joint_exploitability_per_pot": joint_result.exploitability_per_pot,
        "max_value_interval_width_per_pot": interval_width,
        "evaluation_wall_seconds": eval_wall,
        "affinity": affinity,
        "reference": reference,
        **memory,
        **bounds,
        **checkpoint,
    }
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate": candidate_name,
        "turn_board": payload["turn_board"],
        "river": result["river_card_text"],
        "phase": payload["phase"],
        "spr": result["spr"],
        "iterations": result["iterations_each_state"],
        "worst_upper_per_pot": result["worst_loss_upper_per_pot"],
        "peak_working_set_bytes": result["peak_working_set_bytes"],
    }, sort_keys=True))


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return ordered[lo]
    frac = position - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def summarize(rows: list[dict[str, Any]], candidates: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for candidate in candidates:
        selected = [row for row in rows if row["candidate"] == candidate]
        losses = [float(row["worst_loss_upper_per_pot"]) for row in selected]
        throughput = [float(row["joint_iterations_per_second"]) for row in selected]
        peaks = [int(row["peak_working_set_bytes"]) for row in selected]
        slots = [float(row["joint_action_slot_ratio"]) for row in selected]
        intervals = [float(row["max_value_interval_width_per_pot"]) for row in selected]
        out[candidate] = {
            "cells": len(selected),
            "mean_loss_upper_per_pot": statistics.fmean(losses),
            "p90_loss_upper_per_pot": percentile(losses, 0.90),
            "worst_loss_upper_per_pot": max(losses),
            "mean_joint_iterations_per_second": statistics.fmean(throughput),
            "median_iterations_each_state": statistics.median(int(row["iterations_each_state"]) for row in selected),
            "mean_action_slot_ratio": statistics.fmean(slots),
            "peak_working_set_bytes_mean": statistics.fmean(peaks),
            "peak_working_set_bytes_max": max(peaks),
            "mean_resolution_interval_per_pot": statistics.fmean(intervals),
        }
    return out


def parent_run(config_path: Path, out_root: Path) -> Path:
    config = load_json(config_path)
    validate_config(config)
    freeze = load_generation2_finalist_freeze(FINALIST_FREEZE)
    frozen_finalists = set(freeze["selection"]["finalists"])
    if not set(config["candidates"]).issubset(frozen_finalists):
        raise RuntimeError("compatibility candidates are outside the immutable R4 finalist freeze")

    metadata = machine_metadata()
    if metadata["git_tracked_status_porcelain"]:
        raise RuntimeError("tracked repository files are dirty; commit/revert before physical compatibility run")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"r4_r5_r6_compatibility_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "cells").mkdir()
    (run_dir / "logs").mkdir()
    (run_dir / "references").mkdir()

    manifest = {
        "schema": "DEEPCASH_R4_R5_R6_COMPATIBILITY_RUN_V1",
        "started_unix": time.time(),
        "config_sha256": sha256_file(config_path),
        "finalist_freeze_sha256": sha256_file(FINALIST_FREEZE),
        "config": config,
        "machine": metadata,
    }
    (run_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    child_cells: list[dict[str, Any]] = []
    for phase in config["phases"]:
        for spr_text, stack_value in config["spr_to_stack"].items():
            stack = int(stack_value)
            for turn_name, turn_text in config["turn_boards"].items():
                turn_state = build_turn_state(config, turn_text, phase, stack)
                for child_rank, child in enumerate(selected_children(config, turn_state)):
                    child_cells.append({
                        "phase": phase,
                        "spr": spr_text,
                        "stack": stack,
                        "turn_name": turn_name,
                        "turn_text": turn_text,
                        "child_rank": child_rank,
                        "child": child,
                    })

    if len(child_cells) != 48:
        raise RuntimeError(f"expected 48 frozen river-child cells, got {len(child_cells)}")

    rows: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    candidates = list(config["candidates"])
    total_candidate_runs = len(child_cells) * len(candidates)
    completed = 0

    for cell_index, cell in enumerate(child_cells):
        child = cell["child"]
        print(
            f"[reference] child={cell_index+1}/{len(child_cells)} turn={cell['turn_name']} "
            f"river={card_to_str(child.river_card)} phase={cell['phase']['name']} spr={cell['spr']}",
            flush=True,
        )
        reference = train_exact_reference(child.spec, int(config["reference_iterations_per_river_child"]))
        ref_row = {
            "cell_index": cell_index,
            "turn_board": cell["turn_name"],
            "turn_board_text": cell["turn_text"],
            "phase": cell["phase"]["name"],
            "spr": float(cell["spr"]),
            "stack": cell["stack"],
            "river_child_rank": cell["child_rank"],
            "river_card": child.river_card,
            "river_card_text": card_to_str(child.river_card),
            "river_chance_mass": child.chance_mass,
            "river_chance_probability": child.chance_probability,
            "bet_sizes": list(child.spec.bet_sizes),
            **reference,
        }
        references.append(ref_row)
        ref_path = run_dir / "references" / f"ref_{cell_index:03d}_{cell['phase']['name']}_spr{cell['spr']}_{cell['turn_name']}_{card_to_str(child.river_card)}.json"
        ref_path.write_text(json.dumps(ref_row, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        offset = cell_index % len(candidates)
        order = candidates[offset:] + candidates[:offset]
        for candidate in order:
            completed += 1
            river_text = card_to_str(child.river_card)
            stem = f"cell_{cell_index:03d}_{cell['phase']['name']}_spr{cell['spr']}_{cell['turn_name']}_{river_text}_{candidate}"
            input_path = run_dir / "cells" / f"{stem}.input.json"
            output_path = run_dir / "cells" / f"{stem}.json"
            log_path = run_dir / "logs" / f"{stem}.log"
            payload = {
                "cell_index": cell_index,
                "turn_board": cell["turn_name"],
                "turn_board_text": cell["turn_text"],
                "phase": cell["phase"]["name"],
                "phase_config": cell["phase"],
                "spr": float(cell["spr"]),
                "stack": cell["stack"],
                "river_card": child.river_card,
                "candidate": candidate,
                "reference": reference,
                "config": config,
            }
            input_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(
                f"[candidate {completed}/{total_candidate_runs}] {candidate} turn={cell['turn_name']} "
                f"river={river_text} phase={cell['phase']['name']} spr={cell['spr']}",
                flush=True,
            )
            cp = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker-input", str(input_path), "--worker-output", str(output_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            log_path.write_text(
                "STDOUT\n======\n" + cp.stdout + "\nSTDERR\n======\n" + cp.stderr,
                encoding="utf-8",
            )
            if cp.returncode != 0:
                raise RuntimeError(f"compatibility candidate worker failed: {stem}; inspect {log_path}")
            rows.append(load_json(output_path))

    summary = summarize(rows, candidates)
    payload = {
        "schema": "DEEPCASH_R4_R5_R6_COMPATIBILITY_SUMMARY_V1",
        "config_sha256": sha256_file(config_path),
        "machine": metadata,
        "river_child_cells": len(child_cells),
        "candidate_cell_runs": len(rows),
        "candidates": candidates,
        "solver_variant": EXPECTED_VARIANT.value,
        "summary": summary,
        "scope_warning": config["scope_warning"],
    }
    (run_dir / "SUMMARY.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fieldnames = [
        "cell_index", "turn_board", "phase", "river_card_text", "river_chance_probability",
        "candidate", "solver_variant", "spr", "stack", "bet_sizes", "budget_seconds",
        "train_wall_seconds", "budget_overshoot_seconds", "iterations_each_state",
        "joint_iterations_per_second", "peak_working_set_bytes", "joint_infosets",
        "joint_action_slots", "joint_action_slot_ratio", "joint_exploitability_per_pot",
        "max_value_interval_width_per_pot", "worst_loss_upper_per_pot", "checkpoint_bytes",
        "checkpoint_write_mib_s", "checkpoint_read_mib_s", "checkpoint_sha256",
    ]
    with (run_dir / "RESULTS.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flat = {key: row.get(key) for key in fieldnames}
            flat["bet_sizes"] = ",".join(str(value) for value in row["bet_sizes"])
            writer.writerow(flat)

    hashes = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            hashes.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    (run_dir / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")

    zip_path = run_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(run_dir.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=f"{run_dir.name}/{path.relative_to(run_dir).as_posix()}")

    print("\nR4/R5/R6 physical compatibility run complete")
    print(f"RUN_DIR={run_dir}")
    print(f"UPLOAD_ME={zip_path}")
    print(f"ZIP_SHA256={sha256_file(zip_path)}")
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepCash R4/R5/R6 physical compatibility runner")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-root", type=Path, default=ROOT / "r4_ryzen_runs")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--worker-input", type=Path)
    parser.add_argument("--worker-output", type=Path)
    args = parser.parse_args()

    if args.preflight:
        config = load_json(args.config.resolve())
        validate_config(config)
        print(json.dumps({"instrumentation": validate_instrumentation(), "config_sha256": sha256_file(args.config.resolve())}, sort_keys=True))
        return 0

    if args.worker_input or args.worker_output:
        if not args.worker_input or not args.worker_output:
            parser.error("worker mode requires both --worker-input and --worker-output")
        worker_run(load_json(args.worker_input), args.worker_output)
        return 0

    parent_run(args.config.resolve(), args.out_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
