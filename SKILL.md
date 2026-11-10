---
name: ai-documentary-production
description: 制作由需求决定时长的中文人物/主题短片；覆盖 brief、史实核查、旁白、节拍、段/切/关键帧、首帧、H3 投产包、评审、剪辑、配乐、终检与交付；30 秒和 3 分钟只是示例，不是硬范围。
when_to_use: 用户要做人物/主题短片，需要从 brief 到成片的可复用流程、结构化契约、门禁、自测、模板和成本记录。
version: "1.7"
allowed-tools:
  - Read
  - Write
  - Bash
  - Task
  - Glob
triggers:
  - ai-documentary-production
  - 纪录片
  - 人物短片
  - 旁白
  - 分镜
  - 首帧
  - H3
metadata:
  license: Apache-2.0
  requires:
    bins:
      - python
      - ffmpeg
      - ffprobe
    python:
      - pillow
  runtimes:
    - claude-code
    - codex
---

# AI Documentary Production

## 第一次使用：先过环境关

1. **图片**：默认用户 GPT 出图，AI 不调用图片 API；`image_mode=agent` 需明确批准。
2. **环境**：Python 3.10+、`ffmpeg`、`ffprobe`；`contact_sheet.py` 另需 Pillow；无 PyYAML 依赖。
3. **H3**：没配过 MiniMax H3，先看 `references/00_setup.md`：
   - 开放平台注册/实名/充值；
   - 创建 API Key；
   - `MINIMAX_API_KEY` 环境变量或密钥文件；
   - `base_url` / 模型名 / 分辨率对齐；
   - **先跑一条 4 秒测试**，再批量。
4. Key 不进代码、不进日志、不进 git。
5. H3 不可用就换 provider 或先做 animatic，不要假装能生成。
6. 没配置 H3，不进入 G5。

## 何时使用

- 用户要做 **人物/主题短片**，时长由 brief 决定；
- 30 秒、1 分钟、3 分钟都只是示例，不是硬范围；
- 有真实人物、历史资料、AI 情景再现；
- 需要从零走到可交付成片；
- 需要控制成本、保留来源、写 credits。

## 不适用

- 多人物群像、采访型长片；
- 商业广告、纯产品片；
- 纯动画、纯虚拟制片；
- 需要真实摄制的现场纪录片。

> 时长不设硬门槛；超长项目需要另加素材管理，但流程不变。

## 开工前必须问

1. 成片时长、画幅、帧率、语言、平台；
2. 人物是谁、讲哪一段、哪些事实不能错；
3. 预算上限、是否允许重试；
4. 图片谁出（`image_mode=human/agent`）、视频用什么模型、剪辑用什么软件；
5. 旁白是真人还是 TTS；音乐是否单独一轨；
6. 是否有历史照片/音乐授权；是否需要 AI 声明；
7. 交付格式与截止时间；
8. profile：`short`（约 15–60s）/ `standard`（约 2–5min）/ `custom`（按需求）；
9. `model_routing`：`hybrid` / `gpt_only` / `codex_deepseek`；
10. H3 是否已配置（Key/base_url/model/额度）；没配先教配置；
11. 片头卡：`none` / `static`；几秒；算不算目标时长；标题文字到 G2.5 再定。

没有 brief，不进入研究。

## 时长与 profile

时长由 `project.yaml` 的 `duration_target_sec` 决定，不写死。

| profile | 示例时长 | 镜头数（示例） | 段落（示例） | 音乐（示例） |
|---|---:|---:|---:|---:|
| short | 15–60s | 8–18 | 1–2 | 1 段 |
| standard | 2–5min | 24–60 | 3–5 | 3–5 段 |
| custom | 用户定 | 用户定 | 用户定 | 用户定 |

这些是估算，不是门禁；30 秒和 3 分钟只是两个常见例子。

## G4 出图交接

提示词完成后，**先提醒用户出图**，再做并行工作：

1. 发 `image_batch_request.md`：镜号、文件名、提示词位置、数量、优先级；片头卡若启用，`0-1_card.png` 进第一批；
2. 明确说：“现在可以开始生成图片”；
3. 用户开始后，agent 做不依赖图片/视频的工作：字幕、cue sheet、成本表、来源/credits、剪辑骨架、下一批 prompt QA；
4. 不审图、不生成视频、不做最终合成；
5. 用户回图后，先审图，不重新讨论已锁定的旁白/镜头；
6. 片头卡是静态卡，不做 H3；文字逐字验收，中文不稳时改后期叠字。

