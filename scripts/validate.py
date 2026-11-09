#!/usr/bin/env python3
"""Validate shots / vo / beats / segments as one production contract.

This is the project gate. It checks schema, story-beat claiming, segment
coverage against shots, and keyframe presence. It never calls a model.

Run:
    python scripts/validate.py --shots shots.csv --vo vo.csv \
        --beats beats.csv --segments segments.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

from opening import check_opening

TOL = 0.001


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_schema(name: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parent.parent / "schemas" / name
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _is_integer(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _get(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = (row.get(name) or "").strip()
        if value:
            return value
    return ""


def _is_static(row: dict[str, str]) -> bool:
    return _get(row, "static").lower() in {"yes", "true", "1"}


def _split(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[|;,]", text or "") if part.strip()]


def validate_row(row: dict[str, str], schema: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    for field in schema.get("required", []):
        if not (row.get(field) or "").strip():
            errors.append(f"{label}: missing required field '{field}'")

    for field, rule in schema.get("properties", {}).items():
        raw = (row.get(field) or "").strip()
        if not raw:
            continue
        kind = rule.get("type")
        if kind == "number":
            if not _is_number(raw):
                errors.append(f"{label}: '{field}' must be a number, got {raw!r}")
            elif "minimum" in rule and float(raw) < float(rule["minimum"]):
                errors.append(f"{label}: '{field}' must be >= {rule['minimum']}")
        elif kind == "integer":
            if not _is_integer(raw):
                errors.append(f"{label}: '{field}' must be an integer, got {raw!r}")
            elif "minimum" in rule and int(raw) < int(rule["minimum"]):
                errors.append(f"{label}: '{field}' must be >= {rule['minimum']}")
        elif kind == "boolean":
            if raw.lower() not in {"yes", "no", "true", "false", "1", "0"}:
                errors.append(f"{label}: '{field}' must be yes/no")
        if "enum" in rule and raw not in rule["enum"]:
            errors.append(
                f"{label}: '{field}' must be one of {', '.join(rule['enum'])}, got {raw!r}"
            )
    return errors


def validate_rows(
    shots: list[dict[str, str]],
    vo: list[dict[str, str]] | None = None,
    beats: list[dict[str, str]] | None = None,
    segments: list[dict[str, str]] | None = None,
    max_segment: float = 15.0,
    strict_files: bool = False,
    base_dir: Path | None = None,
    allow_partial: bool = False,
    project: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not shots:
        return ["shots: no rows"]

    base_dir = base_dir or Path.cwd()
    shot_by_id: dict[str, dict[str, str]] = {}
    shot_order: dict[str, int] = {}
    shot_scene: dict[str, str] = {}
    shot_span: dict[str, tuple[float, float]] = {}
    cursor = 0.0

    for index, row in enumerate(shots):
        label = f"shots[{index + 1}]"
        errors.extend(validate_row(row, load_schema("shots.schema.json"), label))
        shot_id = _get(row, "id")
        if not shot_id:
            continue
        if shot_id in shot_by_id:
            errors.append(f"shots: duplicate shot id {shot_id}")
        shot_by_id[shot_id] = row
        shot_order[shot_id] = index
        scene_id = _get(row, "scene_id")
        if not scene_id:
            errors.append(f"shot {shot_id}: missing scene_id")
        else:
            shot_scene[shot_id] = scene_id
        if not _get(row, "story_segment", "segment"):
            errors.append(f"shot {shot_id}: missing story_segment (legacy 'segment' is deprecated)")
        if not _get(row, "first_frame"):
            errors.append(f"shot {shot_id}: missing first_frame")
        duration = _get(row, "duration")
        if not _is_number(duration):
            continue
        start = cursor
        end = cursor + float(duration)
        shot_span[shot_id] = (start, end)
        cursor = end

    total = cursor

    vo_by_id: dict[str, dict[str, str]] = {}
    if vo is not None:
        for index, row in enumerate(vo):
            label = f"vo[{index + 1}]"
            errors.extend(validate_row(row, load_schema("vo.schema.json"), label))
            vo_id = _get(row, "vo_id")
            if not vo_id:
                continue
            if vo_id in vo_by_id:
                errors.append(f"vo: duplicate vo_id {vo_id}")
            vo_by_id[vo_id] = row
            start = _get(row, "start")
            end = _get(row, "end")
            if _is_number(start) and _is_number(end) and float(end) <= float(start):
                errors.append(f"vo {vo_id}: end must be after start")
            for shot_id in _split(_get(row, "shot_ids")):
                if shot_id not in shot_by_id:
                    errors.append(f"vo {vo_id}: unknown shot in shot_ids: {shot_id}")

    if beats is None:
        if not allow_partial:
            errors.append("beats.csv: missing (pass --allow-partial to skip story coverage)")
    else:
        seen_beat_ids: set[str] = set()
        claimed_shots: set[str] = set()
        claimed_vo: set[str] = set()
        last_shot_index = -1
        for index, row in enumerate(beats):
            label = f"beats[{index + 1}]"
            errors.extend(validate_row(row, load_schema("beats.schema.json"), label))
            beat_id = _get(row, "beat_id")
            shot_id = _get(row, "shot_id")
            vo_id = _get(row, "vo_id")
            if not beat_id:
                continue
            if beat_id in seen_beat_ids:
                errors.append(f"beats: duplicate beat_id {beat_id}")
            seen_beat_ids.add(beat_id)
            if not shot_id:
                continue
            if shot_id not in shot_by_id:
                errors.append(f"beat {beat_id}: unknown shot_id {shot_id}")
                continue
            claimed_shots.add(shot_id)
            this_index = shot_order[shot_id]
            if this_index < last_shot_index:
                errors.append(f"beat {beat_id}: beats are out of shot order")
            last_shot_index = this_index
            beat_story = _get(row, "story_segment", "segment")
            shot_story = _get(shot_by_id[shot_id], "story_segment", "segment")
            if beat_story and shot_story and beat_story != shot_story:
                errors.append(
                    f"beat {beat_id}: story_segment {beat_story} != shot story_segment {shot_story}"
                )
            if vo_id:
                if vo_by_id and vo_id not in vo_by_id:
                    errors.append(f"beat {beat_id}: unknown vo_id {vo_id}")
                claimed_vo.add(vo_id)
                vo_row = vo_by_id.get(vo_id)
                if vo_row:
                    vo_shots = _split(_get(vo_row, "shot_ids"))
                    shot_vo = _split(_get(shot_by_id[shot_id], "vo_ids"))
                    if shot_id not in vo_shots and vo_id not in shot_vo:
                        errors.append(
                            f"beat {beat_id}: shot {shot_id} and vo {vo_id} are not linked "
                            f"(vo.shot_ids={vo_shots or '[]'}, shot.vo_ids={shot_vo or '[]'})"
                        )

        for shot_id, shot in shot_by_id.items():
            if _is_static(shot):
                continue
            if shot_id not in claimed_shots:
                errors.append(f"shot {shot_id}: no beat claims it")
        if vo_by_id:
            for vo_id in vo_by_id:
                if vo_id not in claimed_vo:
                    errors.append(f"vo {vo_id}: no beat claims it")

    if segments is None:
        if not allow_partial:
            errors.append("segments.csv: missing (pass --allow-partial to skip H3 segment checks)")
    else:
        seen_shots: set[str] = set()
        groups: dict[str, list[dict[str, str]]] = {}
        all_cuts: list[dict[str, str]] = []
        for index, row in enumerate(segments):
            label = f"segments[{index + 1}]"
            generation_id = _get(row, "generation_id", "segment_id")
            if not generation_id:
                errors.append(f"{label}: missing generation_id (legacy 'segment_id' is deprecated)")
                continue
            # Validate against the schema after normalizing the old name.
            row = dict(row)
            row["generation_id"] = generation_id
            errors.extend(validate_row(row, load_schema("segments.schema.json"), label))
            shot_id = _get(row, "shot_id")
            if not shot_id:
                continue
            if shot_id not in shot_by_id:
                errors.append(f"segment {generation_id}: unknown shot_id {shot_id}")
                continue
            if shot_id in seen_shots:
                errors.append(f"segment {generation_id}: shot {shot_id} appears more than once")
            seen_shots.add(shot_id)
            expected = shot_span.get(shot_id)
            if expected:
                start = _get(row, "start")
                end = _get(row, "end")
                duration = _get(row, "duration")
                if not all(_is_number(v) for v in (start, end, duration)):
                    continue
                if abs(float(start) - expected[0]) > TOL or abs(float(end) - expected[1]) > TOL:
                    errors.append(
                        f"segment {generation_id}: cut {shot_id} span {start}-{end} "
                        f"does not match shots.csv {expected[0]:.3f}-{expected[1]:.3f}"
                    )
                if abs(float(duration) - (expected[1] - expected[0])) > TOL:
                    errors.append(
                        f"segment {generation_id}: cut {shot_id} duration {duration} "
                        f"does not match shots.csv {expected[1] - expected[0]:.3f}"
                    )
            segment_scene = _get(row, "scene_id")
            if segment_scene and shot_scene.get(shot_id) and segment_scene != shot_scene[shot_id]:
                errors.append(
                    f"segment {generation_id}: cut {shot_id} scene_id {segment_scene} "
                    f"!= shot scene_id {shot_scene[shot_id]}"
                )
            if _is_static(row) != _is_static(shot_by_id[shot_id]):
                errors.append(
                    f"segment {generation_id}: cut {shot_id} static flag does not match shots.csv"
                )
            keyframe = _get(row, "keyframe")
            first_frame = _get(shot_by_id[shot_id], "first_frame")
            if keyframe and first_frame and Path(keyframe).as_posix() != Path(first_frame).as_posix():
                errors.append(
                    f"segment {generation_id}: cut {shot_id} keyframe {keyframe} "
                    f"!= shot first_frame {first_frame}"
                )
            if strict_files:
                if keyframe and not (base_dir / keyframe).is_file():
                    errors.append(f"segment {generation_id}: keyframe not found: {keyframe}")
            groups.setdefault(generation_id, []).append(row)
            all_cuts.append(row)

        for generation_id, rows in groups.items():
            rows.sort(key=lambda r: int(_get(r, "cut_order") or 0))
            expected_order = 1
            scene_ids = {_get(r, "scene_id") for r in rows}
            if len(scene_ids) > 1:
                errors.append(f"segment {generation_id}: cuts span more than one scene_id")
            if any(_is_static(r) for r in rows) and len(rows) != 1:
                errors.append(f"segment {generation_id}: static card must have exactly one cut")
            total_segment = 0.0
            previous_end: float | None = None
            for row in rows:
                cut_order = int(_get(row, "cut_order") or 0)
                if cut_order != expected_order:
                    errors.append(
                        f"segment {generation_id}: cut_order must be contiguous from 1, got {cut_order}"
                    )
                expected_order += 1
                if not all(_is_number(_get(row, k)) for k in ("start", "end", "duration")):
                    continue
                start = float(_get(row, "start"))
                end = float(_get(row, "end"))
                duration = float(_get(row, "duration"))
                if end <= start:
                    errors.append(f"segment {generation_id}: cut {cut_order} end must be after start")
                if abs((end - start) - duration) > TOL:
                    errors.append(
                        f"segment {generation_id}: cut {cut_order} duration {duration} != end-start"
                    )
                if previous_end is not None and abs(start - previous_end) > TOL:
                    errors.append(
                        f"segment {generation_id}: cut {cut_order} must start at previous cut end"
                    )
                previous_end = end
                total_segment += duration
            if total_segment > max_segment + TOL:
                errors.append(
                    f"segment {generation_id}: {total_segment:.2f}s exceeds max {max_segment:.2f}s"
                )

        # Every shot must appear exactly once, and cuts must cover 0..total with no gap/overlap.
        missing = [sid for sid in shot_by_id if sid not in seen_shots]
        if missing:
            errors.append(f"segments: shots not covered: {', '.join(missing)}")
        valid_cuts = []
        for row in all_cuts:
            if all(_is_number(_get(row, k)) for k in ("start", "end")):
                valid_cuts.append((float(_get(row, "start")), float(_get(row, "end")), _get(row, "shot_id")))
        valid_cuts.sort()
        if valid_cuts:
            if abs(valid_cuts[0][0]) > TOL:
                errors.append(f"segments: first cut must start at 0.000, got {valid_cuts[0][0]:.3f}")
            if abs(valid_cuts[-1][1] - total) > TOL:
                errors.append(
                    f"segments: last cut must end at {total:.3f}, got {valid_cuts[-1][1]:.3f}"
                )
            for (_, prev_end, _), (next_start, _, next_shot) in zip(valid_cuts, valid_cuts[1:]):
                if abs(next_start - prev_end) > TOL:
                    errors.append(
                        f"segments: gap/overlap before {next_shot}: "
                        f"{prev_end:.3f} -> {next_start:.3f}"
                    )

    errors.extend(check_opening(project, shots, segments, base_dir))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate documentary production CSV contracts")
    parser.add_argument("--shots", required=True, type=Path)
    parser.add_argument("--vo", type=Path)
    parser.add_argument("--beats", type=Path)
    parser.add_argument("--segments", type=Path)
    parser.add_argument("--project", type=Path, help="optional project.json for opening-card checks")
    parser.add_argument("--max-segment", type=float, default=15.0)
    parser.add_argument("--strict-files", action="store_true", help="require keyframe files (use at G5)")
    parser.add_argument("--allow-missing-files", action="store_true", help="deprecated alias for default structural mode")
    parser.add_argument("--allow-partial", action="store_true", help="skip beats/segments checks")
    args = parser.parse_args()

    project = json.loads(args.project.read_text(encoding="utf-8")) if args.project else None
    errors = validate_rows(
        read_csv(args.shots),
        read_csv(args.vo) if args.vo else None,
        read_csv(args.beats) if args.beats else None,
        read_csv(args.segments) if args.segments else None,
        max_segment=args.max_segment,
        strict_files=args.strict_files and not args.allow_missing_files,
        base_dir=args.shots.parent,
        allow_partial=args.allow_partial,
        project=project,
    )
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("validate: ok")
    print(f"shots: {len(read_csv(args.shots))}")
    if args.vo:
        print(f"vo: {len(read_csv(args.vo))}")
    if args.beats:
        print(f"beats: {len(read_csv(args.beats))}")
    if args.segments:
        print(f"segments: {len(read_csv(args.segments))}")


if __name__ == "__main__":
    main()
