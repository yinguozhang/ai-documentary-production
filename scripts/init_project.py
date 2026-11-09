#!/usr/bin/env python3
"""Create a new short-documentary project skeleton."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

from config import DEFAULT_PROJECT, DEFAULT_PROVIDERS, PROFILES, fail


SHOTS_HEADER = (
    "id,story_segment,scene_id,duration,shot_size,camera,scene,action,expression,"
    "vo_ids,anchor,first_frame,video,status,cost,notes,long_take,static"
)
VO_HEADER = "vo_id,start,end,text,shot_ids,notes"
BEATS_HEADER = "beat_id,story_segment,kind,shot_id,vo_id,text,notes"
SEGMENTS_HEADER = "generation_id,scene_id,cut_order,shot_id,start,end,duration,keyframe,static,notes"
H3_PROMPTS_HEADER = "shot_id,prompt,soundscape,notes"
FACT_HEADER = "claim,status,source,note"
SOURCE_HEADER = "item,type,source,url_or_location,used_in,license"


def write_text(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        fail(f"file exists: {path} (use --force)")
    path.write_text(text, encoding="utf-8")


def project_yaml(project: dict) -> str:
    providers = project["providers"]
    rights = project["rights"]
    return f"""# 项目卡（人读版）；机器版是 project.json
title: "{project['title']}"
subtitle: "{project['subtitle']}"
profile: "{project['profile']}"
model_routing: "{project['model_routing']}"
image_mode: "{project['image_mode']}"
target_duration_sec: {project['duration_target_sec']}
shot_target: {project['shot_target']}
segment_target: {project['segment_target']}
opening_card: "{project['opening_card']}"
opening_seconds: {project['opening_seconds']}
opening_in_target: {str(project['opening_in_target']).lower()}
aspect: "{project['aspect']}"
resolution: "{project['resolution']}"
fps: {project['fps']}
language: "{project['language']}"
audience: "{project['audience']}"
platform: "{project['platform']}"
deadline: "{project['deadline']}"
budget_cny: {project['budget_cny']}

providers:
  image: {providers['image']}
  video: {providers['video']}
  voice: {providers['voice']}
  music: {providers['music']}
  edit: {providers['edit']}
  qc: {providers['qc']}

rights:
  historical_photos: "{rights['historical_photos']}"
  music: "{rights['music']}"
  ai_disclosure: {str(rights['ai_disclosure']).lower()}
"""


def brief(project: dict) -> str:
    return f"""# 项目卡

## 基本信息

- 片名：{project['title']}
- 副标题：{project['subtitle']}
- profile：{project['profile']}
- model_routing：{project['model_routing']}（hybrid / gpt_only / codex_deepseek）
- image_mode：{project['image_mode']}（human / agent）
- 时长目标：{project['duration_target_sec']} 秒
- 镜头数目标：{project['shot_target']}
- 段数目标：{project['segment_target']}
- 片头卡：{project['opening_card']} / {project['opening_seconds']}s / 算目标时长：{'yes' if project['opening_in_target'] else 'no'}
- 画幅：{project['aspect']}
- 分辨率：{project['resolution']}
- 帧率：{project['fps']}
- 语言：{project['language']}
- 平台/比赛：
- 截止时间：

## 人物与故事

- 人物：
- 时间范围：
- 核心问题：
- 不能错的事实：
- 必须出现的场景/道具：

## 预算与工具

- 预算上限：{project['budget_cny']}
- 图片：用户 GPT
- 视频：{project['providers']['video']}
- 旁白：{project['providers']['voice']}
- 配乐：{project['providers']['music']}
- 剪辑：{project['providers']['edit']}

## 权利

