#!/usr/bin/env python3
"""Compare two vo.csv versions and report the impact."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


REQUIRED = ("vo_id", "start", "end", "text")


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict[str, dict]:
    if not path.is_file():
        fail(f"vo file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail(f"no header: {path}")
        missing = [key for key in REQUIRED if key not in reader.fieldnames]
        if missing:
            fail(f"{path} missing columns: {', '.join(missing)}")
        rows: dict[str, dict] = {}
        for index, raw in enumerate(reader, start=2):
            vo_id = (raw.get("vo_id") or "").strip()
            if not vo_id:
                fail(f"{path} row {index}: empty vo_id")
            if vo_id in rows:
                fail(f"{path} row {index}: duplicate vo_id {vo_id}")
            try:
                start = float((raw.get("start") or "").strip())
                end = float((raw.get("end") or "").strip())
            except ValueError:
                fail(f"{path} row {index}: start/end must be numbers")
            if end <= start:
                fail(f"{path} row {index}: end <= start")
            rows[vo_id] = {
                "vo_id": vo_id,
                "start": start,
                "end": end,
                "text": (raw.get("text") or "").strip(),
                "shot_ids": (raw.get("shot_ids") or "").strip(),
                "notes": (raw.get("notes") or "").strip(),
            }
    return rows


def normalize(text: str) -> str:
    return re.sub(r"[\s，。！？、；：“”‘’…—,.!?;:\"'()\[\]{}]", "", text or "")


def shots(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[|;,]", value or "") if part.strip()]


def cell(text: str) -> str:
    return (text or "").replace("|", "／").replace("\n", " ")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare vo.csv versions")
    parser.add_argument("--old", required=True, type=Path)
    parser.add_argument("--new", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path("vo_diff.md"))
    args = parser.parse_args()

    old = load(args.old)
    new = load(args.new)
    all_ids = sorted(set(old) | set(new))

    rows: list[dict] = []
    affected_shots: set[str] = set()
    text_changed = timing_changed = shot_changed = False

    for vo_id in all_ids:
        if vo_id not in old:
            rows.append(
                {
                    "id": vo_id,
                    "status": "added",
                    "old": "",
                    "new": new[vo_id]["text"],
                    "new_time": f"{new[vo_id]['start']:.3f}-{new[vo_id]['end']:.3f}",
                    "new_shots": new[vo_id]["shot_ids"],
                }
            )
            text_changed = True
            shot_changed = True
            affected_shots.update(shots(new[vo_id]["shot_ids"]))
            continue
        if vo_id not in new:
            rows.append(
                {
                    "id": vo_id,
                    "status": "removed",
                    "old": old[vo_id]["text"],
                    "new": "",
                    "old_time": f"{old[vo_id]['start']:.3f}-{old[vo_id]['end']:.3f}",
                    "old_shots": old[vo_id]["shot_ids"],
                }
            )
            text_changed = True
            shot_changed = True
            affected_shots.update(shots(old[vo_id]["shot_ids"]))
            continue

        before, after = old[vo_id], new[vo_id]
        old_text, new_text = normalize(before["text"]), normalize(after["text"])
        old_timing = (before["start"], before["end"])
        new_timing = (after["start"], after["end"])
        old_shots, new_shots = shots(before["shot_ids"]), shots(after["shot_ids"])

        status = []
        if old_text != new_text:
            status.append("text")
            text_changed = True
        if abs(old_timing[0] - new_timing[0]) > 0.001 or abs(old_timing[1] - new_timing[1]) > 0.001:
            status.append("timing")
            timing_changed = True
        if old_shots != new_shots:
            status.append("shots")
            shot_changed = True
            affected_shots.update(old_shots + new_shots)
        if status:
            rows.append(
                {
                    "id": vo_id,
                    "status": "+".join(status),
                    "old": before["text"],
                    "new": after["text"],
                    "old_time": f"{before['start']:.3f}-{before['end']:.3f}",
                    "new_time": f"{after['start']:.3f}-{after['end']:.3f}",
                    "old_shots": before["shot_ids"],
                    "new_shots": after["shot_ids"],
                }
            )

    old_total = sum(row["end"] - row["start"] for row in old.values())
    new_total = sum(row["end"] - row["start"] for row in new.values())

    if not rows:
        print("no changes")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("# 旁白变更单\n\n无变化。\n", encoding="utf-8")
        print(f"diff: {args.out}")
        return

    must = ["`vo.csv`（已更新）", "`vo_diff.md`（本单）"]
    if text_changed or timing_changed:
        must.append("`subtitles.srt`（重跑 vo2srt）")
        must.append("`vo_report.csv`（重跑 timeline --vo）")
    if timing_changed:
        must.append("`timeline.csv`（重跑 timeline）")
        must.append("`shots.csv` 的镜头时长（检查）")
    if shot_changed:
        must.append("`shots.csv` 的 vo_ids/顺序（检查）")
        must.append("受影响的 `first_frame_prompt.md`（检查）")
    if affected_shots:
        must.append(f"受影响镜号：{', '.join(sorted(affected_shots))}")

    lines = [
        "# 旁白变更单",
        "",
        f"- 旧版：`{args.old}`",
        f"- 新版：`{args.new}`",
        f"- 旧总时长：{old_total:.2f}s",
        f"- 新总时长：{new_total:.2f}s",
        f"- 总时长差：{new_total - old_total:+.2f}s",
        "",
        "## 变更",
        "",
        "| vo_id | 类型 | 旧文本 | 新文本 | 旧时间 | 新时间 | 旧镜头 | 新镜头 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['status']} | {cell(row.get('old', ''))} | "
            f"{cell(row.get('new', ''))} | {row.get('old_time', '')} | {row.get('new_time', '')} | "
            f"{row.get('old_shots', '')} | {row.get('new_shots', '')} |"
        )
    lines += ["", "## 必须重跑/检查", ""]
    lines += [f"- {item}" for item in must]
    lines += [
        "",
        "## 通常不用动",
        "",
        "- 视觉提示词只在 `shots` 类型变化时检查；只改词不改画面时不动。",
        "- 已生成且画面可复用的首帧/素材不重出。",
        "- 不要因为改一句旁白重写全项目。",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"diff: {args.out}")
    print(f"changes: {len(rows)}; total: {old_total:.2f}s -> {new_total:.2f}s ({new_total - old_total:+.2f}s)")
    print(f"text={text_changed} timing={timing_changed} shots={shot_changed}")
    if affected_shots:
        print(f"affected shots: {', '.join(sorted(affected_shots))}")


if __name__ == "__main__":
    main()
