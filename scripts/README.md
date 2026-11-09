# Scripts

十二个命令行脚本，Windows/macOS/Linux 通用。

## 依赖

- Python 3.10+
- `ffmpeg`、`ffprobe` 在 PATH
- `contact_sheet.py` 需要 Pillow：`pip install pillow`
- 无 PyYAML 依赖；机器配置用 `project.json` / `providers.json`

## 0. init_project.py

```bash
python scripts/init_project.py --root my-film --profile short --duration 30 --shots 10 --segments 2
python scripts/init_project.py --root my-film --profile standard --duration 180 --shots 48 --segments 4
python scripts/init_project.py --root my-film --profile short --image-mode agent --model-routing hybrid
python scripts/init_project.py --root my-film --opening-card static --opening-seconds 3 --opening-in-target yes
```

生成：

```text
project.yaml / project.json / providers.json
shots.csv / vo.csv / beats.csv / segments.csv / h3_prompts.csv / opening_card.md / fact_check.csv / source_list.csv
image_handoff.md / image_batch_request.md / vo_text_review.md / voice_audition.md / vo_review.md / vo_lock.md / v0_review.md
vo_versions/
首帧/ clips/ cut/ review/ music/ 字幕/ tasks/
```

## 1. timeline.py

```bash
python scripts/timeline.py --shots shots.csv --out timeline.csv
python scripts/timeline.py --shots shots.csv --vo vo.csv --vo-out vo_report.csv --project project.json --min-gap 0.4
python scripts/timeline.py --shots shots.csv --vo vo.csv --max-density 0.85 --allow-single
python scripts/timeline.py --shots shots.csv --out timeline.csv --target 180
python scripts/timeline.py --shots shots.csv --animatic animatic.mp4 --fps 25 --audio vo.wav
```

- 输入：`shots.csv`，至少 `id,story_segment,scene_id,duration`；
- 支持 float 秒（如 4.4）；
- `shots.csv` 的 `long_take=yes` 允许一镜多段旁白，但每段必须完整在镜内；
- 输出：原列 + `start,end,start_tc,end_tc`；
- `--target` 超过 ±2 秒会 warning；
- `--animatic` 用 `first_frame` 生成静帧 animatic；`--audio` 可混旁白；
- `--vo` 读 `vo.csv`，检查一句旁白跨几个镜头、是否越界/重叠；默认 2–3 镜，一镜一句会 warning；
- `--min-shot/--max-shot` 默认 2/10s：有旁白普通镜头超出范围直接失败；无旁白插入只查上限；
- `--min-gap` 默认 0.4s；句与句之间小于它会 warning（旁白不要铺满画面）；
- `--long-take-min` 默认 5s，`--long-take-max` 默认 15s；
- `--strict-long-take`：超上限直接失败，否则 warning；
- `--max-density` 默认 0.85；总旁白/总时长超了会 warning；
- `--min-rate/--max-rate` 默认 2.0/5.5 字/秒；
- 每个相邻旁白的气口窗口必须包含至少一个镜头切点；句子起止不必贴切点；
- 气口有区间时取大；`--min-gap` 只是下限，不是目标值；
- `--allow-single` 允许一镜一句，不再 warning；
- `--project project.json` 读取 fps/分辨率/目标时长；
- `--animatic-missing black|error`：缺首帧时黑帧占位或直接报错。

## 2. narration_lint.py

```bash
python scripts/narration_lint.py --text vo.csv --style lyrical --max-chars 28
python scripts/narration_lint.py --text script.md --style explanatory --strict
```

- 检查长句、逗号过多、空词/口号、名词化、被动、重复句首；
- `--style lyrical`：允许“大门/种子/明珠”等 motif；`explanatory` 才提示它们要落地；
- `--strict`：有 finding 时 exit 1；
- `--json`：机器可读输出。

## 3. vo2srt.py

```bash
python scripts/vo2srt.py --vo vo.csv --out subtitles.srt --max-chars 18
```

- 按 `vo.csv` 生成 SRT；
- 自动在标点处断行；
- 超过 2 行会 warning。

## 4. vo_gap_report.py

```bash
python scripts/vo_gap_report.py --vo vo.csv --audio vo_scratch.wav --out vo_gap.md
```

- 只看时间码的句间气口，不生成新版本；
- 加 `--audio` 会用 ffmpeg 检测真实静音，和 `vo.csv` 对比；没有 `--audio` 只证明时间码；
- 太短/太长/重叠 warning；
- 低于偏好值提示“能大取大”；
- 排 animatic 前先跑它；v0 animatic 出来后提醒用户听气口；
- 它只报气口，不判断长镜头内部切点；长镜头由 `timeline.py` 检查。

## 5. vo_diff.py

```bash
python scripts/vo_diff.py --old vo_versions/vo_v1.csv --new vo.csv --out vo_diff.md
```

- 按 `vo_id` 比较新增/删除/改词/改时间/改镜头；
- 输出总时长差、受影响镜号、必须重跑的文件；
- 改旁白先跑它，不要整包重写。

## 6. contact_sheet.py

```bash
python scripts/contact_sheet.py --clips clips --out review --frames 6 --width 360
python scripts/contact_sheet.py --clips clips --out review --pattern "b10b_*.mp4"
```

- 每条视频抽 5–8 帧（默认 6）；
- 输出 `review/<id>.jpg`，带 id 和时长；
- 支持单文件或目录、`--recursive`；
- 中文文件名自动用 `msyh.ttc` 等 CJK 字体；也可 `--font` 指定。