- 历史照片来源：
- 音乐/音效授权：
- AI 声明：需要 / 不需要
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a short-documentary project skeleton")
    parser.add_argument("--root", required=True, type=Path, help="project directory")
    parser.add_argument("--profile", choices=["short", "standard", "custom"], default="short")
    parser.add_argument("--model-routing", choices=["hybrid", "gpt_only", "codex_deepseek"], default="hybrid")
    parser.add_argument("--image-mode", choices=["human", "agent"], default="human")
    parser.add_argument("--duration", type=float, default=None, help="target duration in seconds")
    parser.add_argument("--shots", type=int, default=None, help="target shot count")
    parser.add_argument("--segments", type=int, default=None, help="target story-segment count (not H3 generations)")
    parser.add_argument("--opening-card", choices=["none", "static"], default="none", help="static title card or none")
    parser.add_argument("--opening-seconds", type=float, default=3.0, help="title card seconds")
    parser.add_argument("--opening-in-target", choices=["yes", "no"], default="yes", help="count card inside target duration")
    parser.add_argument("--title", default="")
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    preset = PROFILES.get(args.profile, {})
    project = dict(DEFAULT_PROJECT)
    project["title"] = args.title
    project["subtitle"] = args.subtitle
    project["profile"] = args.profile
    project["model_routing"] = args.model_routing
    project["image_mode"] = args.image_mode
    project["providers"] = dict(project["providers"])
    project["providers"]["image"] = "codex_image" if args.image_mode == "agent" else "user_gpt"
    project["duration_target_sec"] = args.duration or preset.get("duration_target_sec", 30)
    project["shot_target"] = args.shots or preset.get("shot_target", 12)
    project["segment_target"] = args.segments or preset.get("segment_target", 2)
    project["opening_card"] = args.opening_card
    project["opening_seconds"] = args.opening_seconds
    project["opening_in_target"] = args.opening_in_target == "yes"

    root = args.root.resolve()
    if root.exists() and any(root.iterdir()) and not args.force:
        fail(f"directory is not empty: {root} (use --force)")
    root.mkdir(parents=True, exist_ok=True)
    for name in ("首帧", "clips", "cut", "review", "music", "字幕", "tasks", "vo_versions"):
        (root / name).mkdir(exist_ok=True)

    write_text(root / "project.yaml", project_yaml(project), args.force)
    write_text(root / "project.json", json.dumps(project, ensure_ascii=False, indent=2) + "\n", args.force)
    providers = json.loads(json.dumps(DEFAULT_PROVIDERS))
    providers["image"]["mode"] = args.image_mode
    providers["image"]["provider"] = project["providers"]["image"]
    write_text(root / "providers.json", json.dumps(providers, ensure_ascii=False, indent=2) + "\n", args.force)
    write_text(root / "project_brief.md", brief(project), args.force)
    write_text(root / "shots.csv", SHOTS_HEADER + "\n", args.force)
    write_text(root / "vo.csv", VO_HEADER + "\n", args.force)
    write_text(root / "beats.csv", BEATS_HEADER + "\n", args.force)
    write_text(root / "segments.csv", SEGMENTS_HEADER + "\n", args.force)
    write_text(root / "h3_prompts.csv", H3_PROMPTS_HEADER + "\n", args.force)
    write_text(root / "vo_versions" / "vo_v1.csv", VO_HEADER + "\n", args.force)
    write_text(root / "fact_check.csv", FACT_HEADER + "\n", args.force)
    write_text(root / "source_list.csv", SOURCE_HEADER + "\n", args.force)
    templates = Path(__file__).resolve().parent.parent / "templates"
    for template_name in ("opening_card.md", "image_handoff.md", "image_batch_request.md", "vo_text_review.md", "voice_audition.md", "vo_review.md", "vo_lock.md", "v0_review.md"):
        template = templates / template_name
        if template.is_file():
            text = template.read_text(encoding="utf-8")
            if template_name == "image_batch_request.md":
                row = (
                    "| 0 | 0-1 | `首帧/0-1_card.png` | 片头卡 | `opening_card.md` | 待定 |\n"
                    if project["opening_card"] == "static"
                    else ""
                )
                text = text.replace("<!-- OPENING_CARD_ROW -->\n", row)
            write_text(root / template_name, text, args.force)
    write_text(
        root / "README.md",
        """# 项目工作区

下一步：

0. 首次用 H3：先配 `MINIMAX_API_KEY`，跑一条 4 秒测试；
1. 填 `project_brief.md`；片头卡在 G0 定 none/static、秒数、是否算目标时长；
2. 先写 `vo.csv`（旁白先行，句间留 0.3–1.0s 气口）；
3. 跑 `narration_lint.py`，填 `vo_review.md`；
4. 把 `vo_text_review.md` 给用户看文案，确认后才做声音；
5. 片头卡文字：填 `opening_card.md`（主标题/副标题/逐字确认）；
6. 生成 2–3 个 `voice_audition.md` 候选，让用户选音色或自己录；
7. 按选定音色做整条 scratch；锁版本到 `vo_versions/vo_v1.csv`，填 `vo_lock.md`；
8. 排 `beats.csv`、`shots.csv`、`segments.csv`：片头卡写 `0-1 static=yes` / `CARD`；跑 `validate.py --project project.json`；再出 v0 animatic（静帧/黑帧 + 旁白）；
9. 提醒用户听 v0 的句间气口；用 `v0_review.md` 确认；
10. 用户确认 v0 后，进入 G4：填 `image_handoff.md` / `image_batch_request.md`；
11. 先提醒用户出图；片头卡进第一批；用户开始后，agent 再做并行工作；
12. 用户回图后审图、生成视频；
13. 长镜头：`shots.csv` 的 `long_take=yes`；`vo_ids` 可写多段，但每段必须完整在镜内；
14. 段/切：`segments.csv` 一段 ≤15s；每切一张关键帧；`export_h3.py` 出多图对齐投产包；
15. 运行：

```bash
python scripts/validate.py --shots shots.csv --vo vo.csv --beats beats.csv --segments segments.csv --project project.json
python scripts/selftest.py
python scripts/export_h3.py --shots shots.csv --segments segments.csv --prompts h3_prompts.csv --out h3_package
python scripts/narration_lint.py --text vo.csv --style lyrical --max-chars 28
python scripts/vo_gap_report.py --vo vo.csv --audio vo_scratch.wav --out vo_gap.md
python scripts/timeline.py --shots shots.csv --vo vo.csv --vo-out vo_report.csv --project project.json --animatic animatic.mp4
python scripts/vo2srt.py --vo vo.csv --out subtitles.srt
```
""",
        args.force,
    )
    print(f"project: {root}")


if __name__ == "__main__":
    main()
