# 05 分镜计划

- 音轨：`/root/.pi/agent/skills/booklist-pipeline-htmlmotion/samples/t21-30s/audio/main-voice.wav` · 25.60s · 5 镜 · 色板 `wood`
- plan.json：`metadata/plan.json`

| # | 起 | 秒 | 语法 | 这一镜在做什么（物 + 动词） | 屏上字 | 书封 |
|---|---|---|---|---|---|---|
| 001-1 | 0.0s | 4.6 | `bl_cover_hero` | 书封升起，一句话压上去 | 被讨厌的勇气 | ✓ |
| 002-1 | 4.6s | 4.6 | `y5_kinetic_type` | 主词砸入，辅句升起 | 可你忍住的那股劲 |  |
| 003-1 | 9.2s | 6.6 | `bl_quote` | 引文逐行写出，出处落定 | 把孩子的课题还给孩子 |  |
| 004-1 | 15.8s | 5.1 | `y5_kinetic_type` | 主词砸入，辅句升起 | 先看见情绪 |  |
| 005-1 | 21.0s | 4.6 | `bl_cover_hero` | 书封升起，一句话压上去 | 被讨厌的勇气 | ✓ |

## 闸门
下一步必须跑 `ours/lint_spec.py`：cue 白名单、边缘半字、文本截断、配比四条全绿才允许渲染。
任何一镜改文案后，只重跑受影响的镜（`render_batch.py --only <id>`），不重渲全片。
