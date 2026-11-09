#!/usr/bin/env python3
"""Report VO gaps before building a v0 animatic.

The CSV report is timing-only. With --audio it also checks the real silence
detected by ffmpeg, so a hand-written vo.csv cannot silently fake a gap.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> list[dict]:
    if not path.is_file():
        fail(f"vo file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail("vo.csv has no header")
        required = ("vo_id", "start", "end", "text")
        missing = [key for key in required if key not in reader.fieldnames]
        if missing:
            fail(f"vo.csv missing columns: {', '.join(missing)}")
        rows = []
        for index, raw in enumerate(reader, start=2):
            vo_id = (raw.get("vo_id") or "").strip()
            if not vo_id:
                fail(f"row {index}: empty vo_id")
            try:
                start = float((raw.get("start") or "").strip())
                end = float((raw.get("end") or "").strip())
            except ValueError:
                fail(f"row {index}: start/end must be numbers")
            if end <= start:
                fail(f"row {index}: end <= start")
            sentences = len(re.findall(r"[。！？!?]", raw.get("text") or ""))
            rows.append(
                {
                    "vo_id": vo_id,
                    "start": start,
                    "end": end,
                    "duration": end - start,
                    "text": (raw.get("text") or "").strip(),
                    "sentences": sentences,
                }
            )
    return sorted(rows, key=lambda row: row["start"])


def audio_duration(path: Path) -> float | None:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(path),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def detect_silences(path: Path, noise_db: float, min_silence: float) -> list[tuple[float, float]]:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-i", str(path),
            "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}",
            "-f", "null", "-",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    starts = [float(value) for value in re.findall(r"silence_start: ([0-9.]+)", result.stderr)]
    ends = [float(value) for value in re.findall(r"silence_end: ([0-9.]+)", result.stderr)]
    duration = audio_duration(path)
    intervals: list[tuple[float, float]] = []
    for index, start in enumerate(starts):
        end = ends[index] if index < len(ends) else (duration or start)
        if end > start:
            intervals.append((start, end))
    return intervals


def main() -> None:
    parser = argparse.ArgumentParser(description="Report VO gaps before an animatic (no separate version)")
    parser.add_argument("--vo", required=True, type=Path)
    parser.add_argument("--audio", type=Path, default=None, help="scratch VO; enables real silence check")
    parser.add_argument("--out", type=Path, default=Path("vo_gap.md"))
    parser.add_argument("--min-gap", type=float, default=0.4)
    parser.add_argument("--target-gap", type=float, default=0.8, help="preferred gap; larger is better")
    parser.add_argument("--max-gap", type=float, default=2.5)
    parser.add_argument("--noise-db", type=float, default=-35.0)
    parser.add_argument("--min-silence", type=float, default=0.15)
    args = parser.parse_args()

    rows = load(args.vo)
    silences: list[tuple[float, float]] = []
    if args.audio is not None:
        if not args.audio.is_file():
            fail(f"audio not found: {args.audio}")
        silences = detect_silences(args.audio, args.noise_db, args.min_silence)
        if not silences:
            print("warning: no silence detected; check threshold or audio", file=sys.stderr)

    report: list[dict] = []
    warnings: list[str] = []
    total_vo = sum(row["duration"] for row in rows)
    between_gaps: list[float] = []
    for index, row in enumerate(rows):
        gap = None
        gap_type = "tail"
        status = "tail"
        audio_silence = None
        if index + 1 < len(rows):
            gap = rows[index + 1]["start"] - row["end"]
            gap_type = "between"
            between_gaps.append(gap)
            if gap < -0.001:
                status = "overlap"
                warnings.append(f"{row['vo_id']} overlaps next cue by {-gap:.2f}s")
            elif gap < args.min_gap:
                status = "short"
                warnings.append(f"gap after {row['vo_id']} is {gap:.2f}s < {args.min_gap:.2f}s")
            elif gap > args.max_gap:
                status = "long"
                warnings.append(f"gap after {row['vo_id']} is {gap:.2f}s > {args.max_gap:.2f}s; check for drag")
            else:
                status = "ok"
            if silences and gap > 0:
                audio_silence = sum(
                    max(0.0, min(row["end"] + gap, end) - max(row["end"], start))
                    for start, end in silences
                )
                if audio_silence < 0.05:
                    warnings.append(
                        f"{row['vo_id']} gap exists only in vo.csv; no real silence detected"
                    )
                elif abs(audio_silence - gap) > 0.15:
                    warnings.append(
                        f"{row['vo_id']} vo.csv gap {gap:.2f}s, audio silence {audio_silence:.2f}s"
                    )
        if row["sentences"] > 1:
            warnings.append(f"{row['vo_id']} has {row['sentences']} sentence ends; use one cue per sentence")
        report.append({
            **row,
            "gap": gap,
            "gap_type": gap_type,
            "status": status,
            "audio_silence": audio_silence,
        })

    last_end = rows[-1]["end"]
    density = total_vo / last_end if last_end > 0 else 0
    below_target = sum(1 for gap in between_gaps if 0 <= gap < args.target_gap)
    gap_min = f"{min(between_gaps):.2f}" if between_gaps else "n/a"
    gap_max = f"{max(between_gaps):.2f}" if between_gaps else "n/a"

    lines = [
        "# 气口报告（v0 animatic 前）",
        "",
        f"- 输入：`{args.vo}`",
        f"- 音频：`{args.audio}`" if args.audio else "- 音频：未提供（只检查时间码）",
        f"- 句数：{len(rows)}",
        f"- 旁白总长：{total_vo:.2f}s",
        f"- 时间轴总长：{last_end:.2f}s",
        f"- 旁白密度：{density:.2f}",
        f"- 句间气口：{gap_min}–{gap_max}s",
        f"- 低于偏好值 {args.target_gap:.2f}s：{below_target}/{len(between_gaps)}（能大取大）",
        "",
        "| vo_id | start | end | 时长 | 句后气口 | 类型 | 状态 | 音频静音 |",
        "|---|---:|---:|---:|---:|---|---|---:|",
    ]
    for row in report:
        gap_text = f"{row['gap']:.2f}" if row["gap"] is not None else "-"
        audio_text = f"{row['audio_silence']:.2f}" if row["audio_silence"] is not None else "-"
        lines.append(
            f"| {row['vo_id']} | {row['start']:.2f} | {row['end']:.2f} | "
            f"{row['duration']:.2f} | {gap_text} | {row['gap_type']} | {row['status']} | {audio_text} |"
        )
    lines += [
        "",
        "## 提醒",
        "",
        "- 这是时间码/音频检查，不是另一个版本；v0 animatic 出来后请用户听气口。",
        "- 气口有区间时取大。",
    ]
    if not args.audio:
        lines += ["", "> 未提供 `--audio`，本报告不能证明真实静音与 `vo.csv` 一致。"]
    if len(rows) == 1:
        lines += ["", "> 只有一句旁白，没有句间气口。"]
    if warnings:
        lines += ["", "## Warnings", ""] + [f"- {warning}" for warning in warnings]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"report: {args.out}")
    print(f"cues: {len(rows)}; vo: {total_vo:.2f}s; density: {density:.2f}")
    if between_gaps:
        print(f"gaps: {gap_min}-{gap_max}s; below target: {below_target}")
    else:
        print("gaps: none (single cue)")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)


if __name__ == "__main__":
    main()
