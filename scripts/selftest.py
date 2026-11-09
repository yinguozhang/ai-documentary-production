#!/usr/bin/env python3
"""Self-test for validate.py and the H3 exporter — no model, no API.

Each quality gate must have a failing case. If a gate stops firing, this
script fails. Run:
    python scripts/selftest.py
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))

import export_h3  # noqa: E402
import validate as v  # noqa: E402
import validate_tasks  # noqa: E402

FIXTURE = SKILL / "tests" / "fixtures" / "validate_good"
STATIC = SKILL / "tests" / "fixtures" / "static_card"


def load_fixture():
    return (
        v.read_csv(FIXTURE / "shots.csv"),
        v.read_csv(FIXTURE / "vo.csv"),
        v.read_csv(FIXTURE / "beats.csv"),
        v.read_csv(FIXTURE / "segments.csv"),
    )


def errors_for(shots, vo, beats, segments) -> list[str]:
    return v.validate_rows(
        shots,
        vo,
        beats,
        segments,
        max_segment=15.0,
        strict_files=True,
        base_dir=FIXTURE,
    )


def main() -> None:
    passed = 0

    def ok(condition: bool, label: str) -> None:
        nonlocal passed
        if not condition:
            raise AssertionError(label)
        passed += 1

    shots, vo, beats, segments = load_fixture()
    ok(errors_for(shots, vo, beats, segments) == [], "good fixture must pass")

    bad = copy.deepcopy(shots)
    bad[0]["status"] = "not_a_status"
    ok(any("status" in e for e in errors_for(bad, vo, beats, segments)), "bad status must fail")

    bad = copy.deepcopy(shots)
    bad[0]["duration"] = ""
    ok(any("missing required field 'duration'" in e for e in errors_for(bad, vo, beats, segments)), "missing required field must fail")

    bad = copy.deepcopy(beats)
    bad.pop()
    ok(any("1-2" in e and "no beat" in e for e in errors_for(shots, vo, bad, segments)), "missing beat must fail")

    bad = copy.deepcopy(beats)
    bad.append(copy.deepcopy(bad[0]))
    ok(any("duplicate beat_id" in e for e in errors_for(shots, vo, bad, segments)), "duplicate beat must fail")

    bad = copy.deepcopy(beats)
    bad[0]["shot_id"] = "9-9"
    ok(any("unknown shot_id" in e for e in errors_for(shots, vo, bad, segments)), "unknown beat shot must fail")

    bad = copy.deepcopy(beats)
    bad[0]["shot_id"] = "1-2"
    bad[1]["shot_id"] = "1-1"
    ok(any("out of shot order" in e for e in errors_for(shots, vo, bad, segments)), "beat order must fail")

    bad = copy.deepcopy(beats)
    bad[1]["shot_id"] = "1-1"
    ok(any("are not linked" in e for e in errors_for(shots, vo, bad, segments)), "beat/VO shot mismatch must fail")

    bad = copy.deepcopy(vo)
    bad.append({"vo_id": "V09", "start": "10", "end": "11", "text": "孤句。", "shot_ids": "1-1"})
    ok(any("V09" in e and "no beat" in e for e in errors_for(shots, bad, beats, segments)), "orphan VO must fail")

    bad = copy.deepcopy(vo)
    bad[0]["end"] = "0.1"
    ok(any("end must be after start" in e for e in errors_for(shots, bad, beats, segments)), "VO timing must fail")

    bad = copy.deepcopy(segments)
    bad[1]["end"] = "20"
    bad[1]["duration"] = "15"
    ok(any("exceeds max" in e for e in errors_for(shots, vo, beats, bad)), "segment overflow must fail")

    bad = copy.deepcopy(segments)
    bad[1]["shot_id"] = "1-1"
    ok(any("more than once" in e for e in errors_for(shots, vo, beats, bad)), "duplicate segment shot must fail")

    bad = copy.deepcopy(segments)
    bad[1]["start"] = "5.5"
    bad[1]["duration"] = "3.5"
    ok(any("start at previous cut end" in e for e in errors_for(shots, vo, beats, bad)), "segment continuity must fail")

    bad = copy.deepcopy(segments)
    bad[1]["cut_order"] = "3"
    ok(any("contiguous" in e for e in errors_for(shots, vo, beats, bad)), "cut order must fail")

    bad = copy.deepcopy(segments)
    bad[1]["scene_id"] = "9"
    ok(any("one scene_id" in e for e in errors_for(shots, vo, beats, bad)), "segment scene change must fail")

    bad = copy.deepcopy(segments)
    bad[1]["shot_id"] = "9-9"
    ok(any("unknown shot_id" in e for e in errors_for(shots, vo, beats, bad)), "unknown segment shot must fail")

    bad = copy.deepcopy(segments)
    bad[0]["end"] = "4"
    bad[0]["duration"] = "4"
    ok(any("does not match shots.csv" in e for e in errors_for(shots, vo, beats, bad)), "segment/shot duration mismatch must fail")

    bad = copy.deepcopy(segments)
    bad[1]["start"] = "4.5"
    bad[1]["duration"] = "4.5"
    ok(any("does not match shots.csv" in e for e in errors_for(shots, vo, beats, bad)), "segment/shot start mismatch must fail")

    bad = copy.deepcopy(segments)
    bad[1]["keyframe"] = "nope.png"
    ok(any("keyframe not found" in e for e in errors_for(shots, vo, beats, bad)), "strict keyframe must fail")

    bad = copy.deepcopy(segments)
    bad[0]["keyframe"] = "首帧/1-2_first.png"
    ok(any("!= shot first_frame" in e for e in errors_for(shots, vo, beats, bad)), "wrong keyframe must fail")

    bad = copy.deepcopy(beats)
    bad[0]["story_segment"] = "9"
    ok(any("story_segment" in e for e in errors_for(shots, vo, bad, segments)), "story segment drift must fail")

    ok(any("beats.csv: missing" in e for e in v.validate_rows(shots, vo, None, segments, allow_partial=False)), "missing beats must fail")
    ok(any("segments.csv: missing" in e for e in v.validate_rows(shots, vo, beats, None, allow_partial=False)), "missing segments must fail")

    # Templates must be internally consistent.
    tshots = v.read_csv(SKILL / "templates" / "shots.csv")
    tvo = v.read_csv(SKILL / "templates" / "vo.csv")
    tbeats = v.read_csv(SKILL / "templates" / "beats.csv")
    tsegments = v.read_csv(SKILL / "templates" / "segments.csv")
    ok(
        v.validate_rows(tshots, tvo, tbeats, tsegments, strict_files=True, base_dir=SKILL / "templates") == [],
        "templates must validate by default",
    )

    # H3 exporter must produce multi-image alignment and correct cut time.
    tprompts = {row["shot_id"]: row for row in v.read_csv(SKILL / "templates" / "h3_prompts.csv")}
    s03 = [row for row in tsegments if row["generation_id"] == "S03"]
    text = export_h3.build_segment("S03", s03, tprompts)
    ok("Picture 2" in text and "00:01.500" in text, "H3 export must contain second-picture cut time")
    ok("non_diegetic_music: N/A" in text, "H3 export must declare no BGM")

    # Static opening card: included in timeline/segments, excluded from H3 tasks/export.
    static_shots = v.read_csv(STATIC / "shots.csv")
    static_vo = v.read_csv(STATIC / "vo.csv")
    static_beats = v.read_csv(STATIC / "beats.csv")
    static_segments = v.read_csv(STATIC / "segments.csv")
    ok(
        v.validate_rows(static_shots, static_vo, static_beats, static_segments, strict_files=True, base_dir=STATIC) == [],
        "static card fixture must pass",
    )
    ok(export_h3.is_static(static_segments[0]) and not export_h3.is_static(static_segments[1]), "static flag must be readable")
    static_project = json.loads((STATIC / "project.json").read_text(encoding="utf-8"))
    ok(
        v.validate_rows(static_shots, static_vo, static_beats, static_segments, strict_files=True, base_dir=STATIC, project=static_project) == [],
        "opening-card project fixture must pass",
    )
    bad = copy.deepcopy(static_shots)
    bad[0]["duration"] = "9"
    ok(any("opening_seconds" in e for e in v.validate_rows(bad, static_vo, static_beats, static_segments, strict_files=True, base_dir=STATIC, project=static_project)), "opening duration mismatch must fail")
    bad_project = dict(static_project)
    bad_project["duration_target_sec"] = 8
    ok(any("total" in e for e in v.validate_rows(static_shots, static_vo, static_beats, static_segments, strict_files=True, base_dir=STATIC, project=bad_project)), "opening target mismatch must fail")
    ok(any("not static" in e for e in v.validate_rows(shots, vo, beats, segments, strict_files=True, base_dir=FIXTURE, project=static_project)), "opening static without card must fail")
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "opening_card.md").write_text("# 片头卡\n\n- 主标题：\n- 逐字确认：[ ]\n", encoding="utf-8")
        errors = v.validate_rows(
            static_shots, static_vo, static_beats, static_segments,
            strict_files=False, base_dir=Path(tmp), project=static_project,
        )
        ok(any("主标题" in e for e in errors), "opening title must fail")
        ok(any("逐字确认" in e for e in errors), "opening confirmation must fail")
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [
                sys.executable,
                str(HERE / "export_h3.py"),
                "--shots", str(STATIC / "shots.csv"),
                "--segments", str(STATIC / "segments.csv"),
                "--prompts", str(SKILL / "templates" / "h3_prompts.csv"),
                "--out", str(Path(tmp) / "pkg"),
            ],
            cwd=SKILL,
            capture_output=True,
            text=True,
        )
        ok(result.returncode == 0 and not (Path(tmp) / "pkg" / "CARD").exists(), "static card must be skipped by H3 export")

    # Timeline still runs on the same templates (no images, so no animatic).
    with tempfile.TemporaryDirectory() as tmp:
        timeline_out = Path(tmp) / "timeline.csv"
        result = subprocess.run(
            [
                sys.executable,
                str(HERE / "timeline.py"),
                "--shots", str(SKILL / "templates" / "shots.csv"),
                "--vo", str(SKILL / "templates" / "vo.csv"),
                "--out", str(timeline_out),
                "--allow-single",
                "--target", "9",
            ],
            cwd=SKILL,
            capture_output=True,
            text=True,
        )
        ok(result.returncode == 0 and timeline_out.is_file(), "timeline must succeed on templates")

    task = {
        "generation_id": "S01",
        "provider": "minimax_h3",
        "model": "MiniMax-H3",
        "resolution": "768P",
        "duration": 9,
        "status": "todo",
        "prompt": "h3_package/S01/prompt.md",
        "first_frames": ["首帧/1-1_first.png"],
    }
    ok(validate_tasks.validate_tasks([task], {"S01"}) == [], "good H3 task must pass")
    bad_task = dict(task)
    bad_task.pop("model")
    ok(any("missing model" in e for e in validate_tasks.validate_tasks([bad_task], {"S01"})), "task missing model must fail")
    bad_task = dict(task)
    bad_task["duration"] = 3
    ok(any("duration" in e for e in validate_tasks.validate_tasks([bad_task], {"S01"})), "task duration must fail")
    bad_task = dict(task)
    bad_task["generation_id"] = "S99"
    ok(any("no such generation_id" in e for e in validate_tasks.validate_tasks([bad_task], {"S01"})), "task unknown generation must fail")

    print(f"selftest: ok - {passed} assertions")
    print("gates: schema, required, status, beat coverage, duplicate beat, unknown shot, beat order, beat/VO link, orphan VO, VO timing, segment max, duplicate shot, continuity, cut order, scene, segment/shot span, keyframe, missing structure, templates, H3 export, static card, timeline")


if __name__ == "__main__":
    main()
