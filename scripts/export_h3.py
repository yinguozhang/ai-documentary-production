#!/usr/bin/env python3
"""Export a multi-image H3 production package from segments.csv.

One generation segment = one H3 call. Each cut inside it gets a keyframe and
a cut time. This script validates the segment/shot contract first, then writes
prompt.md + manifest.json. It never calls an API.

Run:
    python scripts/export_h3.py --shots shots.csv --segments segments.csv \
        --prompts h3_prompts.csv --out h3_package
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate as v  # noqa: E402

FOOTER = (
    "只保留环境音效或人声，不要配乐、不要 BGM、不要旋律。"
    "画面无文字、无字幕、无水印。"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def t(seconds: float) -> str:
    minutes = int(seconds // 60)
    rest = seconds - minutes * 60
    return f"{minutes:02d}:{rest:06.3f}"


def is_static(row: dict[str, str]) -> bool:
    return (row.get("static") or "").strip().lower() in {"yes", "true", "1"}


def normalize_segments(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for row in rows:
        row = dict(row)
        if not row.get("generation_id"):
            row["generation_id"] = row.get("segment_id", "")
        out.append(row)
    return out


def build_segment(generation_id: str, rows: list[dict[str, str]], prompts: dict[str, dict[str, str]]) -> str:
    rows = sorted(rows, key=lambda r: int(r["cut_order"]))
    first = float(rows[0]["start"])
    duration = float(rows[-1]["end"]) - first
    if len(rows) == 1:
        alignment = (
            "For the target video, at 0.00 seconds, "
            "<Picture 1> (from [Shot 1]) is fully referenced."
        )
    else:
        parts = []
        for index, row in enumerate(rows, 1):
            cut_time = float(row["start"]) - first
            parts.append(
                f"Picture {index} (from [Shot {index}]) aligns with the "
                f"{cut_time:.2f}-second mark of the target video"
            )
        alignment = "How the reference pictures align with the target video — " + "; ".join(parts) + "."

    lines = [
        "# H3 段提示词",
        "",
        f"- generation: `{generation_id}`",
        f"- duration: `{duration:.2f}s`",
        "",
        alignment,
        "",
        "integrated_multimodal_description:",
        "",
    ]
    for index, row in enumerate(rows, 1):
        shot_id = row["shot_id"]
        prompt = (prompts.get(shot_id, {}).get("prompt") or "").strip()
        if not prompt:
            raise ValueError(f"missing prompt for shot {shot_id}")
        if index == 1:
            lines.append(f"[Shot 1] {prompt}")
        else:
            cut_time = float(row["start"]) - first
            lines.append(f"[Shot {index}] At {t(cut_time)}, {prompt}")
    soundscapes = []
    for row in rows:
        sound = (prompts.get(row["shot_id"], {}).get("soundscape") or "").strip()
        if sound and sound not in soundscapes:
            soundscapes.append(sound)
    lines += [
        "",
        f"overall_soundscape: {' '.join(soundscapes) if soundscapes else 'N/A'}",
        "",
        "non_diegetic_music: N/A",
        "",
        FOOTER,
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export H3 multi-image production package")
    parser.add_argument("--shots", required=True, type=Path)
    parser.add_argument("--segments", required=True, type=Path)
    parser.add_argument("--prompts", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-missing-files", action="store_true")
    args = parser.parse_args()

    shots = read_csv(args.shots)
    segments = normalize_segments(read_csv(args.segments))
    prompt_rows = read_csv(args.prompts)
    prompts = {row["shot_id"]: row for row in prompt_rows}

    errors = v.validate_rows(
        shots,
        None,
        None,
        segments,
        max_segment=15.0,
        strict_files=not args.allow_missing_files,
        base_dir=args.shots.parent,
        allow_partial=True,
    )
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)

    h3_segments = [row for row in segments if not is_static(row)]
    missing_prompts = [row["shot_id"] for row in h3_segments if row["shot_id"] not in prompts]
    if missing_prompts:
        print(f"error: missing prompts for shots: {', '.join(sorted(set(missing_prompts)))}", file=sys.stderr)
        raise SystemExit(1)

    groups: dict[str, list[dict[str, str]]] = {}
    for row in h3_segments:
        groups.setdefault(row["generation_id"], []).append(row)

    args.out.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    for generation_id, rows in groups.items():
        try:
            text = build_segment(generation_id, rows, prompts)
        except ValueError as exc:
            print(f"error: {generation_id}: {exc}", file=sys.stderr)
            raise SystemExit(1)
        rows = sorted(rows, key=lambda r: int(r["cut_order"]))
        folder = args.out / generation_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "prompt.md").write_text(text, encoding="utf-8")
        manifest.append(
            {
                "generation_id": generation_id,
                "duration": round(float(rows[-1]["end"]) - float(rows[0]["start"]), 3),
                "cuts": [
                    {
                        "shot_id": row["shot_id"],
                        "cut_order": int(row["cut_order"]),
                        "start": float(row["start"]),
                        "end": float(row["end"]),
                        "keyframe": row.get("keyframe", ""),
                    }
                    for row in rows
                ],
                "prompt": f"{generation_id}/prompt.md",
            }
        )

    (args.out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"export: {args.out}")
    print(f"segments: {len(manifest)}; cuts: {sum(len(s['cuts']) for s in manifest)}")
    for segment in manifest:
        print(f"  {segment['generation_id']}: {segment['duration']:.2f}s / {len(segment['cuts'])} cuts")


if __name__ == "__main__":
    main()
