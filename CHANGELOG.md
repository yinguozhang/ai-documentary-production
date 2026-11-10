# Changelog

## 1.7.0 — 2026-11-10

### 新增

- 剧本/旁白加入“冷读者测试”：遮住标题、图片、人物名和画面，只读旁白，必须能回答“他是谁、做过什么、为什么值得看”。
- “他是谁”“做过什么”两条必须答出；“为什么值得看”是加分。答不出先补具体动作/身份/因果，不补形容词。
- 同步到 `SOP.md` G2 和 `templates/vo_text_review.md`。


## 1.6.0 — 2026-11-06

### 修复

- `validate.py --project` 现在检查 G0 片头卡决定：`opening_card=static` 必须有 `0-1 static=yes`、`CARD` 单切、时长等于 `opening_seconds`。
- `timeline.py --project` 同步检查片头卡；`opening_in_target` 会校验总时长 = 目标（或在目标上另加片头秒数）。
- `opening_card.md` 必须有主标题和逐字确认；否则 static 项目不通过。
- `init` 生成的 README 把片头卡步骤移到 G2.5，不再放在 v0 之后。
- `image_batch_request.md` 的 `0-1` 行只在 `opening_card=static` 时由 init 插入；none 时没有这一行。
- `.gitignore` 补 `tests/h3_static/`。
- selftest 扩到 40 项，覆盖无卡但 static、时长不符、总时长不符。


## 1.5.0 — 2026-11-06

### 新增

- 片头卡：G0 问 `opening_card none/static`、秒数、是否算目标时长；G2.5 定标题文字；G3 写 `0-1 static=yes`；G4 出图；G5 不做 H3。
- `templates/opening_card.md`；`init_project.py` 支持 `--opening-card/--opening-seconds/--opening-in-target`。
- `shots.csv` / `segments.csv` 增加 `static` 字段；`validate.py` 校验 static 与单切；`export_h3.py` 跳过 static；`validate_tasks.py` 不要求 static 段有 H3 task。
- `tests/fixtures/static_card/` 覆盖片头卡；selftest 34 项。


## 1.4.0 — 2026-11-06

### 修复

- `validate.py` 强制 `segment.keyframe == shots.first_frame`；G3 默认不查文件，G5 `--strict-files` 才查。
- `validate.py` 强制 `beat.story_segment == shot.story_segment`。
- templates 补 5 张 320×180 占位首帧，默认 validate 通过；新增 `templates/README.md` 说明不可直接投产。
- 新增 `validate_tasks.py`：检查 H3 task 的 `generation_id/provider/model/resolution/duration/status/prompt/first_frames`，duration 4–15 整数。
- `h3_tasks.json` 补 `provider/model/resolution/cost_cny`，与 `tasks.json` 契约一致。
- `metadata.requires` 补 Pillow；`SKILL.md` 的 tasks 示例改为 `generation_id`。
- selftest 扩到 31 项，覆盖错误 keyframe、story_segment 漂移、任务契约。

### 边界

- 角色锚点、场景/道具锚点仍未做。
- DSH loader 仍未实测；manifest 不是 loader 测试。
- `install.sh` 仍未在 WSL 实测；`install.ps1` 已测。


## 1.3.0 — 2026-11-06

### 修复

- 统一命名：`shots.csv` 用 `story_segment` + `scene_id`，`segments.csv` 用 `generation_id` + `scene_id`，不再让“段”双关。
- `validate.py` 对账 `segments` ↔ `shots`：每切起止/时长必须一致，全片必须无断档/无重叠。
- `validate.py` 校验 `beat.shot_id` 与 `vo.shot_ids` / `shot.vo_ids` 的归属。
- `validate.py` 默认要求 beats/segments；缺结构时不再打印 ok，只有 `--allow-partial` 才跳过。
- keyframe 默认检查文件存在；`--allow-missing-files` 才跳过。
- `export_h3.py` 必须先通过 `--shots` 对账；坏段不再导出。
- 新增 `validate_tasks.py`：检查 H3 任务 JSON 的 model/provider/resolution/整数时长/段号。
- keyframe 必须等于 `shots.first_frame`；story_segment 必须与镜头一致。
- templates 补 5 张占位首帧，默认 validate 通过；`templates/README.md` 说明不可直接投产。
- templates 全部重建，自己先通过 validate。
- 根目录测试残留 `timeline.csv`、`__pycache__` 清理；新增 `.gitignore`。
- `test_manifest.py` 检查 allowed-tools/triggers/metadata；`selftest.py` 扩到 31 项，覆盖段/镜错位、缺结构、模板和 H3 导出。
- tests/README 改成只列实际存在的 fixture。

### 变更

- `timeline.py` 增加 `story_segment` 兼容；普通有旁白镜头 2–10s，无旁白插入 ≤10s，long_take 5–15s。
- `init_project.py` 生成新表头。

### 边界

- 角色锚点、场景/道具锚点仍未做（按用户要求）。
- DSH loader 仍未实测；manifest 不是 loader 测试。

## 1.2.0 — 2026-11-06

### 新增

- `beats.csv`：故事节拍表，每个节拍必须恰好被一个镜头认领；每个镜头、每段旁白都要有节拍覆盖。
- `segments.csv`：段 → 切 → 关键帧结构；一段一次 H3 生成，段内多切，每切一张关键帧。
- `schemas/`：`shots` / `vo` / `beats` / `segments` 的 JSON Schema 契约。
- `scripts/validate.py`：项目门，检查 schema、节拍认领、镜头覆盖、段时长/切序/连续性。
- `scripts/selftest.py`：工具门，用“应该失败”的样例证明 validate 真的会拦。
- `scripts/export_h3.py`：按段导出多图对齐 H3 提示词 + `manifest.json` 投产包。
- `scripts/install.ps1` / `scripts/install.sh`：软链安装，软链失败时 Windows 回退复制。
- `LICENSE` / `NOTICE`：Apache-2.0。

### 变更

- `SKILL.md` 增加 `allowed-tools`、`triggers`、`metadata`；版本升到 1.2。
- `init_project.py` 自动创建 `beats.csv`、`segments.csv`、`h3_prompts.csv` 表头。
- `README.md` / `scripts/README.md` 增加新命令和文件约定。

### 边界

- 不改角色锚点、角色参考图链、场景/道具锚点；这些由用户另行决定。
- `validate.py` 不替代 `timeline.py --vo`：前者管结构契约，后者管气口/密度/长镜头时间。
- `export_h3.py` 不调用任何 API，只写提示词和清单。