> 不要默默做别的让用户等；出图任务必须先交出去。详见 `references/13_parallel_work.md`。

## 模型路由

默认 `hybrid`：

| 阶段 | 模型 | 做什么 |
|---|---|---|
| G0–G3 | Codex + DeepSeek | brief、研究、旁白、分镜、提示词 |
| G4 | **GPT** | 出图/审图；`image_mode` 决定谁出 |
| G5–G8 | Codex + DeepSeek | 任务、成本、剪辑文件、QC；看图时临时切 GPT |

- **文字和文件用 DeepSeek，像素和视觉用 GPT**；
- `image_mode=human`：用户 GPT 出图；`image_mode=agent`：Codex + 图像工具出图（需明确批准）；
- 切换前写 `image_handoff.md`，项目文件是交接凭证；
- 详见 `references/10_model_routing.md`。

## 9 个阶段与 G0–G8 门禁

| 阶段 | 产物 | 门禁 |
|---|---|---|
| G0 Brief | `project_brief.md` | 时长、预算、权利、平台锁定 |
| 研究/史实核查 | `fact_check.csv`、`research.md` | G1 事实锁定 |
| 脚本/旁白 | `script.md`、`vo.csv`、`vo_text_review.md`、`voice_audition.md`、`vo_lock.md`、`vo_review.md` | G2 旁白锁定（文案 + 音色 + 版本） |
| 分镜/时间线 | `beats.csv`、`shots.csv`、`segments.csv`、`timeline.csv`、`animatic.mp4`、`v0_review.md` | G3 节拍认领 + 镜头表 + v0 确认 |
| 首帧（按 image_mode） | `首帧/`、`image_review.md`、`image_handoff.md`、`image_batch_request.md` | G4 首帧锁定 |
| 视频生成 | `h3_package/`、`clips/`、`tasks.json`、`cost.csv` | G5 视频锁定 |
| 粗剪/字幕 | `cut/`、`subtitles.srt` | G6 画面锁定 |
| 配乐/音效 | `music/`、`cue_sheet.csv` | G7 声音锁定 |
| 终检/交付 | `final.mp4`、`final_qc.md`、`credits.md` | G8 交付 |

**规则：上一关没过，不进入下一关，不花钱。**

## 片头卡

只在 G0 问“要不要、几秒、算不算目标时长”；标题文字到 G2.5 再定。

- **G0**：`opening_card: none|static`；`opening_seconds`；`opening_in_target`；
- **G2.5**：主标题/副标题/字体风格；`opening_card.md` 逐字确认；
- **G3**：作为 `0-1` 静态镜头写入 `shots.csv`（`static=yes`，无旁白），`segments.csv` 写一行 `CARD`（`static=yes`）；
- **G4**：进第一批出图，文件名 `首帧/0-1_card.png`；文字和图片一起出时逐字验收；
- **G5**：**不做 H3**；`export_h3.py` 跳过 `static=yes`，H3 任务表不排它；
- **G6**：剪辑里静态 hold；可做 1–2% 缓慢推近；
- 片头卡时长从目标时长里扣，或明确加到总长，G0 就定。

> 片头卡是“立项时的时长决策”，不是“出图时的装饰选项”。

## 旁白审核顺序

1. **文案评审**：把 `vo.csv` 全文、时间码、事实备注给用户看；先做“冷读者测试”，用户确认后再做声音；
2. **音色试听**：同一句生成 2–3 个候选，用户选 A/B/C 或自己录；
3. **整条 scratch**：按选定音色生成完整旁白；
4. **v0 animatic**：才做静帧 + 旁白；
5. 任何一步没确认，不进入下一步。

## 旁白先行

这是本技能的核心顺序：

