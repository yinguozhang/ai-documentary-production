# ai-documentary-production

面向中文人物 / 主题短片的 **AI documentary production skill**：从 brief、史实核查、旁白、节拍、分镜、首帧，到 H3 视频、剪辑、配乐和终检，给出一条可执行、可验证的生产流程。

时长由项目决定，30 秒、1 分钟、3 分钟都只是示例，不写死。

## 它解决什么

- **旁白先行**：先定文案和音色，再排镜头；旁白不铺满画面，句间留气口。
- **节拍不靠自觉**：`beats.csv` 保证每个节拍恰好一个镜头，镜头/旁白都有归属。
- **段 / 切 / 关键帧**：一次 H3 生成可以包含多切，每切一张关键帧，切点时刻可对账。
- **结构门**：`validate.py` 检查 schema、节拍、段/镜时间、scene_id、keyframe 是否等于首帧。
- **工具自测**：`selftest.py` 用“应该失败”的样例证明门真的会拦。
- **片头卡**：G0 决定 none/static、秒数和是否算目标时长；G2.5 定文字；G4 出图；G5 不做 H3。
- **制作纪律**：图片由用户 GPT 生成，AI 不调用图片 API；生成视频只保留环境音/人声，不混 BGM。

## 环境

- Python 3.10+
- `ffmpeg`、`ffprobe`
- `contact_sheet.py` 需要 Pillow
- 视频可选 MiniMax H3；没配 H3 先做 animatic，不要假装能生成

## 安装

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
# 或指定目录
powershell -ExecutionPolicy Bypass -File scripts/install.ps1 -Target "$HOME\.claude\skills"
```

```bash
./scripts/install.sh "$HOME/.claude/skills"
./scripts/install.sh --uninstall "$HOME/.claude/skills"
```

软链失败时 Windows 回退复制。

## 快速开始

```bash
python scripts/init_project.py --root my-film --profile short --duration 30
```

然后：

1. 填 `project_brief.md` / `project.json`；G0 定片头卡；
2. 写 `vo.csv`，G2.5 锁文案和音色；
3. 填 `opening_card.md`（如果启用片头卡）；
4. 排 `beats.csv` / `shots.csv` / `segments.csv`；
5. 跑结构门：

```bash
python scripts/validate.py \
  --shots shots.csv --vo vo.csv \
  --beats beats.csv --segments segments.csv \
  --project project.json
```

6. 跑 `selftest.py`；
7. 出 v0 animatic，确认气口；
8. G4 出首帧，G5 生成 H3，G6–G8 剪辑/配乐/终检。

完整流程见 [SKILL.md](SKILL.md) 和 [SOP.md](SOP.md)。

## 目录

```text
SKILL.md                  AI 入口
SOP.md                    人看的 G0–G8 流程
references/               阶段细节与检查表
templates/                项目卡、vo、beats、segments、H3、片头卡、评审、终检
schemas/                  shots / vo / beats / segments 的 JSON Schema
scripts/                  init / validate / validate_tasks / selftest / export_h3 / timeline / 字幕 / 成本
tests/                    自测与 fixture
CHANGELOG.md              版本与变更
LICENSE / NOTICE          Apache-2.0
```

## 验证

```bash
python tests/test_manifest.py
python scripts/selftest.py
python scripts/validate.py \
  --shots templates/shots.csv --vo templates/vo.csv \
  --beats templates/beats.csv --segments templates/segments.csv
```

## 边界

- 不做多人物群像、采访型长片、纯动画；
- 图片默认由用户 GPT 出，AI 不调用图片 API；
- 配乐只由后期单独提供，不混入生成视频；
- 不替代 DSH loader 的安装测试；manifest 测试只检查 frontmatter。

## License

Apache-2.0，见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
