# 成本记录

## 原则

- 按任务日志算，不靠记忆；
- 失败任务不计费，即使写了 `cost_cny` 也不计；
- 任务没有 `model` 时用 `--default-model`；
- 重试/重复提交单独列；
- 价格表可配置。

## 任务日志

```json
[{"id":"1-1","provider":"minimax_h3","model":"MiniMax-H3","duration":4,"status":"succeeded","cost_cny":2.0}]
```

## 汇总

`cost.csv`：

```text
id,provider,model,duration,status,cost_cny,note
```

`cost_summary.md`：

- 按批次；
- 按 provider；
- 按模型；
- 总秒数、总费用、重试费用。

## 门禁

- 每次批量生成后更新；
- 终检前和 `shots.csv` 对一遍。
