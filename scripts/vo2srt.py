#!/usr/bin/env python3
"""Convert vo.csv to a line-broken SRT."""

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


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def timecode(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def wrap(text: str, max_chars: int) -> list[str]:
    text = re.sub(r"\s+", "", text or "")
    if len(text) <= max_chars:
        return [text]
    if len(text) <= max_chars * 2:
        middle = len(text) // 2
        candidates = [
            index
            for index, char in enumerate(text)
            if char in "，。！？；：、,.!?;:" and abs(index - middle) <= max_chars
        ]
        split = min(candidates, key=lambda index: abs(index - middle)) if candidates else middle
        if split == 0 or split >= len(text) - 1:
            split = middle
        return [text[: split + 1], text[split + 1 :]]
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]


def read_vo(path: Path) -> list[dict[str, str]]:
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
        rows = [dict(row) for row in reader]
    if not rows:
        fail("vo.csv has no rows")
    for index, row in enumerate(rows, start=2):
        try:
            start = float((row.get("start") or "").strip())
            end = float((row.get("end") or "").strip())
        except ValueError:
            fail(f"vo row {index}: start/end must be numbers")
        if start < 0 or end <= start:
            fail(f"vo row {index}: invalid range {start}-{end}")
        if not (row.get("text") or "").strip():
            fail(f"vo row {index}: empty text")
        row["start"] = f"{start:.3f}"
        row["end"] = f"{end:.3f}"
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert vo.csv to subtitles.srt")
    parser.add_argument("--vo", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path("subtitles.srt"))
    parser.add_argument("--max-chars", type=int, default=18, help="max characters per subtitle line")
    args = parser.parse_args()

    rows = read_vo(args.vo)
    blocks: list[str] = []
    warned = False
    for index, row in enumerate(rows, start=1):
        lines = wrap(row["text"], args.max_chars)
        if len(lines) > 2:
            warned = True
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{timecode(float(row['start']))} --> {timecode(float(row['end']))}",
                    "\n".join(lines),
                    "",
                ]
            )
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(blocks).rstrip() + "\n", encoding="utf-8-sig")
    print(f"srt: {args.out}")
    print(f"cues: {len(rows)}; max chars/line: {args.max_chars}")
    if warned:
        print("warning: some cues need more than 2 lines; shorten text or split the cue", file=sys.stderr)


if __name__ == "__main__":
    main()