1. **先定旁白**，再定镜头、首帧、视频；
2. **一句旁白配 2–3 个画面是常态**；
3. **一镜一句是特殊情况**（短促反应、口号、单镜蒙太奇），不是默认；
4. 旁白独立成 `vo.csv`，不要按镜头切碎；
5. 不要按镜头生成 TTS；按句子/段落生成，整段放一条音轨；
6. 每句一个信息；每 1–2 句至少一个硬信息（年份/人名/数字/动作/因果）；
7. 诗性意象必须有具体锚点、一条链、能落地；“大门/种子”可以是 motif，不是自动错误；无锚点口号才是空词；先讲清因果，再谈诗意；
8. 写完先跑 `narration_lint.py`，再读一遍定稿；
9. 剪辑时用 J-cut/L-cut：画面切，旁白不断；
10. **句与句之间留 0.3–1.0 秒气口**；5 秒旁白不要硬贴 5 秒画面；气口最好由一个无旁白短镜头承载，不要塞在有旁白的镜头内部；
11. 气口只放在旁白句与句之间；切点要落在气口里，不能落在有旁白的句子内部；
12. 旁白锁定后不直接改旧版；先 `vo_diff.py`，只改受影响文件；
13. **一段旁白可以跨多个镜头；普通镜头最多一段旁白**；`long_take=yes` 的长镜头可以含多段旁白，但每段必须完整在镜内；
14. 相邻旁白的气口窗口必须包含至少一个镜头切点；句子起止可以落在镜头内部，不要求和切点齐平；有区间时气口取大；
15. 排完 `shots.csv` / `timeline.csv` 后先出 **v0 animatic**（静帧/黑帧 + 旁白），明确提醒用户听句间气口；确认后再出首帧/视频；
16. **先给文案看，再定音色，再做 v0**：没有用户对文案和音色的确认，不生成 TTS/animatic。

> 先有旁白，再有画面；不是先有 40 个镜头，再往每镜里塞一句话。

## 文件契约

### `shots.csv`

```text
id,story_segment,scene_id,duration,shot_size,camera,scene,action,expression,vo_ids,anchor,first_frame,video,status,cost,notes,long_take,static
```

- `story_segment` 是叙事段号，不是 H3 生成段；生成段在 `segments.csv` 的 `generation_id`；
- `scene_id` 是场景编号，必须和 `segments.csv` 对得上；
- `duration` 用秒，支持小数；
- `status` 只用 `todo/image_ready/video_running/video_ok/conditional/retake/final`；
- `vo_ids` 可空；普通镜头最多一个 vo_id；`long_take=yes` 的长镜头可以写 `V01|V02`；
- `long_take=yes`：一个连续长镜头，允许 2 段以上旁白，但每段必须完整在镜头内；
- `static=yes`：静态片头/插入卡，不做 H3；必须有 `first_frame`，`segments.csv` 用 `static=yes` 段；
- 这是画面真相源；旁白在 `vo.csv`，两者用 `vo_ids` 关联。

### `vo.csv`

```text
vo_id,start,end,text,shot_ids,notes
V01,0.0,4.2,"一句完整旁白","1-1|1-2","4.2s；句后0.8s气口"
V02,5.0,6.2,"下一句","1-3","1.2s；句尾0.8s"
```

- `start/end` 是绝对秒；
- 一句旁白可以跨 2–3 个镜头；
- 一镜一句只在特殊情况下使用；
- 句与句之间留 0.3–1.0 秒气口；
- 一个 `shot_id` 只能属于一个 cue；一个 cue 可以覆盖多个 shot；
- 字幕从 `vo.csv` 生成，不跟镜头绑定。

### `beats.csv`

```text
beat_id,story_segment,kind,shot_id,vo_id,text,notes
B01,1,action,1-1,V01,柜台后算题,
B02,1,action,2-1,V02,把论文装进信封,
```

- 节拍是故事最小单位，不是音乐节拍；
- 每个节拍**恰好**被一个 `shot_id` 认领；
- 每个非 `static` 镜头至少一个节拍；`static=yes` 的片头卡可以没有 beat；每段旁白至少一个节拍；
- 一个旁白可以跨多个节拍，在每行重复同一个 `vo_id`；
- 节拍顺序必须跟镜头顺序一致；漏拍、重复、乱序由 `validate.py` 拦。

### `segments.csv`

```text
generation_id,scene_id,cut_order,shot_id,start,end,duration,keyframe,static,notes
S01,1,1,1-1,0,5,5,首帧/1-1_first.png,no,单切段
S02,1,1,1-2,5,9,4,首帧/1-2_first.png,no,段内第 1 切
S02,1,2,1-3,9,15,6,首帧/1-3_first.png,no,段内第 2 切
```

