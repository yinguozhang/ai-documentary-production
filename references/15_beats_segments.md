# 节拍、段/切/关键帧与门禁

## 1. 节拍表 `beats.csv`

节拍是**故事最小单位**，不是音乐节拍，也不是旁白句子。

```text
beat_id,story_segment,kind,shot_id,vo_id,text,notes
B01,1,action,1-1,V01,柜台后算题,
B02,1,action,2-1,V02,把论文装进信封,
```

规则：

- 每个节拍**恰好**被一个 `shot_id` 认领；
- 每个非 `static` 镜头至少一个节拍；`static=yes` 的片头卡可以没有 beat；
- 每段旁白至少一个节拍；
- 一个旁白可以跨多个节拍，在每行重复同一个 `vo_id`；
- 节拍顺序必须跟镜头顺序一致；
- 漏拍、重复、乱序由 `validate.py` 拦。

### 为什么

它回答的是“故事有没有漏”，不是“镜头够不够美”。

- 没有节拍表：可能拍了 7 个漂亮镜头，但“他为什么被清华发现”没拍；
- 有节拍表：每个故事点都有镜头，每个镜头都有存在理由。

## 2. 段 / 切 / 关键帧 `segments.csv`

```text
generation_id,scene_id,cut_order,shot_id,start,end,duration,keyframe,notes
S01,1,1,1-1,0,5,5,首帧/1-1_first.png,单切段
S02,1,1,1-2,5,9,4,首帧/1-2_first.png,段内第 1 切
S02,1,2,1-3,9,15,6,首帧/1-3_first.png,段内第 2 切
```

- **段** = 一次 H3 生成，≤15 秒，不跨场；
- **切** = 段内的一次剪辑点，2–8 秒（纪录片可比短剧宽）；
- **关键帧** = 每切一张构图锚图；第 1 切钉 0.00 秒，后续钉自己的切点；
- `scene_id` 必须等于同镜 `shots.scene_id`；
- 每个 shot 只能出现在一个 generation；
- 每刀起止必须等于 `shots.csv` 的累计时间；切序连续、段总长 ≤15 秒；
- `validate.py` 拦越界、错位、断档、重复、跨场。

### H3 多图对齐

`export_h3.py` 按段生成：

```text
Picture 1 aligns with 0.00s
Picture 2 aligns with 6.50s

[Shot 1] ...
[Shot 2] At 00:06.500, ...
```

单切段用 I2VA 固定对齐句；多切段用多图对齐。输出：

```text
h3_package/
├── S01/prompt.md
├── S02/prompt.md
└── manifest.json
```

## 3. validate 与 selftest

| | validate | selftest |
|---|---|---|
| 检查对象 | 当前项目 | 检查器本身 |
| 输入 | shots/vo/beats/segments | 固定好/坏样例 |
| 失败意味着 | 项目不能过 | 规则/代码坏了 |
| 调模型 | 否 | 否 |

```bash
python scripts/validate.py --shots shots.csv --vo vo.csv \
  --beats beats.csv --segments segments.csv --project project.json

# G5 前再查关键帧文件
python scripts/validate.py --shots shots.csv --vo vo.csv \
  --beats beats.csv --segments segments.csv --strict-files

python scripts/selftest.py
```

`validate.py` 管结构；`timeline.py --vo` 管气口/密度/长镜头。两个都跑，不互相替代。

## 4. 常见失败

```text
shot 1-2: no beat claims it
vo V09: no beat claims it
beats: duplicate beat_id B03
beat B04: beats are out of shot order
segment S02: 16.20s exceeds max 15.00s
segment S02: cut 2 must start at previous cut end
segment S02: shot 1-2 appears more than once
segment S02: cuts must stay in one scene
segment S02: keyframe not found: 首帧/1-2_first.png
```

看到这些，不要绕过门；先改数据，再重跑。

## 5. 片头卡

```text
# shots.csv
0-1,0,1,3,todo,no,,首帧/0-1_card.png,yes,片头标题卡
# segments.csv
CARD,1,1,0-1,0,3,3,首帧/0-1_card.png,yes,片头静帧
```

- `static=yes`：静态卡，不做 H3；
- 必须单切；
- `keyframe` 必须等于 `shots.first_frame`；
- `export_h3.py` 跳过 static；
- `validate_tasks.py` 不要求 static 段有 H3 task；
- 片头卡时长从目标时长里扣，或在 G0 明确加总长。
