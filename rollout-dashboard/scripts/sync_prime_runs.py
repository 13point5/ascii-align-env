#!/usr/bin/env python3
"""Sync Prime RL runs into rollout-dashboard/public/mock-data.json deterministically.

Usage:
  python scripts/sync_prime_runs.py --run-id <run_id>
  python scripts/sync_prime_runs.py --run-id <id1> --run-id <id2> --steps last3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _run_json(cmd: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env["COLUMNS"] = "100000"
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}")

    cleaned = ANSI_RE.sub("", proc.stdout).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        snippet = cleaned[:1000]
        raise RuntimeError(f"Failed to parse JSON from {' '.join(cmd)}: {exc}\nOutput snippet:\n{snippet}") from exc


def _parse_json_field(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _extract_messages(sample: dict[str, Any]) -> dict[str, str]:
    prompt = _parse_json_field(sample.get("prompt"), [])
    completion = _parse_json_field(sample.get("completion"), [])

    system_text = ""
    user_text = ""
    assistant_text = ""

    if isinstance(prompt, list):
        for message in prompt:
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            content = message.get("content") or ""
            if role == "system" and not system_text:
                system_text = str(content)
            if role == "user":
                user_text = str(content)

    if isinstance(completion, list):
        for message in completion:
            if not isinstance(message, dict):
                continue
            if message.get("role") == "assistant":
                assistant_text = str(message.get("content") or "")
                break

    return {
        "system": system_text,
        "user": user_text,
        "assistant": assistant_text,
    }


def _to_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalize_rollout(sample: dict[str, Any], run_id: str, step: int, idx: int) -> dict[str, Any]:
    metrics = _parse_json_field(sample.get("metrics"), {})
    info = _parse_json_field(sample.get("info"), {})
    timing = _parse_json_field(sample.get("timing"), {})
    messages = _extract_messages(sample)

    stable_id = (
        f"{run_id}:{step}:{sample.get('problem_id', 'na')}:{sample.get('sample_id', 'na')}:{idx}"
    )

    return {
        "id": stable_id,
        "problem_id": sample.get("problem_id"),
        "sample_id": sample.get("sample_id"),
        "reward": sample.get("reward"),
        "metrics": metrics if isinstance(metrics, dict) else {},
        "info": info if isinstance(info, dict) else {},
        "timing_ms": timing if isinstance(timing, dict) else {},
        "messages": messages,
        "created_at": sample.get("created_at"),
    }


def _summarize_step(rollouts: list[dict[str, Any]]) -> dict[str, float | int | None]:
    rewards = [_to_number(r.get("reward")) for r in rollouts]
    rewards = [x for x in rewards if x is not None]

    misaligned = []
    aligned = []
    for rollout in rollouts:
        metrics = rollout.get("metrics") or {}
        if not isinstance(metrics, dict):
            continue
        mis = _to_number(metrics.get("misaligned_total_metric"))
        ali = _to_number(metrics.get("alignment_reward"))
        if mis is not None:
            misaligned.append(mis)
        if ali is not None:
            aligned.append(ali)

    def avg(values: list[float]) -> float | None:
        return round(statistics.mean(values), 4) if values else None

    return {
        "count": len(rollouts),
        "reward_mean": avg(rewards),
        "reward_min": round(min(rewards), 4) if rewards else None,
        "reward_max": round(max(rewards), 4) if rewards else None,
        "misaligned_mean": avg(misaligned),
        "alignment_mean": avg(aligned),
    }


def _select_steps(progress: dict[str, Any], mode: str) -> list[int]:
    steps = sorted({int(s) for s in (progress.get("steps_with_samples") or [])})
    if mode == "last3":
        return steps[-3:]
    return steps


def fetch_run(run_id: str, steps_mode: str, sample_limit: int) -> dict[str, Any]:
    run_payload = _run_json(["prime", "rl", "get", run_id, "-o", "json"])
    progress = _run_json(["prime", "rl", "progress", run_id])
    checkpoints_payload = _run_json(["prime", "rl", "checkpoints", run_id, "-o", "json"])

    run = run_payload.get("run")
    if not isinstance(run, dict):
        raise RuntimeError(f"Missing run object for run_id={run_id}")

    checkpoints_raw = checkpoints_payload.get("checkpoints") or []
    checkpoints = []
    for checkpoint in checkpoints_raw:
        if not isinstance(checkpoint, dict):
            continue
        checkpoints.append(
            {
                "id": checkpoint.get("id"),
                "step": checkpoint.get("step"),
                "status": checkpoint.get("status"),
                "size_bytes": checkpoint.get("size_bytes"),
                "uploaded_at": checkpoint.get("uploaded_at"),
            }
        )

    steps = _select_steps(progress, steps_mode)
    rollouts_by_step: dict[str, list[dict[str, Any]]] = {}
    step_summary: dict[str, dict[str, Any]] = {}

    for step in steps:
        rollout_payload = _run_json(
            ["prime", "rl", "rollouts", run_id, "-s", str(step), "-n", str(sample_limit)]
        )
        samples = rollout_payload.get("samples") or []
        normalized = [
            _normalize_rollout(sample, run_id, step, idx)
            for idx, sample in enumerate(samples)
            if isinstance(sample, dict)
        ]
        rollouts_by_step[str(step)] = normalized
        step_summary[str(step)] = _summarize_step(normalized)

    environments = run.get("environments") or []
    environment_id = None
    if isinstance(environments, list) and environments and isinstance(environments[0], dict):
        environment_id = environments[0].get("id")

    return {
        "id": run.get("id"),
        "name": run.get("name"),
        "status": run.get("status"),
        "model": run.get("base_model"),
        "environment": environment_id,
        "max_steps": run.get("max_steps"),
        "rollouts_per_example": run.get("rollouts_per_example"),
        "created_at": run.get("created_at"),
        "completed_at": run.get("completed_at"),
        "checkpoints": checkpoints,
        "rollouts_by_step": rollouts_by_step,
        "step_summary": step_summary,
    }


def merge_runs(existing: dict[str, Any], incoming: list[dict[str, Any]]) -> dict[str, Any]:
    runs = existing.get("runs")
    if not isinstance(runs, list):
        runs = []

    index_by_id = {
        run.get("id"): idx
        for idx, run in enumerate(runs)
        if isinstance(run, dict) and run.get("id") is not None
    }

    for run in incoming:
        run_id = run.get("id")
        if run_id in index_by_id:
            runs[index_by_id[run_id]] = run
        else:
            index_by_id[run_id] = len(runs)
            runs.append(run)

    existing["runs"] = runs

    completed_values = [
        run.get("completed_at")
        for run in runs
        if isinstance(run, dict) and run.get("completed_at")
    ]
    if completed_values:
        existing["generated_at"] = max(str(v) for v in completed_values)

    if "title" not in existing:
        existing["title"] = "Prime RL Rollout Inspector Prototype"
    if "selected_steps" not in existing or not isinstance(existing["selected_steps"], list):
        existing["selected_steps"] = []

    return existing


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Prime RL runs into mock-data.json")
    parser.add_argument(
        "--run-id",
        action="append",
        required=True,
        dest="run_ids",
        help="Prime RL run id (repeatable)",
    )
    parser.add_argument(
        "--data-file",
        default="public/mock-data.json",
        help="Path to mock data JSON file (default: public/mock-data.json)",
    )
    parser.add_argument(
        "--steps",
        choices=["all", "last3"],
        default="all",
        help="Which sample steps to import (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Rollout sample page size for each step (default: 100)",
    )

    args = parser.parse_args()
    data_file = Path(args.data_file).resolve()
    data_file.parent.mkdir(parents=True, exist_ok=True)

    if data_file.exists():
        existing = json.loads(data_file.read_text())
    else:
        existing = {
            "generated_at": None,
            "title": "Prime RL Rollout Inspector Prototype",
            "selected_steps": [],
            "runs": [],
        }

    incoming_runs: list[dict[str, Any]] = []
    for run_id in args.run_ids:
        print(f"[sync] Fetching run {run_id} ...")
        run_obj = fetch_run(run_id=run_id, steps_mode=args.steps, sample_limit=args.limit)
        steps_count = len(run_obj.get("rollouts_by_step", {}))
        samples_count = sum(len(v) for v in run_obj.get("rollouts_by_step", {}).values())
        print(f"[sync]   steps={steps_count} samples={samples_count}")
        incoming_runs.append(run_obj)

    merged = merge_runs(existing, incoming_runs)
    data_file.write_text(json.dumps(merged, indent=2) + "\n")
    print(f"[sync] Wrote {data_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

