# Tests

手工冒烟 + 脚本自测。失败的 fixture 留在 `tests/fixtures/`。

## 0. Manifest

```bash
python tests/test_manifest.py
```

预期：`manifest ok: ai-documentary-production ...`  
它检查 frontmatter 字段，不替代 DSH loader。

## 1. 初始化

```bash
python scripts/init_project.py --root tests/project --profile short --duration 30 --shots 10 --segments 2 --force
```

预期生成：

```text
project.yaml / project.json / providers.json
shots.csv / vo.csv / beats.csv / segments.csv / h3_prompts.csv
fact_check.csv / source_list.csv
image_handoff.md / image_batch_request.md / vo_text_review.md / voice_audition.md / vo_lock.md / vo_review.md / v0_review.md
vo_versions/
首帧/ clips/ cut/ review/ music/ 字幕/ tasks/
```

## 2. 结构门

```bash
python scripts/validate.py --shots tests/fixtures/validate_good/shots.csv \
  --vo tests/fixtures/validate_good/vo.csv \
  --beats tests/fixtures/validate_good/beats.csv \
  --segments tests/fixtures/validate_good/segments.csv

python scripts/selftest.py
```

预期：

- `validate: ok`；
- `selftest: ok - 40 assertions`；
- 修改 `segments` 的 `1-1` 时长为 4s，validate 必须报 `does not match shots.csv`；
- 缺 beats/segments 时，validate 必须报 `missing`，不能用 `--allow-partial` 假装通过。

## 3. 模板

```bash
python scripts/validate.py --shots templates/shots.csv --vo templates/vo.csv \
  --beats templates/beats.csv --segments templates/segments.csv --allow-missing-files
```

预期：`validate: ok`；模板自己必须一致。  
模板的 `首帧/` 是占位路径，真实项目要放图。

## 4. 正常时间线 + 旁白

```bash
python scripts/timeline.py --shots templates/shots.csv --vo templates/vo.csv \
  --vo-out tests/vo_report.csv --out tests/timeline.csv --target 9 --allow-single
```

预期：

- 5 镜，9.00s；
- V01 跨 1-1/1-2，V02 在 1-4；
- 句间气口 1.5s / 0.5s；
- density 0.78；
- 1-3/1-5 是无旁白气口镜头。

## 5. 同一镜两段旁白：必须失败

```bash
python scripts/timeline.py --shots tests/fixtures/multi_shots.csv --vo tests/fixtures/multi_vo.csv
```

预期：先报 `vo overlap`；两段不重叠但落同一个普通镜头时，报同一镜多段或气口无切点。

## 6. 长镜头一镜多段：必须通过

```bash
python scripts/timeline.py --shots tests/fixtures/long_take_shots.csv \
  --vo tests/fixtures/long_take_vo.csv --allow-single
```

预期：1 个长镜头 10s，2 段旁白都在镜内，exit 0。

超尾必须失败：

```bash
python scripts/timeline.py --shots tests/fixtures/long_take_shots.csv \
  --vo tests/fixtures/long_take_bad_vo.csv
```

预期：`long take 1-1 contains V02 only partially`。

## 7. 气口没有切点：必须失败

```bash
python scripts/timeline.py --shots tests/fixtures/bad_gap_shots.csv \
  --vo tests/fixtures/bad_gap_vo.csv
```

预期：`gap ... has no shot cut` 或同镜多段，exit 1。

## 8. 字幕

```bash
python scripts/vo2srt.py --vo templates/vo.csv --out tests/subtitles.srt --max-chars 18
```

预期：2 条字幕；时间码正确；行长 ≤18 字。

## 9. 旁白 lint

```bash
python scripts/narration_lint.py --text templates/vo.csv --style lyrical
```

预期：模板旁白 findings 0。

## 10. 旁白差异

```bash
python scripts/vo_diff.py --old tests/fixtures/vo_v1.csv --new tests/fixtures/vo_v2.csv --out tests/vo_diff.md
```

预期：added/removed/text/timing 标记、总时长差、受影响镜号。

## 11. 成本

```bash
python scripts/cost_report.py --tasks tests/fixtures/tasks.json --out tests/cost.csv --summary tests/cost_summary.md --default-model MiniMax-H3
```

预期：失败任务不计费；只有 succeeded 计入。

## 12. H3 任务契约

```bash
python scripts/validate_tasks.py --tasks tests/fixtures/tasks_good.json --segments tests/fixtures/validate_good/segments.csv
```

预期：任务有 model/provider/resolution，generation_id 对得上，duration 4–15 整数。  
`tasks.json` 里没有 model 时必须失败。

## 13. 片头卡

```bash
python scripts/validate.py --shots tests/fixtures/static_card/shots.csv --vo tests/fixtures/static_card/vo.csv --beats tests/fixtures/static_card/beats.csv --segments tests/fixtures/static_card/segments.csv --project tests/fixtures/static_card/project.json
python scripts/export_h3.py --shots tests/fixtures/static_card/shots.csv --segments tests/fixtures/static_card/segments.csv --prompts templates/h3_prompts.csv --out tests/h3_static
```

预期：

- `0-1` 是 `static=yes`，无旁白；
- `CARD` 段单切，validate 通过；
- export 只输出 `S01/`，**不输出 `CARD/`**；
- 片头卡不排 H3 task。

## 14. H3 投产包

```bash
python scripts/export_h3.py --shots tests/fixtures/validate_good/shots.csv \
  --segments tests/fixtures/validate_good/segments.csv \
  --prompts templates/h3_prompts.csv --out tests/h3_package --allow-missing-files
```

预期：

- `tests/h3_package/S01/prompt.md` 多切段有 `Picture 2` 和 `[Shot 2] At 00:05.000`；
- 单切段使用 I2VA 固定对齐句；
- `manifest.json` 记录 cuts / keyframe；
- 段与 shots 不匹配时，export 必须 exit 1。

## 清理

`tests/project`、`tests/*.csv`、`tests/h3_package` 可随时删除；脚本不依赖它们。
