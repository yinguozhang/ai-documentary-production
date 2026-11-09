#!/usr/bin/env python3
"""Opening-card contract checks shared by validate.py and timeline.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

TOL = 0.1
TARGET_TOL = 0.5


def _is_static(row: dict[str, str]) -> bool:
    return (row.get("static") or "").strip().lower() in {"yes", "true", "1"}


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _card_text_errors(base_dir: Path | None) -> list[str]:
    if base_dir is None:
        return []
    path = base_dir / "opening_card.md"
    if not path.is_file():
        return [f"opening_card.md: missing for opening_card=static: {path}"]
    errors = []
    text = path.read_text(encoding="utf-8")
    title = ""
    confirmed = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- 主标题："):
            title = stripped.split("：", 1)[1].strip()
        if "逐字确认" in stripped and "[x]" in stripped.lower():
            confirmed = True
    if not title:
        errors.append("opening_card.md: 主标题 is empty")
    if not confirmed:
        errors.append("opening_card.md: 逐字确认 is not checked [x]")
    return errors


def check_opening(
    project: dict[str, Any] | None,
    shots: list[dict[str, str]],
    segments: list[dict[str, str]] | None = None,
    base_dir: Path | None = None,
) -> list[str]:
    """Check G0 opening-card decision against the actual timeline."""
    if not project:
        return []
    errors: list[str] = []
    mode = str(project.get("opening_card") or "none").strip().lower()
    if mode not in {"none", "static"}:
        errors.append(f"opening_card: must be none or static, got {mode!r}")
        return errors
    if not shots:
        return errors

    total = 0.0
    for row in shots:
        value = _num(row.get("duration"))
        if value is not None:
            total += value

    if mode == "none":
        if _is_static(shots[0]):
            errors.append("opening_card=none but the first shot is static=yes")
        return errors

    seconds = _num(project.get("opening_seconds"))
    if seconds is None or seconds <= 0:
        errors.append("opening_seconds: must be > 0 when opening_card=static")
        return errors

    first = shots[0]
    if not _is_static(first):
        errors.append(
            f"opening_card=static but first shot {first.get('id', '?')} is not static=yes"
        )
        return errors

    duration = _num(first.get("duration"))
    if duration is None or abs(duration - seconds) > TOL:
        errors.append(
            f"opening card {first.get('id', '?')}: duration {duration!r}s != opening_seconds {seconds:.2f}s"
        )

    if segments is not None:
        card_segments = [row for row in segments if row.get("shot_id") == first.get("id")]
        if not card_segments:
            errors.append(f"opening card {first.get('id', '?')}: no CARD segment")
        elif not all(_is_static(row) for row in card_segments):
            errors.append(f"opening card {first.get('id', '?')}: CARD segment must be static=yes")
        if len(card_segments) > 1:
            errors.append(f"opening card {first.get('id', '?')}: more than one segment")

    errors.extend(_card_text_errors(base_dir))

    target = _num(project.get("duration_target_sec"))
    if target is None or target <= 0:
        errors.append("duration_target_sec: missing/<=0; cannot check opening total")
    else:
        expected = target if bool(project.get("opening_in_target", True)) else target + seconds
        if abs(total - expected) > TARGET_TOL:
            label = "inside target" if project.get("opening_in_target", True) else "plus opening"
            errors.append(
                f"total {total:.2f}s != target {expected:.2f}s ({label}; "
                f"opening_seconds={seconds:.2f}s)"
            )

    return errors
