#!/usr/bin/env python3
"""Build contact sheets for quick clip review.

Usage:
  python scripts/contact_sheet.py --clips clips --out review
  python scripts/contact_sheet.py --clips clips --out review --frames 6 --width 360
"""

from __future__ import annotations

import argparse
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(command: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(result.stderr[-2000:], file=sys.stderr)
        fail("command failed: " + " ".join(command))
    return result


def probe_duration(path: Path) -> float:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ]
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        fail(f"cannot read duration: {path}")


def get_font(size: int, custom: str | None = None) -> ImageFont.ImageFont:
    candidates = [
        custom,
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "arial.ttf",
        "segoeui.ttf",
        "DejaVuSans.ttf",
    ]
    for name in candidates:
        if not name:
            continue
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def collect_clips(path: Path, pattern: str, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        fail(f"clips path not found: {path}")
    iterator = path.rglob(pattern) if recursive else path.glob(pattern)
    return sorted(item for item in iterator if item.is_file())


def extract_frames(clip: Path, moments: list[float], tmp: Path) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for index, moment in enumerate(moments):
        target = tmp / f"{index:02d}.png"
        run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{max(0.0, moment):.3f}",
                "-i",
                str(clip),
                "-frames:v",
                "1",
                "-update",
                "1",
                str(target),
            ]
        )
        frames.append(Image.open(target).convert("RGB"))
    return frames


def build_sheet(clip: Path, out: Path, frames_count: int, width: int, font: ImageFont.ImageFont) -> None:
    duration = probe_duration(clip)
    if duration <= 0:
        fail(f"invalid duration: {clip}")

    # Sample inside the clip, not on the exact last frame.
    moments = [duration * (i + 0.5) / frames_count for i in range(frames_count)]
    with tempfile.TemporaryDirectory(prefix="sheet_") as tmp_name:
        frames = extract_frames(clip, moments, Path(tmp_name))
        first = frames[0]
        height = max(1, int(first.height * width / first.width))
        bar = 30
        canvas = Image.new("RGB", (width * len(frames), height + bar), "black")
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 6), f"{clip.stem}   {duration:.2f}s", fill="white", font=font)
        for index, frame in enumerate(frames):
            canvas.paste(frame.resize((width, height), Image.LANCZOS), (index * width, bar))
        out.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out, quality=88)
    print(f"sheet: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 5-8 frame contact sheets for clips")
    parser.add_argument("--clips", required=True, type=Path, help="clip file or directory")
    parser.add_argument("--out", type=Path, default=Path("review"), help="output directory")
    parser.add_argument("--frames", type=int, default=6, help="frames per sheet (5-8 recommended)")
    parser.add_argument("--width", type=int, default=360, help="width of each frame")
    parser.add_argument("--font", default=None, help="optional CJK-capable TTF/TTC path")
    parser.add_argument("--pattern", default="*.mp4", help="glob when --clips is a directory")
    parser.add_argument("--recursive", action="store_true", help="search subdirectories")
    args = parser.parse_args()

    clips = collect_clips(args.clips, args.pattern, args.recursive)
    if not clips:
        fail(f"no clips matched in {args.clips}")
    frames_count = max(2, min(12, args.frames))
    font = get_font(18, args.font)
    for clip in clips:
        build_sheet(clip, args.out / f"{clip.stem}.jpg", frames_count, args.width, font)


if __name__ == "__main__":
    main()
