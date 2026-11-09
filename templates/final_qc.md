# 终检清单

## 规格

- [ ] 1920×1080
- [ ] 30fps（或 25fps）
- [ ] H.264 10–12Mbps
- [ ] 音频 48kHz
- [ ] −14 LUFS / TP ≤ −1.5

## 模型/图像

- [ ] `model_routing` / `image_mode` 与项目卡一致
- [ ] G4 切换前有 `image_handoff.md`
- [ ] agent 模式有用户明确批准；human 模式图片由用户出

## 旁白/字幕

- [ ] `vo.csv` 已用 `timeline.py --vo` 检查
- [ ] `vo_lock.md` 已填；当前旁白版本与 `vo_versions/` 一致
- [ ] `narration_lint.py` 跑过，长句/口号/无锚点意象已处理
- [ ] 旁白密度 ≤ 0.85；没有墙到墙
- [ ] 句间气口 ≥0.4s；普通/跨镜气口含切点，长镜头内部不需要
- [ ] 普通镜头最多一段旁白；长镜头多段全部在镜内
- [ ] `vo2srt.py` 已生成字幕；行长 ≤ 18 字
- [ ] 字幕不溢出/不压脸
- [ ] 无黑帧/跳帧
- [ ] 音画同步
- [ ] credits 完整
- [ ] 资料照片来源
- [ ] AI 声明
- [ ] 文件命名规范

## 交付包

- [ ] final.mp4
- [ ] subtitles.srt
- [ ] vo.wav
- [ ] vo.csv
- [ ] music/A-E.wav
- [ ] cue_sheet.csv
- [ ] credits.md
- [ ] source_list.csv
- [ ] fact_check.csv
