#!/usr/bin/env python3
"""Build a timeline CSV (and optional animatic) from shots.csv.

Usage:
  python scripts/timeline.py --shots shots.csv --out timeline.csv
  python scripts/timeline.py --shots shots.csv --out timeline.csv --target 180
  python scripts/timeline.py --shots shots.csv --animatic animatic.mp4 --fps 25
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass
import tempfile
from pathlib import Path

from config import load_project, load_providers, resolution
from opening import check_opening


REQUIRED = ("id", "duration")


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def timecode(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def read_shots(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"shots file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail("shots.csv has no header")
        missing = [key for key in REQUIRED if key not in reader.fieldnames]
        if missing:
            fail(f"shots.csv missing columns: {', '.join(missing)}")
        rows = [dict(row) for row in reader]

    if not rows:
        fail("shots.csv has no rows")

    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        shot_id = (row.get("id") or "").strip()
        if not shot_id:
            fail(f"row {index}: empty id")
        if shot_id in seen:
            fail(f"row {index}: duplicate id {shot_id}")
        seen.add(shot_id)
        raw = (row.get("duration") or "").strip()
        try:
            duration = float(raw)
        except ValueError:
            fail(f"row {index}: duration is not a number: {raw!r}")
        if duration <= 0:
            fail(f"row {index}: duration must be > 0")
        row["duration"] = f"{duration:.3f}"
    for row in rows:
        if not (row.get("story_segment") or row.get("segment")):
            fail(f"shot {row.get('id', '?')}: missing story_segment (legacy 'segment')")
    return rows


def build_timeline(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    current = 0.0
    output: list[dict[str, str]] = []
    for row in rows:
        duration = float(row["duration"])
        item = dict(row)
        item["start"] = f"{current:.3f}"
        item["end"] = f"{current + duration:.3f}"
        item["start_tc"] = timecode(current)
        item["end_tc"] = timecode(current + duration)
        output.append(item)
        current += duration
    return output


def write_timeline(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, str]], target: float | None) -> None:
    total = float(rows[-1]["end"])
    print(f"shots: {len(rows)}")
    print(f"total: {total:.2f}s ({total / 60:.2f} min)")

    segments: list[tuple[str, float]] = []
    for row in rows:
        segment = (row.get("story_segment") or row.get("segment") or "?").strip() or "?"
        if segments and segments[-1][0] == segment:
            segments[-1] = (segment, segments[-1][1] + float(row["duration"]))
        else:
            segments.append((segment, float(row["duration"])))
    print("segments:")
    for segment, duration in segments:
        print(f"  {segment}: {duration:.2f}s")

    if target is not None:
        diff = total - target
        print(f"target: {target:.2f}s; diff: {diff:+.2f}s")
        if abs(diff) > 2.0:
            print("warning: total differs from target by more than 2s", file=sys.stderr)



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
    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        vo_id = (row.get("vo_id") or "").strip()
        if not vo_id:
            fail(f"vo row {index}: empty vo_id")
        if vo_id in seen:
            fail(f"vo row {index}: duplicate vo_id {vo_id}")
        seen.add(vo_id)
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


def is_long_take(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"yes", "true", "1", "y", "是"}


def visible_chars(text: str) -> int:
    # Count characters that actually take time; drop whitespace and punctuation.
    return len(re.sub(r"[\s，。！？、；：“”‘’《》（）…—,.!?;:\"'()\[\]{}]", "", text or ""))


def check_vo(
    vo_rows: list[dict[str, str]],
    timeline: list[dict[str, str]],
    out: Path | None,
    min_gap: float = 0.4,
    max_density: float = 0.85,
    min_rate: float = 2.0,
    max_rate: float = 5.5,
    allow_single: bool = False,
    long_take_min: float = 5.0,
    long_take_max: float = 15.0,
    strict_long_take: bool = False,
) -> None:
    shot_by_id = {row["id"]: row for row in timeline}
    total_vo = 0.0
    total_time = float(timeline[-1]["end"])
    report: list[dict[str, str]] = []
    warnings: list[str] = []
    multi = 0
    rates: list[float] = []

    for cue in vo_rows:
        start = float(cue["start"])
        end = float(cue["end"])
        duration = end - start
        total_vo += duration
        sentences = len(re.findall(r"[。！？!?]", cue["text"]))
        if sentences > 1:
            fail(
                f"vo {cue['vo_id']} contains {sentences} sentence ends; "
                "use one vo_id per sentence/subtitle unit"
            )
        chars = visible_chars(cue["text"])
        rate = chars / duration if duration > 0 else 0.0
        rates.append(rate)
        raw_ids = (cue.get("shot_ids") or "").strip()
        ids = [part.strip() for part in re.split(r"[|;,]", raw_ids) if part.strip()]
        if not ids:
            ids = [
                row["id"]
                for row in timeline
                if float(row["start"]) < end and float(row["end"]) > start
            ]
        unknown = [shot_id for shot_id in ids if shot_id not in shot_by_id]
        if unknown:
            fail(f"vo {cue['vo_id']} references unknown shots: {', '.join(unknown)}")
        if not ids:
            fail(f"vo {cue['vo_id']} covers no shot")
        if start < 0 or end > float(timeline[-1]["end"]) + 0.001:
            warnings.append(f"vo {cue['vo_id']} extends outside the timeline")
        if len(ids) == 1 and not allow_single:
            warnings.append(f"vo {cue['vo_id']} covers only 1 shot (special case; 2-3 is the default)")
        if len(ids) > 3:
            warnings.append(f"vo {cue['vo_id']} covers {len(ids)} shots; consider splitting for pacing")
        if len(ids) >= 2:
            multi += 1
        report.append(
            {
                "vo_id": cue["vo_id"],
                "start": f"{start:.3f}",
                "end": f"{end:.3f}",
                "duration": f"{duration:.3f}",
                "shot_count": str(len(ids)),
                "shot_ids": "|".join(ids),
                "text": cue["text"],
                "chars": str(chars),
                "rate": f"{rate:.2f}",
                "notes": cue.get("notes", ""),
            }
        )

    # Gap check: different VO cues need breathing room, and each gap must contain a cut.
    ordered = sorted(vo_rows, key=lambda row: float(row["start"]))
    boundary_list = sorted({float(row["end"]) for row in timeline[:-1]})
    cue_by_id = {row["vo_id"]: row for row in vo_rows}
    long_take_shots = [shot for shot in timeline if is_long_take(shot.get("long_take"))]
    for shot in long_take_shots:
        duration = float(shot["end"]) - float(shot["start"])
        if duration < long_take_min:
            warnings.append(
                f"long take {shot['id']} is {duration:.2f}s < {long_take_min:.2f}s; "
                "is it really a long take?"
            )
        if duration > long_take_max:
            message = (
                f"long take {shot['id']} is {duration:.2f}s > {long_take_max:.2f}s; "
                "H3 single generation may not support it"
            )
            if strict_long_take:
                fail(message)
            warnings.append(message)

    def long_take_containing(cue: dict) -> dict | None:
        start = float(cue["start"])
        end = float(cue["end"])
        for shot in long_take_shots:
            shot_start = float(shot["start"])
            shot_end = float(shot["end"])
            if start >= shot_start - 0.001 and end <= shot_end + 0.001:
                return shot
        return None

    # A long take may contain many cues, but none may cross its boundaries.
    for shot in long_take_shots:
        shot_start = float(shot["start"])
        shot_end = float(shot["end"])
        for cue in vo_rows:
            overlaps = float(cue["start"]) < shot_end - 0.001 and float(cue["end"]) > shot_start + 0.001
            if not overlaps:
                continue
            if float(cue["start"]) < shot_start - 0.001 or float(cue["end"]) > shot_end + 0.001:
                fail(
                    f"long take {shot['id']} contains {cue['vo_id']} only partially; "
                    "every VO cue must be fully inside the long take"
                )

    gap_by_id: dict[str, float] = {}
    gaps: list[float] = []
    for index, cue in enumerate(ordered):
        is_tail = index + 1 >= len(ordered)
        if not is_tail:
            next_start = float(ordered[index + 1]["start"])
        else:
            next_start = total_time
        gap = next_start - float(cue["end"])
        gap_by_id[cue["vo_id"]] = gap
        gaps.append(gap)
        if gap < -0.001:
            fail(
                f"vo overlap: {cue['vo_id']} ends {cue['end']}, "
                f"next starts {next_start:.3f}; VO cues must not overlap"
            )
        if is_tail:
            # Tail silence is not a between-cue gap; no cut is required.
            continue
        if gap <= 0.001:
            fail(
                f"vo {cue['vo_id']} has no gap before the next cue; "
                "one shot cannot contain two VO cues"
            )
        # Every between-cue gap must contain a cut, unless both cues live inside
        # the same long take (there is no visible cut inside it).
        previous_long = long_take_containing(cue)
        next_long = long_take_containing(ordered[index + 1])
        same_long_take = (
            previous_long is not None
            and next_long is not None
            and previous_long["id"] == next_long["id"]
        )
        if not same_long_take:
            gap_start = float(cue["end"])
            gap_end = next_start
            cuts = [
                boundary
                for boundary in boundary_list
                if gap_start - 0.001 <= boundary <= gap_end + 0.001
            ]
            if not cuts:
                fail(
                    f"gap {cue['vo_id']}->{ordered[index + 1]['vo_id']} "
                    f"({gap_start:.2f}-{gap_end:.2f}s) has no shot cut; "
                    "move a cut into this gap or add a no-VO shot; prefer the larger gap"
                )
        if gap < min_gap:
            warnings.append(
                f"vo gap after {cue['vo_id']} is {gap:.2f}s; "
                f"target >= {min_gap:.2f}s (prefer larger; do not fill every second)"
            )
    # Hard rule: ordinary shot max one cue; long take may contain many, fully inside.
    for shot in timeline:
        shot_id = shot["id"]
        start = float(shot["start"])
        end = float(shot["end"])
        explicit = [
            part.strip()
            for part in re.split(r"[|;,]", (shot.get("vo_ids") or "").strip())
            if part.strip()
        ]
        overlapping = [
            cue["vo_id"]
            for cue in vo_rows
            if float(cue["start"]) < end - 0.001 and float(cue["end"]) > start + 0.001
        ]
        unique = sorted(set(explicit) | set(overlapping))
        if is_long_take(shot.get("long_take")):
            for vo_id in unique:
                cue = cue_by_id.get(vo_id)
                if cue is None:
                    continue
                if float(cue["start"]) < start - 0.001 or float(cue["end"]) > end + 0.001:
                    fail(
                        f"long take {shot_id} contains {vo_id} only partially; "
                        "every VO cue must be fully inside the long take"
                    )
            continue
        if len(unique) > 1:
            fail(
                f"shot {shot_id} has multiple VO cues: {', '.join(unique)}; "
                "use long_take=yes for a single continuous shot, or split the shot"
            )

    if gaps:
        breathing = sum(1 for gap in gaps if gap >= min_gap)
        print(
            f"vo gaps: min {min(gaps):.2f}s / max {max(gaps):.2f}s / "
            f"breathing {breathing}/{len(gaps)}"
        )
    for item in report:
        item["gap_after"] = f"{gap_by_id.get(item['vo_id'], 0.0):.2f}"

    # Optional shot -> vo check.
    for shot in timeline:
        raw = (shot.get("vo_ids") or "").strip()
        if not raw:
            continue
        for vo_id in [part.strip() for part in re.split(r"[|;,]", raw) if part.strip()]:
            if vo_id not in {row["vo_id"] for row in vo_rows}:
                warnings.append(f"shot {shot['id']} references unknown vo_id {vo_id}")

    density = total_vo / total_time if total_time > 0 else 0.0
    print(f"vo density: {density:.2f} (max {max_density:.2f})")
    if rates:
        print(f"vo rate: min {min(rates):.2f} / max {max(rates):.2f} chars/s")
    if density > max_density:
        warnings.append(
            f"vo density {density:.2f} > {max_density:.2f}; "
            "narration is filling too much of the timeline"
        )
    for cue, rate in zip(vo_rows, rates):
        if rate > max_rate:
            warnings.append(f"vo {cue['vo_id']} rate {rate:.2f} chars/s > {max_rate:.2f}; too fast")
        elif rate < min_rate:
            warnings.append(f"vo {cue['vo_id']} rate {rate:.2f} chars/s < {min_rate:.2f}; too sparse/slow")
    long_take_cues = sum(1 for cue in vo_rows if long_take_containing(cue) is not None)
    print(f"vo cues: {len(vo_rows)}; total vo: {total_vo:.2f}s")
    print(f"multi-shot cues: {multi}/{len(vo_rows)}")
    if multi == 0 and long_take_cues == 0:
        warnings.append("all cues are single-shot; 2-3 shots per cue is the normal case")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(report[0].keys()))
            writer.writeheader()
            writer.writerows(report)
        print(f"vo report: {out}")


def resolve_frame(path_value: str, shots_path: Path) -> Path:
    raw = (path_value or "").strip()
    if not raw:
        return Path("")
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    for base in (shots_path.parent, Path.cwd()):
        resolved = (base / candidate).resolve()
        if resolved.is_file():
            return resolved
    return candidate.resolve()


def make_animatic(
    rows: list[dict[str, str]],
    shots_path: Path,
    output: Path,
    fps: int,
    width: int,
    height: int,
    audio: Path | None,
    missing: str = "black",
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="animatic_") as tmp:
        list_path = Path(tmp) / "frames.txt"
        lines: list[str] = []
        resolved: list[Path] = []
        for index, row in enumerate(rows):
            frame = resolve_frame(row.get("first_frame", ""), shots_path)
            if not frame.is_file():
                if missing == "error":
                    fail(f"first_frame not found: {frame or '(empty)'}")
                placeholder = Path(tmp) / f"missing_{index:02d}.png"
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-f", "lavfi",
                        "-i", f"color=c=black:s={width}x{height}:d=1",
                        "-frames:v", "1", "-update", "1", str(placeholder),
                    ],
                    capture_output=True,
                )
                if not placeholder.is_file():
                    fail(f"cannot create placeholder for missing frame: {frame or '(empty)'}")
                print(f"warning: missing first_frame, using black: {frame or '(empty)'}", file=sys.stderr)
                frame = placeholder
            resolved.append(frame)
            safe = frame.as_posix().replace("'", "'\\''")
            lines.append(f"file '{safe}'")
            lines.append(f"duration {float(row['duration']):.3f}")
        # concat needs the last file repeated without duration
        last = resolved[-1].as_posix().replace("'", "'\\''")
        lines.append(f"file '{last}'")
        list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"fps={fps},format=yuv420p"
        )
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
        ]
        if audio is not None:
            if not audio.is_file():
                fail(f"audio not found: {audio}")
            command += ["-i", str(audio)]
        command += [
            "-vf",
            video_filter,
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-movflags",
            "+faststart",
        ]
        if audio is not None:
            command += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
        else:
            command += ["-an"]
        total = float(rows[-1]["end"])
        command += ["-t", f"{total:.3f}"]
        command.append(str(output))
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            print(result.stderr[-2000:], file=sys.stderr)
            fail("ffmpeg failed")
    print(f"animatic: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build timeline.csv from shots.csv")
    parser.add_argument("--shots", required=True, type=Path, help="input shots.csv")
    parser.add_argument("--out", type=Path, default=Path("timeline.csv"), help="output timeline.csv")
    parser.add_argument("--target", type=float, default=None, help="target total seconds")
    parser.add_argument("--animatic", type=Path, default=None, help="optional animatic mp4")
    parser.add_argument("--vo", type=Path, default=None, help="optional vo.csv to validate")
    parser.add_argument("--vo-out", type=Path, default=None, help="optional vo report CSV")
    parser.add_argument("--min-gap", type=float, default=0.4, help="minimum gap between VO cues, seconds")
    parser.add_argument("--max-density", type=float, default=0.85, help="max total VO / timeline")
    parser.add_argument("--min-rate", type=float, default=2.0, help="min chars/sec per cue")
    parser.add_argument("--max-rate", type=float, default=5.5, help="max chars/sec per cue")
    parser.add_argument("--allow-single", action="store_true", help="allow one-shot VO cues without warning")
    parser.add_argument("--min-shot", type=float, default=2.0, help="min seconds for a shot with VO")
    parser.add_argument("--max-shot", type=float, default=10.0, help="max seconds for an ordinary shot")
    parser.add_argument("--long-take-min", type=float, default=5.0,
                        help="warn when a long_take is shorter than this")
    parser.add_argument("--long-take-max", type=float, default=15.0,
                        help="warn/fail when a long_take is longer than this")
    parser.add_argument("--strict-long-take", action="store_true",
                        help="fail instead of warn when a long_take exceeds max")
    parser.add_argument("--project", type=Path, default=None, help="optional project.json")
    parser.add_argument("--providers", type=Path, default=None, help="optional providers.json")
    parser.add_argument("--fps", type=int, default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--audio", type=Path, default=None, help="optional audio for animatic")
    parser.add_argument("--animatic-missing", choices=["black", "error"], default="black",
                        help="missing first_frame: black placeholder or error")
    args = parser.parse_args()

    project = load_project(args.project) if args.project is not None else None
    if project is not None:
        providers_path = args.providers or (args.project.parent / "providers.json")
        if providers_path.is_file():
            providers = load_providers(providers_path)
            for role, provider_id in (project.get("providers") or {}).items():
                actual = (providers.get(role) or {}).get("provider")
                if actual and actual != provider_id:
                    print(
                        f"warning: project provider {role}={provider_id}, "
                        f"providers.json has {actual}",
                        file=sys.stderr,
                    )
        else:
            print(f"warning: providers.json not found: {providers_path}", file=sys.stderr)
    target = args.target
    if target is None and project is not None:
        target = float(project.get("duration_target_sec", 0) or 0) or None
    fps = args.fps or (int(project.get("fps", 25)) if project else 25)
    if args.width and args.height:
        width, height = args.width, args.height
    elif project is not None:
        width, height = resolution(project.get("resolution", "1280x720"))
    else:
        width, height = 1280, 720

    rows = read_shots(args.shots)
    if project is not None:
        opening_errors = check_opening(project, rows, None, args.project.parent)
        for opening_error in opening_errors:
            print(f"error: {opening_error}", file=sys.stderr)
        if opening_errors:
            raise SystemExit(1)
    for row in rows:
        duration = float(row["duration"])
        is_long = is_long_take(row.get("long_take"))
        has_vo = bool((row.get("vo_ids") or "").strip())
        if not is_long:
            if has_vo and not (args.min_shot <= duration <= args.max_shot):
                fail(
                    f"shot {row['id']}: {duration:.2f}s outside {args.min_shot:.1f}-"
                    f"{args.max_shot:.1f}s for a shot with VO"
                )
            if not has_vo and duration > args.max_shot:
                fail(f"shot {row['id']}: no-VO insert {duration:.2f}s > {args.max_shot:.1f}s")
    timeline = build_timeline(rows)
    write_timeline(timeline, args.out)
    print(f"timeline: {args.out}")
    print_summary(timeline, target)

    if args.vo_out is not None and args.vo is None:
        fail("--vo-out requires --vo")
    if args.vo is not None:
        check_vo(
            read_vo(args.vo),
            timeline,
            args.vo_out,
            args.min_gap,
            args.max_density,
            args.min_rate,
            args.max_rate,
            args.allow_single,
            args.long_take_min,
            args.long_take_max,
            args.strict_long_take,
        )

    if args.animatic is not None:
        make_animatic(
            timeline, args.shots, args.animatic,
            fps, width, height, args.audio, args.animatic_missing,
        )


if __name__ == "__main__":
    main()
