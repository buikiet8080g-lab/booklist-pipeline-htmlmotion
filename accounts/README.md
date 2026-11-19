# accounts · 账号风格体系

一个账号的风格 = **5 层固定组合**（`visual_style_profile`）。不是「整片套一张风格配方」——那是 §16.2 明确排除的做法。

| 层 | 字段 | 取值 | 在哪生效 |
|---|---|---|---|
| 1 底色板 | `palette` | huashu 8 套之一（`paper/poster/ink/navy/bauhaus/snow/wood/chalk`） | `shot_plan.py --theme`，写进每镜 `theme` |
| 2 字体对 | `font_pair` | 正文 `PuHui-*`（思源黑）；引文 `LXGWWenKai-500`（文楷衬线） | 语法内置；引文由 `bl_quote` 固定 |
| 3 语法组合 | `grammar_mix` | 固定 2–3 种 + 权重 | `sheet.json` 选型 + `shot_plan` 自动分配 |
| 4 字幕样式 | `subtitle_style` | 字号 / 描边 / `MarginV` / 字体 | `assemble.py` 读账号 md 的这段 |
| 5 背景媒材（可选） | `recipe_accent` | 某张风格配方的纹理，**只在片头卡/引文纹理/转场**用，`--alpha` 合成 | 目前不启用（第一期不做风格纹理） |

## 已建档

| 账号 | palette | grammar_mix | 字幕 | 背景媒材 |
|---|---|---|---|---|
| `family-education-parent-reader` | `wood` 暖木 | `bl_cover_hero 30% + y5 40% + bl_quote 20% + y2 10%` | 46px / 描边 3 / MarginV 110 | 无（保持干净） |
| `traditional-culture-reader` | `paper` 纸本 | `bl_quote 40% + y2 30% + bl_cover_hero 20% + y5 10%` | 44px / 描边 3 / MarginV 110 | 无（预留 `50_ma_yuan` 引文纹理，未启用） |

新增账号：复制一份 md，改 `visual_style_profile` 五层 + MiMo 声线，**不要新造色板**（要新色板走 §16.5 的四步，0.5–1 天/风格）。
