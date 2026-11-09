# Provider：MiniMax H3

## 第一次配置

没配过 H3，先看 `references/00_setup.md`：

1. 开放平台注册/实名/充值；
2. 创建 API Key；
3. `MINIMAX_API_KEY` 环境变量或 `~/.dsh/secrets/minimax_api_key.txt`；
4. 先跑一条 4 秒测试；
5. 记 `task_id`/费用；失败不计费。

不要把 Key 写进项目文件。

## 规格

- 768P：4–15 秒；
- H3-Max：5–15 秒，768P/480P；
- 图生视频：首帧/尾帧/首尾帧；
- 失败任务不计费。

## 连接参数

```text
base_url: https://api.minimax.cn
创建任务: POST /v2/video_generation
查询任务: GET  /v2/query/video_generation/{task_id}
model: MiniMax-H3 / MiniMax-H3-Max
resolution: 768P
duration: 4-15s
```

区域/模型/价格以官方控制台为准。

## 默认策略

- 一版制；
- H3 失败再换 H3-Max；
- 生成时长 = 成片 + 1 秒，最短 4 秒；
- 生成后丢弃音轨，除非只有环境音/人声。

## 提示词后缀

```text
保持首帧图中人物、服装、场景与光线不变。
<动作>；<表情>。
<镜头>。
最后停在结束姿态，保持不动。
只保留环境音效或人声，不要配乐、不要 BGM、不要旋律。
画面无文字。
```

## 常见失败

- 1033/system error：换 H3-Max 或降时长；
- 动作没发生：改提示词/换首帧；
- 人物变脸：加参考图/改侧影；
- 多手/穿模：重生成；
- 背景穿帮：裁切/换镜。

## 成本

按秒计费；记录 model/duration/status；失败不计费。
