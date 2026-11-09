# 第一次使用：先把 H3 配好

> 没配过 MiniMax H3，不要直接进 G5。先过这 6 关。

## 1. 账号和 Key

1. 在 MiniMax 开放平台注册/登录；
2. 完成实名认证和充值（H3 按秒计费）；
3. 创建 API Key；
4. 确认 Key 所属区域和 `base_url` 一致。

本项目默认中国区：

```text
base_url: https://api.minimax.cn
```

768P 约 ¥0.5/秒（以控制台为准）；4 秒测试约 ¥2。

如果 Key 来自其他区域，按控制台文档换 `base_url`，不要混用。

> 控制台地址、模型名、价格以官方文档为准；本文只写配置方法。

## 2. 存 Key（不要写进代码）

### 方式 A：环境变量（推荐）

Windows PowerShell：

```powershell
$env:MINIMAX_API_KEY = "你的 Key"
```

macOS / Linux：

```bash
export MINIMAX_API_KEY="你的 Key"
```

临时设置只对当前终端有效；要持久化，写进系统环境变量或 shell 配置。

### 方式 B：密钥文件

Windows：

```powershell
New-Item -ItemType Directory -Force "$HOME\.dsh\secrets"
Set-Content "$HOME\.dsh\secrets\minimax_api_key.txt" "你的 Key" -NoNewline
```

macOS / Linux：

```bash
mkdir -p ~/.dsh/secrets
printf '%s' '你的 Key' > ~/.dsh/secrets/minimax_api_key.txt
chmod 600 ~/.dsh/secrets/minimax_api_key.txt
```

规则：

- 不截图、不贴群、不进 git；
- 不写进 `project.json` / `shots.csv` / 提示词；
- `.gitignore` 加 `**/secrets/**`、`.env`；
- 日志里只显示“已配置/未配置”，不打印 Key。

## 3. 选模型和参数

```yaml
video:
  provider: minimax_h3
  base_url: https://api.minimax.cn
  api_key_env: MINIMAX_API_KEY
  model: MiniMax-H3
  fallback_model: MiniMax-H3-Max
  resolution: 768P
  duration: 4-15
  takes: 1
```

- 默认 `MiniMax-H3`；
- 失败再换 `MiniMax-H3-Max`；
- 768P；
- 生成时长 = 成片 + 1 秒，最短 4 秒；
- 一版制，不盲目重跑。

## 4. 先跑一条 4 秒测试

不要一上来批量 10 条。

> 下面的 `tools/minimax_client.py` 是本项目自带工具；单独分发 skill 时没有 `tools/`，用官方 SDK 或等价 curl 即可，参数相同。

```bash
python tools/minimax_client.py video \
  --prompt "测试：人物坐在书桌前，只保留环境音效或人声，不要配乐、不要 BGM、不要旋律。画面无文字。" \
  --first "首帧/1-1_first.png" \
  --duration 4 \
  --resolution 768P \
  --model MiniMax-H3
```

记下返回的 `task_id`，轮询：

```bash
python tools/minimax_client.py query --task-id <task_id>
```

检查：

- 状态是否 `succeeded`；
- 文件能否下载；
- 时长/分辨率；
- 音轨是否只有环境音/人声，没有 BGM；
- 费用是否按秒。

4 秒测试通过，再进批量。

## 5. 记录任务和费用

每条任务至少记：

```json
{
  "id": "1-1",
  "model": "MiniMax-H3",
  "duration": 4,
  "status": "succeeded",
  "task_id": "...",
  "file": "clips/1-1.mp4",
  "cost_cny": 2.0
}
```

然后：

```bash
python scripts/cost_report.py --tasks tasks.json --default-model MiniMax-H3
```

失败任务不计费，即使写了 `cost_cny` 也不计。

## 6. 常见错误

| 现象 | 处理 |
|---|---|
| 401/403 | Key 错、过期、区域/base_url 不匹配 |
| 1033 / system error / context ir | 换 H3-Max，或缩短时长/换首帧；失败通常不计费 |
| 一直 running | 用 task_id 查询，不要重复提交 |
| 人物变脸/多手 | 换首帧或重生成，不要靠剪辑硬补 |
| 视频自带 BGM | 丢弃整条音轨；提示词明确“不要配乐、不要 BGM、不要旋律” |
| 费用对不上 | 用 `tasks.json` 记账，不靠记忆 |

## 7. 没有 H3 怎么办

- 先问用户是否已有 Key/额度；
- 没有就换视频 provider，或先做 animatic；
- 不要假装能生成，也不要替用户开账号/充值；
- 不要调用图片 API；图片仍由用户 GPT 出。

## 8. 配置检查

- [ ] Key 已配置，且未进代码/日志；
- [ ] `base_url` 与 Key 区域一致；
- [ ] 模型名 `MiniMax-H3` 可用；
- [ ] 4 秒测试成功；
- [ ] 任务日志/cost 表已建；
- [ ] 失败不计费规则已知；
- [ ] 图片仍由用户出。
