# 语法预设（05 只准从这些里选）

## 白名单（5 个）

| grammar | scene_type | 承载 | 一镜 | 每片 | cues（白名单） |
|---|---|---|---|---|---|
| `bl_cover_hero` | kit | 书籍导入、书名/作者、CTA | 5–8s | 3–5 次 | `cover` / `text` |
| `bl_quote` | kit | 书中原文引文 | 7–12s | 2–4 次 | `quote` / `source` |
| `y5_kinetic_type` | kit | 要点、清单、金句、数字 | 5–15s | 主力 | `title` / `point` / `number` / `highlight` |
| `t3_finance_chart` | kit | 数据、对比、趋势 | 6–8s | 按需 | `title` / `bar` / `line` / `candle` / `highlight` / `number` |
| `y2_vox` | kit | 照片/书页实拍 + 标注 | 6–10s | ≤5 镜 | `image` / `clip` / `title` / `point` / `highlight` |

## 可选（默认不启用）

| grammar | 为什么可选 | 用法约束 |
|---|---|---|
| `y3_whiteboard` | 竖屏中段留白 30–40%（白板本身留白） | 每片 ≤1 镜；≥4 条要点 |
| `t2_keynote_ui` | 卡片内留白偏多，画面偏「发布会」 | 1–3 张卡一屏；适合步骤/功能 |

## 禁用

`y1_kurzgesagt` / `y4_storytime` / `y6_presenter_explainer` / `t1_3b1b`：
需要角色 rig 或世界画布相机，与竖屏书单号不符；其中 `y4` 的角色走代码画的 Q 版小人，直接踩「一眼 AI 味」红线。

## 兜底

`free_scene`（自研 HTML）：≤10% 镜数、必须写 `free_scene_reason`、必须过 §6.5 与 P3 检查。
**五个语法都表达不了**（特殊版式、品牌卡、自定义图表）才用；它不是「模型想自由发挥」的出口。

## 选型顺序（决策树）

1. 这一镜要观众记住的是**书**吗？→ `bl_cover_hero`
2. 是**书里的原话**吗？→ `bl_quote`
3. 是**数字/趋势/对比量**且有真实数据？→ `t3_finance_chart`
4. 有**真实素材**（照片/书页实拍）要解释吗？→ `y2_vox`
5. 其余（要点、方法、清单、金句）→ `y5_kinetic_type`
6. 以上都不合适，且能写清为什么 → `free_scene`
