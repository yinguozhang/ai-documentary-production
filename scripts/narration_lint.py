#!/usr/bin/env python3
"""Lint Chinese documentary narration for common writing problems."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


CLICHE = {
    "心醉神往", "深深吸引", "不眠之夜", "毕生心血", "永远激励",
    "三尺讲台", "教书育人", "心有大我", "至诚报国", "丰碑", "脊梁",
    "赞歌", "画卷", "篇章", "传奇", "不朽", "伟大", "辉煌", "绽放",
    "升华", "洗礼", "力量", "美丽",
}
# Motifs are not automatically bad in lyrical narration.
MOTIF = {"大门", "种子", "火种", "明珠", "王冠"}
NOMINAL = {"进行", "实现", "彰显", "展现", "体现", "具有", "予以", "加以"}
PATTERNS = {
    "不是…而是…": re.compile(r"不是.{0,12}而是"),
    "既…又…": re.compile(r"既.{0,12}又"),
    "从…到…排比": re.compile(r"从.{0,10}到.{0,10}[，,].{0,10}从"),
    "的…的…的": re.compile(r"的[^。！？]{0,12}的[^。！？]{0,12}的"),
}


def fail(message: str) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_text(path: Path) -> list[tuple[int, str]]:
    if not path.is_file():
        fail(f"file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or "text" not in reader.fieldnames:
                fail("CSV must contain a text column")
            return [(index, (row.get("text") or "").strip()) for index, row in enumerate(reader, start=2)]
    if suffix == ".srt":
        lines: list[tuple[int, str]] = []
        for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
            value = line.strip()
            if not value or value.isdigit() or "-->" in value:
                continue
            lines.append((index, value))
        return lines
    return [
        (index, re.sub(r"^\s*(?:#{1,6}\s*|[-*]\s+|\d+[.、]\s*)", "", line).strip())
        for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1)
        if line.strip()
    ]


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；;])", text)
    return [part.strip() for part in parts if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint Chinese narration")
    parser.add_argument("--text", required=True, type=Path, help="script.md / vo.csv / subtitles.srt")
    parser.add_argument("--max-chars", type=int, default=28, help="max chars per sentence")
    parser.add_argument("--max-avg", type=float, default=22.0, help="max average chars per sentence")
    parser.add_argument("--style", choices=["lyrical", "explanatory"], default="lyrical",
                        help="lyrical: motifs allowed; explanatory: flag motifs for anchoring")
    parser.add_argument("--strict", action="store_true", help="exit 1 if findings exist")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args()

    raw = load_text(args.text)
    sentences: list[tuple[int, str]] = []
    for line_no, text in raw:
        for sentence in split_sentences(text):
            sentences.append((line_no, sentence))
    if not sentences:
        fail("no sentences found")

    long_sentences: list[tuple[int, str, int]] = []
    comma_heavy: list[tuple[int, str, int]] = []
    cliche_hits: list[tuple[int, str, str]] = []
    motif_hits: list[tuple[int, str, str]] = []
    nominal_hits: list[tuple[int, str, str]] = []
    pattern_hits: list[tuple[int, str, str]] = []
    passive_hits: list[tuple[int, str]] = []
    starts: dict[str, list[int]] = {}

    for line_no, sentence in sentences:
        clean = re.sub(r"\s+", "", sentence)
        chars = len(re.sub(r"[，。！？、；：“”‘’《》（）…—,.!?;:\"'()\[\]{}]", "", clean))
        if chars > args.max_chars:
            long_sentences.append((line_no, sentence, chars))
        commas = len(re.findall(r"[，,；;]", sentence))
        if commas > 3:
            comma_heavy.append((line_no, sentence, commas))
        for word in CLICHE:
            if word in sentence:
                cliche_hits.append((line_no, sentence, word))
        if args.style == "explanatory":
            for word in MOTIF:
                if word in sentence:
                    motif_hits.append((line_no, sentence, word))
        for word in NOMINAL:
            if word in sentence:
                nominal_hits.append((line_no, sentence, word))
        for name, pattern in PATTERNS.items():
            if pattern.search(sentence):
                pattern_hits.append((line_no, sentence, name))
        if re.search(r"被[^。！？]{0,10}(?:认为|称为|誉为|视作|用于|发现|证明)", sentence):
            passive_hits.append((line_no, sentence))
        prefix = clean[:2]
        if prefix:
            starts.setdefault(prefix, []).append(line_no)

    repeated = {prefix: lines for prefix, lines in starts.items() if len(lines) >= 3}
    avg = sum(
        len(re.sub(r"[，。！？、；：“”‘’《》（）…—,.!?;:\"'()\[\]{}]", "", re.sub(r"\s+", "", sentence)))
        for _, sentence in sentences
    ) / len(sentences)

    findings = (
        len(long_sentences) + len(comma_heavy) + len(cliche_hits) + len(motif_hits)
        + len(nominal_hits) + len(pattern_hits) + len(passive_hits) + len(repeated)
    )

    if args.json:
        print(json.dumps(
            {
                "sentences": len(sentences),
                "avg_chars": round(avg, 2),
                "long_sentences": long_sentences,
                "comma_heavy": comma_heavy,
                "cliche": cliche_hits,
                "motif": motif_hits,
                "nominal": nominal_hits,
                "patterns": pattern_hits,
                "passive": passive_hits,
                "repeated_starts": repeated,
                "findings": findings,
            },
            ensure_ascii=False,
            indent=2,
        ))
    else:
        print(f"style: {args.style}; sentences: {len(sentences)}; avg: {avg:.1f} chars (max {args.max_avg:.1f})")
        if long_sentences:
            print(f"\nlong sentences > {args.max_chars}: {len(long_sentences)}")
            for line_no, sentence, chars in long_sentences[:8]:
                print(f"  L{line_no} ({chars}): {sentence}")
        if comma_heavy:
            print(f"\ncomma-heavy (one breath?): {len(comma_heavy)}")
            for line_no, sentence, commas in comma_heavy[:8]:
                print(f"  L{line_no} ({commas} commas): {sentence}")
        if cliche_hits:
            print(f"\nabstract/cliché: {len(cliche_hits)}")
            for line_no, sentence, word in cliche_hits[:12]:
                print(f"  L{line_no} [{word}]: {sentence}")
        if motif_hits:
            print(f"\nmotifs to check for anchor (style=explanatory): {len(motif_hits)}")
            for line_no, sentence, word in motif_hits[:8]:
                print(f"  L{line_no} [{word}]: {sentence}")
        if nominal_hits:
            print(f"\nnominalization: {len(nominal_hits)}")
            for line_no, sentence, word in nominal_hits[:8]:
                print(f"  L{line_no} [{word}]: {sentence}")
        if pattern_hits:
            print(f"\nslogan patterns: {len(pattern_hits)}")
            for line_no, sentence, name in pattern_hits[:8]:
                print(f"  L{line_no} [{name}]: {sentence}")
        if passive_hits:
            print(f"\npassive voice candidates: {len(passive_hits)}")
            for line_no, sentence in passive_hits[:6]:
                print(f"  L{line_no}: {sentence}")
        if repeated:
            print("\nrepeated sentence starts:")
            for prefix, lines in list(repeated.items())[:8]:
                print(f"  {prefix}: {lines[:8]}")
        print(f"\nfindings: {findings}")

    if args.strict and findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