## 7. cost_report.py

```bash
python scripts/cost_report.py --tasks tasks.json --out cost.csv --summary cost_summary.md
python scripts/cost_report.py --tasks batch1.json batch2.json --rates rates.json
```

- 输入 `tasks.json`（list 或 `{tasks:[...]}`）；
- `status`：succeeded/success/ok/done/completed 计费；failed/cancelled 不计费；running/unknown 不计费；
- 只有计费状态才用 `cost_cny`；失败/未知即使写了费用也不计；
- 否则按 `duration × rate`；
- `--rates rates.json`：

```json
{"MiniMax-H3": 0.5, "MiniMax-H3-Max": 0.5, "default": 0.5}
```

- `--default-model`：任务没有 model 时使用；
- `--project project.json`：读取预算并提示超支；
- 输出：`cost.csv` + `cost_summary.md`。


## 8. validate.py / opening.py

```bash
python scripts/validate.py --shots shots.csv --vo vo.csv --beats beats.csv --segments segments.csv --project project.json --max-segment 15
python scripts/validate.py --shots shots.csv --vo vo.csv --beats beats.csv --segments segments.csv --allow-missing-files
```

- 检查 `schemas/` 里的字段/枚举；
- 检查每个节拍恰好一个镜头、每个镜头/每段旁白都有节拍；
- 检查段 ≤ `--max-segment`、切序连续、每切起止等于 shots、每个 shot 只出现一次；
- G3 默认不查关键帧文件（图片还没出）；G5 加 `--strict-files` 才查；
- 默认要求 beats/segments；`--allow-partial` 才允许只查 schema；
- `static=yes` 的片头卡：校验单切、keyframe==first_frame；不要求 H3 生成；
- `--project project.json`：检查 `opening_card / opening_seconds / opening_in_target` 与 `0-1` / `CARD` 是否一致；
- 只做结构契约，不替代 `timeline.py --vo` 的气口/密度检查。

## 9. selftest.py

```bash
python scripts/selftest.py
```

- 不调模型、不花额度；
- 用 1 个好样例 + 击穿用例证明 validate/export/tasks 的门真的会拦（共 40 项断言）；
- 改 validate/schema 后先跑它。

## 10. validate_tasks.py

```bash
python scripts/validate_tasks.py --tasks h3_tasks.json --segments segments.csv
python scripts/validate_tasks.py --tasks h3_tasks.json --segments segments.csv --strict-files
```

- 检查 `generation_id/provider/model/resolution/duration/status/prompt/first_frames`；
- duration 必须是 4–15 的整数；
- 每段必须有 task，task 不能指向不存在的 generation；
- `--strict-files` 检查 prompt 与首帧存在。

## 11. export_h3.py

```bash
python scripts/export_h3.py --shots shots.csv --segments segments.csv --prompts h3_prompts.csv --out h3_package
python scripts/export_h3.py --shots shots.csv --segments segments.csv --prompts h3_prompts.csv --out h3_package --allow-missing-files
```

- 一段 = 一次 H3 生成；`static=yes` 的段是静态卡，跳过导出；
- 段内每切一张关键帧；
- 单切段用 I2VA 固定对齐句；多切段用多图对齐 + 切点时刻；
- 必须先通过 `--shots` 对账；坏段/缺关键帧不导出；
- 输出 `h3_package/<generation_id>/prompt.md` + `manifest.json`；
- 不调用 API；`h3_prompts.csv` 每行是 `shot_id,prompt,soundscape`。

## 12. install.ps1 / install.sh

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```
```bash
./scripts/install.sh "$HOME/.claude/skills"
```

- 优先软链；Windows 软链失败时复制；
- 不覆盖非软链目录。

## Smoke tests

```bash
# 初始化一个 30 秒测试项目
python scripts/init_project.py --root tests/project --profile short --duration 30 --shots 10 --segments 2 --force

# 结构门
python scripts/validate.py --shots tests/fixtures/validate_good/shots.csv --vo tests/fixtures/validate_good/vo.csv --beats tests/fixtures/validate_good/beats.csv --segments tests/fixtures/validate_good/segments.csv
python scripts/selftest.py

# timeline：5 镜 9 秒；2 句旁白，中间和结尾各有气口镜头
python scripts/timeline.py --shots templates/shots.csv --vo templates/vo.csv --vo-out tests/vo_report.csv --out tests/timeline.csv --target 9 --min-gap 0.4 --allow-single

# vo.csv -> SRT
python scripts/vo2srt.py --vo templates/vo.csv --out tests/subtitles.srt --max-chars 18

# 旁白版本差异
python scripts/vo_diff.py --old tests/fixtures/vo_v1.csv --new tests/fixtures/vo_v2.csv --out tests/vo_diff.md

# contact sheet：任选 2 条视频
python scripts/contact_sheet.py --clips /path/to/clips --out tests/review --frames 5

# cost：失败任务不计费
python scripts/cost_report.py --tasks tests/fixtures/tasks.json --out tests/cost.csv --summary tests/cost_summary.md --default-model MiniMax-H3
```

## 注意

- 失败任务不计费；
- 重复提交会按任务分别计费；
- `cost_report` 不做“去重”，只做如实汇总；
- 时间线以 `shots.csv` 为准，旁白以 `vo.csv` 为准，成本以 `tasks.json` 为准；不要手算。