- `generation_id` = 一次 H3 生成；一段 ≤15 秒，不跨场；
- `scene_id` 必须等于 `shots.csv` 同镜的 `scene_id`；换场必须换段；
- `cut_order` = 段内第几切，从 1 连续；
- `keyframe` = 这一切的构图锚图；第 1 切钉 0.00 秒，后续钉切点；
- `static=yes` = 静态卡，不进 H3；必须单切；`export_h3.py` 会跳过；
- 每个 shot 只能出现在一个 generation 里；
- 每一刀的 `start/end/duration` 必须等于 `shots.csv` 的累计起止；全片必须无断档、无重叠；
- `validate.py` 拦越界、错位、断档、重复。

### `h3_prompts.csv`

```text
shot_id,prompt,soundscape,notes
1-1,"保持首帧；笔尖缓慢移动，灯焰轻晃。","纸笔声、远处风声。",
```

- `export_h3.py` 按 `segments.csv` 分组，把每个切的 prompt 拼成一段多图对齐提示词；
- 输出 `h3_package/<generation_id>/prompt.md` + `manifest.json`；
- 不调用 API；生成仍由 H3 任务表执行。

### 旁白版本

```text
vo_versions/vo_v1.csv
vo_v1_scratch.wav
vo_lock.md
```

- 锁定前先试读/TTS，量真实时长；
- 锁定后只新增版本，不直接改旧版；
- 改旁白先跑 `vo_diff.py`，再按影响范围改；
- 详见 `references/12_change_control.md`。

### `project.json`

`init_project.py` 生成的机器配置：`profile/model_routing/image_mode/duration_target_sec/shot_target/fps/resolution/providers`。  
`project.yaml` 是人读版；脚本读 `project.json`。

### `tasks.json`

```json
[{"generation_id":"S01","provider":"minimax_h3","model":"MiniMax-H3","resolution":"768P","duration":9,"status":"todo","prompt":"h3_package/S01/prompt.md","first_frames":["首帧_h3/1-1_first.png"],"cost_cny":0.0}]
```

- `generation_id` 对应 `segments.csv` 的生成段；
- `duration` 必须是 4–15 的整数；
- `prompt` / `first_frames` 是投产包路径；
- 失败任务不计费；重试单独列；
- 旧逐镜任务可用 `id`，但 `h3_tasks.json` 一律用 `generation_id`。

### 交付包

```text
final.mp4
subtitles.srt
vo.wav
vo.csv
music/A-E.wav + cue_sheet.csv
credits.md
source_list.csv
fact_check.csv
final_qc.md
```

## 硬规则

1. 图片默认用户 GPT 生成，AI 不调用图片 API；仅当 `image_mode=agent` 且用户明确批准时才允许图像工具；
2. 视频默认一版制，不能用才补一版；
3. 生成的视频只允许环境音/人声，不允许配乐/BGM；
4. 768P 源素材可能是 1344×768（7:4），终版交付 1920×1080；
5. 首帧必须 16:9，否则图生视频比例会漂；
6. 历史照片标来源，AI 画面标“情景再现”；
7. 字幕 16–20 字/行、最多 2 行、左右 ≥100px；
8. 音乐每段留 1.5–2 秒 handle，低谷不是静音；
9. 成本按任务日志算，不靠记忆；
10. 交付前用 ffprobe 复核分辨率/帧率/音频；
11. 先定旁白，再定镜头；默认一句旁白跨 2–3 镜，一镜一句是特殊情况；
12. 旁白不要铺满画面；5 秒旁白配 5 秒画面会赶，句间留 0.3–1.0 秒气口；
13. 旁白可以诗性，但诗性要有物/动作锚点；解释段才要求每句一个硬信息；不要把两套标准混用；
14. 旁白锁定后，禁止因为改一句旁白重写全项目；先 `vo_diff.py`，再只改受影响文件；
15. G4 提示词完成后，先提醒用户出图；用户开始出图后，才做不依赖图片/视频的并行工作；
16. 一段旁白可跨多个镜头；普通镜头最多一段旁白；`long_take=yes` 的长镜头可含多段旁白，但必须全部在镜头内；
17. 气口窗口必须包含镜头切点；不要要求句子起止贴切点；气口有区间时取大；
18. v0 animatic 出完后，先提醒用户检查句间气口；确认前不出首帧、不生成视频；
19. 音色必须试听 2–3 个候选后由用户选定；不能默认用某个 TTS；
20. 旁白默认“清楚但不直白”：先讲清人物/事件/因果，再用具体物象和短句留白；允许加 1–2 句，但每句要有新信息或新画面，不用形容词凑时长；
21. `beats.csv` 的每个节拍必须恰好一个镜头认领；每个镜头、每段旁白都要有节拍覆盖；漏拍/重复/乱序由 `validate.py` 拦；
22. `segments.csv` 一段 ≤15 秒；段内切序连续、每切一张关键帧、每个 shot 只出现一次；每切起止必须等于 `shots.csv` 的累计时间；H3 多图对齐用 `export_h3.py` 出投产包；
23. 片头卡：G0 定时长，G2.5 定文字，G3 写 `0-1 static=yes`，G4 出图，G5 不做 H3；
24. 剧本/旁白必须过冷读者测试：遮住标题和画面，只读文案，**必须答出“他是谁、做过什么”**；“为什么值得看”是加分。答不出就补动作/身份/因果，不补形容词。

