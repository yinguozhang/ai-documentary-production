#!/usr/bin/env python3
"""Build a cost report from task JSON files.

Usage:
  python scripts/cost_report.py --tasks tasks.json
  python scripts/cost_report.py --tasks batch1.json batch2.json --out cost.csv --summary cost_summary.md
  python scripts/cost_report.py --tasks tasks.json --rates rates.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass
from datetime import datetime
from pathlib import Path

from config import load_project


BILLED = {"succeeded", "success", "ok", "done", "completed"}
UNBILLED = {"failed", "failure", "cancelled", "canceled", "error"}


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_rates(path: Path | None, default_rate: float) -> dict[str, float]:
    rates = {"default": default_rate}
    if path is None:
        return rates
    if not path.is_file():
        fail(f"rates file not found: {path}")
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        fail("rates file must be a JSON object")
    for key, value in data.items():
        try:
            rates[str(key)] = float(value)
        except (TypeError, ValueError):
            fail(f"invalid rate for {key}: {value!r}")
    return rates


def read_tasks(path: Path) -> list[dict]:
    if not path.is_file():
        fail(f"tasks file not found: {path}")
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        data = data.get("tasks", [])
    if not isinstance(data, list):
        fail(f"tasks file must be a list or contain a tasks list: {path}")
    return [item for item in data if isinstance(item, dict)]


def number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_status(value) -> str:
    return str(value or "unknown").strip().lower()


def build_rows(paths: list[Path], rates: dict[str, float], default_model: str = "") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        batch = path.stem
        for task in read_tasks(path):
            shot_id = str(task.get("id") or task.get("shot") or "").strip() or "?"
            model = str(task.get("model") or task.get("provider") or default_model or "unknown").strip()
            status = normalize_status(task.get("status"))
            duration = number(task.get("duration") or task.get("seconds"))
            explicit_cost = number(task.get("cost_cny") or task.get("cost"))

            note = ""
            rate = None
            if status in BILLED:
                if explicit_cost is not None:
                    cost = explicit_cost
                    rate = cost / duration if duration else None
                elif duration is not None:
                    rate = rates.get(model, rates["default"])
                    cost = duration * rate
                else:
                    cost = 0.0
                    note = "missing duration"
            else:
                cost = 0.0
                if status in UNBILLED:
                    note = "failed/not billed"
                else:
                    note = "not confirmed; not billed in this report"
            if duration is None:
                note = (note + "; " if note else "") + "missing duration"

            rows.append(
                {
                    "batch": batch,
                    "id": shot_id,
                    "model": model,
                    "duration": f"{duration:.2f}" if duration is not None else "",
                    "status": status,
                    "rate_cny_per_sec": f"{rate:.3f}" if rate is not None else "",
                    "cost_cny": f"{cost:.2f}",
                    "task_id": str(task.get("task_id") or ""),
                    "file": str(task.get("file") or ""),
                    "note": note,
                }
            )
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict], currency: str, budget: float | None = None) -> str:
    succeeded = [row for row in rows if row["status"] in BILLED]
    failed = [row for row in rows if row["status"] in UNBILLED]
    unknown = [row for row in rows if row["status"] not in BILLED | UNBILLED]
    total_seconds = sum(float(row["duration"]) for row in succeeded if row["duration"])
    total_cost = sum(float(row["cost_cny"]) for row in rows)

    by_batch: dict[str, list[float]] = {}
    by_model: dict[str, list[float]] = {}
    for row in succeeded:
        duration = float(row["duration"]) if row["duration"] else 0.0
        cost = float(row["cost_cny"])
        by_batch.setdefault(row["batch"], [0.0, 0.0])
        by_batch[row["batch"]][0] += duration
        by_batch[row["batch"]][1] += cost
        by_model.setdefault(row["model"], [0.0, 0.0])
        by_model[row["model"]][0] += duration
        by_model[row["model"]][1] += cost

    lines = [
        "# Cost report",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- Tasks: {len(rows)}",
        f"- Succeeded: {len(succeeded)}",
        f"- Failed/cancelled: {len(failed)} (not billed)",
        f"- Unknown/running: {len(unknown)} (not billed)",
        f"- Billable seconds: {total_seconds:.2f}",
        f"- Total cost: {currency}{total_cost:.2f}",
        "",
        *([f"- Budget: {currency}{budget:.2f}", f"- Over budget: {currency}{max(0.0, total_cost - budget):.2f}"] if budget else []),
        "",
        "## By batch",
        "",
        "| Batch | Seconds | Cost |",
        "|---|---:|---:|",
    ]
    for batch, (seconds, cost) in sorted(by_batch.items()):
        lines.append(f"| {batch} | {seconds:.2f} | {currency}{cost:.2f} |")
    lines += ["", "## By model", "", "| Model | Seconds | Cost |", "|---|---:|---:|"]
    for model, (seconds, cost) in sorted(by_model.items()):
        lines.append(f"| {model} | {seconds:.2f} | {currency}{cost:.2f} |")
    lines += ["", "> Failed/cancelled and unknown tasks are not billed in this report."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cost.csv and summary from task JSON")
    parser.add_argument("--tasks", required=True, nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("cost.csv"))
    parser.add_argument("--summary", type=Path, default=Path("cost_summary.md"))
    parser.add_argument("--rates", type=Path, default=None, help="JSON mapping model -> CNY/sec")
    parser.add_argument("--rate", type=float, default=0.5, help="default CNY/sec")
    parser.add_argument("--currency", default="¥")
    parser.add_argument("--default-model", default="", help="used when task JSON has no model")
    parser.add_argument("--project", type=Path, default=None, help="optional project.json for budget")
    args = parser.parse_args()

    rates = load_rates(args.rates, args.rate)
    rows = build_rows(args.tasks, rates, args.default_model)
    if not rows:
        fail("no tasks found")
    budget = None
    if args.project is not None:
        project = load_project(args.project)
        budget = float(project.get("budget_cny") or 0) or None
    write_csv(rows, args.out)
    summary = summarize(rows, args.currency, budget)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(summary, encoding="utf-8")
    print(f"cost: {args.out}")
    print(f"summary: {args.summary}")
    print(summary)


if __name__ == "__main__":
    main()
