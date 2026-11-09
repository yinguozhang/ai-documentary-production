#!/usr/bin/env python3
"""Validate h3_tasks.json against the task contract.

Run:
    python scripts/validate_tasks.py --tasks h3_tasks.json --segments segments.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def read_tasks(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "tasks" in data:
        data = data["tasks"]
    if not isinstance(data, list):
        raise ValueError("tasks must be a JSON list (or {tasks:[...]})")
    return data


def validate_tasks(
    tasks: list[dict[str, Any]],
    segment_ids: set[str] | None = None,
    strict_files: bool = False,
    base_dir: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    base_dir = base_dir or Path.cwd()
    seen: set[str] = set()
    for index, task in enumerate(tasks, 1):
        label = f"tasks[{index}]"
        for field in ("generation_id", "provider", "model", "resolution", "duration", "status", "prompt"):
            if not str(task.get(field, "")).strip():
                errors.append(f"{label}: missing {field}")
        gid = str(task.get("generation_id", "")).strip()
        if gid:
            if gid in seen:
                errors.append(f"tasks: duplicate generation_id {gid}")
            seen.add(gid)
            if segment_ids is not None and gid not in segment_ids:
                errors.append(f"task {gid}: no such generation_id in segments.csv")
        duration = task.get("duration")
        if not isinstance(duration, int) or duration < 4 or duration > 15:
            errors.append(f"{label}: duration must be an integer 4–15, got {duration!r}")
        status = task.get("status")
        if status not in {"todo", "running", "succeeded", "failed", "cancelled"}:
            errors.append(f"{label}: invalid status {status!r}")
        if not isinstance(task.get("first_frames"), list) or not task.get("first_frames"):
            errors.append(f"{label}: first_frames must be a non-empty list")
        if "cost_cny" in task and not isinstance(task["cost_cny"], (int, float)):
            errors.append(f"{label}: cost_cny must be numeric")
        prompt = str(task.get("prompt", "")).strip()
        if strict_files and prompt and not (base_dir / prompt).is_file():
            errors.append(f"{label}: prompt not found: {prompt}")
        for frame in task.get("first_frames") or []:
            if strict_files and frame and not (base_dir / frame).is_file():
                errors.append(f"{label}: first frame not found: {frame}")
    if segment_ids is not None:
        missing = [gid for gid in segment_ids if gid not in seen]
        if missing:
            errors.append(f"tasks: segments without a task: {', '.join(sorted(missing))}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate H3 task JSON")
    parser.add_argument("--tasks", required=True, type=Path)
    parser.add_argument("--segments", type=Path)
    parser.add_argument("--strict-files", action="store_true")
    args = parser.parse_args()

    tasks = read_tasks(args.tasks)
    segment_ids = None
    if args.segments:
        import csv
        with args.segments.open("r", encoding="utf-8-sig", newline="") as handle:
            segment_ids = {
                row["generation_id"]
                for row in csv.DictReader(handle)
                if row.get("generation_id")
                and (row.get("static") or "").strip().lower() not in {"yes", "true", "1"}
            }
    errors = validate_tasks(tasks, segment_ids, args.strict_files, args.tasks.parent)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"tasks: ok; {len(tasks)} tasks")


if __name__ == "__main__":
    main()