## Provider

`config/providers.yaml` 是文档；机器配置是 `providers.json`（由 `init_project.py` 生成，`timeline.py` 会校验）。

默认：图片=user_gpt，视频=minimax_h3，旁白=capcut_tts，配乐=local_midi_fluidsynth，剪辑=capcut，质检=ffmpeg。

图片 provider 永远是 human；这条不随配置改变。

## 命令

```bash
python scripts/init_project.py --root my-film --profile short --duration 30 --shots 10 --segments 2
python scripts/timeline.py --shots shots.csv --vo vo.csv --vo-out vo_report.csv --project project.json --min-gap 0.4
python scripts/timeline.py --shots shots.csv --vo vo.csv --max-density 0.85 --allow-single
python scripts/narration_lint.py --text vo.csv --style lyrical --max-chars 28
python scripts/validate.py --shots shots.csv --vo vo.csv --beats beats.csv --segments segments.csv --project project.json
python scripts/validate.py --shots shots.csv --vo vo.csv --beats beats.csv --segments segments.csv --project project.json --strict-files
python scripts/validate_tasks.py --tasks h3_tasks.json --segments segments.csv
python scripts/selftest.py
python scripts/export_h3.py --shots shots.csv --segments segments.csv --prompts h3_prompts.csv --out h3_package
python scripts/timeline.py --shots shots.csv --vo vo.csv --animatic animatic.mp4
python scripts/vo_gap_report.py --vo vo.csv --audio vo_scratch.wav --out vo_gap.md
python scripts/vo_diff.py --old vo_versions/vo_v1.csv --new vo.csv --out vo_diff.md
python scripts/vo2srt.py --vo vo.csv --out subtitles.srt --max-chars 18
python scripts/contact_sheet.py --clips clips --out review --frames 6
python scripts/cost_report.py --tasks tasks.json --out cost.csv --default-model MiniMax-H3
```

脚本：`init_project.py`、`validate.py`、`selftest.py`、`export_h3.py`、`timeline.py`、`narration_lint.py`、`vo2srt.py`、`vo_gap_report.py`、`vo_diff.py`、`contact_sheet.py`、`cost_report.py`。`--animatic` 缺首帧默认黑帧占位，`--animatic-missing error` 可改为报错。

`validate.py` 管结构契约（schema / 节拍 / 段切 / 覆盖）；G3 默认不查关键帧文件，G5 用 `--strict-files` 查。`timeline.py --vo` 管时间（气口 / 密度 / 长镜头）。两个都跑，不互相替代。

## 失败处理

- 视频失败：查任务状态；失败不计费；换 H3-Max 或改首帧，不盲目重跑；
- 人物变脸/多手：重生成或改侧影/背影；
- 动作没发生：重生成，别用剪辑硬补；
- 字幕溢出：改样式/断行，不缩到看不清；
- 音乐突兀：加 pickup、expression ramp、handle，不硬切；
- 导出比例错：回工程改 1920×1080，不拉宽。

## 参考

- `SOP.md`：人看的流程与检查表
- `references/`：阶段细节（含 `00_setup.md`、`09_vo_spans.md`、`10_model_routing.md`、`11_narration.md`、`12_change_control.md`、`13_parallel_work.md`、`14_v0_animatic.md`、`15_beats_segments.md`）
- `providers/`：可替换工具
- `templates/`：项目卡、镜头表、提示词、评审表、cue sheet、credits、终检
