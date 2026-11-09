# 分镜、节拍与时间线

## 1. 镜头表 `shots.csv`

```text
id,story_segment,scene_id,duration,shot_size,camera,scene,action,expression,vo_ids,anchor,first_frame,video,status,cost,notes,long_take
```

规则：

- **先有 `vo.csv`，再排镜头**；
- `story_segment` 是叙事段号，不是 H3 生成段；
- `scene_id` 是场景编号，`segments.csv` 必须引用同一个值；
- 有旁白的普通镜头 2–10 秒；无旁白的气口/插入镜头可短到 0.3 秒；
- `long_take=yes` 建议 5–15 秒（H3 单次上限约 15 秒）；
- 一镜只做一件事；
- 写清“动作真的发生”的可视动作，不写抽象情绪；
- 每镜标参考图/定妆；
- 转场先按硬切设计，再决定是否叠化；
- 画面切点不要求等于句子切点；用 J/L cut；
- `long_take=yes` 的长镜头可以一镜多段旁白，但每段必须完整在镜头内；普通镜头仍是一镜一段；
- 旧 15/16 列 `shots.csv` 仍能读；`story_segment` 缺失时兼容旧 `segment`，但新项目不再写 `segment`。

## 2. 节拍表 `beats.csv`

```text
beat_id,story_segment,kind,shot_id,vo_id,text,notes
```

- 每个节拍恰好一个 `shot_id`；
- 每个镜头至少一个节拍；每段旁白至少一个节拍；
- 节拍顺序跟镜头顺序一致；
- `beat.vo_id` 对应的 VO 必须真的覆盖这个 `shot_id`；
- `validate.py` 拦漏拍、重复、乱序、错配。

## 3. 生成段 `segments.csv`

```text
generation_id,scene_id,cut_order,shot_id,start,end,duration,keyframe,notes
```

- `generation_id` = 一次 H3 生成；一段 ≤15 秒，不跨场；
- 段内 `cut_order` 从 1 连续；
- 每一刀的 `start/end/duration` 必须等于 `shots.csv` 的累计时间；
- 每个 shot 只能出现一次；
- 全片切点必须从 0 到总长，无断档/重叠；
- `scene_id` 必须等于同镜 `shots.scene_id`；
- 每个切一张关键帧，默认检查文件存在；
- `export_h3.py` 用这些数据出多图对齐提示词。

## 4. 时间线

- 用秒，支持 4.4 这种小数；
- 段小计 + 全片总长；
- 目标时长 ±2 秒；
- 先生成静帧 animatic，再生成视频。

## 5. 连续性

- 人物年龄/服装/发型/眼镜；
- 场景年代、道具、光源方向；
- 动作接动作：上一镜结尾姿态 = 下一镜开始姿态；
- 轴线：对话/握手/球台，不要越轴。

## 6. 门禁

- G3：`beats` / `segments` / `shots` 三者对账；`validate.py` 通过；
- 总长对；每镜有 first_frame 和 status；
- `timeline.py --vo` 检查气口/密度/长镜头；
- 普通镜头的时长门由 `timeline.py --min-shot/--max-shot` 检查。

## 7. 片头卡

- G0 定 `opening_card / opening_seconds / opening_in_target`；
- G2.5 定标题文字 `opening_card.md`；
- G3 写 `0-1`：`static=yes`、无旁白、`first_frame=首帧/0-1_card.png`；
- `segments.csv` 写 `CARD`：`static=yes`，单切；
- G4 出图，16:9，与正片同画幅；文字逐字验收；
- G5 不做 H3；`export_h3.py` 跳过 static；
- G6 静态 hold，可做 1–2% 推近。
