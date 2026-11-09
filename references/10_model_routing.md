# 模型路由：DeepSeek 管文字，GPT 管像素

## 两条轴，不要混

```yaml
model_routing: hybrid   # hybrid / gpt_only / codex_deepseek
image_mode: human       # human / agent
```

- `model_routing`：这一阶段用哪个模型；
- `image_mode`：谁真正出图。

**换模型 ≠ 换工具。**  
切回 GPT 不等于自动有图像工具；切到 DeepSeek 也不等于不能读项目文件。

---

## 默认路线：hybrid

| 阶段 | 默认模型 | 做什么 |
|---|---|---|
| G0 Brief | Codex + DeepSeek | 问清需求、写 brief、算时长/预算 |
| G1 研究/事实 | Codex + DeepSeek | 资料整理、fact_check |
| G2 旁白 | Codex + DeepSeek | 写旁白、vo.csv、气口 |
| G3 分镜 | Codex + DeepSeek | 排镜头、提示词、timeline |
| G4 首帧 | **GPT** | 出图/审图；`image_mode` 决定谁出 |
| G5 视频 | Codex + DeepSeek | 任务表、下载、成本、检查 |
| G6 粗剪/字幕 | Codex + DeepSeek | 文件、SRT、时间线 |
| G7 配乐 | Codex + DeepSeek | cue sheet、渲染脚本 |
| G8 终检 | Codex + DeepSeek | ffprobe、QC；需要看图时临时切 GPT |

原则：

> **文字和文件用 DeepSeek，像素和视觉用 GPT。**  
> 按阶段切，不要每张图切一次。

---

## 两种 image_mode

### human（默认）

1. agent 写完整提示词、尺寸、参考图、文件名；
2. 用户切到 GPT 网页/客户端出图；
3. 用户把图放回 `首帧/`；
4. agent 验收、裁切、调色、记录。

适合：

- 其他智能体没有图像工具；
- 项目规则要求图片由用户出；
- 比赛/版权要求人工确认。

### agent（需明确开启）

1. Codex 切到 GPT，并确认图像工具可用；
2. 先出角色卡/风格样张；
3. 用户确认后批量；
4. agent 记录任务、费用、失败重试；
5. 仍然要人工抽检。

适合：

- Codex 里确实有图像工具；
- 用户明确批准 `image_mode=agent`；
- 项目规则允许 agent 调图像工具。

> 本项目 `AGENTS.md` 目前仍是“图片一律用户 GPT”；  
> 在规则没改之前，只使用 `human`，不要偷偷切 `agent`。

---

## 切换前：先写 handoff

模型切换会丢“对话里的细节”，但不会丢项目文件。  
G4 前写 `templates/image_handoff.md` 的副本：

```text
image_handoff.md
```

最少写清：

- 当前阶段/G4；
- 已锁定的 `script.md`、`vo.csv`、`shots.csv`；
- 本轮镜号、文件名、尺寸；
- 统一风格、角色锚点、参考图；
- 提示词在哪；
- 验收标准；
- 不要改什么；
- 输出目录；
- 成本/任务记录。

切换后先读 handoff，不靠聊天记忆。

---

## 切换检查表

- [ ] 客户端是否保留同一会话历史？
- [ ] 切回 GPT 后，图像工具是否可用？
- [ ] GPT 是否能看见之前的参考图/附件？
- [ ] `script.md` / `vo.csv` / `shots.csv` 已锁定？
- [ ] `image_handoff.md` 已写？
- [ ] 文件名/目录规则已写？
- [ ] 费用/任务记录方式已写？

### 三步测试

1. DeepSeek 说“记住 42”；
2. 切 GPT 问“刚才记住什么”；
3. 切回 DeepSeek 问“42 是什么”。

三步都记得，才是同一会话；否则每次切换都从项目文件恢复。

---

## 回退

| 情况 | 回退 |
|---|---|
| Codex 接不了 DeepSeek | `gpt_only` |
| GPT 没有图像工具 | `image_mode=human` |
| 切换后会话丢失 | 以项目文件 + handoff 为准，不依赖记忆 |
| GPT 看不了图 | 留在 GPT 审图，或人工验收 |
| 费用超预算 | 回 DeepSeek 做文字，减少 GPT 调用 |

---

## 常见错误

- **以为接 DeepSeek API 就能生图**：DeepSeek chat 不产图，图靠图像工具；
- **以为切回 GPT 就自动有图**：模型和工具是两层；
- **每张图切一次模型**：按 G4 阶段切，减少上下文丢失；
- **切换后重写旁白**：G2 已锁，不要在 G4 后改脚本；
- **靠聊天记忆交接**：写 `image_handoff.md`；
- **在 `agent` 模式不记录费用**：图像工具也要计费/限额。
